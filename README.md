# 🔬 Deep Research System

A powerful AI-powered research system built with Django, LangChain, and PostgreSQL. This system performs multi-step deep research using AI agents, with support for research continuation, document uploads, cost tracking, and full observability via LangSmith.

## 🎯 Features

- **Deep AI Research**: Execute comprehensive multi-step research queries using GPT-4o-mini
- **Research History**: All research sessions are persisted with full details
- **Research Continuation**: Build upon previous research without repeating covered topics
- **Document Upload**: Upload PDF/TXT files to provide additional context for research
- **Reasoning Visibility**: See how the AI planned and executed the research
- **Cost Tracking**: Track token usage and estimated costs for each research session
- **LangSmith Tracing**: Full observability with trace IDs for debugging

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | Django 6.0 + Django REST Framework |
| Database | PostgreSQL 18 |
| AI Framework | LangChain + LangGraph |
| LLM | OpenAI GPT-4o-mini |
| Tracing | LangSmith |
| Async Tasks | Threading (Celery-ready) |

## 📁 Project Structure
```
deep-research-project/
├── config/                  # Django configuration
│   ├── settings.py         # Main settings
│   ├── urls.py             # URL routing
│   ├── celery.py           # Celery configuration
│   └── wsgi.py             # WSGI entry point
├── research/               # Main research app
│   ├── models.py           # Database models
│   ├── views.py            # API views
│   ├── serializers.py      # DRF serializers
│   ├── services.py         # Business logic
│   ├── urls.py             # App URLs
│   └── admin.py            # Admin configuration
├── open_deep_research/     # Base research repo (integrated)
├── media/                  # Uploaded files
├── .env                    # Environment variables
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🗄️ Database Models

| Model | Purpose |
|-------|---------|
| `ResearchSession` | Main research record with query, report, status |
| `ResearchSummary` | Summarized findings and key points |
| `ResearchReasoning` | Query plan, search strategy, reasoning steps |
| `UploadedDocument` | Files uploaded for research context |
| `ResearchCost` | Token usage and cost tracking |

## 🌐 API Endpoints

### Start New Research
```
POST /api/research/start/
Body: {"query": "Your research question here"}
```

### Continue Previous Research
```
POST /api/research/continue/
Body: {"previous_research_id": "uuid", "query": "Follow-up question"}
```

### Upload Document
```
POST /api/research/upload/
Form Data: file=@document.pdf, research_id=uuid
```

### Get Research History
```
GET /api/research/history/
```

### Get Research Details
```
GET /api/research/{research_id}/
```

## 🚀 Setup Instructions

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- OpenAI API Key
- LangSmith API Key

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/deep-research-project.git
cd deep-research-project
```

2. **Create virtual environment**
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate      # Linux/Mac
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Create PostgreSQL database**
```bash
psql -U postgres -c "CREATE DATABASE deep_research_db;"
```

5. **Configure environment variables**
Create `.env` file:
```env
OPENAI_API_KEY=your-openai-key
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=deep-research-project
SECRET_KEY=your-django-secret-key
DEBUG=True
```

6. **Run migrations**
```bash
python manage.py migrate
```

7. **Create superuser**
```bash
python manage.py createsuperuser
```

8. **Run the server**
```bash
python manage.py runserver
```

## 📊 Design Decisions

### 1. Research Continuation Logic
- Previous research summary is injected into new research context
- System explicitly instructs AI to avoid repeating covered topics
- Parent-child relationship maintained via `parent_session` foreign key

### 2. Cost Tracking Implementation
- Uses `tiktoken` library for accurate token counting
- Tracks input/output tokens separately
- Calculates cost based on current OpenAI pricing
- Stored per session for historical analysis

### 3. LangSmith Tracing
- Enabled via environment variables
- Each research generates unique `trace_id`
- All LLM calls and tool usage captured
- Enables debugging and performance analysis

### 4. Async Research Execution
- Research runs in background threads
- API returns immediately with `pending` status
- Client polls for completion
- Ready for Celery integration in production

### 5. Document Processing
- Supports PDF and TXT files
- Text extraction via `pdfplumber`
- Auto-summarization of uploaded content
- Content injected into research context

## 🧪 Testing the API

### Using cURL

**Start Research:**
```bash
curl -X POST http://localhost:8000/api/research/start/ \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest developments in AI?"}'
```

**Check Status:**
```bash
curl http://localhost:8000/api/research/{research_id}/
```

**Continue Research:**
```bash
curl -X POST http://localhost:8000/api/research/continue/ \
  -H "Content-Type: application/json" \
  -d '{"previous_research_id": "uuid", "query": "Tell me more about healthcare AI"}'
```

**Upload Document:**
```bash
curl -X POST http://localhost:8000/api/research/upload/ \
  -F "file=@document.pdf" \
  -F "research_id=uuid"
```

## 📈 Sample Response
```json
{
  "id": "2e2d263c-d0a4-49dd-a017-82de8b831570",
  "query": "What are the latest developments in AI?",
  "status": "completed",
  "final_report": "# Research Report...",
  "trace_id": "73a7a9e1-e694-447a-a7d5-cd35b17dc819",
  "summary": {
    "summary_text": "...",
    "key_findings": ["...", "..."],
    "sources": ["...", "..."]
  },
  "reasoning": {
    "query_plan": "...",
    "search_strategy": "...",
    "reasoning_steps": ["...", "..."]
  },
  "cost": {
    "input_tokens": 3350,
    "output_tokens": 3222,
    "total_tokens": 6572,
    "estimated_cost": "0.002436",
    "model_used": "gpt-4o-mini"
  }
}
```

## 👨‍💻 Author

Built for Creston & Company Python Developer Internship Challenge

## 📄 License

MIT License