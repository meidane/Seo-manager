"""مدل‌های «فضای شخصی» — کاملاً خصوصی، اسکوپ‌شده به کاربر (نه سازمان).

این اپ عمداً tenant-scoped **نیست**؛ هر رکورد فقط به `user` تعلق دارد و همه‌ی
کوئری‌ها در ویو/API با `user=request.user` فیلتر می‌شوند. دسترسی هم فقط برای
سوپریوزر باز است (`personal.access.admin_only`). داده‌ی شخصی است — هیچ‌جای دیگری
از سیستم به این مدل‌ها وصل نمی‌شود.
"""
from datetime import timedelta

from django.conf import settings
from django.db import models

from core.jalali import g2j


def week_saturday(d):
    """شنبه‌ی هفته‌ی شمسیِ حاویِ تاریخِ میلادیِ d (هفته = شنبه تا جمعه)."""
    return d - timedelta(days=g2j(d).weekday())  # شمسی: شنبه=۰ .. جمعه=۶


class PersonalTask(models.Model):
    """تسکِ شخصی — هم «اینباکسِ» ثبتِ سریع (به تفکیکِ هفته) و هم «تسکِ روزانه»
    (وقتی `planned_date` بگیرد)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='personal_tasks')
    title = models.CharField('عنوان', max_length=255)
    note = models.TextField('توضیحات', blank=True)
    kind = models.CharField('نوع', max_length=40, blank=True)  # برچسبِ آزاد
    week_start = models.DateField('شنبه‌ی هفته', db_index=True)  # هفته‌ی ثبت در اینباکس
    planned_date = models.DateField('تاریخِ برنامه', null=True, blank=True, db_index=True)
    done = models.BooleanField('انجام‌شده', default=False)
    playing = models.BooleanField('در حالِ اجرا', default=False)  # فوکوسِ فعلی (فقط یکی)
    order = models.IntegerField('ترتیب', default=0, db_index=True)  # جابه‌جاییِ باکسِ روزانه
    created_at = models.DateTimeField('ایجاد', auto_now_add=True)
    updated_at = models.DateTimeField('ویرایش', auto_now=True)

    class Meta:
        verbose_name = 'تسک شخصی'
        verbose_name_plural = 'تسک‌های شخصی'
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


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
