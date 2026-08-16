"""
Checkpoint 0 verification: test Groq API + embedding model.
Usage: python scripts/verify_setup.py
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


async def verify_groq():
    from app.utils.llm_client import chat_completion
    from app.config import get_settings
    settings = get_settings()

    print(f"Testing Groq API (model: {settings.groq_model_generation})...")
    try:
        response = await chat_completion(
            messages=[{"role": "user", "content": "Reply with exactly: VIVA_OK"}],
            model=settings.groq_model_generation,
            temperature=0.0,
            max_tokens=20,
        )
        print(f"✓ Groq generation model response: {response.strip()}")
    except Exception as e:
        print(f"✗ Groq generation model failed: {e}")
        return False

    print(f"Testing Groq scoring model ({settings.groq_model_scoring})...")
    try:
        response = await chat_completion(
            messages=[{"role": "user", "content": "Reply with exactly: SCORE_OK"}],
            model=settings.groq_model_scoring,
            temperature=0.0,
            max_tokens=20,
        )
        print(f"✓ Groq scoring model response: {response.strip()}")
    except Exception as e:
        print(f"✗ Groq scoring model failed: {e}")
        return False

    return True


def verify_embeddings():
    print("Loading embedding model (first run downloads ~130MB)...")
    try:
        from app.utils.embeddings import embed_texts
        test_texts = ["machine learning gradient descent"]
        vectors = embed_texts(test_texts, is_query=True)
        assert len(vectors) == 1
        assert len(vectors[0]) == 384
        norm = sum(x**2 for x in vectors[0]) ** 0.5
        print(f"✓ Embedding model loaded — 384-dim vector, L2 norm: {norm:.4f} (should be ~1.0)")
        return True
    except Exception as e:
        print(f"✗ Embedding model failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Viva — Checkpoint 0 Setup Verification")
    print("=" * 50)

    results = []

    # Test embeddings (sync)
    results.append(verify_embeddings())

    # Test Groq (async)
    groq_ok = asyncio.run(verify_groq())
    results.append(groq_ok)

    print("\n" + "=" * 50)
    if all(results):
        print("✓ All Checkpoint 0 checks passed. Proceed to Phase 1 (ingestion).")
    else:
        print("✗ Some checks failed. Fix before proceeding.")
    print("=" * 50)
