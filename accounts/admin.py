"""ثبت مدل‌های حساب در ادمین جنگو (فقط برای مدیریت پایه)."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Team, User

admin.site.register(User, UserAdmin)
admin.site.register(Team)
