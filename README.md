# Viva - AI-Powered Technical Interview Platform

Viva is an adaptive, AI-powered technical interview platform specifically designed to evaluate AI/ML engineering candidates. By ingesting a candidate's resume and leveraging authoritative reference materials (textbooks), the system dynamically generates context-aware, highly relevant interview questions. During the interview, Viva evaluates candidate responses in real-time and adaptively scales the difficulty of follow-up questions to provide a rigorous, personalized assessment experience.

### Links

- **Live Demo (Frontend):** [Insert Live URL Here]
- **Backend API:** [Insert Backend URL Here]
- **Demo Video:** [Insert Video Link Here]

### Quickstart

To run Viva locally, follow these steps. For detailed instructions, see the [Setup Guide](docs/SETUP.md).

```bash
# 1. Clone the repository
git clone https://github.com/Arpitojha1/Viva.git
cd Viva

# 2. Start the Backend
cd backend
python -m venv venv
source venv/Scripts/activate  # Or venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Supabase and Groq keys, then run:
uvicorn main:app --reload

# 3. Start the Frontend (in a new terminal)
cd ../frontend
npm install
cp .env.local.example .env.local
# Edit .env.local, then run:
npm run dev
```

### Tech Stack

- **Backend:** FastAPI (Python) for high-performance, async API endpoints.
- **Database:** PostgreSQL with pgvector (via Supabase) for relational and vector storage.
- **LLM:** Groq (Llama 3 models) for ultra-fast, low-latency generation.
- **Embeddings:** HuggingFace `sentence-transformers` running locally.
- **Frontend:** Next.js (React, TypeScript, Tailwind CSS) for a responsive UI.
- **Deployment:** Vercel (Frontend) and Railway (Backend).

### Documentation

Dive deeper into the project by reading the documentation:

- [Local Setup & Deployment Guide](docs/SETUP.md)
- [System Architecture](docs/ARCHITECTURE.md)
- [Design Decisions & Trade-offs](docs/DESIGN_DECISIONS.md)
- [Known Limitations](docs/KNOWN_LIMITATIONS.md)
