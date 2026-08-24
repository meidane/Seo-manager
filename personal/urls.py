"""نقشه‌ی URL فضای شخصی — `/personal/` + `/personal/api/...`.

تسک‌های شخصی done/حذف/تاریخ/تایمر/ویرایش از همان `tasks/api.py` می‌آیند (reuse)؛
اینجا فقط ساخت/جابه‌جایی + عادت/هدف.
"""
from django.urls import path

from . import api, views

app_name = 'personal'

urlpatterns = [
    path('', views.PersonalDashboardView.as_view(), name='index'),
    path('api/tasks/', api.ptask_add, name='ptask_add'),
    path('api/tasks/reorder/', api.ptask_reorder, name='ptask_reorder'),
    path('api/tasks/<int:pk>/plan/', api.ptask_plan, name='ptask_plan'),
    path('api/tasks/<int:pk>/move/', api.ptask_move, name='ptask_move'),
    path('api/tasks/<int:pk>/done/', api.ptask_done, name='ptask_done'),
    path('api/habits/', api.habit_add, name='habit_add'),
    path('api/habits/<int:pk>/', api.habit_detail, name='habit_detail'),
    path('api/habits/toggle/', api.habit_toggle, name='habit_toggle'),
    path('api/goals/', api.goal_add, name='goal_add'),
    path('api/goals/<int:pk>/', api.goal_detail, name='goal_detail'),
]
