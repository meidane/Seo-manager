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
    current_rank = models.PositiveIntegerField('جایگاه فعلی', null=True, blank=True)
    target_rank = models.PositiveIntegerField('جایگاه هدف', null=True, blank=True)
    published_url = models.URLField('لینک انتشار', blank=True)
    source_url = models.URLField('آدرس مطلب فعلی', blank=True)  # فقط آپدیت

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
        label = dict(self.TYPE_CHOICES).get(self.task_type, '')
        if self.task_type == self.UPDATE and self.update_type:
            label += ' ' + dict(self.UPDATE_TYPE_CHOICES).get(self.update_type, '')
        return label

    @property
    def color_rgb(self):
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
