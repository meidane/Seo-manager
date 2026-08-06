"""نقشه‌ی URL اپ core (تنظیمات)."""
from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('holidays/', views.HolidayListView.as_view(), name='holidays'),
]
