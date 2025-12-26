# Deep Research System

A Django REST API that integrates with **LangChain's Open Deep Research** repository to provide comprehensive AI-powered research capabilities.

## 🎯 Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   User Request                                                  │
│       │                                                         │
│       ▼                                                         │
│   ┌─────────────────┐         ┌─────────────────────────────┐  │
│   │  DJANGO API     │  calls  │  OPEN DEEP RESEARCH         │  │
│   │  (Port 8000)    │ ──────► │  (LangGraph Server)         │  │
│   │                 │         │  (Port 2024)                │  │
│   │  - REST API     │         │                             │  │
│   │  - PostgreSQL   │ ◄────── │  - Multi-agent research     │  │
│   │  - History      │ results │  - Tavily web search        │  │
│   │  - Cost tracking│         │  - OpenAI GPT-4             │  │
│   └─────────────────┘         └─────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🔗 Open Deep Research Integration

This project uses the **mandatory base repository**:
- **Repository:** [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research)
- **Integration:** LangGraph SDK client connects Django to the research server
- **Workflow:** Clarify → Research Brief → Multi-source Research → Compress → Final Report

## ✅ Features Implemented

| Requirement | Status | Description |
|-------------|--------|-------------|
| Django REST Framework | ✅ | Full REST API with all endpoints |
| PostgreSQL Database | ✅ | Persistent storage for research sessions |
| LangSmith Tracing | ✅ | Full observability and debugging |
| Research History | ✅ | Query all past research sessions |
| Cost & Token Tracking | ✅ | Track usage and estimate costs |
| Async Research | ✅ | Non-blocking research execution |
| Open Deep Research | ✅ | **Integrated via LangGraph SDK** |
| Research Continuation | ✅ | Parent-child research linking |
| File Upload | ✅ | PDF and TXT document support |

## 🚀 API Endpoints

### 1. Start Research
```bash
POST /api/research/start/
Content-Type: application/json

{
  "query": "What is artificial intelligence?",
  "user_id": "optional-user-id"
}
```

### 2. Continue Research (with parent context)
```bash
POST /api/research/{research_id}/continue/
Content-Type: application/json

{
  "query": "What are the ethical concerns?"
}
```

### 3. Get Research History
```bash
GET /api/research/history/?user_id=anonymous
```

### 4. Get Research Detail
```bash
GET /api/research/{research_id}/
```

### 5. Upload Document
```bash
POST /api/research/{research_id}/upload/
Content-Type: multipart/form-data

file: <PDF or TXT file>
```

## 📦 Installation

### Prerequisites
- Python 3.11+
- PostgreSQL
- Node.js (for LangGraph CLI)

### Step 1: Clone and Setup Django App
```bash
git clone https://github.com/Princeeze744/deep-research-system.git
cd deep-research-system

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Clone Open Deep Research
```bash
cd ..
git clone https://github.com/langchain-ai/open_deep_research.git
cd open_deep_research

# Setup with uv
pip install uv
uv venv --python 3.11
.venv\Scripts\activate  # Windows
uv sync
```

### Step 3: Configure Environment Variables

**Django App (.env):**
```env
OPENAI_API_KEY=your-openai-key
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=deep-research-system
LANGGRAPH_API_URL=http://127.0.0.1:2024
DATABASE_URL=postgresql://postgres:password@localhost:5432/deep_research_db
```

**Open Deep Research (.env):**
```env
OPENAI_API_KEY=your-openai-key
TAVILY_API_KEY=your-tavily-key
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_TRACING_V2=true
LANGSMITH_TRACING=true
```

### Step 4: Setup Database
```bash
cd deep-research-system
python manage.py migrate
```

### Step 5: Run Both Servers

**Terminal 1 - LangGraph Server:**
```bash
cd open_deep_research
.venv\Scripts\activate
langgraph dev
```

**Terminal 2 - Django Server:**
```bash
cd deep-research-system
venv\Scripts\activate
python manage.py runserver
```

## 🧪 Testing
```bash
# Test research endpoint
curl -X POST http://127.0.0.1:8000/api/research/start/ \
  -H "Content-Type: application/json" \
  -d '{"query": "What is artificial intelligence?"}'

# Test history endpoint
curl http://127.0.0.1:8000/api/research/history/
```

## 📊 Sample Response
```json
{
  "research_id": "8cfef13c-c134-4cd1-ba25-f45c7347dd5d",
  "status": "completed",
  "query": "What is artificial intelligence?",
  "report": "# Artificial Intelligence: A Comprehensive Overview\n\n## Introduction\n\nArtificial Intelligence (AI) is one of the most transformative technologies...",
  "summary": "AI is the field of computer science focused on creating systems capable of tasks requiring human intelligence...",
  "sources": [...],
  "token_usage": {
    "input_tokens": 5,
    "output_tokens": 1842,
    "total_tokens": 1847
  },
  "estimated_cost": 0.1107,
  "elapsed_time": 163.54
}
```

## 🛠️ Tech Stack

- **Backend:** Django 5.0, Django REST Framework
- **Database:** PostgreSQL
- **AI/ML:** LangChain, LangGraph, OpenAI GPT-4
- **Search:** Tavily API
- **Observability:** LangSmith
- **Base Repo:** [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research)

## 📁 Project Structure
```
deep-research-system/
├── config/
│   ├── settings.py
│   └── urls.py
├── research/
│   ├── models.py           # ResearchSession, ResearchDocument
│   ├── views.py            # API endpoints
│   ├── urls.py             # URL routing
│   ├── langgraph_client.py # Open Deep Research integration
│   └── admin.py            # Django admin
├── requirements.txt
├── manage.py
└── README.md
```

## 🔑 Key Integration: langgraph_client.py
```python
from langgraph_sdk import get_sync_client

class OpenDeepResearchClient:
    def __init__(self):
        self.client = get_sync_client(url="http://127.0.0.1:2024")
        self.assistant_id = "e9a5370f-7a53-55a8-ada8-6ab9ef15bb5b"
    
    def run_research(self, query, previous_context=None):
        thread = self.client.threads.create()
        result = self.client.runs.wait(
            thread_id=thread["thread_id"],
            assistant_id=self.assistant_id,
            input={"messages": [{"role": "user", "content": query}]}
        )
        # Process and return results...
```

## 📈 LangSmith Tracing

All research sessions are traced in LangSmith for full observability:
- View at: https://smith.langchain.com
- Project: `deep-research-system`

## 👨‍💻 Author

Built for Creston & Company Python Developer Internship Challenge

## 📄 License

MIT License