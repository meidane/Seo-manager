"""نقشه‌ی URL اپ core (تنظیمات)."""
from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('holidays/', views.HolidayListView.as_view(), name='holidays'),
    path('columns/', views.ColumnsSettingsView.as_view(), name='columns'),
    path('columns/api/save/', views.columns_save, name='columns_save'),
    path('columns/api/reset/', views.columns_reset, name='columns_reset'),

    path('report-months/', views.ReportMonthsView.as_view(), name='report_months'),
    path('report-months/api/add/', views.report_month_add, name='report_month_add'),
    path('report-months/api/reorder/', views.report_month_reorder, name='report_month_reorder'),
    path('report-months/api/<int:pk>/', views.report_month_delete, name='report_month_delete'),
]
