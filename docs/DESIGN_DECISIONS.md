# Design Decisions & Trade-offs

This document outlines the major architectural and technical decisions made during the development of Viva, detailing the alternatives considered and the reasoning behind each choice.

## LLM Provider: Groq vs. OpenAI / OpenRouter

**Decision:** We chose Groq (specifically Llama 3 models) as the primary LLM provider instead of OpenAI (GPT-4o) or an aggregator like OpenRouter.

**Alternatives:**
- OpenAI (GPT-4o/GPT-4o-mini): High quality, but slower inference times and higher latency, particularly noticeable in a real-time conversational interface.
- OpenRouter: Good for flexibility, but adds an extra network hop and potential latency overhead.

**Why:** The core requirement of an adaptive interview platform is speed. Candidates expect near-instantaneous follow-up questions. Groq's LPU infrastructure provides sub-second generation times even for complex, context-heavy RAG prompts. The trade-off is a slightly lower reasoning ceiling compared to frontier models like GPT-4, but for technical interview question generation backed by strong reference context, Llama 3 70B is more than capable, making the speed advantage the decisive factor.

## Embedding Strategy: Local vs. Hosted API

**Decision:** We run embeddings locally using HuggingFace `sentence-transformers` rather than calling a hosted API like OpenAI's `text-embedding-3-small`.

**Alternatives:**
- OpenAI / Cohere Embedding APIs: Extremely easy to implement, but incurs per-token costs for every ingestion run and every runtime query, plus network latency during the interview.

**Why:** By running embeddings locally, we eliminate network latency during the critical retrieval phase of the interview loop. It also makes offline ingestion completely free, allowing us to rapidly iterate on chunking strategies without worrying about API costs. The trade-off is higher memory usage on the backend server, but modern deployment environments can handle the modest requirements of models like `all-MiniLM-L6-v2` comfortably.

## Vector Storage: PostgreSQL + pgvector vs. Dedicated Vector DB

**Decision:** We use PostgreSQL with the `pgvector` extension (hosted on Supabase) for both relational and vector data.

**Alternatives:**
- Pinecone, Chroma, Qdrant: Purpose-built vector databases that offer extreme scale and specialized features.

**Why:** The application requires tight coupling between relational data (interviews, users, scores) and vector data (text chunks). Using a single PostgreSQL database drastically simplifies the architecture, eliminates data synchronization issues between two separate datastores, and reduces operational overhead. For the scale of this project (thousands of chunks, not billions), `pgvector` provides excellent performance via HNSW indexes while keeping the stack lean.

## Ingestion Pipeline: Semantic Deduplication

**Decision:** We implemented a semantic deduplication mechanism during the offline ingestion phase. Before a chunk is inserted, the system checks for highly similar existing chunks based on a similarity threshold.

**Alternatives:**
- Blindly insert all chunks: Simple to build, but pollutes the vector space with identical or highly similar passages (e.g., the same concept repeated across different chapters).
- Exact text matching: Too rigid; fails to catch conceptually identical paragraphs that have minor phrasing differences.

**Why:** A similarity threshold is a deliberate precision/recall trade-off. We chose a threshold that biases toward precision (preventing duplicates). If multiple identical chunks are retrieved during an interview, it starves the context window of diverse information, degrading the LLM's ability to ask well-rounded questions. The trade-off is that we might occasionally drop a conceptually similar chunk that had a slightly different technical nuance.

## Question Generation: All-Synchronous HTTP Requests

**Decision:** Both the initial question set and adaptive follow-up questions are generated **synchronously within the HTTP request** before the response is returned.

**Alternatives:**
- Async/background workers (Celery, FastAPI BackgroundTasks, Redis queue): Allows the API to return immediately while generation runs in the background, requiring client polling or WebSocket push.
- WebSocket connection: Enables streaming progress updates during multi-second generation.

**Why synchronous:** The initial question set must be ready before the interview can start, so the frontend awaits it. For follow-up questions, generating asynchronously would require a separate polling endpoint or WebSocket, adding complexity to both the frontend state machine and the backend infrastructure. Because Groq's LPU inference is very fast (sub-second for typical prompts), the synchronous approach keeps the architecture simple without causing unacceptable latency under normal conditions.

**Trade-offs:**
- Simplicity: No job queue, no polling, no WebSocket infrastructure.
- Timeout risk: On Vercel, session creation (which includes initial question generation) can take 5–15 seconds. The `maxDuration: 300` setting in `vercel.json` covers this. Groq rate-limit retries (via `tenacity`) could push individual requests toward the limit in high-traffic scenarios.
- No durable background worker: The codebase does not contain Celery, Redis, FastAPI `BackgroundTasks`, Socket.IO, or WebSocket implementations.

## Difficulty Tiers and Proxy Metrics

**Decision:** We structured the adaptive difficulty around three distinct tiers (`Fundamentals`, `Intermediate`, `Advanced`) and utilized `chapter_position` as a proxy for topic complexity.

**Alternatives:**
- Continuous floating-point difficulty (e.g., 1.0 to 10.0): Hard for the LLM to interpret consistently. Asking an LLM for a "7.4 difficulty question" yields unpredictable results.

**Why:** Categorical tiers provide much stronger semantic grounding for the LLM. It understands the distinct pedagogical difference between a "fundamental" concept and an "advanced" scenario. Furthermore, by using the chunk's `chapter_position` (early chapters vs. late chapters in a textbook) as a heuristic proxy, we help the retrieval system bias toward foundational text when the target difficulty drops, and complex text when it rises.
