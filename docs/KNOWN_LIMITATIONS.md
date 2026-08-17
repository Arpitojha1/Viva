# Known Limitations

In the interest of transparency and engineering rigor, this document outlines the known gaps, limitations, and unfinished edges of the current Viva implementation. These constraints were largely driven by the tight 48-hour development window of the initial assignment.

## 1. No Authentication System

**Current State:** The database schema includes a `users` table, and the data model is built to support a multi-tenant environment where interviews belong to specific users. However, there is no active login flow, session management, or authentication gateway on the frontend or backend.
**Reasoning:** Implementing robust authentication (e.g., via NextAuth or Supabase Auth) requires significant boilerplate, email verification setup, and edge-case handling. Given the time constraints, we opted to mock the user context and focus development bandwidth entirely on the core AI assessment loop (RAG, generation, adaptive scoring), which is the primary evaluation criteria.
**Future Fix:** Integrate Supabase Auth or Clerk to handle identity, and update the FastAPI backend to require and validate JWTs on all endpoints.

## 2. Single Role Scope (AI/ML Engineer)

**Current State:** The platform is heavily biased toward evaluating AI and Machine Learning Engineers. The system prompt, the baseline difficulty calibrations, and crucially, the ingested offline reference materials (textbooks) are strictly ML-focused.
**Reasoning:** Providing a deep, accurate assessment requires highly specific context. Attempting to support generic Software Engineering, DevOps, or Data Engineering simultaneously would dilute the quality of the RAG retrieval given the limited initial dataset.
**Future Fix:** Extending the system requires creating a role-selection UI, ingesting domain-specific reference materials for other roles, and updating the chunking metadata to tag vectors by domain so the retrieval system only searches within the relevant discipline.

## 3. Groq Rate Limits and Latency Spikes

**Current State:** While Groq is exceptionally fast, the free-tier API endpoints can occasionally experience strict rate-limiting (e.g., requests per minute limits) or transient latency spikes during high global load. 
**Impact:** If the rate limit is hit during an interview, the backend will return an HTTP 429 error, which may cause the frontend to stall or require a manual refresh of the session. The system relies heavily on sequential LLM calls (score the answer -> generate the next question), compounding this risk.
**Future Fix:** Implement robust exponential backoff and retry logic in the backend LLM service. For a production deployment, transitioning to a paid Groq tier or implementing a fallback router (e.g., falling back to OpenAI or Anthropic if Groq 429s) is necessary.

## 4. Limited File Support for Resumes

**Current State:** The resume upload functionality currently assumes well-formatted, standard PDF files. 
**Impact:** Resumes with highly complex multi-column layouts, heavy graphical elements, or non-standard encodings may result in poor text extraction. This garbage-in scenario degrades the quality of the initial resume embedding, leading to less relevant initial interview questions.
**Future Fix:** Integrate a more resilient document parser (e.g., LlamaParse or specialized OCR tools) instead of basic PDF text extraction, and add support for `.docx` and plain text uploads.
