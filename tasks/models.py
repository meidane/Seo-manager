"""مدل تسک — قلب سیستم.

یک مدل واحد با فیلدهای null=True؛ نمایش شرطی فیلدها بر اساس نوع تسک در فرانت
با `static/js/task-schema.js` انجام می‌شود (همان منبع، هم برای مودال هم اعتبارسنجی).

قانون تاریخ: planned_date و done_date میلادی‌اند؛ تبدیل شمسی فقط در نمایش.
"""
from datetime import date, time

from django.conf import settings
from django.db import models
from django.urls import reverse

from core.models import TimeStampedModel

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
    DONE = 'done'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (TODO, 'در انتظار'), (DOING, 'در حال انجام'),
        (DONE, 'انجام شده'), (CANCELLED, 'لغو شده'),
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
    planned_date = models.DateField('تاریخ برنامه')
    planned_time = models.TimeField('ساعت', default=time(8, 0))
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

    # ── رپورتاژ ──
    media_name = models.CharField('نام رسانه', max_length=150, blank=True)
    media_cost = models.DecimalField('هزینه رپورتاژ', max_digits=14, decimal_places=0, null=True, blank=True)
    anchor_text = models.CharField('انکر تکست', max_length=255, blank=True)
    target_url = models.URLField('لینک مقصد', blank=True)

    # ── لینک‌سازی ──
    link_type = models.CharField('نوع لینک', max_length=12, choices=LINK_TYPE_CHOICES, blank=True)
    link_count = models.PositiveIntegerField('تعداد لینک', null=True, blank=True)

    # ── بازبینی (آماده‌سازی فاز ۳) ──
    review_status = models.CharField('وضعیت بازبینی', max_length=12, choices=REVIEW_CHOICES, default=UNREVIEWED)
    review_note = models.TextField('یادداشت بازبینی', blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='بازبین', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    reviewed_at = models.DateTimeField('زمان بازبینی', null=True, blank=True)
    ai_checked_at = models.DateTimeField('بررسی هوش مصنوعی', null=True, blank=True)  # فاز ۳
    ai_score = models.PositiveIntegerField('امتیاز AI', null=True, blank=True)       # فاز ۳
    ai_report = models.JSONField('گزارش AI', null=True, blank=True)                  # فاز ۳

    class Meta:
        verbose_name = 'تسک'
        verbose_name_plural = 'تسک‌ها'
        ordering = ['planned_date', 'planned_time']
        indexes = [
            models.Index(fields=['project', 'status', 'planned_date']),
            models.Index(fields=['assignee', 'status', 'done_date']),
            models.Index(fields=['status', 'planned_date']),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('tasks:list') + f'?open={self.pk}'

    @property
    def is_overdue(self):
        return self.status in (self.TODO, self.DOING) and self.planned_date < date.today()

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
            'done': self.is_done,
            'overdue': self.is_overdue,
            'project': self.project.name,
            'project_id': self.project_id,
            'assignee': self.assignee.full_name if self.assignee else '',
            'assignee_id': self.assignee_id,
            'word_count': self.word_count,
            'published_url': self.published_url,
            'estimate_minutes': self.estimate_minutes,
        }


class TaskTypeDef(TimeStampedModel):
    """نوع تسک سفارشی — کاربر خودش تعریف می‌کند.

    مستقل از انواع built-in مدل Task است. هر نوع مجموعه‌ای از فیلدهای سفارشی
    دارد که مقادیرشان در Task.custom (JSON) ذخیره می‌شوند. فیلدهای هسته‌ایِ Task
    (عنوان، تاریخ برنامه، وضعیت، word_count و…) دست‌نخورده می‌مانند تا داشبورد نشکند.
    """

    name = models.CharField('نام نوع', max_length=80, unique=True)
    color = models.CharField('رنگ', max_length=7, default='#4183F2')
    icon = models.CharField('آیکن (اموجی)', max_length=8, blank=True)
    order = models.PositiveIntegerField('ترتیب', default=0)
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        verbose_name = 'نوع تسک سفارشی'
        verbose_name_plural = 'انواع تسک سفارشی'
        ordering = ['order', 'name']

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
    KIND_CHOICES = [
        (TEXT, 'متن کوتاه'), (TEXTAREA, 'متن بلند'), (NUMBER, 'عدد'),
        (CHECKBOX, 'چک‌باکس'), (SELECT, 'انتخابی'), (URL, 'لینک'), (DATE, 'تاریخ'),
    ]

    type_def = models.ForeignKey(TaskTypeDef, verbose_name='نوع', on_delete=models.CASCADE, related_name='fields')
    key = models.CharField('کلید', max_length=40, blank=True)  # خودکار: f<id>
    label = models.CharField('برچسب', max_length=120)
    kind = models.CharField('نوع فیلد', max_length=12, choices=KIND_CHOICES, default=TEXT)
    options = models.CharField('گزینه‌ها (با ویرگول)', max_length=500, blank=True)  # فقط select
    placeholder = models.CharField('راهنما', max_length=120, blank=True)
    required = models.BooleanField('اجباری', default=False)
    show_to_client = models.BooleanField('نمایش به مشتری', default=True)
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
            'required': self.required, 'show_to_client': self.show_to_client,
        }


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
