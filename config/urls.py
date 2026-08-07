"""نقشه‌ی URL اصلی پروژه."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.views import editor_upload
from reports.views import PublicReportView as ReportPublicView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/editor/upload/', editor_upload, name='editor_upload'),
    path('', include('dashboard.urls')),
    path('', include('accounts.urls')),
    path('colleagues/', include('colleagues.urls')),
    path('projects/', include('projects.urls')),
    path('tasks/', include('tasks.urls')),
    path('calendar/', include('calendarapp.urls')),
    path('reports/', include('reports.urls')),
    path('finance/', include('finance.urls')),
    path('r/<uuid:token>/', ReportPublicView.as_view(), name='report_public'),
    path('settings/task-types/', include('tasks.type_urls')),
    path('settings/', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'static')
