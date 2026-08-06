from django.contrib import admin

from .models import Task, TaskComment


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'assignee', 'task_type', 'status', 'planned_date', 'done_date')
    list_filter = ('task_type', 'status', 'review_status')
    search_fields = ('title', 'seo_title')
    date_hierarchy = 'planned_date'


admin.site.register(TaskComment)
