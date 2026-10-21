"""URLهای API تبِ «AI»ی پروژه."""
from django.urls import path

from . import views

app_name = 'aistudio'

urlpatterns = [
    path('api/project/<int:pk>/', views.project_ai, name='project'),
    path('api/project/<int:pk>/test/', views.project_ai_test, name='test'),
    path('api/project/<int:pk>/prompts/', views.prompt_create, name='prompt_create'),
    path('api/prompts/<int:pk>/', views.prompt_detail, name='prompt'),
    path('api/prompts/<int:pk>/files/', views.prompt_files, name='prompt_files'),
    path('api/files/<int:pk>/', views.prompt_file_detail, name='file'),
]
