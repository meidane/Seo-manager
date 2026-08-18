"""مدل تسک — قلب سیستم.

یک مدل واحد با فیلدهای null=True؛ نمایش شرطی فیلدها بر اساس نوع تسک در فرانت
با `static/js/task-schema.js` انجام می‌شود (همان منبع، هم برای مودال هم اعتبارسنجی).

قانون تاریخ: planned_date و done_date میلادی‌اند؛ تبدیل شمسی فقط در نمایش.
"""
from datetime import date, time, timedelta

from django.conf import settings
from django.db import models
from django.urls import reverse

from accounts.tenancy import TenantManager, stamp_org
from core.models import TimeStampedModel


class TaskManager(TenantManager):
    """مثل TenantManager (اسکوپِ سازمان) ولی پیش‌نماهای تکرار را هم پنهان می‌کند.
    تقویم برای دیدنِ پیش‌نماها از `with_placeholders()` استفاده می‌کند."""

    def get_queryset(self):
        return super().get_queryset().filter(is_placeholder=False, deleted_at__isnull=True)

    def with_placeholders(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def deleted(self):
        """تسک‌های سافت‌دیلیت‌شده (برای تبِ «حذف‌شده‌ها»)."""
        return super().get_queryset().filter(is_placeholder=False, deleted_at__isnull=False)

# رنگ هر نوع تسک (RGB) — با پالت بخش ۲.۳ هم‌خوان؛ در فرانت هم در task-schema.js هست
TYPE_COLORS = {
    'publish': '56,189,248',    # انتشار — info
    'update': '251,191,36',     # آپدیت — warning (اساسی نارنجی می‌شود، در property زیر)
    'tech': '167,139,250',      # فنی — violet
    'reportage': '244,114,182', # رپورتاژ — pink
    'linkbuilding': '45,212,167',  # لینک‌سازی — success
    'other': '143,160,184',     # سایر — slate
}


class Task(TimeStampedModel):
    # ── انواع ──
    PUBLISH = 'publish'
    UPDATE = 'update'
    TECH = 'tech'
    REPORTAGE = 'reportage'
    LINKBUILDING = 'linkbuilding'
    OTHER = 'other'
    TYPE_CHOICES = [
        (PUBLISH, 'انتشار'), (UPDATE, 'آپدیت'), (TECH, 'فنی'),
        (REPORTAGE, 'رپورتاژ'), (LINKBUILDING, 'لینک‌سازی'), (OTHER, 'سایر'),
    ]

    MINOR = 'minor'
    MAJOR = 'major'
    UPDATE_TYPE_CHOICES = [(MINOR, 'سطحی'), (MAJOR, 'اساسی')]

    TODO = 'todo'
    DOING = 'doing'
    PENDING = 'pending'
    DONE = 'done'
    STATUS_CHOICES = [
        (TODO, 'در انتظار'), (DOING, 'در حال انجام'),
        (PENDING, 'تکمیل — در انتظار بازبینی'), (DONE, 'انجام شده'),
    ]

    LOW = 'low'
    MED = 'med'
    HIGH = 'high'
    PRIORITY_CHOICES = [(LOW, 'کم'), (MED, 'متوسط'), (HIGH, 'زیاد')]

    UNREVIEWED = 'unreviewed'
    APPROVED = 'approved'
    NEEDS_FIX = 'needs_fix'
    REVIEW_CHOICES = [
        (UNREVIEWED, 'بررسی‌نشده'), (APPROVED, 'تایید'), (NEEDS_FIX, 'نیاز به اصلاح'),
    ]

    LINK_TYPE_CHOICES = [
        ('comment', 'کامنت'), ('profile', 'پروفایل'), ('forum', 'فروم'),
        ('directory', 'دایرکتوری'), ('social', 'سوشال'), ('other', 'سایر'),
    ]

    # ── فیلدهای مشترک ──
    project = models.ForeignKey('projects.Project', verbose_name='پروژه', on_delete=models.CASCADE, related_name='tasks')
    assignee = models.ForeignKey('colleagues.Colleague', verbose_name='مسئول', on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    task_type = models.CharField('نوع تسک', max_length=20, choices=TYPE_CHOICES, default=PUBLISH)
    # نوع سفارشی (اختیاری) + مقادیر فیلدهای سفارشی؛ فیلدهای هسته‌ای بالا دست‌نخورده می‌مانند
    type_def = models.ForeignKey('tasks.TaskTypeDef', verbose_name='نوع سفارشی', on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    custom = models.JSONField('فیلدهای سفارشی', default=dict, blank=True)
    update_type = models.CharField('زیرنوع آپدیت', max_length=10, choices=UPDATE_TYPE_CHOICES, blank=True)
    title = models.CharField('عنوان', max_length=255)
    description = models.TextField('توضیحات', blank=True)
    planned_date = models.DateField('تاریخ برنامه', null=True, blank=True)
    planned_time = models.TimeField('ساعت', default=time(8, 0))
    # ماهِ گزارش (شخصی‌سازیِ سئو) — ۱=فروردین … ۱۲=اسفند. اختیاری؛ روی هستهٔ سیستم رفتاری ندارد.
    REPORT_MONTH_CHOICES = [
        (1, 'فروردین'), (2, 'اردیبهشت'), (3, 'خرداد'), (4, 'تیر'), (5, 'مرداد'), (6, 'شهریور'),
        (7, 'مهر'), (8, 'آبان'), (9, 'آذر'), (10, 'دی'), (11, 'بهمن'), (12, 'اسفند'),
    ]
    report_month = models.PositiveSmallIntegerField('ماه گزارش', null=True, blank=True, choices=REPORT_MONTH_CHOICES, db_index=True)
    report_year = models.PositiveSmallIntegerField('سالِ گزارش', null=True, blank=True, db_index=True)
    # ترتیبِ دستیِ ردیف در بردِ سئوِ پروژه (جابه‌جاییِ ردیف‌ها)؛ کوچک‌تر = بالاتر
    board_order = models.IntegerField('ترتیبِ برد', default=0, db_index=True)
    status = models.CharField('وضعیت', max_length=12, choices=STATUS_CHOICES, default=TODO)
    done_date = models.DateField('تاریخ انجام', null=True, blank=True)
    priority = models.CharField('اولویت', max_length=6, choices=PRIORITY_CHOICES, default=MED)

    # ── فیلدهای محتوایی (انتشار/آپدیت/رپورتاژ) ──
    word_count = models.PositiveIntegerField('تعداد کلمه', null=True, blank=True)
    keywords = models.TextField('کلمات کلیدی', blank=True)
    lsi_keywords = models.TextField('کلمات LSI', blank=True)
    seo_title = models.CharField('عنوان سئو', max_length=255, blank=True)
    current_rank = models.PositiveIntegerField('جایگاه فعلی', null=True, blank=True)  # فقط آپدیت
    published_url = models.URLField('لینک انتشار', blank=True)  # انتشار/رپورتاژ
    source_url = models.URLField('آدرس مطلب فعلی', blank=True)  # فقط آپدیت
    estimate_minutes = models.PositiveIntegerField('تخمین زمان (دقیقه)', null=True, blank=True)
    # ── زمانِ واقعیِ کارکرد (تایمر) ──
    spent_minutes = models.PositiveIntegerField('زمان کارکرد (دقیقه)', default=0)
    timer_started_at = models.DateTimeField('شروع تایمر جاری', null=True, blank=True)

    # ── رپورتاژ ──
    media_name = models.CharField('نام رسانه', max_length=150, blank=True)
    media_cost = models.DecimalField('هزینه رپورتاژ', max_digits=14, decimal_places=0, null=True, blank=True)
    anchor_text = models.CharField('انکر تکست', max_length=255, blank=True)
    target_url = models.URLField('لینک مقصد', blank=True)

    # ── لینک‌سازی ──
    link_type = models.CharField('نوع لینک', max_length=12, choices=LINK_TYPE_CHOICES, blank=True)
    link_count = models.PositiveIntegerField('تعداد لینک', null=True, blank=True)

    # ── بازبینی (آماده‌سازی فاز ۳) ──
    # آیا این تسکِ مشخص نیاز به بازبینیِ مدیر دارد؟ پیش‌فرض از assignee.needs_review
    # می‌آید (تسکِ جدید)، ولی هربار قابلِ‌تغییرِ دستی است (تیک/عدمِ‌تیک روی خودِ تسک).
    # اگر True بود: مسئول نمی‌تواند وضعیت را مستقیم «انجام‌شده» کند، فقط «تکمیل — در
    # انتظار بازبینی» (PENDING)؛ فقط تاییدِ مدیر (`task_review`) آن را DONE می‌کند.
    needs_review = models.BooleanField('نیاز به بازبینی', default=False)
    review_status = models.CharField('وضعیت بازبینی', max_length=12, choices=REVIEW_CHOICES, default=UNREVIEWED)
    review_note = models.TextField('یادداشت بازبینی', blank=True)
    # وقتی نوعِ تسک هیچ TaskTypeKPIای ندارد، جایگزینِ سادهٔ ۱ تا ۱۰ (نه سیستمِ KPI کامل)
    quality_score = models.PositiveSmallIntegerField('امتیاز کیفیت (بدون KPI)', null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='بازبین', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    reviewed_at = models.DateTimeField('زمان بازبینی', null=True, blank=True)
    ai_checked_at = models.DateTimeField('بررسی هوش مصنوعی', null=True, blank=True)  # فاز ۳
    ai_score = models.PositiveIntegerField('امتیاز AI', null=True, blank=True)       # فاز ۳
    ai_report = models.JSONField('گزارش AI', null=True, blank=True)                  # فاز ۳

    # ── تکرارشونده ──
    recurrence = models.ForeignKey('tasks.RecurrenceRule', verbose_name='قاعده تکرار', on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    is_placeholder = models.BooleanField('پیش‌نمای تکرار', default=False)  # در تقویم کم‌رنگ؛ خارج از آمار/بازبینی

    # ── حذفِ نرم (سطلِ زباله) ──
    deleted_at = models.DateTimeField('زمان حذف', null=True, blank=True, db_index=True)
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='حذف‌کننده', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    organization = models.ForeignKey('accounts.Organization', verbose_name='سازمان', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    objects = TaskManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'تسک'
        verbose_name_plural = 'تسک‌ها'
        ordering = ['planned_date', 'planned_time']
        base_manager_name = 'all_objects'
        indexes = [
            models.Index(fields=['project', 'status', 'planned_date']),
            models.Index(fields=['assignee', 'status', 'done_date']),
            models.Index(fields=['status', 'planned_date']),
        ]

    def save(self, *args, **kwargs):
        # سازمان را از پروژه بگیر (منبعِ درست)؛ وگرنه از سازمانِ جاری
        if self.organization_id is None and self.project_id:
            self.organization_id = self.project.organization_id
        stamp_org(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('tasks:list') + f'?open={self.pk}'

    @property
    def is_overdue(self):
        return bool(self.planned_date) and self.status in (self.TODO, self.DOING) and self.planned_date < date.today()

    @property
    def is_done(self):
        return self.status == self.DONE

    @property
    def type_label(self):
        if self.type_def_id:  # نوع سفارشی
            return self.type_def.name
        label = dict(self.TYPE_CHOICES).get(self.task_type, '')
        if self.task_type == self.UPDATE and self.update_type:
            label += ' ' + dict(self.UPDATE_TYPE_CHOICES).get(self.update_type, '')
        return label

    @property
    def color_rgb(self):
        if self.type_def_id:  # رنگ نوع سفارشی (hex → rgb)
            h = self.type_def.color.lstrip('#')
            if len(h) == 6:
                return ','.join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4))
        # آپدیت اساسی نارنجی، بقیه طبق نگاشت
        if self.task_type == self.UPDATE and self.update_type == self.MAJOR:
            return '249,115,22'
        return TYPE_COLORS.get(self.task_type, TYPE_COLORS['other'])

    def to_dict(self):
        """نمایش سبک برای API تقویم/لیست."""
        return {
            'id': self.id,
            'title': self.title,
            'type': self.task_type,
            'type_label': self.type_label,
            'color': self.color_rgb,
            'time': self.planned_time.strftime('%H:%M') if hasattr(self.planned_time, 'strftime') else str(self.planned_time or ''),
            'status': self.status,
            'needs_review': self.needs_review,
            'done': self.is_done,
            'overdue': self.is_overdue,
            'project': self.project.name,
            'project_id': self.project_id,
            'assignee': self.assignee.full_name if self.assignee else '',
            'assignee_id': self.assignee_id,
            'avatar': (self.assignee.avatar.url if self.assignee and self.assignee.avatar else ''),
            'initials': self.assignee.initials if self.assignee else '',
            'a_color': self.assignee.color if self.assignee else '#8FA0B8',
            'word_count': self.word_count,
            'published_url': self.published_url,
            'estimate_minutes': self.estimate_minutes,
            'is_placeholder': self.is_placeholder,
            'recurring': bool(self.recurrence_id),
            'spent_minutes': self.spent_minutes,
            'timer_running': bool(self.timer_started_at),
            'timer_started': self.timer_started_at.isoformat() if self.timer_started_at else None,
        }


class TaskTypeDef(TimeStampedModel):
    """نوع تسک سفارشی — کاربر خودش تعریف می‌کند.

    مستقل از انواع built-in مدل Task است. هر نوع مجموعه‌ای از فیلدهای سفارشی
    دارد که مقادیرشان در Task.custom (JSON) ذخیره می‌شوند. فیلدهای هسته‌ایِ Task
    (عنوان، تاریخ برنامه، وضعیت، word_count و…) دست‌نخورده می‌مانند تا داشبورد نشکند.
    """

    name = models.CharField('نام نوع', max_length=80)
    color = models.CharField('رنگ', max_length=7, default='#4183F2')
    icon = models.CharField('آیکن (اموجی)', max_length=8, blank=True)
    order = models.PositiveIntegerField('ترتیب', default=0)
    is_active = models.BooleanField('فعال', default=True)
    # اگر نوع built-in باشد، کلیدش اینجاست (publish/update/...) تا فیلدهای هسته‌ای و
    # آمار داشبورد کار کنند. خالی = نوع کاملاً سفارشی.
    builtin_key = models.CharField('کلید built-in', max_length=20, blank=True)
    requires_review = models.BooleanField('نیاز به بازبینی دارد', default=False)

    organization = models.ForeignKey('accounts.Organization', verbose_name='سازمان', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'نوع تسک سفارشی'
        verbose_name_plural = 'انواع تسک سفارشی'
        ordering = ['order', 'name']
        base_manager_name = 'all_objects'
        unique_together = ('organization', 'name')

    def save(self, *args, **kwargs):
        stamp_org(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('task_types:edit', args=[self.pk])

    def schema(self):
        """اسکیمای فیلدها برای مصرف فرانت (مودال آینده/گزارش)."""
        return [f.to_dict() for f in self.fields.all()]


class TaskTypeField(models.Model):
    """یک فیلد سفارشی متعلق به یک TaskTypeDef."""

    TEXT = 'text'
    TEXTAREA = 'textarea'
    NUMBER = 'number'
    CHECKBOX = 'checkbox'
    SELECT = 'select'
    URL = 'url'
    DATE = 'date'
    TAGS = 'tags'
    KIND_CHOICES = [
        (TEXT, 'متن کوتاه'), (TEXTAREA, 'متن بلند'), (NUMBER, 'عدد'),
        (CHECKBOX, 'چک‌باکس'), (SELECT, 'انتخابی'), (URL, 'لینک'), (DATE, 'تاریخ'),
        (TAGS, 'چندتایی (کلمه + اینتر)'),
    ]

    type_def = models.ForeignKey(TaskTypeDef, verbose_name='نوع', on_delete=models.CASCADE, related_name='fields')
    key = models.CharField('کلید', max_length=40, blank=True)  # خودکار: f<id>
    label = models.CharField('برچسب', max_length=120)
    kind = models.CharField('نوع فیلد', max_length=12, choices=KIND_CHOICES, default=TEXT)
    options = models.CharField('گزینه‌ها (با ویرگول)', max_length=500, blank=True)  # فقط select
    placeholder = models.CharField('راهنما', max_length=120, blank=True)
    required = models.BooleanField('اجباری (همیشه)', default=False)
    # مثلِ «لینکِ انتشار» که فقط موقعِ تمام‌کردنِ کار الزامی است، نه موقعِ ساختِ تسک
    required_on_done = models.BooleanField('اجباری فقط برای تکمیل', default=False)
    show_to_client = models.BooleanField('نمایش به مشتری', default=True)
    # این فیلد به‌عنوان «تعداد کلمه» شناخته شود تا در آمار (همکار/داشبورد) حساب شود
    is_word_source = models.BooleanField('منبعِ تعداد کلمه', default=False)
    # فیلدهای وصل‌شونده به بستهٔ سئو (`seo/`) — منبعِ واحدِ این چهارتا در seo/CLAUDE.md
    is_keyword_source = models.BooleanField('حاویِ کلمهٔ کلیدیِ قابل‌جستجو', default=False)
    track_keyword_rank = models.BooleanField('رتبهٔ این کلمه ردیابی شود', default=False)
    is_link_source = models.BooleanField('حاویِ لینکِ هدفِ قابل‌جستجو', default=False)
    is_page_link = models.BooleanField('لینکِ صفحهٔ خودِ همین تسک', default=False)
    order = models.PositiveIntegerField('ترتیب', default=0)

    class Meta:
        verbose_name = 'فیلد نوع تسک'
        verbose_name_plural = 'فیلدهای نوع تسک'
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.label} ({self.get_kind_display()})'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.key:
            self.key = f'f{self.pk}'
            super().save(update_fields=['key'])

    @property
    def options_list(self):
        return [o.strip() for o in self.options.split(',') if o.strip()]

    def to_dict(self):
        return {
            'key': self.key, 'label': self.label, 'kind': self.kind,
            'options': self.options_list, 'placeholder': self.placeholder,
            'required': self.required, 'required_on_done': self.required_on_done,
            'show_to_client': self.show_to_client,
        }


class TaskReviewNote(models.Model):
    """تاریخچه‌ی «نیاز به اصلاح» — هر بار که مدیر تسک را برای اصلاح برمی‌گرداند،
    یک رکورد جدید ثبت می‌شود تا سوابق قبلی (ممکن است ۲–۳ بار) هم قابل‌مشاهده بماند.
    آخرین رکورد همان مقدار `Task.review_note` هم هست (برای سازگاری/دسترسی سریع)."""

    task = models.ForeignKey(Task, verbose_name='تسک', on_delete=models.CASCADE, related_name='review_notes')
    note = models.TextField('یادداشت نیاز به اصلاح')  # HTML پاکسازی‌شده
    author = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='بازبین', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField('زمان', auto_now_add=True)

    class Meta:
        verbose_name = 'یادداشت بازبینی تسک'
        verbose_name_plural = 'یادداشت‌های بازبینی تسک'
        ordering = ['-created_at']  # جدیدترین اول

    def __str__(self):
        return f'اصلاحِ تسک {self.task_id}'


class TaskTypeKPI(models.Model):
    """یک KPI (شاخص کیفیت) متعلق به یک نوع تسک. کارمند آن را می‌بیند و مدیر در
    بازبینی امتیازش می‌دهد. می‌تواند با چک‌لیست باشد (امتیاز = جمع آیتم‌های تیک‌خورده)
    یا بدون چک‌لیست (مدیر عددِ ۰..max_score می‌دهد)."""

    type_def = models.ForeignKey(TaskTypeDef, verbose_name='نوع تسک', on_delete=models.CASCADE, related_name='kpis')
    title = models.CharField('عنوان', max_length=120)
    max_score = models.PositiveIntegerField('حداکثر امتیاز', default=10)
    description = models.TextField('توضیحات', blank=True)  # پشت آیکن نمایش داده می‌شود
    has_checklist = models.BooleanField('چک‌لیستی', default=False)
    order = models.PositiveIntegerField('ترتیب', default=0)

    class Meta:
        verbose_name = 'KPI نوع تسک'
        verbose_name_plural = 'KPIهای نوع تسک'
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

    @property
    def cap(self):
        """سقفِ مؤثر: در حالت چک‌لیستی جمعِ امتیازِ آیتم‌ها، وگرنه max_score."""
        if self.has_checklist:
            return sum(i.score for i in self.items.all())
        return self.max_score

    def to_dict(self):
        return {
            'id': self.id, 'title': self.title, 'max_score': self.max_score,
            'description': self.description, 'has_checklist': self.has_checklist,
            'cap': self.cap,
            'items': [{'id': i.id, 'title': i.title, 'score': i.score,
                       'description': i.description} for i in self.items.all()],
        }


class KPIChecklistItem(models.Model):
    """یک آیتمِ چک‌لیست زیرِ یک KPI (تیک‌خوردنی، با امتیاز و توضیح مستقل)."""

    kpi = models.ForeignKey(TaskTypeKPI, verbose_name='KPI', on_delete=models.CASCADE, related_name='items')
    title = models.CharField('عنوان', max_length=160)
    score = models.PositiveIntegerField('امتیاز', default=0)
    description = models.TextField('توضیحات', blank=True)
    order = models.PositiveIntegerField('ترتیب', default=0)

    class Meta:
        verbose_name = 'آیتم چک‌لیست KPI'
        verbose_name_plural = 'آیتم‌های چک‌لیست KPI'
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


class TaskKPIScore(models.Model):
    """امتیازِ ثبت‌شده‌ی یک KPI روی یک تسکِ مشخص (توسط مدیر در بازبینی)."""

    task = models.ForeignKey(Task, verbose_name='تسک', on_delete=models.CASCADE, related_name='kpi_scores')
    kpi = models.ForeignKey(TaskTypeKPI, verbose_name='KPI', on_delete=models.CASCADE, related_name='scores')
    score = models.PositiveIntegerField('امتیاز', default=0)
    checked_items = models.JSONField('آیتم‌های تیک‌خورده', default=list, blank=True)  # لیست id
    scored_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='بازبین', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    scored_at = models.DateTimeField('زمان امتیاز', auto_now=True)

    class Meta:
        verbose_name = 'امتیاز KPI تسک'
        verbose_name_plural = 'امتیازهای KPI تسک'
        unique_together = ('task', 'kpi')

    def __str__(self):
        return f'{self.task_id}/{self.kpi_id}: {self.score}'


class RecurrenceRule(models.Model):
    """قاعده‌ی تکرارِ تسک — با «تولید تنبل»: همیشه فقط یک تسکِ واقعی + یک پیش‌نما
    (placeholder) جلوتر ساخته می‌شود؛ با انجام‌شدنِ تسکِ فعلی، پیش‌نما واقعی و
    پیش‌نمای بعدی ساخته می‌شود. این‌طور تقویم شلوغ نمی‌شود."""

    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    FREQ_CHOICES = [(DAILY, 'روزانه'), (WEEKLY, 'هفتگی'), (MONTHLY, 'ماهانه')]

    freq = models.CharField('تکرار', max_length=8, choices=FREQ_CHOICES, default=WEEKLY)
    interval = models.PositiveIntegerField('فاصله (هر N)', default=1)
    weekdays = models.CharField('روزهای هفته', max_length=20, blank=True)  # شمسی: شنبه=۰..جمعه=۶، با ویرگول
    start_date = models.DateField('شروع')
    end_date = models.DateField('پایان', null=True, blank=True)
    count = models.PositiveIntegerField('تعداد کل', null=True, blank=True)
    skip_holidays = models.BooleanField('رد کردن تعطیلات', default=True)
    active = models.BooleanField('فعال', default=True)

    organization = models.ForeignKey('accounts.Organization', verbose_name='سازمان', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'قاعده تکرار'
        verbose_name_plural = 'قواعد تکرار'
        base_manager_name = 'all_objects'

    def __str__(self):
        return f'{self.get_freq_display()} ×{self.interval}'

    def save(self, *args, **kwargs):
        stamp_org(self)
        super().save(*args, **kwargs)

    # ── منطق تاریخ بعدی ──
    def _weekday_set(self):
        from core.jalali import g2j
        return {int(x) for x in self.weekdays.split(',') if x.strip().isdigit()}

    @staticmethod
    def _jwd(d):
        """weekday شمسی: شنبه=۰ .. جمعه=۶."""
        from core.jalali import g2j
        return g2j(d).weekday()

    def next_date(self, after):
        """اولین تاریخِ رخدادِ بعدی (با رعایتِ رد کردنِ تعطیلات)."""
        return self._skip(self.raw_next_date(after))

    def raw_next_date(self, after):
        """تاریخِ رخدادِ بعدی بدون رد کردنِ تعطیلات (برای شمارشِ سریعِ نمای تقویم)."""
        from core.jalali import g2j, j2g
        if self.freq == self.DAILY:
            nxt = after + timedelta(days=self.interval)
        elif self.freq == self.WEEKLY:
            wds = self._weekday_set()
            if wds:
                # روزِ بعدیِ عضوِ مجموعه؛ حداکثر تا ۷ روز جلو
                d = after + timedelta(days=1)
                for _ in range(7):
                    if self._jwd(d) in wds:
                        nxt = d
                        break
                    d += timedelta(days=1)
                else:
                    nxt = after + timedelta(days=7 * self.interval)
            else:
                nxt = after + timedelta(days=7 * self.interval)
        else:  # MONTHLY — همان روزِ شمسی در ماهِ بعد
            jt = g2j(after)
            y, m = jt.year, jt.month + self.interval
            y += (m - 1) // 12
            m = (m - 1) % 12 + 1
            day = min(jt.day, 31 if m <= 6 else (30 if m <= 11 else 29))
            nxt = j2g(y, m, day)
        return nxt

    def _skip(self, d):
        """اگر skip_holidays فعال است و روز تعطیل/جمعه بود، به روز کاریِ بعد برو."""
        if not self.skip_holidays:
            return d
        from core.models import Holiday
        for _ in range(14):
            is_fri = self._jwd(d) == 6
            is_off = Holiday.objects.filter(date=d, is_off=True).exists()
            if not is_fri and not is_off:
                return d
            d += timedelta(days=1)
        return d


class TaskComment(models.Model):
    task = models.ForeignKey(Task, verbose_name='تسک', on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='نویسنده', on_delete=models.SET_NULL, null=True)
    body = models.TextField('متن')
    created_at = models.DateTimeField('زمان', auto_now_add=True)

    class Meta:
        verbose_name = 'کامنت تسک'
        verbose_name_plural = 'کامنت‌های تسک'
        ordering = ['created_at']

    def __str__(self):
        return f'کامنت روی {self.task_id}'


class TaskHistory(models.Model):
    """تاریخچهٔ تسک: ساخت/ویرایش/حذف/بازیابی + اینکه چه فیلدهایی تغییر کرده‌اند.

    `changes` = {نامِ نمایشیِ فیلد: [قدیم, جدید]} — برای دیدنِ «نسخهٔ قبلی چه بود».
    """
    CREATED = 'created'
    UPDATED = 'updated'
    DELETED = 'deleted'
    RESTORED = 'restored'
    ACTION_CHOICES = [
        (CREATED, 'ساخته شد'), (UPDATED, 'ویرایش شد'),
        (DELETED, 'حذف شد'), (RESTORED, 'بازیابی شد'),
    ]

    task = models.ForeignKey(Task, verbose_name='تسک', on_delete=models.CASCADE, related_name='history')
    action = models.CharField('عمل', max_length=10, choices=ACTION_CHOICES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='کاربر', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    changes = models.JSONField('تغییرات', default=dict, blank=True)
    created_at = models.DateTimeField('زمان', auto_now_add=True)

    class Meta:
        verbose_name = 'تاریخچهٔ تسک'
        verbose_name_plural = 'تاریخچهٔ تسک‌ها'
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.get_action_display()} — {self.task_id}'


class ReportMonthStrategy(TimeStampedModel):
    """سکشنِ «ماهِ گزارش» در بردِ سئوِ پروژه + استراتژیِ همان ماه.

    وجودِ رکورد یعنی آن (سال، ماه) به‌عنوان یک سکشن برای پروژه ساخته شده (حتی اگر
    استراتژی خالی باشد یا هنوز تسکی نداشته باشد). `description` = متنِ استراتژیِ ماه.
    """
    organization = models.ForeignKey('accounts.Organization', verbose_name='سازمان', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    project = models.ForeignKey('projects.Project', verbose_name='پروژه', on_delete=models.CASCADE, related_name='report_strategies')
    year = models.PositiveSmallIntegerField('سالِ گزارش')
    month = models.PositiveSmallIntegerField('ماهِ گزارش', choices=Task.REPORT_MONTH_CHOICES)
    description = models.TextField('استراتژی', blank=True)

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'استراتژیِ ماهِ گزارش'
        verbose_name_plural = 'استراتژی‌های ماهِ گزارش'
        base_manager_name = 'all_objects'
        unique_together = ('project', 'year', 'month')
        ordering = ['-year', '-month']

    def save(self, *args, **kwargs):
        if self.organization_id is None and self.project_id:
            self.organization_id = self.project.organization_id
        stamp_org(self)
        super().save(*args, **kwargs)

    @property
    def label(self):
        return f'{dict(Task.REPORT_MONTH_CHOICES).get(self.month, self.month)} {self.year}'

    def __str__(self):
        return f'{self.project_id} — {self.label}'


class ReportPeriod(TimeStampedModel):
    """ماهِ گزارشِ تعریف‌شده در تنظیمات (سطحِ سازمان) — «مرداد ۱۴۰۵».

    منبعِ واحدِ ماه‌های گزارش: مودالِ تسک، بردِ سئوِ پروژه و فیلترها همه از همین می‌خوانند
    تا ساختارِ همهٔ پروژه‌ها یکسان بماند و ماهِ گزارش دستی/اشتباه وارد نشود.
    """
    organization = models.ForeignKey('accounts.Organization', verbose_name='سازمان', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    year = models.PositiveSmallIntegerField('سال')
    month = models.PositiveSmallIntegerField('ماه', choices=Task.REPORT_MONTH_CHOICES)
    order = models.IntegerField('ترتیب', default=0, db_index=True)

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'ماهِ گزارش'
        verbose_name_plural = 'ماه‌های گزارش'
        base_manager_name = 'all_objects'
        unique_together = ('organization', 'year', 'month')
        ordering = ['order', '-year', '-month']

    def save(self, *args, **kwargs):
        stamp_org(self)
        super().save(*args, **kwargs)

    @property
    def label(self):
        return f'{dict(Task.REPORT_MONTH_CHOICES).get(self.month, self.month)} {self.year}'

    @property
    def value(self):
        return f'{self.year}-{self.month}'

    def __str__(self):
        return self.label
