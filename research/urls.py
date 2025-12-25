"""
URL routing for the Research API.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Start a new research
    path('start/', views.StartResearchView.as_view(), name='start-research'),
    
    # Continue previous research
    path('continue/', views.ContinueResearchView.as_view(), name='continue-research'),
    
    # Upload context file
    path('upload/', views.UploadFileView.as_view(), name='upload-file'),
    
    # Get research history
    path('history/', views.ResearchHistoryView.as_view(), name='research-history'),
    
    # Get research details
    path('<uuid:research_id>/', views.ResearchDetailView.as_view(), name='research-detail'),
]
