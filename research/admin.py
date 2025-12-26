"""
Admin configuration for Deep Research System
"""

from django.contrib import admin
from .models import ResearchSession, ResearchDocument


@admin.register(ResearchSession)
class ResearchSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'query_short', 'status', 'user_id', 'total_tokens', 'estimated_cost', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['query', 'user_id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'completed_at']
    
    def query_short(self, obj):
        return obj.query[:50] + "..." if len(obj.query) > 50 else obj.query
    query_short.short_description = 'Query'


@admin.register(ResearchDocument)
class ResearchDocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'filename', 'file_type', 'research_session', 'uploaded_at']
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['filename']