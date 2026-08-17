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
   pip install -r requirements.txt
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
   uvicorn main:app --reload
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
   Copy the example file to `.env.local`:
   ```bash
   cp .env.local.example .env.local
   ```
   Ensure the API base URL is pointed to your local backend (usually `http://localhost:8000`).

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

Viva is designed to be deployed using Vercel for the frontend and Railway for the backend.

### Backend (Railway)
- Deploy the `backend/` directory as a service.
- **Environment Variables:** Set `DATABASE_URL` (production Supabase instance) and `GROQ_API_KEY`.
- Also set `ALLOWED_ORIGINS` to the URL of your Vercel frontend deployment to configure CORS properly.
- Railway's build process will automatically detect `requirements.txt` and install dependencies. Set the start command to `uvicorn main:app --host 0.0.0.0 --port $PORT`.

### Frontend (Vercel)
- Deploy the `frontend/` directory to Vercel.
- **Environment Variables:** Set `NEXT_PUBLIC_API_BASE_URL` to your production Railway backend URL.
