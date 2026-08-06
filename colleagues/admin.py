from django.contrib import admin

from .models import Colleague


@admin.register(Colleague)
class ColleagueAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'roles', 'status', 'join_date')
    list_filter = ('status',)
    search_fields = ('full_name', 'email', 'phone')
