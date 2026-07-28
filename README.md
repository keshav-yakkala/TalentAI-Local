# TalentAI — Agentic AI Recruitment Intelligence Platform

> Migrated and rebuilt from the original **AI_Recruitment_Partner** (Euron Recruitment Agent) Streamlit prototype into a production-grade, multi-tenant AI recruitment platform.

---

## Architecture

```
React + TypeScript + Vite
        ↓
FastAPI (Python 3.11)
        ↓
LangGraph Workflows → LLM (Ollama / Gemini / OpenAI)
        ↓
PostgreSQL + pgvector (semantic search)
        ↓
Redis + Celery (background jobs)
```

## What's New vs Original

| Feature | Before | After |
|---|---|---|
| Embeddings | Fake word-hash function | Real sentence-transformers |
| LLM calls | Direct `ollama.chat()` + `eval()` | Abstract `LLMProvider` + `json.loads()` + Pydantic |
| Resume parsing | PyPDF2 only | PyMuPDF (primary) + DOCX support |
| Session storage | `st.session_state` | PostgreSQL + LangGraph checkpoints |
| Multi-user | Single user, no auth | Multi-tenant, JWT auth, org isolation |
| Interview | Binary yes/no scoring | Multi-dimensional scores (0-10 per category) |
| RAG | Fake cosine similarity | Real pgvector semantic search |
| Frontend | Streamlit | React + TypeScript + Vite |
| Background jobs | None (blocking) | Celery + Redis |
| Security | eval() on LLM output 🚨 | Pydantic validation + strict IDOR protection |

## Security Fixes Applied

- ✅ Removed `eval()` on LLM output (was in `agents.py:185`) — replaced with `json.loads()` + Pydantic
- ✅ Added `.streamlit/credentials.toml` to `.gitignore` (contained real email address)
- ✅ `organization_id` never trusted from frontend/JWT — always resolved from DB membership
- ✅ Cross-tenant access attempts logged as CRITICAL and return generic 403

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.com) with `llama3` pulled
- PostgreSQL with pgvector (or use Docker)

### With Docker (recommended)
```bash
cp .env.example .env
# Edit .env: set JWT_SECRET_KEY with `openssl rand -hex 32`

docker-compose up postgres redis -d

cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

cd frontend
npm install
npm run dev
```

### Verify
```bash
curl http://localhost:8000/health
# → {"status": "ok", "app": "TalentAI", ...}
```

## Project Structure

```
.
├── legacy/              ← Original Streamlit app (preserved, not deleted)
├── frontend/            ← React + TypeScript + Vite
│   └── src/
│       ├── pages/       ← Landing, Login, Register, Recruiter pages
│       ├── layouts/     ← RecruiterLayout with sidebar
│       ├── store/       ← Zustand auth store
│       ├── api/         ← Typed Axios client
│       └── types/       ← TypeScript type definitions
├── backend/
│   └── app/
│       ├── core/        ← Config, security, logging, exceptions
│       ├── db/          ← SQLAlchemy session, base, migrations
│       ├── models/      ← User, Org, Job, Candidate, Resume, Interview, Audit
│       ├── schemas/     ← Pydantic v2 request/response schemas
│       ├── api/routes/  ← FastAPI routes (auth, jobs, resumes)
│       ├── ai/          ← LLM providers, structured outputs, prompts
│       ├── graphs/      ← LangGraph workflows (resume_ingestion, screening, interview)
│       ├── rag/         ← Vector store, chunking, retrieval (Phase 5)
│       ├── services/    ← Business logic services (Phase 3+)
│       └── workers/     ← Celery tasks (Phase 11)
├── docs/
│   └── migration-plan.md
├── docker-compose.yml
├── .env.example
└── .gitignore
```

## AI Architecture

### LangGraph Workflows
1. **Resume Ingestion** — validate → extract → clean → detect sections → LLM extract → validate → chunk → embed → store
2. **Candidate Screening** (Phase 8) — Evidence-based, weighted scoring across 7 categories
3. **Adaptive Interview** (Phase 9) — Stateful Q&A with real-time difficulty adaptation + Whisper voice

### Scoring System
| Category | Weight |
|---|---|
| Required Skills | 30% |
| Experience | 20% |
| Projects | 20% |
| Preferred Skills | 10% |
| Semantic Match | 10% |
| Education | 5% |
| Domain Knowledge | 5% |

All scores are backed by **cited evidence** from the resume — not hallucinated by the LLM.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Login → JWT |
| POST | `/api/v1/auth/refresh` | Refresh token |
| GET | `/api/v1/auth/me` | Current user |
| POST | `/api/v1/jobs` | Create job |
| GET | `/api/v1/jobs` | List jobs |
| PATCH | `/api/v1/jobs/{id}` | Update job |
| POST | `/api/v1/resumes` | Upload resume |
| GET | `/api/v1/resumes/{id}/processing-status` | Check parsing |

Swagger UI (dev only): `http://localhost:8000/api/docs`

## Running Tests

```bash
cd backend
pytest tests/ -v
```

Security tests in `tests/rag/test_tenant_isolation.py` verify:
1. Every chunk carries `organization_id` — cross-tenant retrieval impossible
2. `eval()` is not present anywhere in the AI pipeline

## Phase Roadmap

| Phase | Status |
|---|---|
| 0 — Security Fixes | ✅ |
| 1 — FastAPI Backend | ✅ |
| 2 — React Frontend | ✅ |
| 3 — Resume Parser Service | 🔜 |
| 4 — Structured Resume Intelligence | 🔜 |
| 5 — RAG (pgvector) | 🔜 |
| 6 — JD Intelligence | 🔜 |
| 7 — Resume Ingestion Graph | 🔜 |
| 8 — Candidate Screening | 🔜 |
| 9 — Adaptive Interview + Whisper | 🔜 |
| 10 — Full Recruiter UI | 🔜 |
| 11 — Bulk Processing | 🔜 |
| 12 — Production Hardening | 🔜 |

## Legacy App

The original Streamlit app is preserved in `legacy/` and still works:
```bash
cd legacy
pip install -r requirements.txt
streamlit run app.py
```