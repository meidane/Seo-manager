"""نقشه‌ی URL احراز هویت + مدیریت افراد و تیم‌ها."""
from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('signup/', views.signup, name='signup'),
    path('settings/switch-org/', views.switch_org, name='switch_org'),

    # هابِ تنظیمات (تکِ لینکِ سایدبار) + ویرایشِ نامِ سازمان
    path('settings/', views.SettingsHomeView.as_view(), name='settings_home'),
    path('settings/api/organization/', views.organization_edit, name='organization_edit'),

    # تیم‌ها و نقش‌های سفارشی (خودِ «افراد» به colleagues:list منتقل شد)
    path('settings/people/', views.PeopleView.as_view(), name='people'),
    path('settings/people/api/team/', views.team_create, name='team_create'),
    path('settings/people/api/team/<int:pk>/', views.team_edit, name='team_edit'),
    path('settings/people/api/person/<int:pk>/', views.person_edit, name='person_edit'),
    path('settings/people/api/role/', views.role_create, name='role_create'),
    path('settings/people/api/role/<int:pk>/', views.role_edit, name='role_edit'),

    # توکن‌های API (افزونه/اتوماسیون/AI)
    path('settings/api-tokens/', views.APITokenListView.as_view(), name='api_tokens'),
    path('settings/api-tokens/api/create/', views.token_create, name='token_create'),
    path('settings/api-tokens/api/<int:pk>/', views.token_revoke, name='token_revoke'),

    # دعوت‌نامه‌ها
    path('invites/', views.InvitesLandingView.as_view(), name='invites_landing'),
    path('invites/<int:pk>/accept/', views.invite_accept, name='invite_accept'),
    path('invites/<int:pk>/reject/', views.invite_reject, name='invite_reject'),
    path('invites/create-org/', views.create_own_org, name='create_own_org'),
]
