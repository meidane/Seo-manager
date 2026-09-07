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
# انواعِ سئوِ جدید `task_type='other'` دارند؛ سطلِ درست از **نامِ نوعِ سفارشی** می‌آید.
BUCKET_BY_TYPE_NAME = {'انتشار': 'publish', 'آپدیت': 'update', 'فنی': 'tech',
                       'رپورتاژ': 'promo', 'لینک‌سازی': 'promo'}
# ستون‌های هر سکشنِ گزارش (خواستِ کاربر): فقط انتشار/آپدیت «تعداد کلمه» و «لینک انتشار»
# دارند؛ رپورتاژ لینک دارد ولی تعداد کلمه نه؛ فنی/سایر هیچ‌کدام.
BUCKET_COLS = {
    'publish': {'word': True, 'link': True},
    'update': {'word': True, 'link': True},
    'promo': {'word': False, 'link': True},
    'tech': {'word': False, 'link': False},
    'other': {'word': False, 'link': False},
}


class Report(TimeStampedModel):
    DRAFT = 'draft'
    FINAL = 'final'
    STATUS_CHOICES = [(DRAFT, 'پیش‌نویس'), (FINAL, 'نهایی')]

    project = models.ForeignKey('projects.Project', verbose_name='پروژه', on_delete=models.CASCADE, related_name='reports')
    invoice = models.ForeignKey('finance.Invoice', verbose_name='فاکتور', on_delete=models.SET_NULL, null=True, blank=True, related_name='reports')
    title = models.CharField('عنوان', max_length=200)
    date_from = models.DateField('از تاریخ')
    date_to = models.DateField('تا تاریخ')
    description = models.TextField('توضیحات', blank=True)  # HTML پاکسازی‌شده
    status = models.CharField('وضعیت', max_length=10, choices=STATUS_CHOICES, default=DRAFT)

    public_token = models.UUIDField('توکن عمومی', default=uuid.uuid4, unique=True, editable=False)
    is_public = models.BooleanField('لینک عمومی فعال', default=False)
    visible_fields = models.JSONField('فیلدهای قابل‌نمایش به مشتری', default=list, blank=True)

    # اسنپ‌شاتِ نرخِ تولید محتوا (از پروژه، موقعِ ساخت) — تغییرِ بعدیِ نرخِ پروژه
    # نباید این گزارش را عوض کند. ۰ = محاسبه نشود.
    content_hourly_rate = models.BigIntegerField('نرخِ ساعتیِ تولید محتوا (اسنپ‌شات)', default=0)
    content_word_rate = models.BigIntegerField('نرخِ هر کلمهٔ تولید محتوا (اسنپ‌شات)', default=0)
    # رسیدِ پرداختِ مشتری — مشتری از نسخهٔ عمومی/پیش‌نمایش کنارِ اطلاعاتِ حساب آپلود می‌کند؛
    # اگر گزارش فاکتور دارد، در صفحهٔ فاکتور هم دیده می‌شود.
    receipt = models.FileField('رسیدِ پرداخت', upload_to='receipts/', null=True, blank=True)

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
        # اسنپ‌شاتِ نرخِ تولید محتوا فقط موقعِ ساخت (نه ویرایش) — تغییرِ بعدیِ نرخِ پروژه
        # گزارشِ قبلی را عوض نکند.
        if self._state.adding and not (self.content_hourly_rate or self.content_word_rate):
            self.snapshot_content_rates()
        stamp_org(self)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('reports:detail', args=[self.pk])

    def public_url(self):
        return reverse('report_public', args=[self.public_token])

    def sees(self, field_key):
        return field_key in (self.visible_fields or [])

    def grouped_items(self):
        """آیتم‌ها را در سطل‌های نوع برمی‌گرداند: dictهای {key,label,items,cols}."""
        items = list(self.items.select_related('task', 'task__assignee', 'task__type_def').all())
        out = []
        for key, label, types in BUCKETS:
            bucket = [it for it in items if it.bucket == key]
            if bucket:
                out.append({'key': key, 'label': label, 'items': bucket,
                            'add_type': types[0],  # نوعِ ردیفِ دستیِ این سکشن
                            'cols': BUCKET_COLS.get(key, {'word': False, 'link': False})})
        return out

    def snapshot_content_rates(self):
        """نرخِ تولید محتوا را از پروژه روی گزارش کپی می‌کند (اسنپ‌شات موقعِ ساخت)."""
        if self.project_id:
            self.content_hourly_rate = self.project.content_hourly_rate or 0
            self.content_word_rate = self.project.content_word_rate or 0

    def content_cost(self):
        """هزینهٔ تولید محتوا با نرخِ اسنپ‌شات‌شدهٔ همین گزارش.

        فقط آیتم‌های «انتشار/تولید محتوا» و «آپدیت» شمرده می‌شوند.
        `time` = Σ(ساعتِ تخمینی × نرخِ ساعتی)، `word` = Σ(تعدادِ کلمه × نرخِ هر کلمه).
        نرخِ ۰ → آن بخش ۰ (هیچ محاسبه). `total = time + word`.
        """
        hourly = self.content_hourly_rate or 0
        word_rate = self.content_word_rate or 0
        time_cost = word_cost = 0
        total_min = total_words = 0
        for it in self.items.select_related('task', 'task__type_def').all():
            if it.bucket not in ('publish', 'update'):
                continue
            total_min += it.eff_estimate or 0
            total_words += it.eff_word_count or 0
        if hourly:
            time_cost = int(round(total_min / 60 * hourly))
        if word_rate:
            word_cost = int(total_words * word_rate)
        return {'time': time_cost, 'word': word_cost, 'total': time_cost + word_cost,
                'minutes': total_min, 'words': total_words}

    def stats(self):
        """آمارِ خلاصهٔ گزارش: تعداد هر سطل + جمعِ زمان/کلمه + هزینهٔ تولید محتوا."""
        groups = self.grouped_items()
        total_min = total_words = 0
        for it in self.items.all():
            total_min += it.eff_estimate or 0
            total_words += it.eff_word_count or 0
        return {
            'buckets': [{'key': g['key'], 'label': g['label'], 'count': len(g['items'])} for g in groups],
            'item_count': sum(len(g['items']) for g in groups),
            'minutes': total_min, 'words': total_words,
            'content_cost': self.content_cost(),
        }


class ReportItem(models.Model):
    report = models.ForeignKey(Report, verbose_name='گزارش', on_delete=models.CASCADE, related_name='items')
    task = models.ForeignKey('tasks.Task', verbose_name='تسک', on_delete=models.SET_NULL, null=True, blank=True, related_name='report_items')
    order = models.PositiveIntegerField('ترتیب', default=0)

    # override‌های مخصوص همین گزارش (null/خالی = مقدار زنده‌ی تسک)
    override_title = models.CharField('عنوان (override)', max_length=255, blank=True)
    override_done_date = models.DateField('تاریخ انجام (override)', null=True, blank=True)
    override_description = models.TextField('توضیحات (override)', blank=True)
    override_estimate = models.PositiveIntegerField('زمان به دقیقه (override)', null=True, blank=True)
    override_word_count = models.PositiveIntegerField('تعداد کلمه (override)', null=True, blank=True)
    override_assignee = models.ForeignKey('colleagues.Colleague', verbose_name='مسئول (override)',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

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
        # نوعِ سفارشی (سئوی جدید) از **نامِ نوع** سطل‌بندی می‌شود، نه task_type='other'
        t = self.task
        if t and t.type_def_id and t.type_def.name in BUCKET_BY_TYPE_NAME:
            return BUCKET_BY_TYPE_NAME[t.type_def.name]
        return TYPE_TO_BUCKET.get(self.eff_type, 'other')

    @property
    def eff_type_label(self):
        """برچسبِ نوع برای بَجِ کنارِ عنوان (نوعِ سفارشی یا built-in)."""
        t = self.task
        if t:
            return t.type_label
        return self.manual_type or ''

    @property
    def eff_estimate(self):
        if self.override_estimate is not None:
            return self.override_estimate
        return self.task.estimate_minutes if self.task else None

    @property
    def eff_word_count(self):
        if self.override_word_count is not None:
            return self.override_word_count
        return (self.task.word_count if self.task else 0) or 0

    @property
    def eff_assignee(self):
        return self.override_assignee or (self.task.assignee if self.task else None)

    @property
    def eff_url(self):
        # page_link = فیلدِ سفارشیِ is_page_link (سئوِ جدید) یا published_urlِ هسته — منبعِ واحد
        return (self.task.page_link if self.task else '') or self.manual_url

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
        # این‌ها برای ردیفِ دستی هم مقدارِ override دارند (t لازم نیست):
        if key == 'assignee':
            a = self.eff_assignee
            return a.full_name if a else ''
        if key == 'word_count':
            return self.eff_word_count or ''
        if not t:
            return ''
        if key == 'planned_date':
            return format_jalali(t.planned_date)
        if key == 'status':
            return t.get_status_display()
        if key == 'seo_title':
            return t.seo_title
        if key == 'keywords':
            return t.keywords
        if key == 'review_status':
            return t.get_review_status_display()
        return ''


class ReportSection(models.Model):
    """سکشنِ سفارشیِ گزارش («افزودن سکشن و نمودار») — عنوان + توضیحاتِ HTML، دلخواه."""
    report = models.ForeignKey(Report, verbose_name='گزارش', on_delete=models.CASCADE, related_name='sections')
    title = models.CharField('عنوان', max_length=200)
    description = models.TextField('توضیحات', blank=True)  # HTML پاکسازی‌شده
    order = models.PositiveIntegerField('ترتیب', default=0)

    class Meta:
        verbose_name = 'سکشنِ گزارش'
        verbose_name_plural = 'سکشن‌های گزارش'
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


class ReportKeyword(models.Model):
    """جایگاهِ یک کلمهٔ کلیدی در گزارش (فعلاً دستی).

    **اتصالِ آینده (خواستِ صریحِ کاربر):** این سکشن باید به بخشِ ردیابیِ کلماتِ کلیدی
    (`seo/models.py` + افزونهٔ مرورگر `seo/api.py`) وصل شود — جایگاه‌های گزارش ↔ تسک‌ها
    ↔ رپورتاژ ↔ اکستنشن با **هیستوریِ** جایگاه. فعلاً `position` دستی پر می‌شود؛ بعداً
    از منبعِ واحدِ `seo/rank.py` می‌آید. جزئیات: `reports/CLAUDE.md`.
    """
    report = models.ForeignKey(Report, verbose_name='گزارش', on_delete=models.CASCADE, related_name='keywords')
    keyword = models.CharField('کلمهٔ کلیدی', max_length=200)
    position = models.CharField('جایگاه', max_length=30, blank=True)  # رشته: «۳» یا «۳ (+۲)» یا خالی
    order = models.PositiveIntegerField('ترتیب', default=0)

    class Meta:
        verbose_name = 'کلمهٔ کلیدیِ گزارش'
        verbose_name_plural = 'کلماتِ کلیدیِ گزارش'
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.keyword} — {self.position}'
