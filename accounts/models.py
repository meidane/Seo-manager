"""مدل‌های کاربر و تیم.

`User` سفارشی است تا فاز ۳ (چندتیمی) بدون مهاجرت دردناک پشتیبانی شود؛
فیلد `team` از همین ابتدا ساخته می‌شود ولی فعلاً استفاده‌ای ندارد.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Team(models.Model):
    """تیم — آماده‌سازی برای حالت چندتیمی فاز ۳."""

    name = models.CharField('نام تیم', max_length=120)
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)

    class Meta:
        verbose_name = 'تیم'
        verbose_name_plural = 'تیم‌ها'

    def __str__(self):
        return self.name


class User(AbstractUser):
    """کاربر سیستم. برای ورود به پنل مدیریت استفاده می‌شود."""

    team = models.ForeignKey(
        Team,
        verbose_name='تیم',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
    )
    avatar = models.ImageField('آواتار', upload_to='avatars/', null=True, blank=True)

    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'

    def __str__(self):
        return self.get_full_name() or self.username
