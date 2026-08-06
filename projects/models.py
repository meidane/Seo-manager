"""مدل‌های پروژه و دسترسی (Credential).

انواع پروژه به‌صورت رشته‌ی جداشده با ویرگول ذخیره می‌شوند. پسورد دسترسی‌ها
با Fernet رمزنگاری و در `password_enc` نگه داشته می‌شود.
"""
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.urls import reverse
from django.utils import timezone

from core.crypto import decrypt, encrypt
from core.models import Attachment, TimeStampedModel


class Project(TimeStampedModel):
    # انواع پروژه
    WEB = 'web'
    SEO = 'seo'
    TECH = 'tech'
    TYPE_CHOICES = [(WEB, 'طراحی سایت'), (SEO, 'سئو'), (TECH, 'فنی')]

    # وضعیت
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    STATUS_CHOICES = [(ACTIVE, 'فعال'), (INACTIVE, 'غیرفعال')]

    PALETTE = [
        '#4183F2', '#2DD4A7', '#FBBF24', '#FB5773', '#38BDF8', '#A78BFA',
        '#F472B6', '#F97316', '#8FA0B8', '#6BA1FF', '#34D399', '#F59E0B',
    ]

    name = models.CharField('نام پروژه', max_length=150)
    domain = models.CharField('دامنه', max_length=200, blank=True, help_text='بدون http')
    color = models.CharField('رنگ', max_length=7, default='#4183F2')
    project_types = models.CharField('نوع پروژه', max_length=100, blank=True)
    status = models.CharField('وضعیت', max_length=10, choices=STATUS_CHOICES, default=ACTIVE)
    archived_at = models.DateTimeField('زمان غیرفعال‌سازی', null=True, blank=True)

    amount = models.DecimalField('مبلغ قرارداد', max_digits=14, decimal_places=0, null=True, blank=True)
    contract_start = models.DateField('شروع قرارداد', null=True, blank=True)
    contract_end = models.DateField('پایان قرارداد', null=True, blank=True)
    description = models.TextField('توضیحات', blank=True)

    client_name = models.CharField('نام کارفرما', max_length=120, blank=True)
    client_phone = models.CharField('تلفن کارفرما', max_length=30, blank=True)

    manager = models.ForeignKey(
        'colleagues.Colleague', verbose_name='مسئول پروژه',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_projects',
    )
    members = models.ManyToManyField(
        'colleagues.Colleague', verbose_name='تیم', blank=True, related_name='projects',
    )

    # فاز ۳ — اتصال وردپرس (فعلاً فقط ساخته می‌شود)
    wp_api_url = models.URLField('WP API URL', blank=True)
    wp_username = models.CharField('WP Username', max_length=120, blank=True)
    wp_app_password = models.CharField('WP App Password', max_length=200, blank=True)

    files = GenericRelation(Attachment)

    class Meta:
        verbose_name = 'پروژه'
        verbose_name_plural = 'پروژه‌ها'
        ordering = ['status', 'name']  # فعال‌ها بالا

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('projects:detail', args=[self.pk])

    @property
    def is_active(self):
        return self.status == self.ACTIVE

    @property
    def types_list(self):
        return [t for t in self.project_types.split(',') if t]

    @property
    def types_display(self):
        labels = dict(self.TYPE_CHOICES)
        return [labels.get(t, t) for t in self.types_list]

    def archive(self):
        self.status = self.INACTIVE
        self.archived_at = timezone.now()
        self.save(update_fields=['status', 'archived_at', 'updated_at'])

    def restore(self):
        self.status = self.ACTIVE
        self.archived_at = None
        self.save(update_fields=['status', 'archived_at', 'updated_at'])


class Credential(models.Model):
    """دسترسی پروژه — پسورد رمزنگاری‌شده. هر «نمایش» در ActivityLog ثبت می‌شود."""

    project = models.ForeignKey(
        Project, verbose_name='پروژه', on_delete=models.CASCADE, related_name='credentials'
    )
    title = models.CharField('عنوان', max_length=120)
    url = models.URLField('آدرس', blank=True)
    username = models.CharField('نام کاربری', max_length=150, blank=True)
    password_enc = models.TextField('پسورد رمزنگاری‌شده', blank=True)
    note = models.CharField('یادداشت', max_length=255, blank=True)
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)

    class Meta:
        verbose_name = 'دسترسی'
        verbose_name_plural = 'دسترسی‌ها'
        ordering = ['title']

    def __str__(self):
        return f'{self.title} — {self.project.name}'

    def set_password(self, raw: str):
        self.password_enc = encrypt(raw or '')

    def reveal_password(self) -> str:
        return decrypt(self.password_enc)
