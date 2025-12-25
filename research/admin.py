"""
Django Admin configuration for Research models.
"""

from django.contrib import admin
from .models import (
    ResearchSession,
    ResearchSummary,
    ResearchReasoning,
    UploadedDocument,
    ResearchCost
)


@admin.register(ResearchSession)
class ResearchSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'query_short', 'user', 'status', 'created_at', 'completed_at']
    list_filter = ['status', 'created_at']
    search_fields = ['query', 'user__username']
    readonly_fields = ['id', 'trace_id', 'created_at', 'updated_at']
    
    def query_short(self, obj):
        return obj.query[:50] + '...' if len(obj.query) > 50 else obj.query
    query_short.short_description = 'Query'


@admin.register(ResearchSummary)
class ResearchSummaryAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'created_at']
    search_fields = ['session__query']


@admin.register(ResearchReasoning)
class ResearchReasoningAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'created_at']
    search_fields = ['session__query']


@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'filename', 'document_type', 'session', 'uploaded_at']
    list_filter = ['document_type', 'uploaded_at']
    search_fields = ['filename', 'session__query']


@admin.register(ResearchCost)
class ResearchCostAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'total_tokens', 'estimated_cost', 'model_used']
    list_filter = ['model_used']
    search_fields = ['session__query']