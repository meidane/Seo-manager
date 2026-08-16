from django.urls import path , re_path , include
from . import views


urlpatterns = [
    path('' , views.index , name='index'),
    path('ajax/start-recording',views.start_recording , name='start_recording'),
    path('ajax/stop-recording',views.stop_recording , name='stop_recording'),
    path('ajax/vocation-request',views.vocation_request , name='vocation_request'),

    path('users/<str:username>/',views.user_profile,name='user_profile'),
    path('users/<str:username>/save_courses_image',views.save_courses_image ,name='save_courses_image'),
    path('users/<str:username>/show-logs',views.user_logs ,name='user_logs'),

    path('ajax/load-more-day-records',views.load_more_day_records,name='load_more_day_records'),
    path('ajax/calc-reminded-vocation',views.calc_reminded_vocation,name='calc_reminded_vocation'),
    path('ajax/update-users-last-record',views.update_users_last_record ,name='update_users_last_record'),
    path('ajax/update-record-time',views.update_record_time ,name='update_record_time'),
    path('ajax/check-last-record-status',views.check_last_record_status ,name='check_last_record_status'),
    path('ajax/sum-month-report',views.sum_month_report ,name='sum_month_report'),
    path('ajax/sum-profile-report',views.sum_profile_report ,name='sum_profile_report'),
    path('ajax/delete-availability-time',views.delete_availability_time ,name='delete_availability_time'),
    path('ajax/add-availability-time',views.add_availability_time ,name='add_availability_time'),
   
    path('ajax/delete-user-record',views.delete_user_record ,name='delete_user_record'),
    
]
