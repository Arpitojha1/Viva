"""
Viva — FastAPI Application Factory
Sets up CORS, mounts all routers, and registers the startup lifespan handler
that pre-loads the embedding model so the first request isn't slow.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: pre-load the embedding model (avoids cold-start latency on first request)."""
    logger.info("Viva backend starting up — pre-loading embedding model...")
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    loop = asyncio.get_event_loop()
    # Load model in a thread pool so we don't block the event loop
    with ThreadPoolExecutor(max_workers=1) as pool:
        await loop.run_in_executor(pool, _preload_embeddings)
    logger.info("Embedding model ready. Viva is live.")
    yield
    logger.info("Viva backend shutting down.")


def _preload_embeddings() -> None:
    """Trigger lazy model load during startup."""
    from app.utils.embeddings import _get_model
    _get_model()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Viva",
        description="AI-powered role-based candidate screening system (RAG pipeline).",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # -----------------------------------------------------------------------
    # CORS — allow all origins from ALLOWED_ORIGINS env var.
    # In production, set ALLOWED_ORIGINS=https://your-vercel-url.vercel.app
    # -----------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # Routers
    # -----------------------------------------------------------------------
    from app.routers import resume, session, interview, summary

    app.include_router(resume.router, prefix="/api")
    app.include_router(session.router, prefix="/api")
    app.include_router(interview.router, prefix="/api")
    app.include_router(summary.router, prefix="/api")

    @app.get("/health", tags=["health"])
    async def health_check():
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
