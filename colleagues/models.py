"""مدل همکار.

نقش‌ها به‌صورت رشته‌ی جداشده با ویرگول ذخیره می‌شوند تا بدون کتابخانه‌ی
اضافی چندتایی باشند. تاریخ‌ها میلادی‌اند و در نمایش شمسی می‌شوند.
"""
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.urls import reverse
from django.utils import timezone

from accounts.tenancy import TenantManager, stamp_org
from core.models import Attachment, TimeStampedModel


class Colleague(TimeStampedModel):
    # وضعیت
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    STATUS_CHOICES = [(ACTIVE, 'فعال'), (INACTIVE, 'غیرفعال')]

    # پالت ۱۲ رنگی برای رنگ اختصاصی همکار در نمودارها
    PALETTE = [
        '#4183F2', '#2DD4A7', '#FBBF24', '#FB5773', '#38BDF8', '#A78BFA',
        '#F472B6', '#F97316', '#8FA0B8', '#6BA1FF', '#34D399', '#F59E0B',
    ]

    full_name = models.CharField('نام و نام خانوادگی', max_length=120)
    roles = models.CharField('نقش‌ها', max_length=200, blank=True)
    avatar = models.ImageField('آواتار', upload_to='avatars/colleagues/', null=True, blank=True)
    color = models.CharField('رنگ', max_length=7, default='#4183F2')
    description = models.TextField('توضیحات', blank=True)
    phone = models.CharField('تلفن', max_length=30, blank=True)
    email = models.EmailField('ایمیل', blank=True)
    status = models.CharField('وضعیت', max_length=10, choices=STATUS_CHOICES, default=ACTIVE)
    archived_at = models.DateTimeField('زمان غیرفعال‌سازی', null=True, blank=True)
    join_date = models.DateField('تاریخ عضویت', null=True, blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name='کاربر',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='colleague',
    )
    manager = models.ForeignKey(
        'self', verbose_name='مدیر', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reports',
    )
    needs_review = models.BooleanField(
        'تسک‌هایش نیاز به بازبینی دارد', default=False,
        help_text='فقط با تعیینِ مدیر معنا دارد؛ تسک‌های انجام‌شده برای تاییدِ مدیرش به «بازبینی تسک» می‌رود.',
    )
    files = GenericRelation(Attachment)

    organization = models.ForeignKey('accounts.Organization', verbose_name='سازمان', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'همکار'
        verbose_name_plural = 'همکاران'
        ordering = ['status', 'full_name']  # فعال‌ها بالا (active < inactive)
        base_manager_name = 'all_objects'

    def save(self, *args, **kwargs):
        stamp_org(self)
        if self.manager_id == self.pk:  # همکار نمی‌تواند مدیرِ خودش باشد
            self.manager_id = None
        if not self.manager_id:
            self.needs_review = False
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        return reverse('colleagues:detail', args=[self.pk])

    @property
    def is_active(self):
        return self.status == self.ACTIVE

    @property
    def roles_list(self):
        return [r for r in self.roles.split(',') if r]

    @property
    def roles_display(self):
        """برچسبِ نمایشیِ نقش‌ها — از کاتالوگِ نقش‌های سازمان می‌خواند (`accounts.Role`،
        همان‌هایی که در «تنظیمات → تیم‌ها و نقش‌ها» تعریف می‌شوند)، نه فهرستِ ثابتِ قدیمی."""
        keys = self.roles_list
        if not keys:
            return ''
        from accounts.models import Role
        labels = dict(Role.objects.filter(
            organization_id=self.organization_id, key__in=keys).values_list('key', 'name'))
        return ' · '.join(labels.get(r, r) for r in keys)

    @property
    def initials(self):
        parts = self.full_name.split()
        return (parts[0][:1] + (parts[1][:1] if len(parts) > 1 else '')).upper()

    def archive(self):
        self.status = self.INACTIVE
        self.archived_at = timezone.now()
        self.save(update_fields=['status', 'archived_at', 'updated_at'])

    def restore(self):
        self.status = self.ACTIVE
        self.archived_at = None
        self.save(update_fields=['status', 'archived_at', 'updated_at'])


def ensure_colleague_for_user(user, org):
    """اگر کاربرِ عضوِ سازمان (مثلاً مالک، که در ساختِ سازمان Colleague ندارد) هنوز
    پروفایلِ همکار وصل ندارد، یکی می‌سازد — تا هرکسی که به سازمان دسترسی دارد در
    «افراد و دسترسی‌ها» هم دیده شود و بتواند مسئولِ تسک باشد (own_tasks_only و
    پیش‌فرضِ «مسئول = خودم» به این نیاز دارند)."""
    if not user or not org or not getattr(user, 'is_authenticated', False):
        return None
    existing = getattr(user, 'colleague', None)
    if existing:
        return existing
    return Colleague.objects.create(
        full_name=user.get_full_name() or user.username,
        email=user.email, phone=user.phone, user=user, organization=org)
