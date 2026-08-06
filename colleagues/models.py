"""مدل همکار.

نقش‌ها به‌صورت رشته‌ی جداشده با ویرگول ذخیره می‌شوند تا بدون کتابخانه‌ی
اضافی چندتایی باشند. تاریخ‌ها میلادی‌اند و در نمایش شمسی می‌شوند.
"""
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.urls import reverse
from django.utils import timezone

from core.models import Attachment, TimeStampedModel


class Colleague(TimeStampedModel):
    # نقش‌ها
    WRITER = 'writer'
    SEO = 'seo'
    SUPERVISOR = 'supervisor'
    WEBTECH = 'webtech'
    ROLE_CHOICES = [
        (WRITER, 'نویسنده'),
        (SEO, 'مدیر سئو'),
        (SUPERVISOR, 'سرپرست'),
        (WEBTECH, 'مدیر طراحی سایت و فنی'),
    ]

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
    rate_per_word = models.DecimalField(
        'دستمزد هر کلمه', max_digits=12, decimal_places=2, null=True, blank=True
    )
    rate_per_task = models.DecimalField(
        'دستمزد هر تسک', max_digits=12, decimal_places=2, null=True, blank=True
    )
    files = GenericRelation(Attachment)

    class Meta:
        verbose_name = 'همکار'
        verbose_name_plural = 'همکاران'
        ordering = ['status', 'full_name']  # فعال‌ها بالا (active < inactive)

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
        labels = dict(self.ROLE_CHOICES)
        return ' · '.join(labels.get(r, r) for r in self.roles_list)

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
