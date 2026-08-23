"""نقشه‌ی URL فضای شخصی — `/personal/` + `/personal/api/...`."""
from django.urls import path

from . import api, views

app_name = 'personal'

urlpatterns = [
    path('', views.PersonalDashboardView.as_view(), name='index'),
    path('api/tasks/', api.ptask_add, name='ptask_add'),
    path('api/tasks/<int:pk>/', api.ptask_detail, name='ptask_detail'),
    path('api/tasks/reorder/', api.ptask_reorder, name='ptask_reorder'),
    path('api/habits/', api.habit_add, name='habit_add'),
    path('api/habits/<int:pk>/', api.habit_detail, name='habit_detail'),
    path('api/habits/toggle/', api.habit_toggle, name='habit_toggle'),
    path('api/goals/', api.goal_add, name='goal_add'),
    path('api/goals/<int:pk>/', api.goal_detail, name='goal_detail'),
]
