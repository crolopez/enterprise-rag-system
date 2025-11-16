FROM python:3.11-slim

WORKDIR /app

# Install dependencies and curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir requests flask

# Copy RAG API service (provides Ollama-compatible API with automatic context injection)
COPY services/rag-wrapper/rag_api.py .

# Make it executable
RUN chmod +x rag_api.py

ENTRYPOINT ["python", "rag_api.py"]
