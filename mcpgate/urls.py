from django.urls import path

from . import views

app_name = 'mcpgate'

urlpatterns = [
    path('mcp/', views.endpoint, name='endpoint_header'),  # توکن در هدرِ Authorization: Bearer
    path('mcp/<str:token>/', views.endpoint, name='endpoint'),
    path('mcp/<str:token>', views.endpoint),  # بدونِ اسلشِ آخر هم (POST ریدایرکت نمی‌شود)
    path('settings/mcp/', views.page, name='page'),
    path('settings/mcp/gate/', views.gate_update, name='gate'),
    path('settings/mcp/site/', views.site_save, name='site_save'),
    path('settings/mcp/site/<int:pk>/delete/', views.site_delete, name='site_delete'),
    path('settings/mcp/site/<int:pk>/test/', views.site_test, name='site_test'),
    path('settings/mcp/import/', views.site_import, name='site_import'),
]
