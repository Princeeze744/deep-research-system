"""
Database models for Deep Research system.
Stores research sessions, summaries, reasoning, documents, and costs.
"""

import uuid
from django.db import models
from django.contrib.auth.models import User


class ResearchSession(models.Model):
    """
    Main research session model.
    Stores the research query, status, results, and links to parent sessions for continuation.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='research_sessions')
    
    # Research query and results
    query = models.TextField(help_text="The original research query")
    final_report = models.TextField(blank=True, null=True, help_text="The final research report")
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Continuation support - links to parent research
    parent_session = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='child_sessions',
        help_text="Parent research session if this is a continuation"
    )
    
    # LangSmith tracing
    trace_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Research: {self.query[:50]}... ({self.status})"


class ResearchSummary(models.Model):
    """
    Stores summarized findings from a research session.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(
        ResearchSession, 
        on_delete=models.CASCADE, 
        related_name='summary'
    )
    
    # Summary content
    summary_text = models.TextField(help_text="Summarized research findings")
    key_findings = models.JSONField(default=list, help_text="List of key findings")
    sources = models.JSONField(default=list, help_text="List of sources used")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Summary for: {self.session.query[:30]}..."


class ResearchReasoning(models.Model):
    """
    Stores high-level reasoning steps (NOT raw chain-of-thought).
    Shows how conclusions were reached without exposing internal details.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(
        ResearchSession, 
        on_delete=models.CASCADE, 
        related_name='reasoning'
    )
    
    # Reasoning steps
    query_plan = models.TextField(blank=True, null=True, help_text="How the query was broken down")
    search_strategy = models.TextField(blank=True, null=True, help_text="Search strategy used")
    source_selection = models.TextField(blank=True, null=True, help_text="Why certain sources were selected")
    synthesis_approach = models.TextField(blank=True, null=True, help_text="How information was synthesized")
    
    # Structured reasoning steps
    reasoning_steps = models.JSONField(default=list, help_text="List of reasoning steps")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reasoning for: {self.session.query[:30]}..."


class UploadedDocument(models.Model):
    """
    Stores documents uploaded by users for research context.
    Supports PDF and TXT files.
    """
    DOCUMENT_TYPES = [
        ('pdf', 'PDF'),
        ('txt', 'Text'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ResearchSession, 
        on_delete=models.CASCADE, 
        related_name='documents'
    )
    
    # File information
    file = models.FileField(upload_to='research_documents/')
    filename = models.CharField(max_length=255)
    document_type = models.CharField(max_length=10, choices=DOCUMENT_TYPES)
    file_size = models.IntegerField(help_text="File size in bytes")
    
    # Extracted content
    extracted_text = models.TextField(blank=True, null=True, help_text="Text extracted from document")
    summary = models.TextField(blank=True, null=True, help_text="Summary of document content")
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.filename} ({self.document_type})"


class ResearchCost(models.Model):
    """
    Tracks token usage and estimated costs for each research session.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(
        ResearchSession, 
        on_delete=models.CASCADE, 
        related_name='cost'
    )
    
    # Token tracking
    input_tokens = models.IntegerField(default=0, help_text="Total input tokens used")
    output_tokens = models.IntegerField(default=0, help_text="Total output tokens used")
    total_tokens = models.IntegerField(default=0, help_text="Total tokens used")
    
    # Cost calculation (in USD)
    estimated_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=6, 
        default=0,
        help_text="Estimated cost in USD"
    )
    
    # Model information
    model_used = models.CharField(max_length=100, default='gpt-4o-mini')
    
    # Breakdown by step (optional detailed tracking)
    cost_breakdown = models.JSONField(default=dict, help_text="Cost breakdown by step")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cost for {self.session.query[:30]}...: ${self.estimated_cost}"

    def calculate_cost(self):
        """
        Calculate estimated cost based on token usage.
        Prices for GPT-4o-mini (as of 2024):
        - Input: $0.15 per 1M tokens
        - Output: $0.60 per 1M tokens
        """
        input_cost = (self.input_tokens / 1_000_000) * 0.15
        output_cost = (self.output_tokens / 1_000_000) * 0.60
        self.estimated_cost = input_cost + output_cost
        self.total_tokens = self.input_tokens + self.output_tokens
        self.save()
        return self.estimated_cost