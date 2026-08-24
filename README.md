# Adaptive RAG - Agentic AI Chatbot

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.5.4-orange.svg)](https://python.langchain.com/langgraph/)
[![Qdrant](https://img.shields.io/badge/Qdrant-VectorDB-purple.svg)](https://qdrant.tech/)

## 📋 Overview

**Adaptive RAG** is an intelligent, end-to-end Retrieval-Augmented Generation (RAG) system powered by agentic AI architecture. It combines dynamic query routing, intelligent document retrieval, and advanced LLM capabilities to provide accurate, context-aware answers to user queries.

The system intelligently adapts its retrieval strategy based on query type, utilizing indexed documents, general knowledge, or real-time web search to generate comprehensive responses. Built with a modular architecture using LangGraph for workflow orchestration and multiple storage backends for scalability.

---

## 🎯 Key Features

### 🧠 Intelligent Query Routing
- **Adaptive Classification**: Automatically routes queries to the most appropriate processing pipeline
- **Three Query Types**:
  - **Index**: Queries answerable from uploaded documents
  - **General**: Queries answerable with general knowledge
  - **Search**: Queries requiring real-time web search

### 📚 Advanced RAG Pipeline
- **Document Processing**: Intelligent chunking and embedding of documents
- **Vector Search**: Fast similarity-based retrieval using Qdrant
- **Relevance Grading**: Automatic evaluation of retrieved documents
- **Query Rewriting**: Optimizes queries for better retrieval results

### 🤖 Agentic AI Architecture
- **Multi-Agent System**: Specialized agents for different tasks
- **ReAct Framework**: Reasoning and Acting pattern for intelligent decision-making
- **Tool Integration**: Seamless integration with retrieval tools and web search

### 💾 State Management
- **MongoDB Backend**: Persistent chat history and session management
- **Session Tracking**: Individual conversation contexts per user
- **Memory Management**: Full conversation context retention

### 🎨 User Interface
- **Streamlit Web App**: Interactive chat interface with document upload
- **File Support**: PDF and TXT document uploads
- **Real-time Feedback**: Live chat with instant responses

### ⚡ API-First Architecture
- **FastAPI Backend**: High-performance REST API
- **Async Operations**: Non-blocking database and API calls
- **RESTful Endpoints**: Well-defined API contracts

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                          │
│  ┌──────────────��───────────────────────────────────────��───┐  │
│  │  Streamlit Web Application                               │  │
│  │  • Chat Interface                                        │  │
│  │  • Document Upload (PDF, TXT)                            │  │
│  │  • Session Management                                    │  │
│  └──────────────────────────────────────────────────────────��  │
└───────────────────────────────────────────��─────────────────────┘
                            ↓
┌────────────────────────────────────────────────��────────────────┐
│                       FastAPI Backend                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  REST API Endpoints                                      │  │
│  │  • POST /rag/query                                       │  │
│  │  • POST /rag/documents/upload                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Orchestration                      │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐         │
│  │ Query   │→ │ Classify │→ │ Router  │→ │ Pipeline │         │
│  │ Analyze │  │ Query    │  │ Output  │  │ Exec     │         │
│  └─────────┘  └──────────┘  └───��─────┘  └──────────┘         │
└─────────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────��──────────┬────────────────��─┬────────────────┐
        ↓                  ↓                  ↓                ↓
   ┌─────────┐       ┌──────────┐      ┌────────────┐   ┌──────────┐
   │ Retriever│      │ General  │      │ Web Search │   │ Response │
   │ (Index)  │      │ LLM      │      │ (Tavily)   │   │ Generator│
   └─────────┘       └──────────┘      └────────────┘   └──────────┘
        ↓                  ↓                  ↓                ↓
        └──────────────────┬──────────────────┬────────────────┘
                           ↓
            ┌─────────────────────────────────┐
            │   Response to User               │
            └─────────────────────────────────┘
```

### Graph Nodes

1. **query_analysis**: Analyzes and classifies incoming queries
2. **retriever**: Retrieves relevant documents from vector store
3. **grade**: Evaluates relevance of retrieved documents
4. **rewrite**: Optimizes query for better retrieval results
5. **generate**: Generates final response from context
6. **web_search**: Performs real-time web search when needed
7. **general_llm**: Provides general knowledge answers

---

## 📦 Project Structure

```
AdaptiveRag/
├── src/                              # Main source code
│   ��── main.py                       # FastAPI application entry point
│   ├── api/                          # API routes and endpoints
│   │   └── routes.py                 # RAG query and document upload endpoints
│   ├── config/                       # Configuration management
│   │   ├── settings.py               # Application settings
│   │   └── prompts.yaml              # LLM prompts and system messages
│   ├── core/                         # Core utilities
│   │   ├── config.py                 # Core configuration
│   │   └── logger.py                 # Logging setup
│   ├── db/                           # Database layer
│   │   └── mongo_client.py           # MongoDB client initialization
│   ├── llms/                         # Language model integrations
│   │   └── openai.py                 # OpenAI ChatGPT-4o initialization
│   ├── memory/                       # Chat memory management
│   │   ├── chat_history_mongo.py     # MongoDB-backed chat history
│   │   └── chathistory_in_memory.py  # In-memory chat history (fallback)
│   ├── models/                       # Data models and schemas
│   │   ├── state.py                  # Graph state definition
│   │   ├── query_request.py          # Query request schema
│   │   ├── grade.py                  # Relevance grade model
│   │   ├── route_identifier.py       # Route classification model
│   │   └── verification_result.py    # Answer verification model
│   ├── rag/                          # RAG pipeline implementation
│   │   ├── graph_builder.py          # LangGraph workflow construction
│   │   ├── nodes.py                  # Graph node implementations
│   │   ├── retriever_setup.py        # Vector store and retriever setup
│   │   ├── document_upload.py        # Document processing and upload
│   │   └── reAct_agent.py            # ReAct agent setup
│   └── tools/                        # Utility tools and functions
│       ├── common_tools.py           # Shared utility functions
│       └── graph_tools.py            # Graph routing and decision tools
│
├── streamlit_app/                    # Streamlit web application
│   ├── home.py                       # Authentication and login page
│   ├── pages/                        # Multi-page application
│   │   └── chat.py                   # Chat interface and document upload
│   └── utils/                        # Streamlit utilities
│       └── api_client.py             # Backend API client
│
├── frontend/                         # Next.js web application (recommended UI)
│   └── src/
│       ├── app/                      # App Router pages & API route handlers
│       │   ├── login/                # Sign in / register (server actions)
│       │   ├── chat/                 # Protected chat page
│       │   └── api/                  # Proxies to FastAPI (/chat, /documents)
│       ├── components/               # ChatWindow, DocumentsSidebar, etc.
│       ├── lib/                      # Backend client + MongoDB helpers
│       ├── auth.ts                   # NextAuth v5 configuration
│       └── proxy.ts                  # Auth gate (Next 16 middleware → proxy)
│
├── README.md                         # This file
├── requirements.txt                  # Python dependencies
├── CODE_STYLE_GUIDE.md               # Code formatting standards
├── QUICK_REFERENCE.md                # Quick reference guide
├── README_FORMATTING.md              # Formatting documentation
├── VERIFICATION_CHECKLIST.md         # QA verification checklist
├── FORMATTING_SUMMARY.md             # Summary of code formatting
└── DOCUMENTATION_INDEX.md            # Documentation navigation index
```

---

## 🔌 API Endpoints

### Base URL
```
http://localhost:8000
```

### 1. Query Endpoint
**Process a RAG query and get intelligent response**

```http
POST /rag/query
Content-Type: application/json

{
  "query": "What is the main topic of the document?",
  "session_id": "user_session_123",
  "user_id": "alice"
}
```

**Response:**
```json
{
  "result": {
    "type": "ai",
    "content": "Based on the document, the main topic is..."
  }
}
```

**Parameters:**
- `query` (string, required): User's question or query
- `session_id` (string, required): Unique session identifier for conversation tracking
- `user_id` (string, required): Document owner; queries only search this user's documents

**Status Codes:**
- `200`: Success
- `400`: Invalid request format
- `500`: Server error

---

### 2. Document Upload Endpoint
**Upload documents for RAG indexing (documents accumulate per user)**

```http
POST /rag/documents/upload
X-Description: Brief description of the document
X-User-ID: alice

Form Data:
- file: <PDF or TXT file>
```

**Response:**
```json
{
  "status": "uploaded",
  "document": {
    "doc_id": "b7c1...",
    "user_id": "alice",
    "filename": "handbook.pdf",
    "description": "Enhanced tool instruction generated from your description",
    "num_chunks": 42,
    "created_at": "2026-08-24T10:00:00+00:00"
  }
}
```

**Headers:**
- `X-Description` (string, required): Document description for context
- `X-User-ID` (string, required): Owner of the document

**Parameters:**
- `file` (file, required): PDF or TXT file to upload

**Supported Formats:**
- PDF (.pdf)
- Plain Text (.txt)

**Status Codes:**
- `201`: Successfully uploaded and indexed
- `400`: Unsupported file type
- `409`: Identical content already uploaded by this user
- `503`: Vector database / storage unavailable

---

### 3. List Documents Endpoint
**List the requesting user's indexed documents**

```http
GET /rag/documents
X-User-ID: alice
```

**Response:**
```json
{
  "documents": [ { "doc_id": "...", "filename": "...", "description": "...",
                   "num_chunks": 42, "created_at": "..." } ]
}
```

---

### 4. Delete Document Endpoint
**Delete a document and its vectors from Qdrant**

```http
DELETE /rag/documents/{doc_id}
X-User-ID: alice
```

**Response:**
```json
{ "deleted": true, "doc_id": "...", "chunks_deleted": 42, "vectors_removed": true }
```

**Status Codes:**
- `200`: Deleted (registry row removed first, vectors cleaned up)
- `404`: Unknown document or not owned by `X-User-ID`
- `503`: Vector database unavailable

---

### 5. Health Endpoint
**Check backend dependencies (Qdrant + MongoDB)**

```http
GET /health
```

Returns `{"status": "ok", "qdrant": "ok", "mongo": "ok"}` or HTTP 503 with per-dependency status.

---

## 📖 Usage Guide

### 1. Prerequisites

```bash
# System Requirements
- Python 3.9 or higher
- MongoDB (local or cloud)
- Qdrant vector database (local Docker or Qdrant Cloud)
- Groq API key (free, console.groq.com) — or set LLM_PROVIDER to openai/huggingface/ollama
- HuggingFace token only if EMBEDDINGS_PROVIDER=huggingface_api (default is local, no token)
- Tavily API key (free tier, for web search)
```

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/dhruvsinghal09/Adaptive-Rag.git
cd AdaptiveRag

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the project root (see `.env.example` for all options):

```env
# Chat LLM (groq | openai | huggingface | ollama)
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b

# Embeddings (huggingface_local | huggingface_api | groq_openai_compat | openai)
EMBEDDINGS_PROVIDER=huggingface_local
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Web search
TAVILY_API_KEY=your_tavily_api_key_here

# Qdrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_DOCS_COLLECTION=documents

# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=adaptive_rag
```

> ⚠️ Never mix embedding providers once documents are ingested — the first
> provider fixes the collection's vector dimension. To switch, wipe the
> Qdrant collection and re-upload.

### 4. Running the Application

**Start FastAPI Backend:**
```bash
# Terminal 1: Run FastAPI server
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Start the Next.js Frontend (recommended):**
```bash
# Terminal 2: Run the Next.js dev server
cd frontend
npm install
npm run dev
```

**Or start the legacy Streamlit Frontend:**
```bash
# Terminal 2: Run Streamlit app
streamlit run streamlit_app/home.py
```

**Access the Application:**
- Web Interface: http://localhost:3000 (Next.js) or http://localhost:8501 (Streamlit)
- API Documentation: http://localhost:8000/docs
- ReDoc Documentation: http://localhost:8000/redoc

### 5. Example Usage

**Using the Web Interface:**
1. Navigate to http://localhost:8501
2. Create account or login
3. Upload documents in the sidebar
4. Start chatting in the main chat area

**Using cURL:**
```bash
# Upload a document
curl -X POST http://localhost:8000/rag/documents/upload \
  -H "X-User-ID: alice" \
  -H "X-Description: Sample document about Python" \
  -F "file=@document.pdf"

# List your documents
curl http://localhost:8000/rag/documents -H "X-User-ID: alice"

# Query the RAG system
curl -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Tell me about Python",
    "session_id": "user_123",
    "user_id": "alice"
  }'

# Delete a document
curl -X DELETE http://localhost:8000/rag/documents/<doc_id> -H "X-User-ID: alice"
```

**Using Python:**
```python
import requests

# Query endpoint
response = requests.post(
    "http://localhost:8000/rag/query",
    json={
        "query": "What is Python?",
        "session_id": "user_123"
    }
)
print(response.json())
```

---

## 🖥️ Next.js Frontend (`frontend/`)

A full-stack Next.js (App Router) UI with authentication built in. The
Streamlit app remains available and untouched; the two frontends share the
same FastAPI backend and databases.

### Stack

| Piece | Choice |
|-------|--------|
| Framework | Next.js 16 (App Router, React 19, TypeScript) |
| Styling | Tailwind CSS v4 |
| Auth | NextAuth v5 (Auth.js) — credentials provider, bcrypt-hashed users |
| User store | MongoDB `users` collection (same DB the backend uses) |
| Markdown | react-markdown |

### How auth works

- **Accounts live in MongoDB** (`users` collection, unique username, bcrypt
  password hash). Register/sign-in forms are server actions; sessions are
  JWT cookies signed with `AUTH_SECRET`.
- **Identity never comes from the browser.** All backend calls happen in
  Next.js route handlers under `/api/*`, which read the username from the
  server-side session and attach `X-User-ID` themselves. The browser never
  talks to FastAPI directly — no CORS, and one user cannot read or delete
  another user's documents by spoofing a header.
- This replaces the old external Rust auth service dependency; the backend
  itself is unchanged.

### Setup

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
# openssl rand -base64 32  (or: node -e "console.log(require('crypto').randomBytes(32).toString('base64'))")
AUTH_SECRET=<random string>
AUTH_TRUST_HOST=true

# Same MongoDB the FastAPI backend uses
MONGODB_URI=mongodb://localhost:27017   # or your Atlas URI
MONGODB_DB_NAME=adaptive_rag            # optional, defaults to adaptive_rag

# Where the FastAPI backend runs
BACKEND_URL=http://127.0.0.1:8000
```

Run it:

```bash
npm run dev     # http://localhost:3000
```

### Pages & routes

- `/login` — sign in / create account (server actions + useActionState)
- `/chat` — chat window + documents sidebar (upload with description,
  list, delete); protected by `src/proxy.ts` (Next 16 renamed middleware →
  proxy)
- `POST /api/chat` — proxies `POST /rag/query`
- `GET/POST /api/documents` — list / upload documents
- `DELETE /api/documents/[docId]` — delete a document

---

## 🔧 Configuration

### Key Configuration Files

#### `config/settings.py`
```python
# Core application settings loaded from environment
OPENAI_API_KEY           # OpenAI API authentication
TAVILY_API_KEY          # Web search functionality
QDRANT_URL              # Vector database endpoint
QDRANT_API_KEY          # Vector database authentication
MONGODB_URL             # Chat history database
```

#### `config/prompts.yaml`
Contains system prompts for:
- **system_prompt**: ReAct agent system instructions
- **classify_prompt**: Query classification logic
- **grading_prompt**: Document relevance evaluation
- **rewrite_prompt**: Query optimization
- **generate_prompt**: Response generation

### Query Routing Logic

The system routes queries based on classification. The classifier also sees a
catalogue of the requesting user's indexed documents and selects which ones
are relevant; retrieval is then filtered to those documents:

```
Query Classification (+ relevant doc_ids)
├── "index"   → Qdrant retriever filtered by user_id + selected docs
├── "general" → Use general LLM (common knowledge)
└── "search"  → Use web search (real-time information)
```

### Multi-Document Knowledge Base

- All documents live in one persistent **Qdrant** collection, tagged with
  `doc_id`, `user_id`, `source` and `description` metadata.
- Uploads **accumulate**: every document gets its own registry entry in
  MongoDB (`documents` collection) — no data is lost between uploads or
  server restarts.
- Queries are **isolated per user**: users only ever search their own documents.
- Documents can be listed via `GET /rag/documents` and deleted via
  `DELETE /rag/documents/{doc_id}`.
- See `.env.example` for all configuration options.

---

## 🧪 Testing the API

### Using FastAPI Interactive Documentation

1. Navigate to http://localhost:8000/docs
2. Expand endpoint sections
3. Click "Try it out"
4. Enter test data
5. Click "Execute"

### Example Test Cases

**Test 1: Simple Query**
```json
{
  "query": "Hello, how are you?",
  "session_id": "test_user_1"
}
```

**Test 2: Document-Based Query**
```json
{
  "query": "What topics are covered in the uploaded document?",
  "session_id": "test_user_1"
}
```

**Test 3: General Knowledge Query**
```json
{
  "query": "What is machine learning?",
  "session_id": "test_user_1"
}
```

---

## 🔐 Security Considerations

- Store API keys in `.env` file (never commit)
- Use environment variables for sensitive data
- Implement rate limiting for production
- Validate all user inputs
- Use HTTPS in production
- Implement authentication/authorization
- Secure MongoDB with proper credentials

---

## 🚀 Deployment

### Local Development
```bash
# Run development server with auto-reload
python -m uvicorn src.main:app --reload
```

### Production Deployment
```bash
# Run with production settings
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker Support (Optional)
Create `Dockerfile` and `docker-compose.yml` for containerized deployment.

---

## 📊 Performance Optimization

- **Document Chunking**: Configurable chunk size (1000 chars, 150 overlap)
- **Vector Search**: Efficient similarity search with Qdrant
- **Async Operations**: Non-blocking I/O for better throughput
- **Caching**: Query results cached when applicable
- **Batch Processing**: Document processing in batches

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/YourFeature`)
3. Make changes following CODE_STYLE_GUIDE.md
4. Commit with descriptive messages (`git commit -m 'feat: Add YourFeature'`)
5. Push to your branch (`git push origin feature/YourFeature`)
6. Open a Pull Request

### Code Quality
- Follow PEP 8 standards
- Add docstrings to all functions
- Write unit tests for new features
- Update documentation
- Run linting: `flake8 src/`

---

## 📚 Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **LLM Framework** | LangChain | ~0.3.27 |
| **Workflow Orchestration** | LangGraph | ~0.5.4 |
| **Web Framework** | FastAPI | Latest |
| **ASGI Server** | Uvicorn | Latest |
| **UI Framework** | Streamlit | Latest |
| **Vector Database** | Qdrant | Latest |
| **Chat Database** | MongoDB/InMemory | Latest |
| **Document Processing** | LangChain Community | ~0.3.27 |
| **LLM Provider** | Groq (gpt-oss-120b) / OpenAI / HuggingFace / Ollama | Latest |
| **Embeddings** | HuggingFace local MiniLM (default) / OpenAI / Groq | Latest |
| **Web Search** | Tavily | Latest |
| **Frontend** | Next.js 16 + React 19 + Tailwind v4 (+ legacy Streamlit) | Latest |
| **Frontend Auth** | NextAuth v5 (credentials, bcrypt via MongoDB) | 5.0.0-beta.32 |
| **Async DB** | Motor | Latest |
| **Data Validation** | Pydantic | ~2.11.7 |

---

## 📝 Documentation References

- [CODE_STYLE_GUIDE.md](CODE_STYLE_GUIDE.md) - Comprehensive coding standards
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Quick patterns and templates
- [README_FORMATTING.md](README_FORMATTING.md) - Code formatting overview
- [VERIFICATION_CHECKLIST.md](VERIFICATION_CHECKLIST.md) - QA checklist
- [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) - Full documentation index

---

## ❓ FAQ

**Q: How do I upload multiple documents?**  
A: Upload one document at a time through the Streamlit interface. Each upload creates a new indexed collection.

**Q: What's the maximum file size?**  
A: Limited by system memory and Qdrant storage. Typical limit is 100MB per file.

**Q: Can I use different LLM providers?**  
A: Yes — set `LLM_PROVIDER` to `groq` (default, free), `openai`, `huggingface`, or `ollama` in `.env`. Embeddings are switched separately via `EMBEDDINGS_PROVIDER`. See `src/llms/chat_model.py` and `src/llms/embeddings.py`.

**Q: How is conversation history stored?**  
A: MongoDB stores all chat messages with timestamps and session IDs for full context retention.

**Q: Can I run this without web search?**  
A: Yes, remove Tavily dependency. Queries will use index or general LLM only.

---

## 💬 Support & Contact

For issues, questions, or suggestions:
- Open an [Issue](https://github.com/dhruvsinghal09/Adaptive-Rag/issues)
- Check existing documentation
- Review the code comments

---

## 🙏 Acknowledgments

- Built with LangChain and LangGraph
- Vector search powered by Qdrant
- LLM capabilities by OpenAI
- Web search by Tavily
- UI powered by Streamlit
- Thanks to the open-source community

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Dhruv Singhal**
- GitHub: [@dhruvsinghal09](https://github.com/dhruvsinghal09)
- Project: [Adaptive RAG](https://github.com/dhruvsinghal09/Adaptive-Rag)

---

## 📈 Project Status

- ✅ Core RAG pipeline implemented
- ✅ Document upload and indexing
- ✅ Query routing (index/general/search)
- ✅ MongoDB chat history
- ✅ Streamlit web interface
- ✅ Code formatted and documented
- 🚀 Production ready

---

## 🗺️ Roadmap

- [ ] Enhanced context management
- [ ] Multi-language support
- [ ] Performance benchmarks
- [ ] Extended LLM provider support
- [ ] Advanced authentication
- [ ] Real-time collaboration
- [ ] Analytics dashboard
- [ ] Cost optimization

---

**Last Updated**: March 5, 2026  
**Status**: ✅ Production Ready  
**Documentation**: ✅ Comprehensive
