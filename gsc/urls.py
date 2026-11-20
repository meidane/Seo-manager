from django.urls import path

from . import views

app_name = 'gsc'

urlpatterns = [
    path('settings/gsc/', views.page, name='page'),
    path('settings/gsc/save/', views.save, name='save'),
    path('settings/gsc/test/', views.test, name='test'),
    path('settings/gsc/sync/', views.sync_now, name='sync'),
    path('settings/gsc/status/', views.status, name='status'),
    path('settings/gsc/site/<int:pk>/', views.site_update, name='site_update'),
    path('gsc/api/task/<int:pk>/', views.task_api, name='task_api'),
    path('gsc/api/project/<int:pk>/', views.project_api, name='project_api'),
]
