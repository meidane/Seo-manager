"""مدل‌های «فضای شخصی» — عادت‌ها و اهداف (کاملاً خصوصی، اسکوپ‌شده به کاربر).

تسک‌های شخصی (اینباکس/روزانه) **مدلِ جدا ندارند**؛ همان `tasks.Task`اند با نوعِ
«شخصی» (`TaskTypeDef` که کاربر می‌سازد)، در پروژهٔ شخصیِ خودکارِ همکار
(`Project.personal_owner`، فقط خودش می‌بیند) — پس در تقویم/لیست هم فقط برای admin
دیده می‌شوند بدونِ سیستمِ موازی. فقط عادت/هدف اینجا مدلِ اختصاصی دارند (معادلی در
سیستمِ تسک ندارند). این اپ عمداً tenant-scoped **نیست**؛ اسکوپِ هر رکورد `user` است.
دسترسی فقط برای یوزرِ `admin` (`personal.access.admin_only`).
"""
from datetime import timedelta

from django.conf import settings
from django.db import models

from core.jalali import g2j


def week_saturday(d):
    """شنبه‌ی هفته‌ی شمسیِ حاویِ تاریخِ میلادیِ d (هفته = شنبه تا جمعه)."""
    return d - timedelta(days=g2j(d).weekday())  # شمسی: شنبه=۰ .. جمعه=۶


class Habit(models.Model):
    """عادت (هبیت) — مثبت (سبز) یا منفی (قرمز)، با روزهای هفته‌ی هدف."""

    GOOD = 'good'
    BAD = 'bad'
    POLARITY_CHOICES = [(GOOD, 'مثبت'), (BAD, 'منفی')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='habits')
    title = models.CharField('عنوان', max_length=120)
    weekdays = models.CharField('روزهای هفته', max_length=20, blank=True)  # شمسی شنبه=۰..جمعه=۶، با ویرگول
    polarity = models.CharField('قطبیت', max_length=4, choices=POLARITY_CHOICES, default=GOOD)
    active = models.BooleanField('فعال', default=True)
    order = models.IntegerField('ترتیب', default=0, db_index=True)
    created_at = models.DateTimeField('ایجاد', auto_now_add=True)

    class Meta:
        verbose_name = 'عادت'
        verbose_name_plural = 'عادت‌ها'
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

    def weekday_set(self):
        return {int(x) for x in self.weekdays.split(',') if x.strip().isdigit()}


class HabitLog(models.Model):
    """رعایتِ یک عادت در یک روزِ مشخص (تیک)."""

    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='logs')
    date = models.DateField('تاریخ')
    done = models.BooleanField('رعایت‌شده', default=True)

    class Meta:
        verbose_name = 'لاگِ عادت'
        verbose_name_plural = 'لاگ‌های عادت'
        unique_together = ('habit', 'date')

    def __str__(self):
        return f'{self.habit_id}@{self.date}'


class DailyPlan(models.Model):
    """رکوردِ «این تسک برای این روز برنامه‌ریزی شده بود» — تاریخچهٔ روزانه.

    با «انتقال به فردا» رکوردِ روزِ اصلی پاک نمی‌شود (فقط رکوردِ روزِ جدید اضافه می‌شود)،
    تا درصدِ برنامه‌ریزی/انجامِ هر روز در نمودارِ باکسِ روزانه حفظ بماند. `done` = آیا در
    همان روز انجام شد (per-day، نه وضعیتِ سراسریِ تسک).
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_plans')
    task = models.ForeignKey('tasks.Task', on_delete=models.CASCADE, related_name='daily_plans')
    date = models.DateField('تاریخ', db_index=True)
    done = models.BooleanField('انجام‌شده در همان روز', default=False)

    class Meta:
        verbose_name = 'برنامهٔ روزانه'
        verbose_name_plural = 'برنامه‌های روزانه'
        unique_together = ('task', 'date')

    def __str__(self):
        return f'{self.task_id}@{self.date}'


class Goal(models.Model):
    """هدف — با تایم‌لاینِ ساده‌ی «چند روزش گذشته» + رنگ (برای آیکنِ 🎯 روی تسکِ وصل‌شده)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='goals')
    title = models.CharField('عنوان', max_length=200)
    description = models.TextField('توضیحات', blank=True)  # HTML پاکسازی‌شده (TinyMCE)
    color = models.CharField('رنگ', max_length=7, default='#6366F1')
    start_date = models.DateField('شروع')
    end_date = models.DateField('پایان')
    created_at = models.DateTimeField('ایجاد', auto_now_add=True)

    class Meta:
        verbose_name = 'هدف'
        verbose_name_plural = 'اهداف'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class GoalLink(models.Model):
    """وصلِ یک تسکِ شخصی به یک هدف (فقط در فضای شخصی؛ مدلِ Task دست‌نخورده می‌ماند).
    هر تسک حداکثر به یک هدف وصل است (OneToOne)."""

    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name='links')
    task = models.OneToOneField('tasks.Task', on_delete=models.CASCADE, related_name='goal_link')
    order = models.IntegerField('ترتیب', default=0, db_index=True)

    class Meta:
        verbose_name = 'وصلِ تسک به هدف'
        verbose_name_plural = 'وصل‌های تسک به هدف'
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.task_id}→{self.goal_id}'
