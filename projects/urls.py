"""نقشه‌ی URL پروژه‌ها + API دسترسی‌ها."""
from django.urls import path

from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.ProjectListView.as_view(), name='list'),
    path('add/', views.ProjectCreateView.as_view(), name='add'),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.ProjectUpdateView.as_view(), name='edit'),
    path('<int:pk>/archive/', views.ProjectArchiveView.as_view(), name='archive'),
    path('<int:pk>/restore/', views.ProjectRestoreView.as_view(), name='restore'),

    # API دسترسی‌ها
    path('api/<int:pk>/credentials/', views.credential_create, name='credential_create'),
    path('api/credentials/<int:pk>/reveal/', views.credential_reveal, name='credential_reveal'),
    path('api/credentials/<int:pk>/', views.credential_delete, name='credential_delete'),

    # فایل‌ها
    path('api/<int:pk>/files/', views.project_files, name='files'),
    path('api/files/<int:pk>/', views.project_file_delete, name='file_delete'),

    # دسترسی به همکاران
    path('api/<int:pk>/members/', views.project_members, name='members'),
]
