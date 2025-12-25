"""
Service layer for Deep Research system.
Contains business logic for research execution, document processing, and cost tracking.
"""

import os
import uuid
from datetime import datetime
from typing import Optional
import threading

from django.utils import timezone
from django.conf import settings
from dotenv import load_dotenv

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import tiktoken

# Load environment variables
load_dotenv()

# Import models (imported here to avoid circular imports)
from .models import (
    ResearchSession,
    ResearchSummary,
    ResearchReasoning,
    UploadedDocument,
    ResearchCost
)


class TokenTracker:
    """
    Tracks token usage for cost calculation.
    """
    
    # Pricing per 1M tokens (GPT-4o-mini as of 2024)
    PRICING = {
        'gpt-4o-mini': {'input': 0.15, 'output': 0.60},
        'gpt-4o': {'input': 2.50, 'output': 10.00},
        'gpt-4': {'input': 30.00, 'output': 60.00},
    }
    
    def __init__(self, model: str = 'gpt-4o-mini'):
        self.model = model
        self.input_tokens = 0
        self.output_tokens = 0
        try:
            self.encoder = tiktoken.encoding_for_model(model)
        except KeyError:
            self.encoder = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string."""
        return len(self.encoder.encode(text))
    
    def add_input(self, text: str):
        """Track input tokens."""
        self.input_tokens += self.count_tokens(text)
    
    def add_output(self, text: str):
        """Track output tokens."""
        self.output_tokens += self.count_tokens(text)
    
    def get_cost(self) -> float:
        """Calculate estimated cost in USD."""
        pricing = self.PRICING.get(self.model, self.PRICING['gpt-4o-mini'])
        input_cost = (self.input_tokens / 1_000_000) * pricing['input']
        output_cost = (self.output_tokens / 1_000_000) * pricing['output']
        return input_cost + output_cost
    
    def get_stats(self) -> dict:
        """Get token usage statistics."""
        return {
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'total_tokens': self.input_tokens + self.output_tokens,
            'estimated_cost': self.get_cost(),
            'model': self.model
        }


class ResearchService:
    """
    Handles research execution using LangChain and the open_deep_research approach.
    """
    
    @staticmethod
    def start_research(session: ResearchSession) -> None:
        """
        Start a new research session asynchronously.
        """
        # Run research in a background thread
        thread = threading.Thread(
            target=ResearchService._execute_research,
            args=(session, None)
        )
        thread.start()
    
    @staticmethod
    def continue_research(session: ResearchSession, parent_session: ResearchSession) -> None:
        """
        Continue research from a previous session.
        """
        # Run research in a background thread with parent context
        thread = threading.Thread(
            target=ResearchService._execute_research,
            args=(session, parent_session)
        )
        thread.start()
    
    @staticmethod
    def _execute_research(session: ResearchSession, parent_session: Optional[ResearchSession] = None) -> None:
        """
        Execute the actual research process.
        This runs in a background thread.
        """
        # Initialize token tracker
        tracker = TokenTracker(model='gpt-4o-mini')
        
        # Generate trace ID for LangSmith
        trace_id = str(uuid.uuid4())
        session.trace_id = trace_id
        session.status = 'running'
        session.save()
        
        try:
            # Set up LangSmith tracing
            os.environ['LANGCHAIN_TRACING_V2'] = 'true'
            os.environ['LANGCHAIN_PROJECT'] = settings.LANGCHAIN_PROJECT
            
            # Initialize LLM
            llm = ChatOpenAI(
                model='gpt-4o-mini',
                temperature=0.7,
                api_key=os.getenv('OPENAI_API_KEY')
            )
            
            # Build context from parent session if continuing
            parent_context = ""
            if parent_session:
                parent_context = ResearchService._build_parent_context(parent_session)
                tracker.add_input(parent_context)
            
            # Build context from uploaded documents
            doc_context = ResearchService._build_document_context(session)
            tracker.add_input(doc_context)
            
            # Execute multi-step research
            result = ResearchService._run_research_pipeline(
                llm=llm,
                query=session.query,
                parent_context=parent_context,
                doc_context=doc_context,
                tracker=tracker,
                session=session
            )
            
            # Save results
            session.final_report = result['report']
            session.status = 'completed'
            session.completed_at = timezone.now()
            session.save()
            
            # Save summary
            ResearchSummary.objects.create(
                session=session,
                summary_text=result['summary'],
                key_findings=result['key_findings'],
                sources=result['sources']
            )
            
            # Save reasoning
            ResearchReasoning.objects.create(
                session=session,
                query_plan=result['reasoning']['query_plan'],
                search_strategy=result['reasoning']['search_strategy'],
                source_selection=result['reasoning']['source_selection'],
                synthesis_approach=result['reasoning']['synthesis_approach'],
                reasoning_steps=result['reasoning']['steps']
            )
            
            # Update cost tracking
            cost = session.cost
            stats = tracker.get_stats()
            cost.input_tokens = stats['input_tokens']
            cost.output_tokens = stats['output_tokens']
            cost.total_tokens = stats['total_tokens']
            cost.estimated_cost = stats['estimated_cost']
            cost.model_used = stats['model']
            cost.save()
            
        except Exception as e:
            session.status = 'failed'
            session.final_report = f"Research failed: {str(e)}"
            session.save()
            raise
    
    @staticmethod
    def _build_parent_context(parent_session: ResearchSession) -> str:
        """Build context from parent research session."""
        context_parts = [
            "=== PREVIOUS RESEARCH CONTEXT ===",
            f"Previous Query: {parent_session.query}",
        ]
        
        # Add previous summary if available
        try:
            if hasattr(parent_session, 'summary') and parent_session.summary:
                context_parts.append(f"\nPrevious Summary:\n{parent_session.summary.summary_text}")
                context_parts.append(f"\nPrevious Key Findings:\n{parent_session.summary.key_findings}")
        except:
            pass
        
        # Add previous report excerpt
        if parent_session.final_report:
            # Include first 2000 chars of previous report
            report_excerpt = parent_session.final_report[:2000]
            context_parts.append(f"\nPrevious Report Excerpt:\n{report_excerpt}")
        
        context_parts.append("\n=== END PREVIOUS CONTEXT ===\n")
        context_parts.append("BUILD UPON this previous research. Do NOT repeat what was already covered.")
        
        return "\n".join(context_parts)
    
    @staticmethod
    def _build_document_context(session: ResearchSession) -> str:
        """Build context from uploaded documents."""
        documents = UploadedDocument.objects.filter(session=session)
        
        if not documents.exists():
            return ""
        
        context_parts = ["=== UPLOADED DOCUMENT CONTEXT ==="]
        
        for doc in documents:
            context_parts.append(f"\n--- Document: {doc.filename} ---")
            if doc.summary:
                context_parts.append(f"Summary: {doc.summary}")
            if doc.extracted_text:
                # Include first 3000 chars of extracted text
                text_excerpt = doc.extracted_text[:3000]
                context_parts.append(f"Content:\n{text_excerpt}")
        
        context_parts.append("\n=== END DOCUMENT CONTEXT ===\n")
        
        return "\n".join(context_parts)
    
    @staticmethod
    def _run_research_pipeline(
        llm: ChatOpenAI,
        query: str,
        parent_context: str,
        doc_context: str,
        tracker: TokenTracker,
        session: ResearchSession
    ) -> dict:
        """
        Run the multi-step research pipeline.
        Returns structured research results.
        """
        
        # Step 1: Query Planning
        planning_prompt = f"""You are a research planning assistant.

{parent_context}
{doc_context}

USER QUERY: {query}

Create a research plan with:
1. Break down the query into sub-questions
2. Identify key topics to research
3. Suggest search strategies

Respond in a structured format."""

        tracker.add_input(planning_prompt)
        
        planning_response = llm.invoke([
            SystemMessage(content="You are an expert research planner."),
            HumanMessage(content=planning_prompt)
        ])
        
        query_plan = planning_response.content
        tracker.add_output(query_plan)
        
        # Step 2: Research Execution (Simulated web search + synthesis)
        research_prompt = f"""You are a deep research assistant.

{parent_context}
{doc_context}

RESEARCH PLAN:
{query_plan}

USER QUERY: {query}

Conduct thorough research on this topic. Provide:
1. Comprehensive findings from multiple perspectives
2. Key facts and data points
3. Expert opinions and analyses
4. Relevant examples and case studies

Be thorough, accurate, and cite your reasoning."""

        tracker.add_input(research_prompt)
        
        research_response = llm.invoke([
            SystemMessage(content="You are an expert researcher with access to comprehensive knowledge."),
            HumanMessage(content=research_prompt)
        ])
        
        research_findings = research_response.content
        tracker.add_output(research_findings)
        
        # Step 3: Report Generation
        report_prompt = f"""You are a research report writer.

RESEARCH FINDINGS:
{research_findings}

USER QUERY: {query}

Write a comprehensive, well-structured research report that:
1. Has a clear executive summary
2. Presents findings in logical sections
3. Includes key insights and conclusions
4. Is professional and easy to read

Format with clear headings and sections."""

        tracker.add_input(report_prompt)
        
        report_response = llm.invoke([
            SystemMessage(content="You are an expert report writer."),
            HumanMessage(content=report_prompt)
        ])
        
        final_report = report_response.content
        tracker.add_output(final_report)
        
        # Step 4: Generate Summary and Key Findings
        summary_prompt = f"""Based on this research report, provide:

REPORT:
{final_report}

1. A 2-3 sentence summary
2. A JSON list of 3-5 key findings (as strings)
3. A JSON list of sources/topics covered (as strings)

Format your response as:
SUMMARY: [your summary]
KEY_FINDINGS: ["finding 1", "finding 2", ...]
SOURCES: ["source 1", "source 2", ...]"""

        tracker.add_input(summary_prompt)
        
        summary_response = llm.invoke([
            SystemMessage(content="You are a research summarizer."),
            HumanMessage(content=summary_prompt)
        ])
        
        summary_text = summary_response.content
        tracker.add_output(summary_text)
        
        # Parse summary response
        summary, key_findings, sources = ResearchService._parse_summary_response(summary_text)
        
        return {
            'report': final_report,
            'summary': summary,
            'key_findings': key_findings,
            'sources': sources,
            'reasoning': {
                'query_plan': query_plan,
                'search_strategy': "Multi-step LLM-based research with context building",
                'source_selection': "AI knowledge synthesis with document context",
                'synthesis_approach': "Iterative refinement with planning, research, and report generation",
                'steps': [
                    "Query planning and decomposition",
                    "Deep research with context",
                    "Report generation",
                    "Summary extraction"
                ]
            }
        }
    
    @staticmethod
    def _parse_summary_response(response: str) -> tuple:
        """Parse the summary response into components."""
        import json
        import re
        
        summary = ""
        key_findings = []
        sources = []
        
        try:
            # Extract summary
            summary_match = re.search(r'SUMMARY:\s*(.+?)(?=KEY_FINDINGS:|$)', response, re.DOTALL)
            if summary_match:
                summary = summary_match.group(1).strip()
            
            # Extract key findings
            findings_match = re.search(r'KEY_FINDINGS:\s*(\[.+?\])', response, re.DOTALL)
            if findings_match:
                key_findings = json.loads(findings_match.group(1))
            
            # Extract sources
            sources_match = re.search(r'SOURCES:\s*(\[.+?\])', response, re.DOTALL)
            if sources_match:
                sources = json.loads(sources_match.group(1))
                
        except (json.JSONDecodeError, AttributeError):
            # Fallback if parsing fails
            summary = response[:500]
            key_findings = ["Research completed successfully"]
            sources = ["AI-synthesized research"]
        
        return summary, key_findings, sources


class DocumentService:
    """
    Handles document upload and processing.
    """
    
    @staticmethod
    def process_upload(file, session: ResearchSession) -> UploadedDocument:
        """
        Process an uploaded file: save it, extract text, and generate summary.
        """
        filename = file.name
        file_size = file.size
        
        # Determine document type
        if filename.lower().endswith('.pdf'):
            doc_type = 'pdf'
        else:
            doc_type = 'txt'
        
        # Create document record
        document = UploadedDocument.objects.create(
            session=session,
            file=file,
            filename=filename,
            document_type=doc_type,
            file_size=file_size
        )
        
        # Extract text based on file type
        try:
            if doc_type == 'pdf':
                extracted_text = DocumentService._extract_pdf_text(document.file.path)
            else:
                extracted_text = DocumentService._extract_txt_text(document.file.path)
            
            document.extracted_text = extracted_text
            
            # Generate summary
            document.summary = DocumentService._generate_summary(extracted_text)
            document.save()
            
        except Exception as e:
            document.extracted_text = f"Error extracting text: {str(e)}"
            document.summary = "Could not generate summary due to extraction error."
            document.save()
        
        return document
    
    @staticmethod
    def _extract_pdf_text(file_path: str) -> str:
        """Extract text from PDF file."""
        import pdfplumber
        
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        
        return "\n\n".join(text_parts)
    
    @staticmethod
    def _extract_txt_text(file_path: str) -> str:
        """Extract text from TXT file."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    @staticmethod
    def _generate_summary(text: str) -> str:
        """Generate a summary of the extracted text using LLM."""
        if not text or len(text.strip()) < 50:
            return "Document too short to summarize."
        
        try:
            llm = ChatOpenAI(
                model='gpt-4o-mini',
                temperature=0.5,
                api_key=os.getenv('OPENAI_API_KEY')
            )
            
            # Truncate text if too long
            text_to_summarize = text[:10000]
            
            response = llm.invoke([
                SystemMessage(content="You are a document summarizer. Provide a concise 2-3 sentence summary."),
                HumanMessage(content=f"Summarize this document:\n\n{text_to_summarize}")
            ])
            
            return response.content
            
        except Exception as e:
            return f"Summary generation failed: {str(e)}"