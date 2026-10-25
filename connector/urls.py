from django.urls import path

from . import api, views

app_name = 'connector'

urlpatterns = [
    path('settings/chatgpt-sync/', views.SyncPageView.as_view(), name='page'),
    path('connector/api/state/', api.state, name='state'),
    path('connector/api/file/', api.file, name='file'),
    path('connector/api/file/delete/', api.file_delete, name='file_delete'),
]
