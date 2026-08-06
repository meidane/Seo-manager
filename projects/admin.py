from django.contrib import admin

from .models import Credential, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'status', 'manager', 'amount')
    list_filter = ('status',)
    search_fields = ('name', 'domain', 'client_name')


@admin.register(Credential)
class CredentialAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'username')
    search_fields = ('title', 'username')
