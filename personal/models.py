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


class Goal(models.Model):
    """هدف — با تایم‌لاینِ ساده‌ی «چند روزش گذشته»."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='goals')
    title = models.CharField('عنوان', max_length=200)
    description = models.TextField('توضیحات', blank=True)
    start_date = models.DateField('شروع')
    end_date = models.DateField('پایان')
    created_at = models.DateTimeField('ایجاد', auto_now_add=True)

    class Meta:
        verbose_name = 'هدف'
        verbose_name_plural = 'اهداف'
        ordering = ['-created_at']

    def __str__(self):
        return self.title
