FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for pdfplumber (poppler) and onnxruntime (gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpoppler-cpp-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the ONNX embedding model during build (avoids cold-start download in prod)
# fastembed caches the model at FASTEMBED_CACHE_PATH; set to a known location for the image.
ENV FASTEMBED_CACHE_PATH=/app/.fastembed_cache
RUN python -c "from fastembed import TextEmbedding; list(TextEmbedding(model_name='BAAI/bge-small-en-v1.5').embed(['warmup']))"

COPY . .

EXPOSE 8000

CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
