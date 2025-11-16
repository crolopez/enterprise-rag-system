# Enterprise RAG System

Enterprise-ready knowledge indexer that consolidates everything your company knows—scanned PDFs, internal playbooks, wiki exports, scheduled API feeds, and curated corrections—into a single retrieval layer.

The platform ships as a microservice bundle (Ollama, Qdrant, embeddings, storage, WebUI) that boots with minimal configuration so you can focus on connecting data sources instead of wiring infrastructure.

## Key Features

- **Unified Data Ingestion**: Data Indexer syncs files and external APIs into Qdrant using pluggable handlers.
- **Scheduled API Harvesting**: Handler-based system ingests external feeds (Open-Meteo sample included).
- **Web Content Crawling** [status: planned] – Index wiki pages, documentation sites, and online knowledge bases directly from URLs.
- **Feedback & Override Loop** [status: planned] – Extension point for injecting corrections or guardrails into the knowledge base.
- **Local-First & Private**: Entire stack runs on your infrastructure with optional GPU acceleration and no external dependencies.
- **Composable Microservices**: Docker Compose keeps services decoupled, observable, and easy to scale or swap.

## Prerequisites

| Requirement | Minimum | Recommended |
|---|---|---|
| **Docker** | v20.10+ | Latest |
| **Docker Compose** | v1.29+ | Latest |
| **RAM** | 4GB | 8GB+ |
| **Storage** | 10GB | 20GB+ |
| **GPU** | Not required | NVIDIA GPU with 16GB+ VRAM (reduces response latency) |
| **OS** | Windows, macOS, Linux | Linux |

**Note**: The system runs on CPU-only setups, though GPU acceleration is recommended for production workloads. Without a GPU, allocate at least 16GB of system RAM to ensure smooth operation.

## How to Launch

```bash
cp .env.example .env
```

Configure `.env` with your preferences:

| Setting | Default | Purpose |
|---|---|---|
| `WEBUI_PORT` | 3000 | Web interface port |
| `OLLAMA_PORT` | 32101 | LLM engine port |
| `QDRANT_PORT` | 6333 | Vector database port |
| `EMBEDDINGS_PORT` | 8080 | Embeddings service port |
| `MINIO_PORT` | 9000 | Document storage API port |
| `MINIO_CONSOLE_PORT` | 9001 | Document storage console port |
| `MINIO_ROOT_USER` | minioadmin | Storage admin username (change for production) |
| `MINIO_ROOT_PASSWORD` | minioadmin | Storage admin password (change for production) |
| `MINIO_BUCKET_NAME` | documents | Default bucket for synchronized knowledge assets |
| `OLLAMA_MODEL` | llama3.1:8b-instruct-q5_K_M | LLM model to use |
| `EMBEDDINGS_MODEL` | intfloat/multilingual-e5-base | Embeddings model |
| `COMPOSE_PROJECT_NAME` | enterprise-rag | Docker Compose project identifier |

Configure data sources in `config/data_sources.json` (file indexing and Open-Meteo examples included). New handlers are auto-discovered from `services/data-indexer/handlers/`.

```bash
docker-compose down
# First time you launch it, you'll need to register your admin account from the UI
docker-compose up  --build
```

Open browser: **http://localhost:3000**

Ready to use. Upload documents and start asking questions.

## Documentation

- **[Architecture](.docs/ARCHITECTURE.md)** - System design and components
- **[Data Indexing](.docs/DATA_INDEXING_OVERVIEW.md)** - How to index and manage data
- **[Models & Embeddings](.docs/MODELS_EMBEDDINGS.md)** - Model information and available models
- **[Performance Tuning](.docs/PERFORMANCE_TUNING.md)** - Hardware configuration and scaling guide
- **[Troubleshooting](.docs/TROUBLESHOOTING.md)** - Common issues and solutions

## License

MIT License - See [LICENSE](LICENSE) file for details
