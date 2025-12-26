"""
Models for Deep Research System
"""

import uuid
from django.db import models


class ResearchSession(models.Model):
    """Stores research sessions with full history and cost tracking."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=255, default='anonymous')
    query = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Research outputs
    report = models.TextField(blank=True, null=True)
    summary = models.TextField(blank=True, null=True)
    sources = models.JSONField(default=list, blank=True)
    reasoning = models.JSONField(default=list, blank=True)
    
    # LangGraph integration
    thread_id = models.CharField(max_length=255, blank=True, null=True)
    trace_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Research continuation (parent-child relationship)
    parent_research = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_researches'
    )
    
    # Token usage and cost tracking
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    # Error tracking
    error_message = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Research: {self.query[:50]}..."


class ResearchDocument(models.Model):
    """Stores uploaded documents for research context."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    research_session = models.ForeignKey(
        ResearchSession,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10)  # pdf, txt
    content = models.TextField(blank=True)
    file_size = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.filename} - {self.research_session.query[:30]}"