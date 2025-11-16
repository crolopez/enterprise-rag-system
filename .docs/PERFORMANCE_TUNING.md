# Performance Tuning & Hardware Configuration

This guide explains how to adjust the Enterprise RAG system's configuration based on your hardware constraints.

## Hardware Profiles

The system is tested and optimized for the following configuration:

### Recommended Profile
- **Hardware**: NVIDIA GPU with 16GB+ VRAM
- **System RAM**: 16GB+
- **Storage**: 100GB+ SSD
- **Model Configuration**: Default (`llama3.1:8b-instruct-q5_K_M` with `sentence-transformers/all-mpnet-base-v2`)

### Minimum Profile (CPU-only)
- **Hardware**: CPU-only
- **System RAM**: 16GB minimum
- **Storage**: 20GB
- **Model Configuration**: See [Scaling Down](#scaling-down) section

## Scaling Down (Lower Resource Requirements)

If you have limited resources, you can reduce memory footprint by changing models.

### Option A: Smaller LLM Model

Edit `.env`:

```env
OLLAMA_MODEL=mistral:latest
```

Available models in [Ollama library](https://ollama.com/library) that may use less resources. Common alternatives:
- `mistral:latest` - 7B model
- Other models from the Ollama library

**Note**: We have tested `llama3.1:8b-instruct-q5_K_M`. Other models may have different memory requirements and performance characteristics. Test before deploying to production.

After changing:
```bash
docker-compose restart ollama
```

### Option B: Smaller Embedding Model

Edit `.env`:

```env
EMBEDDINGS_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

**Critical**: The embedding model's vector dimensions MUST match the Qdrant collection dimensions. Different models generate different vector sizes:

- `sentence-transformers/all-mpnet-base-v2` (default) → **768-dimensional** vectors
- `sentence-transformers/all-MiniLM-L6-v2` → **384-dimensional** vectors
- `intfloat/multilingual-e5-base` → **1024-dimensional** vectors

**If you change the embedding model to one with different dimensions, you must reset the Qdrant vector database:**

```bash
docker volume rm enterprise-rag_qdrant_data
docker-compose up
```

After restart, you'll need to re-index your documents. The system will initialize new collections with the correct vector dimensions.

## Scaling Up (Higher Performance)

For larger deployments or higher accuracy requirements:

### Larger LLM Model

Edit `.env`:

```env
OLLAMA_MODEL=llama2:70b-chat-q4_K_M
```

**Note**: Larger models require more VRAM. Ensure you have sufficient GPU memory before deploying.

### Larger Embedding Model

Edit `.env`:

```env
EMBEDDINGS_MODEL=intfloat/multilingual-e5-large
```

Remember: this generates 1024-dimensional vectors, so you'll need to reset Qdrant as described above.

## Memory Management

### Monitor Container Memory Usage

```bash
docker stats
```

### Limit Memory per Container

Edit `docker-compose.yml`:

```yaml
services:
  ollama:
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 6G
```

### Swap Space (Linux)

If you're running on a system with limited RAM, Linux swap can help prevent out-of-memory crashes (though performance will degrade):

```bash
# Check current swap
free -h

# Create 4GB swap file if needed
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent (add to /etc/fstab for persistence across reboots)
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Model Management

### Check Available Models

```bash
docker-compose exec ollama ollama list
```

### Remove Unused Models

If you switch models and want to free up space:

```bash
docker-compose exec ollama ollama rm MODEL_NAME
```

Example:
```bash
docker-compose exec ollama ollama rm llama2
```

## Troubleshooting Performance Issues

### Symptom: Slow Response Times

1. Check if embeddings service is healthy:
   ```bash
   docker-compose exec embeddings curl http://localhost/health
   ```

2. Check Ollama status:
   ```bash
   docker-compose logs ollama | tail -20
   ```

3. Monitor memory usage:
   ```bash
   docker stats
   ```

### Symptom: Out of Memory Errors

1. Scale down to a smaller LLM model (see [Scaling Down](#scaling-down))
2. Check if you have enough system RAM without GPU
3. Consider adding swap space (see [Swap Space](#swap-space-linux))

### Symptom: Slow Document Indexing

1. Check embeddings service is running:
   ```bash
   docker-compose exec embeddings curl http://localhost/health
   ```

2. Check Qdrant is healthy:
   ```bash
   docker-compose exec qdrant curl http://localhost:6333/health
   ```

3. View service logs:
   ```bash
   docker-compose logs embeddings
   docker-compose logs qdrant
   ```

## Configuration Examples

### Standard Setup (Recommended)
```env
OLLAMA_MODEL=llama3.1:8b-instruct-q5_K_M
EMBEDDINGS_MODEL=sentence-transformers/all-mpnet-base-v2
OLLAMA_KEEP_ALIVE=5m
```

### Lightweight Setup
```env
OLLAMA_MODEL=mistral:latest
EMBEDDINGS_MODEL=sentence-transformers/all-MiniLM-L6-v2
OLLAMA_KEEP_ALIVE=1m
```

### High-Accuracy Setup
```env
OLLAMA_MODEL=llama3.1:8b-instruct-q5_K_M
EMBEDDINGS_MODEL=intfloat/multilingual-e5-large
OLLAMA_KEEP_ALIVE=24h
```

## Understanding Vector Dimensions

When changing embedding models, understand that each model generates vectors of a specific dimensionality:

- **Lower dimensions (384D)**: Faster processing, lower memory usage, less semantic precision
- **Standard dimensions (768D)**: Good balance of speed, memory, and accuracy
- **Higher dimensions (1024D)**: Better semantic understanding, higher memory usage, slower processing

The Qdrant vector database must be initialized with the same vector dimension as your embedding model. Mismatches will cause errors. If you change models to one with different dimensions, delete the Qdrant volume and let it reinitialize.

## References

- [Ollama Model Library](https://ollama.com/library)
- [Sentence Transformers Models](https://huggingface.co/sentence-transformers)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
