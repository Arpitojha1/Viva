# System Architecture

Viva is designed to be highly modular, separating the offline knowledge ingestion process from the real-time adaptive interview pipeline. The architecture leverages modern web frameworks and vector search capabilities to deliver a responsive experience.

## System Diagram

```ascii
                      +-------------------+
                      |                   |
                      |   Administrator   |
                      |   (Ingestion)     |
                      +---------+---------+
                                |
                                v
+------------------+   +-------------------+
| Reference Books  |-->| Ingestion Script  |
| (PDFs)           |   | (Python)          |
+------------------+   +-------------------+
                                | 1. Parse & Chunk
                                | 2. Embed (Local HF)
                                | 3. Semantic Dedup
                                v
                      +-------------------+
                      |   PostgreSQL DB   |
                      |   (Supabase)      |
                      |   w/ pgvector     |
                      +-------------------+
                                ^
                                |
+------------------+   +--------+----------+   +-------------------+
|                  |   |                   |   |                   |
|   React + Vite   |<->|   FastAPI         |<->|   Groq API        |
|   Frontend       |   |   Backend         |   |   (Llama 3)       |
|                  |   |                   |   |                   |
+------------------+   +-------------------+   +-------------------+
     ^                           ^
     |                           | 4. Semantic Search (pgvector)
     v                           | 5. Generate Question
+------------------+             v
|                  |   +-------------------+
|   Candidate      |   |   Local Embedding |
|   (User)         |   |   Model (HF)      |
+------------------+   +-------------------+
```

## Data Flow

The platform's data flow operates in two distinct phases:

### Phase 1: Offline Ingestion
1. **PDF Processing:** Reference textbooks are parsed and divided into logical chunks.
2. **Embedding:** Each chunk is converted into a vector embedding using a local HuggingFace `sentence-transformers` model.
3. **Semantic Dedup:** Before insertion, the system queries existing chunks in the database. If a highly similar chunk already exists (based on a similarity threshold), the new chunk is skipped to prevent duplicate context from degrading retrieval quality.
4. **Storage:** Chunks and their embeddings are stored in PostgreSQL using the `pgvector` extension, maintaining traceability back to the source book, chapter, and page.

### Phase 2: Runtime Execution
1. **Initialization:** A candidate uploads their resume, creating an interview session.
2. **Retrieval:** The backend extracts key concepts from the resume and queries the database via vector search to fetch the most relevant textbook chunks.
3. **Generation:** The retrieved chunks and the resume data are sent to the Groq LLM to generate an initial, highly contextual interview question. Traceability data (book title, chapter, page) is passed through to the frontend.
4. **Adaptive Interview:** The candidate submits an answer. The backend uses the LLM to score the response against the initial context. Based on the score, the `difficulty_target` is adjusted (up, down, or stays the same). This adjusted difficulty biases the prompt for the next question's generation.
5. **Summary:** Once the question limit is reached, a final comprehensive summary of the candidate's performance is generated.

## Database Schema

The database relies on a relational structure combined with vector storage.

- **`interviews`**: Manages the core interview sessions, tracking candidate details, resume text, status, and aggregate metrics.
- **`questions`**: Stores the individual questions generated during an interview, including their specific difficulty level and the text of the prompt.
- **`answers`**: Records the candidate's responses to questions, along with the LLM-evaluated score and detailed feedback.
- **`chunks`**: The core knowledge base. Stores the textual content of reference materials along with their vector embeddings (`embedding` column using `vector` type) to enable semantic search.
- **`chunk_sources`**: Maintains the metadata (book title, chapter, page number) for chunks. Separating this from `chunks` allows multiple similar passages to map to shared content or standardizes metadata tracking independently of the raw text.
- **`ingested_books`**: A tracking table to ensure books aren't ingested multiple times unnecessarily. It logs which files have been successfully processed by the offline ingestion script.

## API Surface

All routes are served over ordinary HTTP (no Socket.IO or WebSockets). The health endpoint is at `/health`; all application routes are prefixed with `/api`.

- `POST /api/resume/upload` — Upload a PDF resume (max 5 MB, in-memory only); returns extracted skills and a `resumeId`.
- `POST /api/session` — Create an interview session for a previously uploaded resume; generates initial questions synchronously before returning.
- `GET  /api/session/{session_token}` — Get session status and progress (question count, answered count).
- `GET  /api/interview/{session_token}/next-question` — Retrieve the next unanswered question with source traceability metadata.
- `POST /api/interview/{session_token}/answer` — Submit a candidate answer; scores it via Groq, adjusts difficulty, optionally generates an adaptive follow-up question (synchronously, within the same HTTP request).
- `GET  /api/session/{session_token}/summary` — Generate a structured performance summary from stored Q&A records.
- `GET  /health` — Health check. Returns `{"status": "ok", "app": "Viva"}`.
- `GET  /docs` — OpenAPI interactive documentation (Swagger UI).

> **Note:** All question generation (initial and adaptive follow-up) is **synchronous within the HTTP request**. There is no durable background worker, job queue, Celery, Redis, or WebSocket implementation in this codebase.

## Offline Ingestion

The textbook ingestion pipeline (`backend/scripts/`, `backend/ingestion/`) runs **outside** the deployed request API. It is a one-time offline operation that populates the `chunks` and `chunk_sources` tables in Supabase. It must not be run as part of Vercel build commands or startup hooks.

## Deployment

- **Frontend:** React + Vite deployed to Vercel (existing project).
- **Backend:** FastAPI deployed to Vercel as a separate project (Root Directory: `backend`). Railway remains available as a rollback deployment until production Vercel verification is complete. Do not retire Railway until the owner explicitly authorizes it.
- **Database:** Supabase PostgreSQL + pgvector (unchanged).

## RAG Retrieval Mechanism

The Retrieval-Augmented Generation (RAG) system forms the foundation of context-aware questioning. When a resume is uploaded, key terms are extracted and converted into vector embeddings locally. These embeddings are used to perform a cosine similarity search against the `chunks` table using `pgvector`. 
The highest-scoring chunks are retrieved and injected into the Groq LLM prompt. Crucially, the source metadata (`chunk_sources`) for each retrieved chunk is preserved and returned alongside the generated question. This ensures complete traceability, allowing the UI to display exactly which book, chapter, and page the question is based on.

## Adaptive Difficulty Mechanism

The core differentiator of Viva is its ability to adapt in real-time. 

1. **Scoring:** When an answer is submitted, the LLM evaluates it against the original question and retrieved context, assigning a score (typically 0-100).
2. **Difficulty Adjustment:** If the score is high (e.g., >80), the system increases the `difficulty_target`. If the score is low (e.g., <50), it decreases the target.
3. **Biased Generation:** The updated `difficulty_target` (categorized internally into tiers like Fundamentals, Intermediate, Advanced) is injected into the system prompt for the next question.
4. **Execution:** The LLM uses this target to dynamically alter its phrasing, the depth of technical knowledge required, and the complexity of the scenario presented in the subsequent question, ensuring the interview continuously probes the boundaries of the candidate's actual capability.
