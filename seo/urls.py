"""نقشه‌ی URL بخش سئو — `/seo/api/...`."""
from django.urls import path

from . import api

app_name = 'seo'

urlpatterns = [
    path('api/keywords/', api.keyword_add, name='keyword_add'),
    path('api/keywords/<int:pk>/', api.keyword_edit, name='keyword_edit'),
    path('api/keywords/<int:pk>/history/', api.keyword_history, name='keyword_history'),
    path('api/keywords/<int:pk>/tasks/', api.keyword_tasks, name='keyword_tasks'),
    path('api/pages/rename/', api.page_rename, name='page_rename'),
    path('api/pages/star/', api.page_star, name='page_star'),
    path('api/tracked-domains/', api.tracked_domains, name='tracked_domains'),
    path('api/rank-ingest/', api.rank_ingest, name='rank_ingest'),
]
