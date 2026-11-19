from django.urls import path

from . import views

app_name = 'skills'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/', views.api_save, name='api_save'),
    path('api/detect/', views.api_detect, name='api_detect'),
    path('api/starters/', views.api_starters, name='api_starters'),
    path('api/<int:pk>/', views.api_detail, name='api_detail'),
    path('api/<int:pk>/restore/<int:vid>/', views.api_restore, name='api_restore'),
    path('api/<int:pk>/duplicate/', views.api_duplicate, name='api_duplicate'),
    path('api/<int:pk>/files/', views.api_files, name='api_files'),
    path('api/files/<int:fid>/', views.api_file, name='api_file'),
    path('f/<str:token>/', views.public_file, name='public_file'),
    path('f/<str:token>/<path:name>', views.public_file, name='public_file_named'),
]
