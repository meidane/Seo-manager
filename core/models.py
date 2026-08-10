"""مدل‌های پایه‌ی مشترک بین همه‌ی اپ‌ها.

قانون تاریخ: همه‌ی تاریخ‌ها اینجا و در سراسر سیستم **میلادی** ذخیره می‌شوند.
تبدیل شمسی فقط در لایه‌ی نمایش (تمپلیت‌فیلتر `jalali`) انجام می‌شود.
"""
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from accounts.tenancy import TenantManager, stamp_org


class TimeStampedModel(models.Model):
    """مدل انتزاعی با زمان ایجاد/ویرایش و سازنده."""

    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)
    updated_at = models.DateTimeField('تاریخ ویرایش', auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='ایجادکننده',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )

    class Meta:
        abstract = True


class Attachment(models.Model):
    """فایل یکپارچه با GenericFK — یک مدل برای فایل‌های پروژه، همکار و تسک."""

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    file = models.FileField('فایل', upload_to='attachments/%Y/%m/')
    original_name = models.CharField('نام اصلی', max_length=255, blank=True)
    size = models.PositiveIntegerField('حجم (بایت)', default=0)
    mime = models.CharField('نوع MIME', max_length=120, blank=True)
    title = models.CharField('عنوان', max_length=255, blank=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='آپلودکننده',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    uploaded_at = models.DateTimeField('تاریخ آپلود', auto_now_add=True)

    class Meta:
        verbose_name = 'پیوست'
        verbose_name_plural = 'پیوست‌ها'
        indexes = [models.Index(fields=['content_type', 'object_id'])]

    def __str__(self):
        return self.title or self.original_name or f'پیوست #{self.pk}'

    @property
    def is_image(self):
        return (self.mime or '').startswith('image/') or \
            (self.original_name or '').lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))

    @property
    def size_h(self):
        n = self.size or 0
        for unit in ('B', 'KB', 'MB', 'GB'):
            if n < 1024:
                return f'{n:.0f} {unit}'
            n /= 1024
        return f'{n:.0f} TB'


class ActivityLog(models.Model):
    """ثبت فعالیت‌ها — کی چه کاری روی چه چیزی انجام داد."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='کاربر',
        on_delete=models.SET_NULL,
        null=True,
        related_name='activities',
    )
    verb = models.CharField('عمل', max_length=120)

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    changes = models.JSONField('تغییرات', default=dict, blank=True)
    created_at = models.DateTimeField('زمان', auto_now_add=True)

    class Meta:
        verbose_name = 'لاگ فعالیت'
        verbose_name_plural = 'لاگ فعالیت‌ها'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['content_type', 'object_id'])]

    def __str__(self):
        return f'{self.actor} {self.verb}'


class Holiday(models.Model):
    """تعطیلات رسمی و مذهبی. جمعه محاسباتی است و اینجا ذخیره نمی‌شود."""

    OFFICIAL = 'official'
    RELIGIOUS = 'religious'
    OCCASION = 'occasion'
    KIND_CHOICES = [
        (OFFICIAL, 'رسمی'),
        (RELIGIOUS, 'مذهبی'),
        (OCCASION, 'مناسبت'),  # مناسبت = تعطیل نیست
    ]

    date = models.DateField('تاریخ (میلادی)', unique=True)
    title = models.CharField('عنوان', max_length=120)
    kind = models.CharField('نوع', max_length=20, choices=KIND_CHOICES, default=OFFICIAL)
    is_off = models.BooleanField('تعطیل است', default=True)

    class Meta:
        verbose_name = 'تعطیلی'
        verbose_name_plural = 'تعطیلات'
        ordering = ['date']

    def __str__(self):
        return f'{self.title} ({self.date})'


class ColumnConfig(models.Model):
    """سفارشی‌سازیِ ستون‌های یک جدول برای یک سازمان — منبعِ واحدِ «کدام ستون‌ها، به
    چه ترتیبی» دیده شوند. کاتالوگِ ستون‌های موجود (برچسب/حالتِ نمایش) در `core/columns.py`
    است؛ اینجا فقط فهرستِ کلیدهای انتخاب‌شده ذخیره می‌شود (بدون تکرارِ برچسب/حالت).
    اگر رکوردی نباشد یا `keys` خالی باشد، `core.columns.get_columns` پیش‌فرضِ کاتالوگ
    را برمی‌گرداند — یعنی صفحه بدون تنظیم هم کار می‌کند."""

    TASKS = 'tasks'
    PROJECTS = 'projects'
    COLLEAGUES = 'colleagues'
    TABLE_CHOICES = [(TASKS, 'تسک‌ها'), (PROJECTS, 'پروژه‌ها'), (COLLEAGUES, 'همکاران')]

    PAGE = 'page'
    DASHBOARD = 'dashboard'
    SCOPE_CHOICES = [(PAGE, 'صفحه‌ی خودش'), (DASHBOARD, 'داشبورد')]

    table = models.CharField('جدول', max_length=12, choices=TABLE_CHOICES)
    scope = models.CharField('محل نمایش', max_length=10, choices=SCOPE_CHOICES)
    keys = models.JSONField('کلیدهای ستون (به ترتیب)', default=list, blank=True)

    organization = models.ForeignKey('accounts.Organization', verbose_name='سازمان', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'تنظیمِ ستون‌ها'
        verbose_name_plural = 'تنظیمِ ستون‌ها'
        base_manager_name = 'all_objects'
        unique_together = ('organization', 'table', 'scope')

    def save(self, *args, **kwargs):
        stamp_org(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.get_table_display()} — {self.get_scope_display()}'
