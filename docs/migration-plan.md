# TalentAI — Migration Plan

## Status: Phase 0 & 1 COMPLETE → Phase 2 (React) COMPLETE

---

## Security Fixes Applied (Phase 0)

| Fix | Status |
|---|---|
| `.streamlit/credentials.toml` added to `.gitignore` | ✅ |
| `eval()` on LLM output removed → `json.loads()` + Pydantic | ✅ |
| organization_id never trusted from JWT claims | ✅ (architecture rule) |
| Cross-tenant access attempts → CRITICAL log + 403 | ✅ |

## Phase 1 — FastAPI Backend (COMPLETE)

Files created:
- `backend/app/main.py` — FastAPI app, exception handlers, routes
- `backend/app/core/config.py` — Pydantic-settings config
- `backend/app/core/security.py` — bcrypt + JWT
- `backend/app/core/logging.py` — structlog
- `backend/app/core/exceptions.py` — domain exception hierarchy
- `backend/app/db/session.py` — Async SQLAlchemy session
- `backend/app/db/base.py` — DeclarativeBase + mixins
- `backend/app/models/` — All 5 model files (User, Org, Job, Candidate, Application/Interview, Audit)
- `backend/app/schemas/__init__.py` — All Pydantic schemas
- `backend/app/api/dependencies/auth.py` — JWT dependency
- `backend/app/api/routes/auth.py` — Register/login/refresh/me
- `backend/app/api/routes/jobs.py` — Job CRUD
- `backend/app/api/routes/resumes.py` — Resume upload
- `backend/app/ai/llms/` — LLM abstraction (base, Ollama, factory)
- `backend/app/ai/structured_outputs/` — Pydantic LLM output schemas
- `backend/app/ai/prompts/resume_extraction.py` — Versioned prompts
- `backend/app/graphs/resume_ingestion/` — LangGraph state + nodes + graph
- `backend/tests/` — Node tests + security/tenant isolation tests
- `backend/requirements.txt` — Full production deps
- `backend/pytest.ini` — pytest config
- `.env.example` — Environment variable template
- `docker-compose.yml` — Full stack docker compose

## Phase 2 — React Frontend (COMPLETE)

Files created:
- `frontend/src/index.css` — Glassmorphism design system
- `frontend/src/main.tsx` — React entry + TanStack Query
- `frontend/src/App.tsx` — Router with protected routes
- `frontend/src/api/client.ts` — Axios client with JWT
- `frontend/src/types/index.ts` — TypeScript types
- `frontend/src/store/auth.ts` — Zustand auth store
- `frontend/src/layouts/RecruiterLayout.tsx` — Sidebar layout
- `frontend/src/pages/LandingPage.tsx` — Premium landing page
- `frontend/src/pages/LoginPage.tsx` — Login with Zod
- `frontend/src/pages/RegisterPage.tsx` — Register with role toggle
- `frontend/src/pages/recruiter/Dashboard.tsx` — Recruiter dashboard
- `frontend/src/pages/recruiter/Jobs.tsx` — Job listings
- `frontend/package.json`, `vite.config.ts`, `tsconfig.json`, `tailwind.config.js`

## Remaining Phases

| Phase | Objective | Status |
|---|---|---|
| 3 | Resume Parser Service (PyMuPDF + DOCX) | Pending |
| 4 | Structured Resume Intelligence + DB persistence | Pending |
| 5 | RAG System (real embeddings, pgvector) | Pending |
| 6 | JD Intelligence (replace ROLE_REQUIREMENTS) | Pending |
| 7 | LangGraph Resume Ingestion (full) | Pending |
| 8 | Candidate Screening LangGraph | Pending |
| 9 | Adaptive Interview LangGraph + Whisper | Pending |
| 10 | Full Recruiter UI build-out | Pending |
| 11 | Bulk Processing (Celery) | Pending |
| 12 | Production Hardening | Pending |

## Getting Started

```bash
# 1. Start infrastructure
docker-compose up postgres redis -d

# 2. Backend
cd backend
cp ../.env.example .env   # Edit secrets!
pip install -r requirements.txt
uvicorn app.main:app --reload

# 3. Frontend
cd frontend
npm install
npm run dev

# 4. Verify
curl http://localhost:8000/health
```
