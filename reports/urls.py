"""نقشه‌ی URL گزارش‌ها + API + لینک عمومی."""
from django.urls import path

from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.ReportListView.as_view(), name='list'),
    path('add/', views.ReportCreateView.as_view(), name='add'),
    path('<int:pk>/', views.ReportDetailView.as_view(), name='detail'),

    # API
    path('api/<int:pk>/pull-tasks/', views.pull_tasks, name='pull_tasks'),
    path('api/<int:pk>/items/', views.add_items, name='add_items'),
    path('api/<int:pk>/manual/', views.add_manual, name='add_manual'),
    path('api/<int:pk>/reorder/', views.reorder, name='reorder'),
    path('api/<int:pk>/update/', views.report_update, name='update'),
    path('api/<int:pk>/upload-image/', views.upload_image, name='upload_image'),
    path('api/items/<int:pk>/', views.item_edit, name='item_edit'),
]
