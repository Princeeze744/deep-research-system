"""
Serializers for the Research API.
Converts model instances to JSON and validates incoming data.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    ResearchSession, 
    ResearchSummary, 
    ResearchReasoning, 
    UploadedDocument, 
    ResearchCost
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class ResearchCostSerializer(serializers.ModelSerializer):
    """Serializer for research cost and token tracking."""
    
    class Meta:
        model = ResearchCost
        fields = [
            'input_tokens',
            'output_tokens', 
            'total_tokens',
            'estimated_cost',
            'model_used',
            'cost_breakdown'
        ]


class ResearchSummarySerializer(serializers.ModelSerializer):
    """Serializer for research summary."""
    
    class Meta:
        model = ResearchSummary
        fields = [
            'summary_text',
            'key_findings',
            'sources',
            'created_at'
        ]


class ResearchReasoningSerializer(serializers.ModelSerializer):
    """Serializer for research reasoning steps."""
    
    class Meta:
        model = ResearchReasoning
        fields = [
            'query_plan',
            'search_strategy',
            'source_selection',
            'synthesis_approach',
            'reasoning_steps',
            'created_at'
        ]


class UploadedDocumentSerializer(serializers.ModelSerializer):
    """Serializer for uploaded documents."""
    
    class Meta:
        model = UploadedDocument
        fields = [
            'id',
            'filename',
            'document_type',
            'file_size',
            'summary',
            'uploaded_at'
        ]


class ResearchSessionListSerializer(serializers.ModelSerializer):
    """Serializer for listing research sessions (minimal data)."""
    
    class Meta:
        model = ResearchSession
        fields = [
            'id',
            'query',
            'status',
            'created_at',
            'completed_at'
        ]


class ResearchSessionDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for a single research session.
    Includes summary, reasoning, documents, and cost.
    """
    summary = ResearchSummarySerializer(read_only=True)
    reasoning = ResearchReasoningSerializer(read_only=True)
    documents = UploadedDocumentSerializer(many=True, read_only=True)
    cost = ResearchCostSerializer(read_only=True)
    parent_session_id = serializers.UUIDField(source='parent_session.id', read_only=True, allow_null=True)
    
    class Meta:
        model = ResearchSession
        fields = [
            'id',
            'query',
            'final_report',
            'status',
            'parent_session_id',
            'trace_id',
            'created_at',
            'updated_at',
            'completed_at',
            'summary',
            'reasoning',
            'documents',
            'cost'
        ]


class StartResearchSerializer(serializers.Serializer):
    """Serializer for starting a new research session."""
    
    query = serializers.CharField(
        required=True,
        min_length=10,
        max_length=5000,
        help_text="The research query (10-5000 characters)"
    )
    
    def validate_query(self, value):
        """Validate the research query."""
        if not value.strip():
            raise serializers.ValidationError("Query cannot be empty or whitespace only.")
        return value.strip()


class ContinueResearchSerializer(serializers.Serializer):
    """Serializer for continuing a previous research session."""
    
    previous_research_id = serializers.UUIDField(
        required=True,
        help_text="ID of the previous research session to continue from"
    )
    query = serializers.CharField(
        required=True,
        min_length=10,
        max_length=5000,
        help_text="The new research query that builds on previous research"
    )
    
    def validate_previous_research_id(self, value):
        """Validate that the previous research exists and is completed."""
        try:
            session = ResearchSession.objects.get(id=value)
            if session.status != 'completed':
                raise serializers.ValidationError(
                    "Can only continue from a completed research session."
                )
        except ResearchSession.DoesNotExist:
            raise serializers.ValidationError("Previous research session not found.")
        return value
    
    def validate_query(self, value):
        """Validate the research query."""
        if not value.strip():
            raise serializers.ValidationError("Query cannot be empty or whitespace only.")
        return value.strip()


class FileUploadSerializer(serializers.Serializer):
    """Serializer for file uploads."""
    
    file = serializers.FileField(
        required=True,
        help_text="PDF or TXT file to upload"
    )
    research_id = serializers.UUIDField(
        required=True,
        help_text="ID of the research session to attach this file to"
    )
    
    def validate_file(self, value):
        """Validate file type and size."""
        # Check file extension
        filename = value.name.lower()
        if not (filename.endswith('.pdf') or filename.endswith('.txt')):
            raise serializers.ValidationError(
                "Only PDF and TXT files are supported."
            )
        
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                "File size cannot exceed 10MB."
            )
        
        return value
    
    def validate_research_id(self, value):
        """Validate that the research session exists."""
        try:
            ResearchSession.objects.get(id=value)
        except ResearchSession.DoesNotExist:
            raise serializers.ValidationError("Research session not found.")
        return value
