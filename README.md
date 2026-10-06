# ✦ Aegis-HR — Agentic RAG Engine with Role-Based Access Control for Enterprise HR Intelligence

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_Workflow-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Groq](https://img.shields.io/badge/Groq-Ultra--Fast_LPU_Inference-f55036.svg)](https://groq.com/)
[![Pinecone](https://img.shields.io/badge/Pinecone-Vector_DB_with_RBAC-00b4d8.svg)](https://www.pinecone.io/)
[![Cohere](https://img.shields.io/badge/Cohere-Embed_English_v3.0-39A0ED.svg)](https://cohere.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon_Async_Checkpointer-336791.svg)](https://neon.tech/)
[![Redis](https://img.shields.io/badge/Redis-Rate_Limiting-DC382D.svg)](https://redis.io/)
[![LangSmith](https://img.shields.io/badge/LangSmith-Observability-orange.svg)](https://smith.langchain.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](#-license)

> **A fully asynchronous, RBAC-secured agentic RAG engine for enterprise HR policy intelligence — featuring LLM-driven adaptive routing, multi-path document grading with automatic web fallback, clearance-gated vector retrieval, per-user persistent memory via async PostgreSQL checkpointing, and Redis-backed rate limiting.**

---

## 📋 **Table of Contents**

- [Problem Statement](#-problem-statement)
- [Solution Overview](#-solution-overview)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Usage](#-usage)
- [API Endpoints](#-api-endpoints)
- [RBAC Security Model](#-rbac-security-model)
- [Observability with LangSmith](#-observability-with-langsmith)
- [Configuration](#-configuration)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)
- [Contact & Support](#-contact--support)

---

## 🚨 **Problem Statement**

### **The Challenge**

Enterprise HR departments manage highly sensitive, multi-tiered policy documents — from public employee handbooks to confidential executive severance agreements. Building an AI assistant that serves this information safely and accurately faces several critical barriers:

- **Data Leakage Risk**: Standard RAG pipelines retrieve documents purely by semantic similarity, ignoring organizational security hierarchies. An intern querying *"What is the severance policy?"* could receive board-level executive compensation details, PIP runbook strategies, or M&A acceleration clauses — a catastrophic data breach.
- **Hallucination in HR Context**: Generic LLMs fabricate HR policies, invent leave quotas, or generate fictitious legal clauses. In regulated environments (banking, healthcare, government), a hallucinated policy answer is a compliance liability.
- **Static Retrieval Pipelines**: Traditional RAG systems retrieve → generate in a single pass. They cannot self-assess whether retrieved documents are actually relevant, cannot fall back to alternative data sources when the knowledge base lacks coverage, and cannot gracefully degrade.
- **Stateless Conversations**: Most AI assistants treat each query as isolated. HR conversations are inherently multi-turn: *"What's the leave policy?"* → *"Does that apply during probation?"* → *"Can I carry forward unused days?"*. Without persistent memory, context is lost between every request.
- **Event Loop Blocking**: Many Python AI backends use synchronous LLM calls inside async frameworks (FastAPI), causing the entire server to freeze during inference — making the system unusable under concurrent load.

### **The Gap**

There is no **open, production-grade, RBAC-secured agentic RAG engine** that:

- Enforces document-level security clearances directly at the vector database query layer.
- Uses an LLM-powered adaptive router to intelligently classify queries as internal knowledge vs. general web.
- Implements multi-stage document grading with automatic fallback chains (KB → Web → Graceful Fallback).
- Maintains per-user conversational memory persisted in PostgreSQL with crash resilience.
- Runs a fully non-blocking async architecture from endpoint to LLM inference.
- Provides enterprise-grade rate limiting, JWT authentication, and production observability.

---

## 💡 **Solution Overview**

**Aegis-HR** is an agentic RAG engine that orchestrates an intelligent, self-correcting retrieval and generation workflow through a **LangGraph** state machine:

```
[User Query + JWT Token]
        │
        ▼
[Route Question — LLM Classifier]
        │
   ┌────┴─────┐
   ▼           ▼
[Retrieve KB]  [Web Search]
(Pinecone      (Tavily API)
 + RBAC          │
 Filter)         ▼
   │         [Grade Web Docs]
   ▼              │
[Grade KB     ┌───┴───┐
 Docs]        ▼       ▼
   │       [Generate] [Fallback]
┌──┴──┐     (Groq     "Insufficient
▼     ▼     LPU)      Information"
[Gen] [Web
erate] Search
(Groq   ──►
 LPU)
```

### **Execution Flow**

1. **JWT Authentication & RBAC Extraction** — Every request is authenticated via OAuth2 Bearer tokens. The JWT payload carries the user's `role`, `department`, and `clearance` level (1–5).
2. **Adaptive LLM Router** — The `route_question` node uses Groq-powered structured output (`routequery`) to classify the query as internal HR knowledge (`KB`) or general world knowledge (`web`).
3. **RBAC-Gated Vector Retrieval** — The `retrieve_kb` node queries Pinecone with a metadata filter `{"clearance": {"$lte": user_clearance}}`, ensuring users **never see documents above their security clearance**.
4. **Multi-Stage Document Grading** — Retrieved documents pass through an LLM grader (`gradedocuments`) that assesses semantic relevance. Irrelevant documents are filtered out.
5. **Automatic Web Fallback** — If all KB documents fail grading, the workflow automatically pivots to Tavily web search, which is also graded for relevance.
6. **Graceful Degradation** — If both KB and web results fail relevance grading, the system returns a transparent fallback message instead of hallucinating.
7. **Grounded Generation** — The final `generate` node uses a strict system prompt: *"Answer based ONLY on the provided context."* — eliminating fabricated policies.
8. **Per-User Persistent Memory** — Conversation history is checkpointed per-user into Neon PostgreSQL via `AsyncPostgresSaver`, surviving server restarts and disconnections.

### **What Makes It Special**

- ✅ **Security at the Data Layer**: RBAC is enforced at the Pinecone query level — not as a post-retrieval filter. Documents above a user's clearance **never leave the vector database**.
- ✅ **Self-Correcting Retrieval**: The graph doesn't blindly trust retrieved documents. It grades them, and autonomously reroutes to web search if the KB fails.
- ✅ **Fully Non-Blocking Async Architecture**: Every LangGraph node uses `async def` with `ainvoke` / `asimilarity_search`. The FastAPI event loop is never blocked, even under heavy concurrent load.
- ✅ **Ultra-Low Latency Inference**: Powered by Groq LPU running `openai/gpt-oss-120b` for sub-second structured output and generation.
- ✅ **Production-Grade Rate Limiting**: Redis-backed per-user rate limiting (5 requests / 60 seconds) via `fastapi-limiter`.
- ✅ **Enterprise Observability**: Full end-to-end tracing with LangSmith — node-level latency, token costs, and routing decision visibility.

---

## ✨ **Features**

### 🌟 **Core Features**

| Feature | Description |
|---------|-------------|
| **🛡️ RBAC-Gated Retrieval** | Pinecone metadata filter `{"clearance": {"$lte": N}}` enforces document-level security at the vector DB query layer |
| **🧠 Adaptive LLM Router** | Groq-powered structured output classifies queries into KB (HR policies) or Web (general knowledge) paths |
| **📊 Multi-Stage Document Grading** | LLM grader evaluates each retrieved document for semantic relevance before generation |
| **🔄 Automatic Web Fallback** | If KB documents fail relevance grading, the graph autonomously pivots to Tavily web search |
| **🚫 Graceful Degradation** | Transparent fallback message when both KB and web sources fail — zero hallucination guarantee |
| **💬 Per-User Persistent Memory** | Conversation threads checkpointed into Neon PostgreSQL via `AsyncPostgresSaver` |
| **⚡ Fully Async Architecture** | Every node uses `async def` + `ainvoke` — the FastAPI event loop is never blocked |
| **🔑 JWT OAuth2 Authentication** | HS256-signed tokens carrying `role`, `department`, and `clearance` claims |
| **🚦 Redis Rate Limiting** | Per-user throttling (5 req/60s) via Docker Redis + `fastapi-limiter` |
| **📝 Source Attribution** | Every response includes `*(Source: Knowledge Base)*`, `*(Source: Web)*`, or `*(Source: Fallback)*` |

### 🚀 **Advanced Features**

| Feature | Description |
|---------|-------------|
| **⚡ Groq LPU Acceleration** | Sub-second inference via `openai/gpt-oss-120b` on Groq's custom Language Processing Units |
| **🔗 Cohere Embed v3.0** | State-of-the-art 1024-dimensional embeddings for high-precision semantic retrieval |
| **🗄️ Async PostgreSQL Pooling** | `AsyncConnectionPool` with max 20 connections, `autocommit` mode, and zero-downtime shutdown |
| **📦 Docker Compose Infra** | One-command local setup for PostgreSQL 15 + Redis Alpine containers |
| **🔬 LangSmith Tracing** | Full observability — node-by-node latency, token accounting, and routing decision traces |
| **🏗️ Factory-Pattern Graph Compilation** | `build_rag_app(checkpointer)` allows hot-swapping memory backends without code changes |
| **🔐 Secret-Safe Configuration** | All API keys stored as `SecretStr` via Pydantic Settings, loaded from `.env` |

### 🎯 **Use Cases**

- **Enterprise HR Chatbots**: Deploy secure, multi-clearance HR assistants for organizations where different roles see different policies.
- **Regulated Industry Compliance**: Banking, healthcare, and government organizations requiring strict data access controls on AI-generated answers.
- **Multi-Tier Knowledge Management**: Any organization with hierarchical document sensitivity (public → confidential → restricted → top secret).
- **Agentic RAG Research**: Benchmark self-correcting retrieval graphs, adaptive routing, and document grading pipelines.

---

## 🛠️ **Tech Stack**

### **System Architecture**

```mermaid
graph TD
    Client[API Consumer / Postman / Frontend] -->|HTTP + JWT Bearer| FastAPI[FastAPI Async Server]
    FastAPI -->|Rate Check| Redis[(Redis Rate Limiter)]
    FastAPI --> LG[LangGraph Agentic Workflow]
    LG --> Checkpoint[(Neon PostgreSQL Checkpointer)]
    LG --> Groq[Groq LPU — gpt-oss-120b]
    
    subgraph Retrieval Plane [Retrieval & Search Plane]
        LG --> Pinecone[(Pinecone Vector DB + RBAC Filter)]
        LG --> Cohere[Cohere Embed v3.0]
        LG --> Tavily[Tavily Web Search API]
    end

    LG --> LS[LangSmith Observability]
    Pinecone -.->|Metadata: clearance ≤ N| RBAC{RBAC Security Layer}
```

### **Backend**

| Technology | Purpose |
|------------|---------|
| **Python 3.11+** | Primary programming language |
| **FastAPI 0.115+** | High-performance asynchronous API framework with automatic OpenAPI docs |
| **LangGraph** | Stateful multi-node agentic workflow orchestration with conditional routing |
| **LangChain 0.3+** | LLM abstractions, prompt templates, structured output, and chain composition |
| **Groq (`langchain-groq`)** | Sub-second LPU inference with `openai/gpt-oss-120b` |
| **Pinecone (`langchain-pinecone`)** | Serverless vector database with metadata-filtered RBAC similarity search |
| **Cohere (`langchain-cohere`)** | `embed-english-v3.0` — 1024-dim embeddings for high-precision retrieval |
| **Tavily (`langchain-tavily`)** | Web search API for fallback knowledge grounding |
| **Neon PostgreSQL** | Cloud-native serverless PostgreSQL for async LangGraph checkpointing |
| **psycopg 3.2+ & psycopg-pool** | Asynchronous connection pooling with `AsyncConnectionPool` |
| **Redis + fastapi-limiter** | In-memory rate limiting backend (5 requests / 60 seconds per user) |
| **python-jose + passlib** | JWT (HS256) token signing, verification, and password hashing |
| **Pydantic v2+ & pydantic-settings** | Strict schema validation, structured LLM output, and `.env` configuration |
| **LangSmith** | Production tracing, token evaluation, and node-level latency monitoring |

### **Infrastructure**

| Technology | Purpose |
|------------|---------|
| **Docker Compose** | Local development stack — PostgreSQL 15 Alpine + Redis Alpine |
| **Uvicorn** | ASGI server with `--reload` for development |

---

## 🏗️ **Architecture**

### **State Graph Topology**

```mermaid
flowchart TD
    START([START]) --> RouteQ{route_question<br/>LLM Classifier}
    
    RouteQ -->|HR / Policy Query| RetrieveKB[retrieve_kb<br/>Pinecone + RBAC Filter]
    RouteQ -->|General Knowledge| WebSearch[web_search<br/>Tavily API]
    
    RetrieveKB --> GradeKB[grade_documents<br/>LLM Relevance Grader]
    
    GradeKB -->|KB Grade: GOOD| Generate[generate<br/>Groq LPU Answer]
    GradeKB -->|KB Grade: WEAK| WebSearch
    
    WebSearch --> GradeWeb[grade_web_documents<br/>LLM Relevance Grader]
    
    GradeWeb -->|Web Grade: GOOD| Generate
    GradeWeb -->|Web Grade: WEAK| Fallback[fallback<br/>Graceful Degradation]
    
    Generate --> END_GEN([END])
    Fallback --> END_FALL([END])
```

### **Data Flow Walkthrough**

1. **Authentication**: User sends a `POST /api/auth/login` with username/password. Server returns a signed JWT containing `sub` (username), `role`, `department`, and `clearance` claims.
2. **Secure Chat Request**: User sends `POST /api/rag/ask` with the JWT Bearer token and a JSON body `{"question": "..."}`.
3. **Rate Limiting**: Redis-backed `RateLimiter` checks if the user has exceeded 5 requests per 60 seconds. Excess requests receive `HTTP 429`.
4. **RBAC Context Injection**: The `get_current_user` dependency extracts the user's `clearance` (1–5) and `department` from the JWT and injects them into the LangGraph state.
5. **Adaptive Routing**: The `route_question` node invokes the Groq LLM with structured output (`routequery`) to classify the query. HR-related queries route to `retrieve_kb`; general queries route to `web_search`.
6. **RBAC-Gated Retrieval**: The `retrieve_kb` node queries Pinecone with filter `{"clearance": {"$lte": user_clearance}}`. A Clearance-1 intern **never receives** Clearance-4 HR runbook data or Clearance-5 board documents.
7. **Document Grading**: Each retrieved document is evaluated by the LLM grader for semantic relevance. Irrelevant results are discarded.
8. **Conditional Fallback**: If all KB documents are graded `weak`, the graph automatically redirects to `web_search` → `grade_web_documents`. If web results also fail, the graph routes to `fallback`.
9. **Grounded Generation**: The `generate` node answers using **only** the graded context, with explicit source attribution appended.
10. **Persistent Checkpointing**: The entire `TravelState` is saved per-user into Neon PostgreSQL via `AsyncPostgresSaver`, enabling multi-turn conversations across sessions.

### **RBAC Security Architecture**

```
┌─────────────────────────────────────────────────────────┐
│                    PINECONE VECTOR DB                    │
├─────────────────────────────────────────────────────────┤
│ Clearance 1 │ Employee Handbook (Leave, Remote Work)    │ ◄── All Users
│ Clearance 4 │ HR Runbook (PIP, Bonus Forfeiture)        │ ◄── HR Admins Only
│ Clearance 5 │ Executive Severance (Stock Acceleration)  │ ◄── Board Only
└─────────────────────────────────────────────────────────┘

   intern_bob (Clearance 1)  →  Sees ONLY Clearance ≤ 1 docs
   hr_alice   (Clearance 4)  →  Sees ONLY Clearance ≤ 4 docs
   aditya     (Clearance 5)  →  Sees ALL docs (Clearance ≤ 5)
```

---

## 📁 **Project Structure**

```
Aegis-HR/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, lifespan (Redis + Async PG + Graph)
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py              # Pydantic Settings (SecretStr, .env loader)
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── auth.py            # POST /api/auth/login — JWT token issuance
│   │       └── chat.py            # POST /api/rag/ask — Secure async RAG endpoint
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── state.py               # TypedDict state schema for LangGraph
│   │   ├── retriever.py           # Pinecone + Cohere vectorstore factory
│   │   └── workflow.py            # LangGraph nodes, chains, routing, graph builder
│   ├── schemas/
│   │   └── __init__.py            # Pydantic models (routequery, gradedocuments)
│   └── services/
│       ├── __init__.py
│       └── auth.py                # JWT creation, validation, user directory, RBAC
├── data/
│   └── sample_kb/                 # Sample HR knowledge base documents
├── ingest_kb.py                   # RBAC-tagged document ingestion into Pinecone
├── docker-compose.yml             # PostgreSQL 15 + Redis Alpine containers
├── requirements.txt               # All Python dependencies
├── .env                           # API keys & database credentials (git-ignored)
├── .gitignore
├── LICENSE                        # MIT License
└── README.md
```

---

## 📦 **Installation**

### **Prerequisites**

- **Python 3.11+** installed
- **Docker Desktop** — For local PostgreSQL and Redis containers
- **API Keys**:
  - **Groq API Key**: Ultra-fast LLM inference ([console.groq.com](https://console.groq.com/))
  - **Pinecone API Key**: Serverless vector database ([pinecone.io](https://www.pinecone.io/))
  - **Cohere API Key**: Embedding model ([cohere.com](https://cohere.com/))
  - **Tavily API Key**: Web search fallback ([tavily.com](https://tavily.com/))
  - **LangSmith API Key** *(Optional)*: Observability ([smith.langchain.com](https://smith.langchain.com/))

---

### **1. Clone the Repository**

```bash
git clone https://github.com/Aditya-Sharma-dev18/Aegis-HR.git
cd Aegis-HR
```

---

### **2. Set Up Virtual Environment**

Using Conda:
```bash
conda create -n aegis python=3.11 -y
conda activate aegis
```

Or using standard Python `venv`:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

---

### **3. Install Dependencies**

```bash
pip install -r requirements.txt
```

---

### **4. Configure Environment Variables**

Create a `.env` file in the project root:

```env
# ── AI Provider Keys ──────────────────────────────────
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxx
COHERE_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ── Pinecone Vector DB ────────────────────────────────
PINECONE_API_KEY=pcsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
PINECONE_INDEX_NAME=aegis-hr-index

# ── PostgreSQL Database (Neon or Local) ───────────────
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require

# ── JWT Security ──────────────────────────────────────
SECRET_KEY=your-256-bit-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ── Redis Rate Limiter ────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── LangSmith Observability (Optional) ────────────────
LANGSMITH_API_KEY=lsv2_pt_xxxxxxxxxxxxxxxxxxxxxxxx
LANGSMITH_PROJECT_NAME=aegis-hr
LANGSMITH_TRACING_V2=True
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

---

### **5. Start Infrastructure (Docker)**

```bash
docker-compose up -d
```

This starts:
- **PostgreSQL 15 Alpine** on port `5432` (container: `aegis_postgres`)
- **Redis Alpine** on port `6379` (container: `aegis_redis`)

---

### **6. Ingest the Knowledge Base**

```bash
python ingest_kb.py
```

This uploads RBAC-tagged HR documents into Pinecone with clearance-level metadata:

| Document | Clearance | Department |
|----------|-----------|------------|
| Employee Handbook (Leave, Remote Work) | 1 (Standard) | All |
| HR Runbook (PIP, Bonus Forfeiture) | 4 (Confidential) | HR |
| Executive Severance (Stock Acceleration) | 5 (Top Secret) | Board |

---

### **7. Run the Application**

```bash
uvicorn app.main:app --reload --port 8000
```

Server starts at **http://127.0.0.1:8000**. Startup logs will confirm:

```
🟢 Redis Rate Limiter Initialized via Docker!
🟢 Async Postgres Connection Pool Opened!
🟢 LangGraph Async Checkpointer Ready!
🟢 Agentic RAG Graph Compiled Successfully!
```

---

## 🎯 **Usage**

### **Step 1: Authenticate**

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=aditya&password=password123"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### **Step 2: Ask a Question**

```bash
curl -X POST http://127.0.0.1:8000/api/rag/ask \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the leave policy?"}'
```

**Response:**
```json
{
  "query": "What is the leave policy?",
  "answer": "Every employee is entitled to 20 days of paid annual leave. Sick leave is capped at 10 days per year. \n\n*(Source: Knowledge Base)*",
  "security_context": {
    "user": "aditya",
    "clearance_applied": 5,
    "thread_id": "aditya"
  }
}
```

### **RBAC in Action**

#### **Executive (Clearance 5) — Sees Everything**
```
Q: "What happens to stock options during an acquisition?"
A: "The CEO and Board members will receive accelerated vesting of 100% of their stock options."
   *(Source: Knowledge Base)*
```

#### **Intern (Clearance 1) — Restricted View**
```
Q: "What happens to stock options during an acquisition?"
A: "I do not have clearance or information to answer this."
```

> The intern's query hits Pinecone with filter `{"clearance": {"$lte": 1}}`. The Clearance-5 executive severance document **never leaves the database**.

---

## 📡 **API Endpoints**

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | `GET` | ❌ | System health check — `{"status": "online"}` |
| `/api/auth/login` | `POST` | ❌ | OAuth2 login — returns JWT Bearer token |
| `/api/rag/ask` | `POST` | ✅ JWT | Secure RAG chat — RBAC-filtered, rate-limited, memory-backed |
| `/docs` | `GET` | ❌ | Interactive Swagger UI (auto-generated by FastAPI) |
| `/redoc` | `GET` | ❌ | ReDoc API documentation |

### **Rate Limiting**

All authenticated endpoints enforce **5 requests per 60 seconds** per user via Redis. Exceeding this limit returns:

```json
{
  "detail": "Too Many Requests"
}
```

---

## 🔐 **RBAC Security Model**

### **Clearance Levels**

| Level | Name | Access Scope | Example Role |
|-------|------|-------------|--------------|
| **1** | Standard | Public employee policies (leave, remote work, benefits) | `employee`, `intern` |
| **2** | Internal | Internal operational procedures | `team_lead` |
| **3** | Sensitive | Compensation structures, performance metrics | `manager` |
| **4** | Confidential | PIP procedures, bonus forfeiture rules, HR runbooks | `hr_admin` |
| **5** | Top Secret | Executive severance, stock acceleration, M&A clauses | `executive`, `board` |

### **How It Works**

1. **Ingestion**: Documents are uploaded to Pinecone with `metadata={"clearance": N, "department": "..."}`.
2. **Retrieval**: The `retrieve_kb` node applies `filter={"clearance": {"$lte": user_clearance}}` — only documents at or below the user's clearance are ever returned.
3. **Enforcement**: This is **not** a post-retrieval filter. The Pinecone server itself excludes restricted documents from the similarity search results. They never enter the application's memory space.

### **Demo Users**

| Username | Password | Role | Department | Clearance |
|----------|----------|------|------------|-----------|
| `aditya` | `password123` | Executive | Board | 5 |
| `hr_alice` | `password123` | HR Admin | HR | 4 |
| `intern_bob` | `password123` | Employee | Engineering | 1 |

---

## 🔬 **Observability with LangSmith**

Aegis-HR is instrumented with **LangSmith** for full production-grade visibility across the agentic retrieval pipeline.

### **What You Get**

- **Node-by-Node Tracing**: Latency breakdown for `route_question`, `retrieve_kb`, `grade_documents`, `web_search`, `generate`, and `fallback`.
- **Routing Decision Logs**: See exactly why the LLM classified a query as `KB` vs `web`.
- **Document Grading Audit Trail**: Inspect which documents passed / failed the relevance grader and why.
- **Token Accounting**: Track prompt tokens, completion tokens, and dollar expenditure per Groq query.
- **Error Diagnostics**: Complete stack traces linked to exact graph nodes.

### **Setup**

1. Sign up at [smith.langchain.com](https://smith.langchain.com/).
2. Add your credentials to `.env`:

```env
LANGSMITH_TRACING_V2=True
LANGSMITH_API_KEY=lsv2_pt_xxxxxxxxxxxxxxxx
LANGSMITH_PROJECT_NAME=aegis-hr
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

---

## 🔧 **Configuration**

### **Model Configuration (`workflow.py`)**

```python
# Groq LPU — Ultra-fast inference for routing, grading, and generation
model = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=settings.GROQ_API_KEY,
)
```

### **Embedding Model (`retriever.py`)**

```python
# Cohere Embed English v3.0 — 1024-dimensional embeddings
embeddings = CohereEmbeddings(
    cohere_api_key=settings.COHERE_API_KEY.get_secret_value(),
    model="embed-english-v3.0"
)
```

### **PostgreSQL Pool Settings (`main.py`)**

```python
pool = AsyncConnectionPool(
    conninfo=settings.DATABASE_URL,
    max_size=20,
    kwargs={"autocommit": True},
)
```

### **Rate Limiting**

```python
# 5 requests per 60 seconds per authenticated user
@router.post("/ask", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
```

---

## 🚀 **Deployment**

### **Option 1: Render.com**

```yaml
services:
  - type: web
    name: aegis-hr
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: GROQ_API_KEY
        sync: false
      - key: PINECONE_API_KEY
        sync: false
      - key: COHERE_API_KEY
        sync: false
      - key: TAVILY_API_KEY
        sync: false
      - key: SECRET_KEY
        sync: false
      - key: REDIS_URL
        sync: false
```

### **Option 2: Docker Container**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t aegis-hr .
docker run -p 8000:8000 --env-file .env aegis-hr
```

---

## 🔧 **Troubleshooting**

### **Common Issues & Solutions**

| Issue | Cause | Solution |
|-------|-------|----------|
| `ConnectionRefusedError: Redis` | Redis container not running | Run `docker-compose up -d` to start Redis |
| `psycopg.OperationalError: SSL SYSCALL` | Neon serverless connection timeout | Ensure `sslmode=require` is in `DATABASE_URL` |
| `RuntimeError: Event loop is closed` on Windows | Default `ProactorEventLoop` incompatible with async psycopg | Add `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())` before imports |
| `HTTP 429: Too Many Requests` | Rate limiter triggered | Wait 60 seconds or increase `times` in `RateLimiter(times=5, seconds=60)` |
| `HTTP 401: Could not validate credentials` | Missing or expired JWT token | Re-authenticate via `POST /api/auth/login` |
| `Pinecone index not found` | KB not ingested | Run `python ingest_kb.py` to create the index and upload documents |
| `Groq 429: Rate Limit Exceeded` | Exceeded Groq free-tier TPM/RPM | Wait briefly or switch to a smaller model like `openai/gpt-oss-20b` |

---

## 🤝 **Contributing**

Contributions are welcome! Whether it's adding new clearance tiers, integrating a real database for users, or building a frontend UI.

### **How to Contribute**

1. **Fork** the repository: [Aegis-HR on GitHub](https://github.com/Aditya-Sharma-dev18/Aegis-HR)
2. **Create** a feature branch:
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Commit** your changes following conventional commits:
   ```bash
   git commit -m "feat(rbac): add department-level filtering to vector queries"
   ```
4. **Push** to the branch:
   ```bash
   git push origin feature/amazing-feature
   ```
5. **Open** a Pull Request.

---

## 📄 **License**

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for complete details.

```
MIT License

Copyright (c) 2026 Aditya Sharma
```

---

## 🙏 **Acknowledgments**

- **LangChain & LangGraph** teams for stateful multi-agent primitives and conditional graph routing.
- **Groq** for high-throughput, low-latency LPU inference.
- **Pinecone** for serverless vector search with native metadata filtering.
- **Cohere** for state-of-the-art multilingual embedding models.
- **Neon Tech** for reliable, serverless PostgreSQL with instant autoscaling.
- **Tavily AI** for search intelligence and real-time web grounding.
- **Redis** for blazing-fast in-memory rate limiting.

---

## 🏆 **Project Status**

![Status](https://img.shields.io/badge/Status-Production_Ready-brightgreen.svg)
![Build](https://img.shields.io/badge/Build-Passing-brightgreen.svg)
![RBAC](https://img.shields.io/badge/RBAC-5--Tier_Clearance-blue.svg)
![Async](https://img.shields.io/badge/Architecture-Fully_Async-purple.svg)
![Observability](https://img.shields.io/badge/Observability-LangSmith-orange.svg)

---

## 📞 **Contact & Support**

- **GitHub Repository**: [Aditya-Sharma-dev18/Aegis-HR](https://github.com/Aditya-Sharma-dev18/Aegis-HR)
- **Issue Tracker**: [Report a Bug or Request a Feature](https://github.com/Aditya-Sharma-dev18/Aegis-HR/issues)
- **Author**: Aditya Sharma
- **Email**: [sharma.adityaaa0001@gmail.com](mailto:sharma.adityaaa0001@gmail.com)

---

## ⭐ **Star Us!**

If you find **Aegis-HR** useful or inspiring, please consider starring ⭐ the repository on GitHub!

---

**Crafted with 🛡️ by [Aditya Sharma](https://github.com/Aditya-Sharma-dev18)**
