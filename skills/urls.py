from django.urls import path

from . import views

app_name = 'skills'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/', views.api_save, name='api_save'),
    path('api/<int:pk>/', views.api_detail, name='api_detail'),
    path('api/<int:pk>/restore/<int:vid>/', views.api_restore, name='api_restore'),
]
