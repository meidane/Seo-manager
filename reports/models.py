"""مدل‌های گزارش‌دهی — بدون snapshot.

ReportItem یک **مرجع زنده** به Task است؛ اما هر فیلدی که در گزارش inline ویرایش
شود به‌صورت override فقط روی همان ReportItem ذخیره می‌شود و تسک اصلی دست‌نخورده
می‌ماند. نمایش = override اگر پر باشد، وگرنه مقدار زنده‌ی تسک.

نمایش به مشتری کاملاً قابل‌تنظیم است: `Report.visible_fields` فهرست کلید فیلدهایی
است که در نسخه‌ی عمومی دیده می‌شوند (عنوان همیشه دیده می‌شود).
"""
import uuid

from django.db import models
from django.urls import reverse

from accounts.tenancy import TenantManager, stamp_org
from core.models import TimeStampedModel

# فیلدهایی که در نسخه‌ی عمومی قابل نمایش/مخفی‌شدن‌اند (عنوان همیشه هست)
CLIENT_FIELDS = [
    ('type', 'نوع تسک'),
    ('planned_date', 'تاریخ برنامه‌ریزی'),
    ('done_date', 'تاریخ انجام'),
    ('assignee', 'مسئول/نویسنده'),
    ('status', 'وضعیت'),
    ('word_count', 'تعداد کلمه'),
    ('seo_title', 'عنوان سئو'),
    ('keywords', 'کلمات کلیدی'),
    ('published_url', 'لینک انتشار'),
    ('review_status', 'بازبینی'),
]
DEFAULT_VISIBLE = ['type', 'word_count', 'published_url']

# گروه‌بندی نمایش گزارش: انتشار / آپدیت / فنی / (رپورتاژ+لینک‌سازی) / سایر
BUCKETS = [
    ('publish', 'انتشار', ['publish']),
    ('update', 'آپدیت', ['update']),
    ('tech', 'فنی', ['tech']),
    ('promo', 'رپورتاژ و لینک‌سازی', ['reportage', 'linkbuilding']),
    ('other', 'سایر', ['other']),
]
TYPE_TO_BUCKET = {t: key for key, _, types in BUCKETS for t in types}


class Report(TimeStampedModel):
    DRAFT = 'draft'
    FINAL = 'final'
    STATUS_CHOICES = [(DRAFT, 'پیش‌نویس'), (FINAL, 'نهایی')]

    project = models.ForeignKey('projects.Project', verbose_name='پروژه', on_delete=models.CASCADE, related_name='reports')
    title = models.CharField('عنوان', max_length=200)
    date_from = models.DateField('از تاریخ')
    date_to = models.DateField('تا تاریخ')
    description = models.TextField('توضیحات', blank=True)  # HTML پاکسازی‌شده
    status = models.CharField('وضعیت', max_length=10, choices=STATUS_CHOICES, default=DRAFT)

    public_token = models.UUIDField('توکن عمومی', default=uuid.uuid4, unique=True, editable=False)
    is_public = models.BooleanField('لینک عمومی فعال', default=False)
    visible_fields = models.JSONField('فیلدهای قابل‌نمایش به مشتری', default=list, blank=True)

    organization = models.ForeignKey('accounts.Organization', verbose_name='سازمان', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'گزارش'
        verbose_name_plural = 'گزارش‌ها'
        ordering = ['-created_at']
        base_manager_name = 'all_objects'

    def __str__(self):
        return f'{self.title} — {self.project.name}'

    def save(self, *args, **kwargs):
        if not self.visible_fields:
            self.visible_fields = list(DEFAULT_VISIBLE)
        if self.organization_id is None and self.project_id:
            self.organization_id = self.project.organization_id
        stamp_org(self)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('reports:detail', args=[self.pk])

    def public_url(self):
        return reverse('report_public', args=[self.public_token])

    def sees(self, field_key):
        return field_key in (self.visible_fields or [])

    def grouped_items(self):
        """آیتم‌ها را در سطل‌های نوع برمی‌گرداند: [(bucket_key, label, [items])]."""
        items = list(self.items.select_related('task', 'task__assignee').all())
        out = []
        for key, label, _types in BUCKETS:
            bucket = [it for it in items if it.bucket == key]
            if bucket:
                out.append((key, label, bucket))
        return out


class ReportItem(models.Model):
    report = models.ForeignKey(Report, verbose_name='گزارش', on_delete=models.CASCADE, related_name='items')
    task = models.ForeignKey('tasks.Task', verbose_name='تسک', on_delete=models.SET_NULL, null=True, blank=True, related_name='report_items')
    order = models.PositiveIntegerField('ترتیب', default=0)

    # override‌های مخصوص همین گزارش (null/خالی = مقدار زنده‌ی تسک)
    override_title = models.CharField('عنوان (override)', max_length=255, blank=True)
    override_done_date = models.DateField('تاریخ انجام (override)', null=True, blank=True)
    override_description = models.TextField('توضیحات (override)', blank=True)

    # برای ردیف دستی (بدون تسک)
    manual_type = models.CharField('نوع (ردیف دستی)', max_length=20, blank=True)
    manual_url = models.URLField('لینک (ردیف دستی)', blank=True)

    class Meta:
        verbose_name = 'ردیف گزارش'
        verbose_name_plural = 'ردیف‌های گزارش'
        ordering = ['order', 'id']

    def __str__(self):
        return self.eff_title

    # ── مقادیر مؤثر (override → وگرنه تسک زنده) ──
    @property
    def eff_title(self):
        return self.override_title or (self.task.title if self.task else '(بدون عنوان)')

    @property
    def eff_done_date(self):
        return self.override_done_date or (self.task.done_date if self.task else None)

    @property
    def eff_description(self):
        return self.override_description or (self.task.description if self.task else '')

    @property
    def eff_type(self):
        return self.task.task_type if self.task else (self.manual_type or 'other')

    @property
    def bucket(self):
        return TYPE_TO_BUCKET.get(self.eff_type, 'other')

    @property
    def eff_url(self):
        return (self.task.published_url if self.task else '') or self.manual_url

    def field_value(self, key):
        """مقدار یک فیلد برای نمایش (تاریخ‌ها شمسی می‌شوند)."""
        from core.jalali import format_jalali
        t = self.task
        if key == 'type':
            return t.type_label if t else self.manual_type
        if key == 'done_date':
            return format_jalali(self.eff_done_date)
        if key == 'published_url':
            return self.eff_url
        if not t:
            return ''
        if key == 'planned_date':
            return format_jalali(t.planned_date)
        if key == 'assignee':
            return t.assignee.full_name if t.assignee else ''
        if key == 'status':
            return t.get_status_display()
        if key == 'word_count':
            return t.word_count
        if key == 'seo_title':
            return t.seo_title
        if key == 'keywords':
            return t.keywords
        if key == 'review_status':
            return t.get_review_status_display()
        return ''
