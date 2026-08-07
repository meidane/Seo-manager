from django.contrib import admin

from .models import Report, ReportItem


class ItemInline(admin.TabularInline):
    model = ReportItem
    extra = 0


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'date_from', 'date_to', 'status', 'is_public')
    list_filter = ('status', 'is_public')
    inlines = [ItemInline]
