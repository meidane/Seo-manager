"""نقشه‌ی URL احراز هویت + مدیریت افراد و تیم‌ها."""
from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('signup/', views.signup, name='signup'),
    path('settings/switch-org/', views.switch_org, name='switch_org'),

    # مدیریت افراد و تیم‌ها (چندشرکتی — ساده)
    path('settings/people/', views.PeopleView.as_view(), name='people'),
    path('settings/people/api/team/', views.team_create, name='team_create'),
    path('settings/people/api/team/<int:pk>/', views.team_edit, name='team_edit'),
    path('settings/people/api/person/', views.person_create, name='person_create'),
    path('settings/people/api/person/<int:pk>/', views.person_edit, name='person_edit'),
    path('settings/people/api/invite/', views.person_invite, name='person_invite'),
    path('settings/people/api/role/', views.role_create, name='role_create'),
    path('settings/people/api/role/<int:pk>/', views.role_edit, name='role_edit'),

    # توکن‌های API (افزونه/اتوماسیون/AI)
    path('settings/api-tokens/', views.APITokenListView.as_view(), name='api_tokens'),
    path('settings/api-tokens/api/create/', views.token_create, name='token_create'),
    path('settings/api-tokens/api/<int:pk>/', views.token_revoke, name='token_revoke'),
]
