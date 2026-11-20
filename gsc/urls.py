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
    path('settings/gsc/key/', views.cred_add, name='cred_add'),
    path('settings/gsc/key/<int:pk>/delete/', views.cred_delete, name='cred_delete'),
    path('gsc/api/task/<int:pk>/', views.task_api, name='task_api'),
    path('gsc/api/project/<int:pk>/', views.project_api, name='project_api'),
    path('gsc/api/project/<int:pk>/unseen/', views.unseen_api, name='unseen_api'),
    path('gsc/api/project/<int:pk>/inspect/', views.inspect_api, name='inspect_api'),
    path('gsc/api/project/<int:pk>/inventory/', views.inventory_api, name='inventory_api'),
    path('gsc/api/project/<int:pk>/export/', views.project_export, name='project_export'),
    path('gsc/api/task/<int:pk>/export/', views.task_export, name='task_export'),
]
