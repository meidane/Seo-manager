"""مدل‌های هویت و سازمان (چندشرکتی / multi-tenant — مقدمات).

سلسله‌مراتب: **Organization (شرکت/کسب‌وکار) → Team → زیرمجموعه (Team.parent)**.
عضویتِ کاربر در سازمان با نقش، در `Membership`؛ عضویتش در تیم/زیرمجموعه در
`TeamMembership`. فیلد قدیمیِ `User.team` برای سازگاری می‌ماند ولی منبعِ اصلی
عضویت، جدول‌های جدیدند.

نکته: در این فاز فقط «مقدمات» است — داده‌ی اپ‌های دیگر (Project/Task/…) هنوز به
سازمان اسکوپ نشده‌اند؛ آن مرحله در نقشه‌ی راه (docs/PLATFORM.md) فاز بعدی است.
"""
import hashlib
import secrets

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify

from .permissions import MEMBER, ROLE_CHOICES, ROLE_PERMS, role_perms


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
    phone = models.CharField('شماره تماس', max_length=20, blank=True, db_index=True)

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
        return f'{self.user} @ {self.organization} ({self.role})'

    @property
    def perms(self) -> set:
        """مجموعه‌ی دسترسی‌ها؛ اول از رکوردِ Role سازمان، وگرنه پیش‌فرض ثابت.
        مالک همیشه '*' (همه) دارد."""
        if not self.is_active:
            return set()
        r = Role.objects.filter(organization_id=self.organization_id, key=self.role).first()
        if r:
            return {'*'} if r.key == 'owner' else set(r.perms or [])
        # fallback اگر Role هنوز seed نشده باشد
        return {'*'} if self.role == 'owner' else role_perms(self.role)

    def can(self, perm: str) -> bool:
        p = self.perms
        if perm == 'own_tasks_only':
            # این یک محدودیت است نه یک قابلیت — با ویلدکارد «همه‌چیز» مشتق نمی‌شود،
            # وگرنه مالک (که perms اش لفظاً {'*'} است) به‌اشتباه محدود به تسک‌های
            # خودش می‌شود و چون Colleagueِ وصل ندارد، هیچ تسکی نمی‌بیند.
            return perm in p
        return '*' in p or perm in p

    @property
    def role_label(self):
        r = Role.objects.filter(organization_id=self.organization_id, key=self.role).first()
        return r.name if r else dict(ROLE_CHOICES).get(self.role, self.role)


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


class Role(models.Model):
    """نقشِ قابل‌تعریف per سازمان (ساده). نقش‌های پیش‌فرض `is_builtin=True`اند و هر
    سازمان می‌تواند نقشِ سفارشی با ترکیبِ دلخواهِ دسترسی‌ها بسازد.

    `key` شناسه‌ی نقش داخلِ سازمان است (`Membership.role` به همین اشاره می‌کند)؛
    `perms` فهرست کلیدهای دسترسی (permissions.PERMS). نقشِ `owner` همیشه همه‌ی
    دسترسی‌ها را دارد (در `Membership.perms` هندل شده)."""

    organization = models.ForeignKey(Organization, verbose_name='سازمان', on_delete=models.CASCADE, related_name='roles')
    key = models.CharField('کلید', max_length=32)
    name = models.CharField('نام نقش', max_length=60)
    perms = models.JSONField('دسترسی‌ها', default=list, blank=True)
    is_builtin = models.BooleanField('پیش‌فرض', default=False)

    class Meta:
        verbose_name = 'نقش'
        verbose_name_plural = 'نقش‌ها'
        unique_together = ('organization', 'key')
        ordering = ['name']

    def __str__(self):
        return f'{self.name} @ {self.organization}'


class Invite(models.Model):
    """دعوت‌نامه‌ی در انتظار — عضویتِ فوری نیست. تنها راهِ افزودنِ فرد، شماره‌ی تماس است
    (`colleagues.views.colleague_grant_access`، از پروفایلِ همکار)؛ ما هرگز نام‌کاربری/رمز
    نمی‌سازیم — ساختِ حساب کاملاً دستِ خودِ فرد است.

    دو حالت: (۱) شماره‌ای که از قبل کاربر دارد → `user` بلافاصله ست می‌شود. (۲) شماره‌ای
    که هنوز حساب ندارد → `user=None` و `phone` نگه داشته می‌شود؛ وقتی آن شماره در
    `/signup/` ثبت‌نام کند، `views.signup` به‌جای ساختِ سازمانِ تازه همین دعوت را با
    حساب تازه‌ساز وصل می‌کند (`claim`). در هر دو حالت، فرد بعدِ لاگین بالای هر صفحه
    (بدونِ سازمان → `/invites/`، با سازمان → بنر) قبول/رد می‌کند."""

    PENDING = 'pending'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    STATUS_CHOICES = [(PENDING, 'در انتظار'), (ACCEPTED, 'پذیرفته‌شده'), (REJECTED, 'ردشده')]

    organization = models.ForeignKey(Organization, verbose_name='سازمان', on_delete=models.CASCADE, related_name='invites')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='کاربر', on_delete=models.CASCADE,
        null=True, blank=True, related_name='invites',
    )
    phone = models.CharField(
        'شماره تماس', max_length=20, blank=True,
        help_text='برای دعوتِ شماره‌ای که هنوز ثبت‌نام نکرده — تا ثبت‌نامش با همین دعوت وصل شود.',
    )
    role = models.CharField('نقش', max_length=32)
    colleague = models.ForeignKey(
        'colleagues.Colleague', verbose_name='همکار', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='invites',
    )
    status = models.CharField('وضعیت', max_length=10, choices=STATUS_CHOICES, default=PENDING)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='دعوت‌کننده', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField('تاریخ دعوت', auto_now_add=True)
    decided_at = models.DateTimeField('زمانِ تصمیم', null=True, blank=True)

    class Meta:
        verbose_name = 'دعوت‌نامه'
        verbose_name_plural = 'دعوت‌نامه‌ها'
        ordering = ['-created_at']

    def __str__(self):
        who = self.user or self.phone or '—'
        return f'{who} → {self.organization} ({self.get_status_display()})'

    @property
    def role_label(self):
        r = Role.objects.filter(organization_id=self.organization_id, key=self.role).first()
        return r.name if r else dict(ROLE_CHOICES).get(self.role, self.role)

    def accept(self):
        Membership.objects.update_or_create(
            user=self.user, organization=self.organization,
            defaults={'role': self.role, 'is_active': True})
        if self.colleague_id and not self.colleague.user_id:
            self.colleague.user = self.user
            self.colleague.save(update_fields=['user'])
        from django.utils import timezone
        self.status = self.ACCEPTED
        self.decided_at = timezone.now()
        self.save(update_fields=['status', 'decided_at'])

    def reject(self):
        from django.utils import timezone
        self.status = self.REJECTED
        self.decided_at = timezone.now()
        self.save(update_fields=['status', 'decided_at'])


class APIToken(models.Model):
    """توکنِ ورودِ برنامه‌های بیرونی (افزونهٔ مرورگر، اتوماسیون‌ها، AI). برخلافِ مدل‌های
    tenant، **خودش** راهِ رسیدن به سازمان است؛ پس عمداً بدونِ `TenantManager` است —
    یک درخواستِ بدونِ سشن (بدونِ کوکی) با این هدر خودش را معرفی می‌کند:
    `Authorization: Token <key>`. ببین `seo/api.py: token_or_login_required`.
    سشن+کوکیِ سایت برای افزونه‌ای که همیشه در همان مرورگرِ لاگین‌شده اجرا می‌شود کافی
    بود، اما SameSite=Lax (پیش‌فرضِ جنگو) کوکیِ سشن را در fetchِ کراس‌سایتِ افزونه
    نمی‌فرستد؛ توکن این مشکل را کلاً کنار می‌زند.

    مثلِ پسوردها، مقدارِ خامِ کلید هرگز ذخیره نمی‌شود — فقط هشِ SHA-256اش
    (`key_hash`، قابلِ جستجو، دترمینیستیک). کلیدِ خام فقط **یک‌بار**، بلافاصله بعدِ
    ساخت، به کاربر نشان داده می‌شود (`APIToken.generate`)."""

    organization = models.ForeignKey(Organization, verbose_name='سازمان', on_delete=models.CASCADE, related_name='api_tokens')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='کاربر', on_delete=models.CASCADE, related_name='api_tokens')
    name = models.CharField('نام (برای خودت)', max_length=100, blank=True)
    key_hash = models.CharField('هشِ کلید', max_length=64, unique=True, editable=False)
    key_prefix = models.CharField('پیشوندِ نمایشی', max_length=10, editable=False, blank=True)
    is_active = models.BooleanField('فعال', default=True)
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)
    last_used_at = models.DateTimeField('آخرین استفاده', null=True, blank=True)

    class Meta:
        verbose_name = 'توکنِ API'
        verbose_name_plural = 'توکن‌های API'
        ordering = ['-created_at']

    def __str__(self):
        return self.name or f'توکن {self.key_prefix}…'

    @classmethod
    def generate(cls, organization, user, name=''):
        """می‌سازد و کلیدِ خام را برمی‌گرداند (فقط همین یک‌بار در دسترس است)."""
        raw = secrets.token_hex(24)
        obj = cls.objects.create(
            organization=organization, user=user, name=name,
            key_hash=hashlib.sha256(raw.encode()).hexdigest(), key_prefix=raw[:8])
        return obj, raw

    @staticmethod
    def authenticate(raw_key):
        h = hashlib.sha256((raw_key or '').encode()).hexdigest()
        return APIToken.objects.filter(key_hash=h, is_active=True).select_related('organization', 'user').first()

    def touch(self):
        from django.utils import timezone
        APIToken.objects.filter(pk=self.pk).update(last_used_at=timezone.now())


def seed_roles(organization):
    """نقش‌های پیش‌فرض را برای یک سازمان می‌سازد (اجرای مکرر ایمن)."""
    for key, name in ROLE_CHOICES:
        Role.objects.get_or_create(
            organization=organization, key=key,
            defaults={'name': name, 'perms': sorted(ROLE_PERMS.get(key, set())),
                      'is_builtin': True})
