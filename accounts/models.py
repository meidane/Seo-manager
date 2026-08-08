"""مدل‌های هویت و سازمان (چندشرکتی / multi-tenant — مقدمات).

سلسله‌مراتب: **Organization (شرکت/کسب‌وکار) → Team → زیرمجموعه (Team.parent)**.
عضویتِ کاربر در سازمان با نقش، در `Membership`؛ عضویتش در تیم/زیرمجموعه در
`TeamMembership`. فیلد قدیمیِ `User.team` برای سازگاری می‌ماند ولی منبعِ اصلی
عضویت، جدول‌های جدیدند.

نکته: در این فاز فقط «مقدمات» است — داده‌ی اپ‌های دیگر (Project/Task/…) هنوز به
سازمان اسکوپ نشده‌اند؛ آن مرحله در نقشه‌ی راه (docs/PLATFORM.md) فاز بعدی است.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify

from .permissions import MEMBER, ROLE_CHOICES, role_can, role_perms


class Organization(models.Model):
    """یک شرکت/کسب‌وکار — بالاترین سطحِ جداسازی داده (tenant)."""

    name = models.CharField('نام شرکت/کسب‌وکار', max_length=150)
    slug = models.SlugField('شناسه', max_length=160, unique=True, blank=True)
    is_active = models.BooleanField('فعال', default=True)
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)

    class Meta:
        verbose_name = 'سازمان'
        verbose_name_plural = 'سازمان‌ها'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name, allow_unicode=True) or 'org'
            slug, i = base, 1
            while Organization.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                i += 1
                slug = f'{base}-{i}'
            self.slug = slug
        super().save(*args, **kwargs)

    def root_teams(self):
        return self.teams.filter(parent__isnull=True)


class Team(models.Model):
    """تیم؛ با `parent` می‌تواند زیرمجموعه باشد (چند سطح مجاز)."""

    organization = models.ForeignKey(
        Organization, verbose_name='سازمان', on_delete=models.CASCADE,
        related_name='teams', null=True, blank=True)
    parent = models.ForeignKey(
        'self', verbose_name='تیم والد', on_delete=models.CASCADE,
        null=True, blank=True, related_name='subteams')
    name = models.CharField('نام تیم', max_length=120)
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)

    class Meta:
        verbose_name = 'تیم'
        verbose_name_plural = 'تیم‌ها'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def is_subgroup(self):
        return self.parent_id is not None


class User(AbstractUser):
    """کاربر سیستم. عضویت‌های سازمان/تیم از طریق Membership/TeamMembership است."""

    # فیلد قدیمی (deprecated) — برای سازگاری با کدهای فعلی نگه داشته شده
    team = models.ForeignKey(
        Team, verbose_name='تیم (قدیمی)', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='legacy_members')
    avatar = models.ImageField('آواتار', upload_to='avatars/', null=True, blank=True)

    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'

    def __str__(self):
        return self.get_full_name() or self.username

    def default_membership(self):
        """عضویتِ فعالِ اصلی (سازمانِ جاری). فعلاً اولین عضویتِ فعال."""
        return (self.memberships.filter(is_active=True)
                .select_related('organization').first())


class Membership(models.Model):
    """عضویت یک کاربر در یک سازمان، همراه نقش و وضعیت فعال."""

    user = models.ForeignKey(User, verbose_name='کاربر', on_delete=models.CASCADE, related_name='memberships')
    organization = models.ForeignKey(Organization, verbose_name='سازمان', on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField('نقش', max_length=12, choices=ROLE_CHOICES, default=MEMBER)
    is_active = models.BooleanField('فعال', default=True)
    joined_at = models.DateTimeField('زمان عضویت', auto_now_add=True)

    class Meta:
        verbose_name = 'عضویت سازمانی'
        verbose_name_plural = 'عضویت‌های سازمانی'
        unique_together = ('user', 'organization')
        ordering = ['-joined_at']

    def __str__(self):
        return f'{self.user} @ {self.organization} ({self.get_role_display()})'

    def can(self, perm: str) -> bool:
        return self.is_active and role_can(self.role, perm)

    @property
    def perms(self) -> set:
        return role_perms(self.role) if self.is_active else set()


class TeamMembership(models.Model):
    """عضویت یک کاربر در یک تیم/زیرمجموعه."""

    user = models.ForeignKey(User, verbose_name='کاربر', on_delete=models.CASCADE, related_name='team_memberships')
    team = models.ForeignKey(Team, verbose_name='تیم', on_delete=models.CASCADE, related_name='memberships')
    joined_at = models.DateTimeField('زمان عضویت', auto_now_add=True)

    class Meta:
        verbose_name = 'عضویت تیمی'
        verbose_name_plural = 'عضویت‌های تیمی'
        unique_together = ('user', 'team')

    def __str__(self):
        return f'{self.user} → {self.team}'
