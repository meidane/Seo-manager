"""نقشه‌ی URL همکاران."""
from django.urls import path

from . import views

app_name = 'colleagues'

urlpatterns = [
    path('', views.ColleagueListView.as_view(), name='list'),
    path('<int:pk>/', views.ColleagueDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.ColleagueUpdateView.as_view(), name='edit'),
    path('<int:pk>/archive/', views.ColleagueArchiveView.as_view(), name='archive'),
    path('<int:pk>/restore/', views.ColleagueRestoreView.as_view(), name='restore'),
    path('<int:pk>/api/grant-access/', views.colleague_grant_access, name='grant_access'),
    path('<int:pk>/api/revoke-invite/', views.colleague_revoke_invite, name='revoke_invite'),
    path('api/quick-create/', views.colleague_quick_create, name='quick_create'),
]
