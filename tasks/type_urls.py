"""نقشه‌ی URL بخش مدیریت انواع تسک سفارشی."""
from django.urls import path

from . import type_views as v

app_name = 'task_types'

urlpatterns = [
    path('', v.TaskTypeListView.as_view(), name='list'),
    path('<int:pk>/', v.TaskTypeEditView.as_view(), name='edit'),

    # API
    path('api/', v.type_create, name='create'),
    path('api/<int:pk>/', v.type_edit, name='type_edit'),
    path('api/<int:pk>/fields/', v.field_create, name='field_create'),
    path('api/<int:pk>/reorder/', v.field_reorder, name='field_reorder'),
    path('api/fields/<int:pk>/', v.field_edit, name='field_edit'),
]
