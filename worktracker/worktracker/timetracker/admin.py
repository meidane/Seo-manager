from django.contrib import admin
from . import models

@admin.register(models.WorkRecord)
class WorkRecordAdmin(admin.ModelAdmin):
    list_display = ('user','start','end','inactive_time','sum_words')
    raw_id_fields = ('p_record',)
    list_filter = ('user',)

@admin.register(models.UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user','in_person',)

@admin.register(models.VocationRequest)
class VocationRequestAdmin(admin.ModelAdmin):
    list_display = ('user','start','v_type',)


# @admin.register(models.UserAvailability)
# class UserAvailabilityAdmin(admin.ModelAdmin):
#     pass

@admin.register(models.RecordedApp)
class RecordedAppAdmin(admin.ModelAdmin):
    list_display = ('name','is_browser',)

@admin.register(models.AppRecord)
class AppRecordAdmin(admin.ModelAdmin):
    list_display = ('work_record','app','website','w_time')

@admin.register(models.RecordedWebsite)
class RecordedWebsiteAdmin(admin.ModelAdmin):
    list_display = ('name','domain')

@admin.register(models.SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ('allowed_inactive_time','allowed_inactive_time_in_person')



@admin.register(models.RecordInactiveTime)
class RecordInactiveTimeAdmin(admin.ModelAdmin):
    list_display = ('work_record','start','end')
    raw_id_fields = ('work_record',)
    
@admin.register(models.UserError)
class UserErrorTimeAdmin(admin.ModelAdmin):
    list_display = ('user','error_text','created')