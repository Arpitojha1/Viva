# Local Setup & Deployment

This guide provides full instructions to clone the repository, set it up locally, and verify it's working. It also covers deployment configurations.

## Prerequisites

Before starting, ensure you have the following installed and configured:

- **Python 3.10+** (for the backend)
- **Node.js 18+** (for the frontend)
- **Supabase Account:** Required for the PostgreSQL database with the pgvector extension.
- **Groq Account:** Required to get an API key for the LLM inference.

## Backend Setup

The backend handles document ingestion, RAG generation, and exposes the API.

1. **Navigate to the backend directory and set up a virtual environment:**
   ```bash
   cd backend
   python -m venv venv
   
   # On macOS/Linux:
   source venv/bin/activate
   
   # On Windows:
   source venv/Scripts/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Configure Environment Variables:**
   Copy the example file to `.env`:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and fill in the following:
   - `DATABASE_URL`: Get this from your Supabase project settings (Settings > Database > Connection string).
   - `GROQ_API_KEY`: Get this from the Groq console.

4. **Run Database Migrations:**
   Ensure your Supabase project is empty (or has no conflicting tables) and run Alembic:
   ```bash
   alembic upgrade head
   ```

5. **Run the Offline Ingestion Script:**
   To populate the database with the reference materials, place the expected book PDFs in the `data/books/` directory (these must match the hardcoded paths in the script, such as `data/books/book1.pdf`).
   Run the ingestion pipeline:
   ```bash
   python -m scripts.ingest
   ```

6. **Start the Dev Server:**
   ```bash
   uvicorn app.main:app --reload
   ```
   The API will be available at `http://localhost:8000`.

## Frontend Setup

The frontend provides the interactive interview experience.

1. **Navigate to the frontend directory:**
   Open a new terminal (leave the backend running) and navigate to the frontend folder.
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Configure Environment Variables:**
   Copy the example file to `.env`:
   ```bash
   cp .env.example .env
   ```
   Set `VITE_API_BASE_URL` to your local backend URL:
   ```
   VITE_API_BASE_URL=http://localhost:8000/api
   ```

4. **Start the Dev Server:**
   ```bash
   npm run dev
   ```
   The app will be accessible at `http://localhost:3000`.

## Verification

To verify the setup is working correctly:
1. Open `http://localhost:3000` in your browser.
2. Upload a sample resume (PDF).
3. Wait for the generation phase to complete. You should see an initial question generated from the resume content and the reference materials.
4. Provide an answer and submit. The system should evaluate your response and generate a follow-up question adaptively.

## Deployment Notes

Viva uses Vercel for both the frontend and backend, with Railway remaining as a rollback option.

### Backend (Vercel — new)

Deploy the `backend/` directory as a **separate** Vercel project:

- **Repository:** `Arpitojha1/Viva`
- **Root Directory:** `backend`
- **Framework:** Python (automatic detection)
- **Build Command:** leave empty/default
- **Install Command:** leave empty (Vercel installs `requirements.txt` automatically)

**Required environment variables** (set in Vercel Dashboard → Project → Settings → Environment Variables):

| Variable | Example / Note |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:<pw>@db.<ref>.supabase.co:5432/postgres` |
| `GROQ_API_KEY` | `gsk_...` (secret) |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` |
| `GROQ_MODEL_GENERATION` | `llama-3.3-70b-versatile` |
| `GROQ_MODEL_SCORING` | `llama-3.1-8b-instant` |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` |
| `EMBEDDING_DIM` | `384` |
| `ENVIRONMENT` | `production` |
| `ALLOWED_ORIGINS` | `https://your-frontend.vercel.app` (no trailing slash) |
| `PRELOAD_EMBEDDING_MODEL` | `false` |
| `MAX_RESUME_SIZE_MB` | `5` |
| `RATE_LIMIT_RESUME` | `5/minute` |
| `RATE_LIMIT_SESSION` | `10/minute` |
| `INITIAL_QUESTION_COUNT` | `5` |
| `MAX_ADAPTIVE_FOLLOWUPS` | `3` |
| `QUESTION_BANK_MAX_PER_BATCH` | `5` |
| `VERCEL_SUPPORT_LARGE_FUNCTIONS` | `1` (required — PyTorch bundle exceeds standard limit) |

**Important:** Do NOT add `PORT` or Supabase anon/service-role keys.

### Backend (Railway — rollback)

The existing Railway service must remain **untouched and running** until the Vercel backend has been fully verified end-to-end in production. Do not pause, delete, or redeploy Railway until the project owner explicitly authorizes it.

To restore the frontend to the Railway backend, update `VITE_API_BASE_URL` in the frontend Vercel project to point to the Railway URL, then redeploy.

### Frontend (Vercel)

Deploy the `frontend/` directory to Vercel (existing project).

**Environment variable** (set in Vercel Dashboard → Project → Settings → Environment Variables):

```
VITE_API_BASE_URL=https://<your-viva-api>.vercel.app/api
```

The `/api` suffix is mandatory — `frontend/src/lib/api.ts` appends paths such as `/resume/upload` and `/session` to this base URL.

Vite embeds environment variables at **build time**. After changing `VITE_API_BASE_URL`, trigger a new frontend deployment for the change to take effect.

> **Do not update `VITE_API_BASE_URL` to point at the Vercel backend until the Vercel backend has been directly verified** (health check + end-to-end API test).
