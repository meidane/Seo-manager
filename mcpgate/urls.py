from django.urls import path

from . import views

app_name = 'mcpgate'

urlpatterns = [
    path('mcp/', views.endpoint, name='endpoint_header'),  # توکن در هدرِ Authorization: Bearer
    path('mcp/<str:token>/panel/', views.endpoint_panel, name='endpoint_panel'),  # ابزارهای پنل (تسک/گزارش/تراکنش)
    path('mcp/<str:token>/panel', views.endpoint_panel),
    path('mcp/<str:token>/', views.endpoint, name='endpoint'),
    path('mcp/<str:token>', views.endpoint),  # بدونِ اسلشِ آخر هم (POST ریدایرکت نمی‌شود)
    path('settings/mcp/', views.page, name='page'),
    path('settings/mcp/gate/', views.gate_update, name='gate'),
    path('settings/mcp/site/', views.site_save, name='site_save'),
    path('settings/mcp/site/<int:pk>/delete/', views.site_delete, name='site_delete'),
    path('settings/mcp/site/<int:pk>/test/', views.site_test, name='site_test'),
    path('settings/mcp/import/', views.site_import, name='site_import'),
    path('settings/mcp/log/', views.log_page, name='log'),
    path('settings/mcp/log/<int:pk>/', views.log_page, name='log_detail'),
    path('settings/mcp/log/<int:pk>/undo/', views.log_undo, name='log_undo'),
]
