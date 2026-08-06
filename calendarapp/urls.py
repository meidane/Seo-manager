"""نقشه‌ی URL تقویم + API."""
from django.urls import path

from . import views

app_name = 'calendarapp'

urlpatterns = [
    path('', views.CalendarView.as_view(), name='index'),
    path('api/', views.calendar_api, name='api'),
    path('api/workload/', views.workload_api, name='workload'),
]
