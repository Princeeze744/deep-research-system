"""
API Views for Deep Research system.
Handles research execution, continuation, file uploads, and history.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth.models import User
from django.utils import timezone

from .models import (
    ResearchSession,
    ResearchSummary,
    ResearchReasoning,
    UploadedDocument,
    ResearchCost
)
from .serializers import (
    ResearchSessionListSerializer,
    ResearchSessionDetailSerializer,
    StartResearchSerializer,
    ContinueResearchSerializer,
    FileUploadSerializer
)
from .services import ResearchService, DocumentService


class StartResearchView(APIView):
    """
    POST /api/research/start/
    Start a new research session.
    """
    
    def post(self, request):
        serializer = StartResearchSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid input', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        query = serializer.validated_data['query']
        
        # Get or create a default user (for demo purposes)
        user, _ = User.objects.get_or_create(
            username='demo_user',
            defaults={'email': 'demo@example.com'}
        )
        
        # Create research session
        session = ResearchSession.objects.create(
            user=user,
            query=query,
            status='pending'
        )
        
        # Create cost tracking record
        ResearchCost.objects.create(session=session)
        
        # Start async research task
        try:
            ResearchService.start_research(session)
            
            return Response({
                'message': 'Research started successfully',
                'research_id': str(session.id),
                'status': session.status,
                'query': session.query
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            session.status = 'failed'
            session.save()
            return Response(
                {'error': f'Failed to start research: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ContinueResearchView(APIView):
    """
    POST /api/research/continue/
    Continue from a previous research session.
    """
    
    def post(self, request):
        serializer = ContinueResearchSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid input', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        previous_research_id = serializer.validated_data['previous_research_id']
        query = serializer.validated_data['query']
        
        # Get previous research session
        try:
            parent_session = ResearchSession.objects.get(id=previous_research_id)
        except ResearchSession.DoesNotExist:
            return Response(
                {'error': 'Previous research session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create new session linked to parent
        session = ResearchSession.objects.create(
            user=parent_session.user,
            query=query,
            status='pending',
            parent_session=parent_session
        )
        
        # Create cost tracking record
        ResearchCost.objects.create(session=session)
        
        # Start async research with parent context
        try:
            ResearchService.continue_research(session, parent_session)
            
            return Response({
                'message': 'Continuation research started successfully',
                'research_id': str(session.id),
                'parent_research_id': str(parent_session.id),
                'status': session.status,
                'query': session.query
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            session.status = 'failed'
            session.save()
            return Response(
                {'error': f'Failed to continue research: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UploadFileView(APIView):
    """
    POST /api/research/upload/
    Upload a document for research context.
    """
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        serializer = FileUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid input', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = serializer.validated_data['file']
        research_id = serializer.validated_data['research_id']
        
        # Get research session
        try:
            session = ResearchSession.objects.get(id=research_id)
        except ResearchSession.DoesNotExist:
            return Response(
                {'error': 'Research session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Process and save document
        try:
            document = DocumentService.process_upload(file, session)
            
            return Response({
                'message': 'File uploaded successfully',
                'document_id': str(document.id),
                'filename': document.filename,
                'document_type': document.document_type,
                'file_size': document.file_size,
                'summary': document.summary
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResearchHistoryView(APIView):
    """
    GET /api/research/history/
    Get list of all research sessions.
    """
    
    def get(self, request):
        # Get user's research sessions
        user, _ = User.objects.get_or_create(
            username='demo_user',
            defaults={'email': 'demo@example.com'}
        )
        
        sessions = ResearchSession.objects.filter(user=user)
        serializer = ResearchSessionListSerializer(sessions, many=True)
        
        return Response({
            'count': sessions.count(),
            'results': serializer.data
        })


class ResearchDetailView(APIView):
    """
    GET /api/research/<research_id>/
    Get detailed information about a specific research session.
    """
    
    def get(self, request, research_id):
        try:
            session = ResearchSession.objects.get(id=research_id)
        except ResearchSession.DoesNotExist:
            return Response(
                {'error': 'Research session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ResearchSessionDetailSerializer(session)
        return Response(serializer.data)
