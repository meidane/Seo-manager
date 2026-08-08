"""نقشه‌ی URL احراز هویت + مدیریت افراد و تیم‌ها."""
from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # مدیریت افراد و تیم‌ها (چندشرکتی — ساده)
    path('settings/people/', views.PeopleView.as_view(), name='people'),
    path('settings/people/api/team/', views.team_create, name='team_create'),
    path('settings/people/api/team/<int:pk>/', views.team_edit, name='team_edit'),
    path('settings/people/api/person/', views.person_create, name='person_create'),
    path('settings/people/api/person/<int:pk>/', views.person_edit, name='person_edit'),
]
