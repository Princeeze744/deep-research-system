"""
LangGraph Client - Connects Django to Open Deep Research Server
"""

import os
import time
from typing import Optional, Dict, Any, List
from langgraph_sdk import get_sync_client
from dotenv import load_dotenv

load_dotenv()


class OpenDeepResearchClient:
    """
    Client to interact with the Open Deep Research LangGraph server.
    Uses synchronous client to avoid async issues in Django.
    """
    
    def __init__(self):
        self.base_url = os.getenv('LANGGRAPH_API_URL', 'http://127.0.0.1:2024')
        self.client = get_sync_client(url=self.base_url)
        self.assistant_id = "e9a5370f-7a53-55a8-ada8-6ab9ef15bb5b"
    
    def run_research(
        self,
        query: str,
        previous_context: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run deep research using the Open Deep Research agent.
        """
        start_time = time.time()
        
        if previous_context:
            full_query = f"""PREVIOUS RESEARCH CONTEXT:
{previous_context}

NEW RESEARCH QUERY:
{query}

Please build upon the previous research and avoid repeating already covered topics."""
        else:
            full_query = query
        
        input_data = {
            "messages": [{"role": "user", "content": full_query}]
        }
        
        # Create a new thread if not provided
        if not thread_id:
            thread = self.client.threads.create()
            thread_id = thread["thread_id"]
        
        sources = []
        reasoning_steps = []
        final_report = ""
        
        try:
            # Use wait instead of stream for simpler handling
            result = self.client.runs.wait(
                thread_id=thread_id,
                assistant_id=self.assistant_id,
                input=input_data
            )
            
            # Get the final state
            state = self.client.threads.get_state(thread_id)
            
            # Extract final report from state
            if state and 'values' in state:
                values = state['values']
                if 'messages' in values:
                    for msg in reversed(values['messages']):
                        if hasattr(msg, 'content'):
                            final_report = msg.content
                            break
                        elif isinstance(msg, dict) and msg.get('content'):
                            final_report = msg.get('content', '')
                            break
            
            elapsed_time = time.time() - start_time
            input_tokens = int(len(full_query.split()) * 1.3)
            output_tokens = int(len(final_report.split()) * 1.3) if final_report else 0
            
            return {
                'success': True,
                'report': final_report or "Research completed.",
                'summary': self._generate_summary(final_report) if final_report else "",
                'sources': sources,
                'reasoning': reasoning_steps,
                'thread_id': thread_id,
                'elapsed_time': round(elapsed_time, 2),
                'token_usage': {
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'total_tokens': input_tokens + output_tokens
                },
                'estimated_cost': self._estimate_cost(input_tokens, output_tokens)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'report': "",
                'summary': "",
                'sources': [],
                'reasoning': [],
                'thread_id': thread_id,
                'elapsed_time': round(time.time() - start_time, 2),
                'token_usage': {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0},
                'estimated_cost': 0.0
            }
    
    def _generate_summary(self, report: str, max_length: int = 500) -> str:
        if not report:
            return ""
        paragraphs = report.split('\n\n')
        summary = ""
        for para in paragraphs[:3]:
            if len(summary) + len(para) < max_length:
                summary += para + "\n\n"
            else:
                break
        return summary.strip() or report[:max_length] + "..."
    
    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        input_cost = (input_tokens / 1000) * 0.03
        output_cost = (output_tokens / 1000) * 0.06
        return round(input_cost + output_cost, 4)


# Global instance
deep_research_client = OpenDeepResearchClient()