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


class Notification(models.Model):
    """اعلانِ درون‌برنامه‌ای — per user (نه tenant). متن + لینک + نوع (برای آیکنِ SVG) + تسکِ مرتبط.
    ساخته می‌شود با `Notification.push(...)` از نقاطِ کلیدیِ tasks/api.
    **خودپاک‌شونده:** اعلانی که «کارش انجام شد» حذف می‌شود (`cleanup`) — تسک حذف شد (نرم یا سخت)،
    تسکِ واگذارشده/نیازمندِ اصلاح تکمیل شد، یا بازبینیِ تسکِ «آمادهٔ بازبینی» انجام شد."""

    ASSIGNED, REVIEW, NEEDS_FIX, APPROVED = 'assigned', 'review', 'needs_fix', 'approved'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    text = models.CharField('متن', max_length=255)
    url = models.CharField('لینک', max_length=300, blank=True)
    icon = models.CharField('آیکن', max_length=8, blank=True)
    kind = models.CharField('نوع', max_length=20, blank=True, db_index=True)
    task = models.ForeignKey('tasks.Task', verbose_name='تسک', on_delete=models.CASCADE, null=True, blank=True,
                             related_name='notifications')
    read = models.BooleanField('خوانده‌شده', default=False, db_index=True)
    created_at = models.DateTimeField('ایجاد', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'اعلان'
        verbose_name_plural = 'اعلان‌ها'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user_id} — {self.text[:40]}'

    @classmethod
    def push(cls, user, text, url='', icon='', actor=None, task=None, kind=''):
        """یک اعلان بساز. `user` می‌تواند User یا None باشد؛ اگر گیرنده = عاملِ رویداد
        بود (کارِ خودش) اعلانی ساخته نمی‌شود. سبک و بی‌خطا (هرگز جریانِ اصلی را نمی‌شکند)."""
        try:
            if not user or (actor and getattr(actor, 'id', None) == getattr(user, 'id', None)):
                return None
            return cls.objects.create(user=user, text=text[:255], url=url or '', icon=icon or '',
                                      task=task, kind=kind or '')
        except Exception:  # noqa: BLE001 — اعلان هرگز نباید عملیاتِ اصلی را خراب کند
            return None

    @classmethod
    def cleanup(cls, user):
        """اعلان‌های «انجام‌شده» را پاک کن — منبعِ واحد، موقعِ خواندنِ اعلان‌ها صدا زده می‌شود
        (هر مسیرِ تغییرِ تسک، حتی آپدیتِ گروهی، را پوشش می‌دهد). خوانده‌شده‌های قدیمی‌تر از ۳۰ روز هم."""
        from datetime import timedelta

        from django.db.models import Q
        from django.utils import timezone
        try:
            qs = cls.objects.filter(user=user)
            done = ('done', 'pending')
            qs.filter(
                Q(task__deleted_at__isnull=False)
                | Q(kind__in=[cls.ASSIGNED, cls.NEEDS_FIX], task__status__in=done)
                | (Q(kind=cls.REVIEW) & ~Q(task__status='pending'))
                | Q(read=True, created_at__lt=timezone.now() - timedelta(days=30))
            ).delete()
        except Exception:  # noqa: BLE001
            pass

    def payload(self):
        """دادهٔ نمایشِ یک اعلان (منبعِ واحدِ API و بارِ اولِ صفحه)."""
        from django.utils import timezone

        from core.jalali import g2j
        local = timezone.localtime(self.created_at)
        delta = timezone.now() - self.created_at
        mins = int(delta.total_seconds() // 60)
        if mins < 1:
            ago = 'همین الان'
        elif mins < 60:
            ago = f'{mins} دقیقه پیش'
        elif mins < 24 * 60:
            ago = f'{mins // 60} ساعت پیش'
        elif mins < 48 * 60:
            ago = 'دیروز'
        else:
            ago = f'{mins // (24 * 60)} روز پیش'
        try:
            jd = g2j(local.date())
            date_fa = f'{jd.year}/{jd.month:02d}/{jd.day:02d} · {local:%H:%M}'
        except Exception:  # noqa: BLE001
            date_fa = local.strftime('%Y/%m/%d %H:%M')
        fa = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')
        return {'id': self.id, 'text': self.text, 'url': self.url, 'kind': self.kind or 'info', 'read': self.read,
                'ago': ago.translate(fa), 'date': date_fa.translate(fa), 'today': local.date() == timezone.localdate()}
