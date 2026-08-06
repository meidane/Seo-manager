"""ثبت مدل‌های core در ادمین."""
from django.contrib import admin

from .models import ActivityLog, Attachment, Holiday


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'kind', 'is_off')
    list_filter = ('kind', 'is_off')
    search_fields = ('title',)
    ordering = ('date',)


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'content_type', 'object_id', 'uploaded_at')


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('actor', 'verb', 'created_at')
    list_filter = ('verb',)
