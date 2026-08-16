"""
Viva — Local Sentence-Transformers Embeddings
Lazy-loads BAAI/bge-small-en-v1.5 once on first use.
Applies the recommended query prefix for retrieval tasks.
Runs synchronously (CPU-bound); call from a thread pool in async context.
"""
import logging
from functools import lru_cache
from typing import List

import numpy as np

logger = logging.getLogger(__name__)

# Query prefix recommended by BAAI for bge-small-en-v1.5 retrieval tasks.
# Apply to QUERY strings only — NOT to document/chunk text at ingestion time.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def _get_model():
    """Load and cache the SentenceTransformer model (singleton)."""
    from sentence_transformers import SentenceTransformer
    from app.config import get_settings
    model_name = get_settings().embedding_model
    logger.info("Loading embedding model: %s", model_name)
    model = SentenceTransformer(model_name)
    logger.info("Embedding model loaded successfully")
    return model


def embed_texts(texts: List[str], is_query: bool = False) -> List[List[float]]:
    """
    Embed a list of texts using BAAI/bge-small-en-v1.5.

    Args:
        texts: List of strings to embed.
        is_query: If True, prepends the QUERY_PREFIX to each text.
                  Set True for retrieval queries; False for document chunks at ingestion.

    Returns:
        List of 384-dimensional float vectors, L2-normalized (unit sphere).
        Cosine similarity between any two is just their dot product.
    """
    if not texts:
        return []

    model = _get_model()

    if is_query:
        texts = [QUERY_PREFIX + t for t in texts]

    embeddings: np.ndarray = model.encode(
        texts,
        normalize_embeddings=True,  # L2-normalize; cosine sim = dot product
        show_progress_bar=False,
        batch_size=64,
    )
    return embeddings.tolist()


def embed_query(query: str) -> List[float]:
    """Convenience function to embed a single retrieval query."""
    return embed_texts([query], is_query=True)[0]


def embed_chunk(text: str) -> List[float]:
    """Convenience function to embed a single document chunk (no query prefix)."""
    return embed_texts([text], is_query=False)[0]
