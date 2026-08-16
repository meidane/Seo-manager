from django.contrib import admin

from .models import Task, TaskComment, TaskHistory, TaskTypeDef, TaskTypeField


class FieldInline(admin.TabularInline):
    model = TaskTypeField
    extra = 1


@admin.register(TaskTypeDef)
class TaskTypeDefAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'is_active', 'order')
    inlines = [FieldInline]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'assignee', 'task_type', 'status', 'planned_date', 'done_date')
    list_filter = ('task_type', 'status', 'review_status')
    search_fields = ('title', 'seo_title')
    date_hierarchy = 'planned_date'


admin.site.register(TaskComment)


@admin.register(TaskHistory)
class TaskHistoryAdmin(admin.ModelAdmin):
    list_display = ('task', 'action', 'user', 'created_at')
    list_filter = ('action',)
