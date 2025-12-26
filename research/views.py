"""
Views for Deep Research API - Using Open Deep Research (LangGraph)
"""

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
import uuid

from .models import ResearchSession, ResearchDocument
from .langgraph_client import deep_research_client


@api_view(['POST'])
def start_research(request):
    """
    POST /api/research/start
    Start a new deep research session using Open Deep Research.
    """
    query = request.data.get('query')
    user_id = request.data.get('user_id', 'anonymous')
    parent_research_id = request.data.get('parent_research_id')
    
    if not query:
        return Response(
            {'error': 'Query is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Handle continuation from parent research
    previous_context = None
    parent_session = None
    
    if parent_research_id:
        try:
            parent_session = ResearchSession.objects.get(id=parent_research_id)
            previous_context = f"""
PREVIOUS QUERY: {parent_session.query}

PREVIOUS FINDINGS:
{parent_session.summary or parent_session.report[:2000] if parent_session.report else 'No previous findings'}
"""
        except ResearchSession.DoesNotExist:
            return Response(
                {'error': 'Parent research session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Create research session
    session = ResearchSession.objects.create(
        user_id=user_id,
        query=query,
        status='processing',
        parent_research=parent_session
    )
    
    try:
        # Call Open Deep Research via LangGraph
        result = deep_research_client.run_research(
            query=query,
            previous_context=previous_context
        )
        
        if result['success']:
            # Update session with results
            session.status = 'completed'
            session.report = result['report']
            session.summary = result['summary']
            session.sources = result['sources']
            session.reasoning = result['reasoning']
            session.thread_id = result.get('thread_id')
            session.input_tokens = result['token_usage']['input_tokens']
            session.output_tokens = result['token_usage']['output_tokens']
            session.total_tokens = result['token_usage']['total_tokens']
            session.estimated_cost = result['estimated_cost']
            session.completed_at = timezone.now()
            session.save()
            
            return Response({
                'research_id': str(session.id),
                'status': 'completed',
                'query': query,
                'report': result['report'],
                'summary': result['summary'],
                'sources': result['sources'],
                'reasoning': result['reasoning'],
                'token_usage': result['token_usage'],
                'estimated_cost': result['estimated_cost'],
                'elapsed_time': result['elapsed_time']
            }, status=status.HTTP_201_CREATED)
        else:
            session.status = 'failed'
            session.error_message = result.get('error', 'Unknown error')
            session.save()
            
            return Response({
                'research_id': str(session.id),
                'status': 'failed',
                'error': result.get('error')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        session.status = 'failed'
        session.error_message = str(e)
        session.save()
        
        return Response({
            'research_id': str(session.id),
            'status': 'failed',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def continue_research(request, research_id):
    """
    POST /api/research/{research_id}/continue
    Continue a previous research session with a new query.
    """
    query = request.data.get('query')
    
    if not query:
        return Response(
            {'error': 'Query is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    parent_session = get_object_or_404(ResearchSession, id=research_id)
    
    # Build context from parent
    previous_context = f"""
PREVIOUS QUERY: {parent_session.query}

PREVIOUS FINDINGS:
{parent_session.summary or parent_session.report[:3000] if parent_session.report else 'No previous findings'}

SOURCES USED:
{parent_session.sources if parent_session.sources else 'None'}
"""
    
    # Create new session linked to parent
    session = ResearchSession.objects.create(
        user_id=parent_session.user_id,
        query=query,
        status='processing',
        parent_research=parent_session
    )
    
    try:
        result = deep_research_client.run_research(
            query=query,
            previous_context=previous_context,
            thread_id=parent_session.thread_id
        )
        
        if result['success']:
            session.status = 'completed'
            session.report = result['report']
            session.summary = result['summary']
            session.sources = result['sources']
            session.reasoning = result['reasoning']
            session.thread_id = result.get('thread_id')
            session.input_tokens = result['token_usage']['input_tokens']
            session.output_tokens = result['token_usage']['output_tokens']
            session.total_tokens = result['token_usage']['total_tokens']
            session.estimated_cost = result['estimated_cost']
            session.completed_at = timezone.now()
            session.save()
            
            return Response({
                'research_id': str(session.id),
                'parent_research_id': str(parent_session.id),
                'status': 'completed',
                'query': query,
                'report': result['report'],
                'summary': result['summary'],
                'sources': result['sources'],
                'reasoning': result['reasoning'],
                'token_usage': result['token_usage'],
                'estimated_cost': result['estimated_cost']
            }, status=status.HTTP_201_CREATED)
        else:
            session.status = 'failed'
            session.error_message = result.get('error')
            session.save()
            
            return Response({
                'error': result.get('error')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        session.status = 'failed'
        session.error_message = str(e)
        session.save()
        
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def upload_document(request, research_id):
    """
    POST /api/research/{research_id}/upload
    Upload a document for research context.
    """
    session = get_object_or_404(ResearchSession, id=research_id)
    
    if 'file' not in request.FILES:
        return Response(
            {'error': 'No file provided'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    uploaded_file = request.FILES['file']
    filename = uploaded_file.name.lower()
    
    # Validate file type
    if not (filename.endswith('.pdf') or filename.endswith('.txt')):
        return Response(
            {'error': 'Only PDF and TXT files are supported'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Extract text content
    try:
        if filename.endswith('.txt'):
            content = uploaded_file.read().decode('utf-8')
        elif filename.endswith('.pdf'):
            import pdfplumber
            content = ""
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        content += text + "\n\n"
        
        # Create document record
        doc = ResearchDocument.objects.create(
            research_session=session,
            filename=uploaded_file.name,
            file_type='pdf' if filename.endswith('.pdf') else 'txt',
            content=content,
            file_size=uploaded_file.size
        )
        
        return Response({
            'document_id': str(doc.id),
            'filename': doc.filename,
            'file_type': doc.file_type,
            'content_length': len(content),
            'message': 'Document uploaded successfully'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to process document: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_research_history(request):
    """
    GET /api/research/history
    Get all research sessions for a user.
    """
    user_id = request.query_params.get('user_id', 'anonymous')
    
    sessions = ResearchSession.objects.filter(user_id=user_id).order_by('-created_at')
    
    data = [{
        'id': str(s.id),
        'query': s.query,
        'status': s.status,
        'summary': s.summary,
        'parent_research_id': str(s.parent_research.id) if s.parent_research else None,
        'token_usage': {
            'input_tokens': s.input_tokens,
            'output_tokens': s.output_tokens,
            'total_tokens': s.total_tokens
        },
        'estimated_cost': float(s.estimated_cost) if s.estimated_cost else 0,
        'created_at': s.created_at.isoformat(),
        'completed_at': s.completed_at.isoformat() if s.completed_at else None
    } for s in sessions]
    
    return Response({
        'count': len(data),
        'sessions': data
    })


@api_view(['GET'])
def get_research_detail(request, research_id):
    """
    GET /api/research/{research_id}
    Get detailed information about a research session.
    """
    session = get_object_or_404(ResearchSession, id=research_id)
    
    # Get uploaded documents
    documents = [{
        'id': str(doc.id),
        'filename': doc.filename,
        'file_type': doc.file_type,
        'uploaded_at': doc.uploaded_at.isoformat()
    } for doc in session.documents.all()]
    
    return Response({
        'id': str(session.id),
        'user_id': session.user_id,
        'query': session.query,
        'status': session.status,
        'report': session.report,
        'summary': session.summary,
        'sources': session.sources,
        'reasoning': session.reasoning,
        'documents': documents,
        'parent_research_id': str(session.parent_research.id) if session.parent_research else None,
        'thread_id': session.thread_id,
        'token_usage': {
            'input_tokens': session.input_tokens,
            'output_tokens': session.output_tokens,
            'total_tokens': session.total_tokens
        },
        'estimated_cost': float(session.estimated_cost) if session.estimated_cost else 0,
        'trace_id': session.trace_id,
        'created_at': session.created_at.isoformat(),
        'completed_at': session.completed_at.isoformat() if session.completed_at else None
    })