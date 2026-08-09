"""نقشه‌ی URL تسک‌ها + API."""
from django.urls import path

from . import api, views

app_name = 'tasks'

urlpatterns = [
    path('', views.TaskListView.as_view(), name='list'),
    path('review/', views.TaskReviewView.as_view(), name='review'),

    # API
    path('api/formdata/', api.form_data, name='api_formdata'),
    path('api/', api.task_create, name='api_create'),
    path('api/<int:pk>/', api.task_detail, name='api_detail'),
    path('api/<int:pk>/status/', api.task_status, name='api_status'),
    path('api/<int:pk>/timer/', api.task_timer, name='api_timer'),
    path('api/<int:pk>/review/', api.task_review, name='api_review'),
    path('api/<int:pk>/comments/', api.task_comments, name='api_comments'),
    path('api/comment/<int:pk>/', api.task_comment_edit, name='api_comment_edit'),
    path('api/<int:pk>/kpis/', api.task_kpis, name='api_kpis'),
    path('api/<int:pk>/kpi-score/', api.task_kpi_score, name='api_kpi_score'),
    path('api/recurrence/<int:pk>/', api.recurrence_delete, name='api_recurrence_delete'),
    path('api/bulk/', api.task_bulk, name='api_bulk'),
]
