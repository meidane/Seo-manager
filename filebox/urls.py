from django.urls import path

from . import views

app_name = 'filebox'

urlpatterns = [
    path('files/', views.page, name='page'),
    path('files/api/', views.api_list, name='api_list'),
    path('files/api/<int:pk>/', views.api_detail, name='api_detail'),
    path('files/api/folders/', views.folder_create, name='folder_create'),
    path('files/api/folders/<int:pk>/', views.folder_detail, name='folder_detail'),
    path('f/<str:token>/', views.public, name='public'),  # لینکِ قدیمیِ توکنی
    path('f/<str:org>/<path:path>', views.public_path, name='public_path'),  # لینکِ ثابت با نام و پسوند
]
