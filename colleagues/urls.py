"""نقشه‌ی URL همکاران."""
from django.urls import path

from . import views

app_name = 'colleagues'

urlpatterns = [
    path('', views.ColleagueListView.as_view(), name='list'),
    path('add/', views.ColleagueCreateView.as_view(), name='add'),
    path('<int:pk>/', views.ColleagueDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.ColleagueUpdateView.as_view(), name='edit'),
    path('<int:pk>/archive/', views.ColleagueArchiveView.as_view(), name='archive'),
    path('<int:pk>/restore/', views.ColleagueRestoreView.as_view(), name='restore'),
]
