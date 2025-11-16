# Troubleshooting

Common issues and solutions for the Enterprise RAG system.

## Services Not Starting

### Symptoms
- Container exits immediately
- Port already in use
- Permission denied errors

### Diagnosis

```bash
# Check container status
docker-compose ps

# View error logs
docker-compose logs

# Check specific service
docker-compose logs ollama
```

### Solutions

**Port already in use:**
```bash
# Change port in .env
OLLAMA_PORT=32102        # instead of 32101
WEBUI_PORT=3001          # instead of 3000

# Restart
docker-compose down
docker-compose up -d
```

**Permission denied (Linux):**
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Apply group changes
newgrp docker

# Restart
docker-compose up -d
```

**Out of disk space:**
```bash
# Check available space
df -h

# Clean up Docker
docker system prune -a

# Free space and retry
docker-compose up -d
```

## Out of Memory

### Symptoms
- Container killed/restarts
- Application crashes
- Slow performance

### Diagnosis

```bash
# Monitor memory usage
watch -n 1 docker stats

# Check Docker stats
docker system df

# Specific container memory
docker stats --no-stream | grep ollama
```

### Solutions

**Reduce batch size:**
```yaml
embeddings:
  environment:
    - BATCH_SIZE=8              # Default 32
```

Restart:
```bash
docker-compose restart embeddings
```

**Use smaller model:**
```env
OLLAMA_MODEL=openchat           # Instead of llama2
EMBEDDINGS_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

**Increase system swap (Linux):**
```bash
# Create 8GB swap
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

**Set memory limits:**
```yaml
ollama:
  deploy:
    resources:
      limits:
        memory: 4G
      reservations:
        memory: 2G
```

## Slow Performance

### Symptoms
- Embedding takes >200ms per text
- LLM response generation is slow
- Search latency is high

### Diagnosis

```bash
# Check CPU usage
docker stats

# Monitor system load
top

# Check disk I/O
iostat -x 1

# GPU status (if available)
nvidia-smi
```

### Solutions

**Enable GPU (if available):**

See [OPTIMIZATION.md](OPTIMIZATION.md) for GPU setup.

**Increase batch size:**
```yaml
embeddings:
  environment:
    - BATCH_SIZE=64             # From default 32
```

**Use smaller model:**
```env
OLLAMA_MODEL=mistral            # Faster than llama2
EMBEDDINGS_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

**Allocate more CPU cores:**
```yaml
ollama:
  deploy:
    resources:
      reservations:
        cpus: '4'               # From default
```

**Check disk speed:**
```bash
# Test disk I/O
dd if=/dev/zero of=testfile bs=1M count=1000 oflag=direct
```

Models stored on slow disks will load slowly.

## Connection Issues

### Symptoms
- Services can't communicate
- "Connection refused" errors
- Timeout errors

### Diagnosis

```bash
# Test service connectivity
docker-compose exec webui curl http://ollama:11434/api/tags
docker-compose exec webui curl http://qdrant:6333/health
docker-compose exec webui curl http://embeddings:80/health

# Check network
docker network ls
docker network inspect enterprise-rag-network
```

### Solutions

**Restart all services:**
```bash
docker-compose restart
```

**Recreate network:**
```bash
docker-compose down
docker-compose up -d
```

**Check Docker daemon:**
```bash
# Restart Docker
sudo systemctl restart docker

# Or on macOS
# Restart Docker Desktop
```

## Port Conflicts

### Symptoms
- "Address already in use" error
- Can't access services

### Diagnosis

```bash
# Check listening ports (Linux/macOS)
lsof -i :3000
lsof -i :32101

# Windows
netstat -ano | findstr :3000
```

### Solutions

**Change port in .env:**
```env
WEBUI_PORT=3001              # Instead of 3000
OLLAMA_PORT=32102            # Instead of 32101
```

**Stop conflicting service:**
```bash
# Find process using port 3000
lsof -i :3000

# Kill it (if it's not needed)
kill -9 <PID>
```

## Document Upload Issues

### Symptoms
- Upload fails silently
- "File too large" error
- "Unsupported format" error

### Diagnosis

```bash
# Check MinIO health
docker-compose logs minio

# Check available space
df -h

# Check permissions
docker-compose exec minio ls -la /data
```

### Solutions

**Increase disk space:**
```bash
# Check available space
df -h

# Delete old backups
bash scripts/backup.sh cleanup 7
```

**Check file format:**

Supported formats:
- PDF, TXT, DOCX, XLSX, PPTX, MD, JSON, CSV

**Check file size:**
- Recommended: <100MB per file
- For larger files: Split into chunks

**Reset MinIO:**
```bash
docker-compose down
docker volume rm enterprise-rag-minio
docker-compose up -d
```

## Indexing Issues

### Symptoms
- Documents don't appear in search
- Embeddings not generating
- "Collection not found" error

### Diagnosis

```bash
# Check Qdrant collections
curl http://localhost:6333/collections

# Check embeddings service
docker-compose logs embeddings | tail -20

# Check MinIO documents
docker-compose exec minio ls /data/documents/
```

### Solutions

**Create collection manually:**
```bash
curl -X PUT http://localhost:6333/collections/documents \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 1024,
      "distance": "Cosine"
    }
  }'
```

**Re-index documents:**
```bash
# Delete and recreate
curl -X DELETE http://localhost:6333/collections/documents

# Re-upload through Web UI
# Or use API to re-index
```

**Check embeddings service:**
```bash
# Restart
docker-compose restart embeddings

# Check logs
docker-compose logs embeddings

# Test manually
curl -X POST http://localhost:8080/embed \
  -H "Content-Type: application/json" \
  -d '{"inputs": "test"}'
```

## Model Loading Issues

### Symptoms
- No models appear in Open WebUI dropdown
- "Model not found" error when trying to chat
- Model download appears stuck or slow
- First startup takes longer than expected (2-5 minutes)

### Important: Automatic Model Pulling

On first startup, Ollama automatically downloads the model specified in `.env` (`OLLAMA_MODEL`). This may take 2-5 minutes depending on internet speed and model size (~6GB for default model). **This is normal behavior.**

### Diagnosis

```bash
# Check Ollama logs during startup
docker-compose logs -f ollama

# Check available space
docker exec enterprise-rag-ollama df -h /root/.ollama

# Check downloaded models
docker-compose exec ollama ollama list

# Check if model exists
docker-compose exec ollama ollama list | grep llama
```

### Solutions

**Wait for model to download:**
- First startup takes 2-5 minutes
- Check logs: `docker-compose logs ollama`
- Once download completes, restart Web UI: `docker-compose restart webui`

**Free disk space:**
```bash
# Check space requirements
# - Default model (llama3.1:8b) needs ~6GB
# - Embeddings model needs ~500MB
df -h

# Delete old backups
bash scripts/backup.sh cleanup 30

# Remove unused Docker images
docker image prune -a
```

**Delete unused models:**
```bash
docker-compose exec ollama ollama rm mistral
docker-compose exec ollama ollama list
```

**Manually pull a different model:**
```bash
# Download a specific model
docker-compose exec ollama ollama pull llama2

# Update .env to use it
OLLAMA_MODEL=llama2

# Restart Ollama
docker-compose restart ollama
```

**Check download progress:**
```bash
# View logs in real-time during download
docker-compose logs -f ollama | grep -i "pulling\|downloading"
```

## Web UI Issues

### First-Time Registration (Expected Behavior)

When you access Open WebUI for the first time at **http://localhost:3000**:
1. You'll see a registration form (not a login form)
2. Enter any email and password - the first user becomes the **admin**
3. Subsequent users will be regular users
4. Login with these credentials on future visits

This is normal Open WebUI behavior and expected on first startup.

### Symptoms
- Page won't load
- "Connection refused" on localhost:3000
- Blank/broken interface
- Model doesn't appear after registration

### Diagnosis

```bash
# Check Web UI health
docker-compose ps webui

# View logs
docker-compose logs webui

# Test manually
curl http://localhost:3000

# Check network
docker network inspect enterprise-rag-network

# Check if Ollama has model
docker-compose exec ollama ollama list
```

### Solutions

**Restart Web UI:**
```bash
docker-compose restart webui
```

**Wait for Ollama model:**
- If model doesn't appear, Ollama may still be downloading it
- Check: `docker-compose logs ollama | grep -i "pulling\|downloading"`
- Wait for download to complete (2-5 minutes)
- Then refresh page

**Clear cache:**
```bash
# Browser: Clear cache and cookies
# Then refresh page (Ctrl+Shift+Delete in Chrome)
```

**Rebuild container:**
```bash
docker-compose down
docker-compose up -d webui
```

**Check port:**
```bash
# Verify port is correct
docker-compose ps webui

# Default: 3000
# Check .env for WEBUI_PORT
```

## API Issues

### Symptoms
- API requests timeout
- "No response" from endpoints
- 500 internal server errors

### Diagnosis

```bash
# Test API endpoint
curl http://localhost:3000/api/health

# Check logs
docker-compose logs webui

# Test underlying services
curl http://localhost:32101/api/tags      # Ollama
curl http://localhost:6333/health          # Qdrant
curl http://localhost:8080/health          # Embeddings
```

### Solutions

**Restart Web UI:**
```bash
docker-compose restart webui
```

**Check service health:**
```bash
bash scripts/health-check.sh
```

**Test endpoints individually:**
```bash
# If Ollama fails
docker-compose restart ollama
docker-compose exec webui curl http://ollama:11434/api/tags

# If Qdrant fails
docker-compose restart qdrant
docker-compose exec webui curl http://qdrant:6333/health
```

## Backup/Restore Issues

### Symptoms
- Backup fails
- Restore doesn't work
- Data loss

### Diagnosis

```bash
# Check backup logs
bash scripts/backup.sh list

# Check disk space
df -h

# Check backup files
ls -lah _backups/
```

### Solutions

**Ensure sufficient disk space:**
```bash
# Check space
df -h

# Free up space
docker system prune -a
bash scripts/backup.sh cleanup 30
```

**Test restore:**
```bash
# List backups
bash scripts/backup.sh list

# Restore specific backup
bash scripts/backup.sh restore enterprise-rag-backup-20240115_120000
```

**Manual backup:**
```bash
# If script fails
docker-compose exec qdrant tar czf /qdrant/storage/backup.tar.gz -C /qdrant/storage .
docker cp enterprise-rag-qdrant:/qdrant/storage/backup.tar.gz ./manual-backup.tar.gz
```

## System Restart

### Reset Everything (Careful!)

```bash
# Stop services
docker-compose down

# Remove all data (irreversible!)
docker-compose down -v

# Remove local data
rm -rf data/documents/* _backups/*

# Start fresh
docker-compose up -d

# System will auto-initialize (minio-init service creates buckets automatically)
```

## Getting Help

### Collect Debug Information

```bash
# System info
docker --version
docker-compose --version
docker-compose config

# Service status
docker-compose ps
docker-compose logs > debug-logs.txt

# Resource usage
docker stats --no-stream > resources.txt

# Network
docker network inspect enterprise-rag-network
```

### Common Commands

```bash
# Full system restart
docker-compose down && docker-compose up -d

# Force restart service
docker-compose kill ollama && docker-compose up -d ollama

# View detailed logs
docker-compose logs --tail=100 -f ollama

# Check service config
docker-compose exec ollama env

# System cleanup
docker system prune
```
