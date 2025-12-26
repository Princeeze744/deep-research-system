"""
URL routes for Deep Research API
"""

from django.urls import path
from . import views

urlpatterns = [
    path('start/', views.start_research, name='start-research'),
    path('<uuid:research_id>/continue/', views.continue_research, name='continue-research'),
    path('<uuid:research_id>/upload/', views.upload_document, name='upload-document'),
    path('<uuid:research_id>/', views.get_research_detail, name='research-detail'),
    path('history/', views.get_research_history, name='research-history'),
]