# Viva

**AI-powered role-based candidate screening system** — dynamically generates ML interview questions grounded in a textbook knowledge base via RAG, with adaptive difficulty based on answer quality.

*Viva* is Latin for "viva voce" — an oral examination conducted by live questioning.

---

## Architecture

```
INGESTION (run once):
  PDFs (Mitchell / Bishop / Burkov)
    → pdfplumber text extraction (page-by-page)
    → recursive chunking (~600 tokens, ~80 overlap, with chapter/section metadata)
    → sentence-transformers BAAI/bge-small-en-v1.5 embeddings (local, 384-dim)
    → pgvector upsert with content-hash + semantic dedup
    → ingested_books record (idempotent: skips unchanged PDFs on re-run)

RUNTIME (per interview):
  1. Resume PDF upload → pdfplumber text → Groq 70b structured JSON extraction
  2. Role fixed to AI/ML Engineer → 3 retrieval queries generated from resume profile
  3. pgvector cosine similarity search with soft chapter_position difficulty bias
  4. Groq 70b generates 5 initial questions grounded in retrieved chunks
  5. Interview loop:
       candidate answers → Groq 8b scores answer (weak/ok/strong)
       → difficulty_target adjusted (±0.15)
       → if strong/weak: generate one adaptive follow-up question
       → repeat until all questions answered (max 8 total)
  6. Session summary: Groq 70b generates structured assessment from stored Q&A records
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + asyncpg (Python 3.11+) |
| Database | PostgreSQL + pgvector (Supabase) |
| LLM | Groq: `llama-3.3-70b-versatile` (generation), `llama-3.1-8b-instant` (scoring) |
| Embeddings | `sentence-transformers` BAAI/bge-small-en-v1.5 (local, 384-dim) |
| PDF extraction | pdfplumber |
| Frontend | React + Vite + TypeScript + Tailwind |
| Deploy | Railway (backend) + Vercel (frontend) |

---

## Setup

### Prerequisites
- Python 3.11+
- A Supabase project with pgvector enabled
- Groq API key (free tier at console.groq.com)
- The three textbook PDFs (see below)

### 1. Backend Setup

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Copy and fill in environment variables:
```bash
cp .env.example .env
# Edit .env with your Supabase DATABASE_URL and GROQ_API_KEY
```

### 2. Database Migration

Run the SQL in `backend/migrations/001_initial_schema.sql` in your Supabase SQL Editor.

> **Note:** Use the direct port 5432 connection string for `DATABASE_URL`, not the PgBouncer pooler port 6543. asyncpg requires prepared statement support which PgBouncer transaction mode disables.

### 3. Textbook PDFs

Place the three PDFs at these exact paths (gitignored — do not commit):
```
backend/data/books/mitchell_machine_learning.pdf
backend/data/books/bishop_prml.pdf
backend/data/books/burkov_100page_ml.pdf
```

### 4. Run Ingestion

```bash
cd backend
python -m ingestion.ingest
```

The pipeline is **idempotent** — re-running it on unchanged PDFs is a no-op (file hash check). 
After ingestion, run Checkpoint 1 spot-check queries (see below).

### 5. Start Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 6. Frontend Setup

```bash
cd frontend
npm install
# Create .env.local with:
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

---

## Checkpoint 1 — Retrieval Quality Spot-Check

After ingestion, verify retrieval quality before proceeding to Phase 3:

```python
# Quick retrieval test (run from backend/ with venv activated)
import asyncio, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()

from app.database import AsyncSessionLocal
from app.services.retrieval import retrieve_chunks
from app.schemas import ExtractedResumeData

async def test_retrieval():
    test_queries = [
        "bias variance tradeoff model complexity",
        "gradient descent optimization convergence",
        "kernel methods support vector machine",
        "regularization overfitting L2 penalty",
        "expectation maximization algorithm",
    ]
    async with AsyncSessionLocal() as db:
        for q in test_queries:
            results = await retrieve_chunks([q], db, top_k=5)
            print(f"\nQuery: {q}")
            for r in results[:3]:
                print(f"  [{r.book} | p.{r.page} | pos={r.chapter_position:.2f}] sim={r.similarity:.3f}")
                print(f"  {r.content[:150]}...")

asyncio.run(test_retrieval())
```

**Pass criteria:**
- Top 3 results are thematically relevant to each query
- `book` fields show real book slugs (`mitchell`, `bishop`, `burkov`)
- `chapter_position` values are spread across 0.0–1.0 range
- At least some chunks from each book appear across the test set

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/resume/upload` | Upload PDF resume → returns `{ success, extractedSkills, resumeId }` |
| `POST` | `/api/session` | Create session → runs retrieval + generates 5 questions |
| `GET`  | `/api/session/{id}` | Session status and progress |
| `GET`  | `/api/interview/{id}/next-question` | Next unanswered question with source citation |
| `POST` | `/api/interview/{id}/answer` | Submit answer → score + adaptive difficulty update |
| `GET`  | `/api/session/{id}/summary` | Structured session summary |
| `GET`  | `/health` | Health check |

---

## Key Design Decisions

### RAG Pipeline Design
- **Why pdfplumber over pypdf:** Academic textbooks have multi-column layouts, figures, and complex spacing. pdfplumber uses coordinate-based spatial extraction which handles these layouts significantly better than pypdf's linear stream parsing.
- **Why local embeddings:** Groq has no embedding endpoint. Local `bge-small-en-v1.5` embeddings run once at ingestion time with no per-call cost or rate limits. The 384-dim model is fast to embed on CPU and retrieval quality is strong for domain-specific text.
- **Why chapter_position as difficulty proxy:** Textbooks are generally structured front-to-back from foundational to advanced content. Using the normalized page position as a continuous difficulty proxy avoids expensive LLM-based difficulty labeling at ingestion time, while still producing measurable retrieval bias toward fundamentals vs. advanced sections.

### Adaptive Difficulty
- Hybrid approach: 5 pre-generated questions provide structure; adaptive follow-ups inject on `strong`/`weak` scores only (not `ok`). This respects Groq free-tier rate limits (~30 RPM for 70b) while ensuring the differentiator is real and observable.
- `difficulty_target` is persisted per session so adaptive state survives page refreshes.

### Deduplication (Addendum 2)
- **Layer 1 (exact):** SHA-256 content hash prevents re-storing identical text chunks on reruns.
- **Layer 2 (semantic):** Cosine similarity ≥ 0.93 threshold detects near-duplicate passages across books (e.g., both Mitchell and Bishop explain maximum likelihood). The duplicate chunk gains an additional `chunk_sources` row pointing to its second occurrence, improving citation honesty.
- **Why this improves retrieval:** Without dedup, a concept covered in multiple books fills top-k results with near-identical text, crowding out genuinely diverse chunks. With dedup, each slot in top-k represents a distinct concept.

### Known Gaps (Future Work)
- **No authentication:** `user_id` is nullable throughout. The `users` table exists for future auth integration. Row-Level Security (RLS) is not enabled — all session data is accessible via the service role key. Add Supabase Auth + RLS before any multi-tenant deployment.
- **No streaming:** Groq responses are awaited synchronously. For production UX, stream question generation responses to reduce perceived latency.
- **Role fixed to AI/ML Engineer:** The role selector in the UI shows other options as "Coming Soon." Extending to new roles requires adding a role-specific knowledge base.

---

## Repository Structure

```
viva/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory + CORS + lifespan
│   │   ├── config.py            # Pydantic Settings (all env vars)
│   │   ├── database.py          # Async SQLAlchemy engine + get_db()
│   │   ├── models.py            # ORM models (7 tables)
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── routers/             # HTTP layer (thin: validate → service → respond)
│   │   ├── services/            # Business logic (resume_parser, retrieval, etc.)
│   │   └── utils/               # Shared infra (llm_client, embeddings)
│   ├── ingestion/               # Offline pipeline (PDF → chunks → pgvector)
│   ├── migrations/              # SQL migration files
│   ├── tests/                   # Unit tests
│   ├── data/books/              # Textbook PDFs (gitignored)
│   └── Dockerfile               # Railway deployment
├── frontend/                    # Next.js + Tailwind + GSAP (separate build)
└── README.md
```
