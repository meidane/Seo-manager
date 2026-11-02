from django.urls import path

from . import views

app_name = 'filebox'

urlpatterns = [
    path('files/', views.page, name='page'),
    path('files/api/', views.api_list, name='api_list'),
    path('files/api/<int:pk>/', views.api_detail, name='api_detail'),
    path('f/<str:token>/', views.public, name='public'),
]
