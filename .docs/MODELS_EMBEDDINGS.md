# Models and Embeddings

Information about the LLM model and embedding model used in the Enterprise RAG system.

## Language Model (LLM)

The system uses Ollama to run open-source language models locally.

### Current Configuration

#### Default Model: `llama3.1:8b-instruct-q5_K_M`

This is an 8-billion parameter quantized version of Llama 3.1 optimized for instruction-following and conversational tasks.

#### Characteristics
- Size: 8B parameters
- Type: Instruction-tuned
- Format: Q5_K_M quantization (5-bit, medium accuracy, good balance)
- Memory requirement: ~6GB RAM
- Inference speed: 50-150ms per token (CPU dependent)
- Quality: Excellent reasoning and instruction following
- Best for: General-purpose conversations, question-answering, RAG tasks

### Changing the Model

Edit `.env`:

```env
OLLAMA_MODEL=llama3.1:8b-instruct-q5_K_M    # Default (recommended)
OLLAMA_MODEL=mistral:latest                   # Alternative
OLLAMA_MODEL=neural-chat:latest               # Alternative
```

Then restart the Ollama service:

```bash
docker-compose restart ollama
```

The model will be downloaded automatically on first run and cached for future use.

### Storing and Managing Models

Models are stored in the `ollama_data` volume. On your system, this maps to the local Docker volume storage.

#### Check available space
```bash
# See storage location
docker volume inspect enterprise-rag_ollama_data

# Typical model sizes:
# - Llama 3.1 8B: ~6GB
# - Mistral 7B: ~4GB
```

#### Remove an unused model

If you switch models and want to free up space, connect to the Ollama container and remove the old model:

```bash
docker-compose exec ollama ollama rm llama2
```

Or for other models:
```bash
docker-compose exec ollama ollama rm mistral
```

## Embedding Model

Embeddings convert text into numerical vectors for semantic search.

### Current Configuration

#### Default Model: `sentence-transformers/all-mpnet-base-v2`

- Supports 100+ languages
- Creates 768-dimensional vectors
- Optimized for semantic search and speed
- Good balance between accuracy and performance

#### Why embeddings matter

Embeddings enable semantic similarity search. Instead of keyword matching, they capture the meaning of text:

```
"The cat is sleeping"
  → [0.234, -0.156, 0.891, ... 768 values]

"The dog is napping"
  → [0.241, -0.142, 0.885, ... 768 values]

These vectors are similar in vector space → semantically related
```

### Changing the Embedding Model

Edit `.env`:

```env
EMBEDDINGS_MODEL=sentence-transformers/all-mpnet-base-v2  # Default, recommended (768D)
EMBEDDINGS_MODEL=intfloat/multilingual-e5-base             # Higher accuracy (768D)
EMBEDDINGS_MODEL=sentence-transformers/all-MiniLM-L6-v2   # Lightweight, English only (384D)
```

Restart the embeddings service:

```bash
docker-compose restart embeddings
```

**Important**: If you change to a model with different vector dimensions, you must reset the Qdrant vector database:

```bash
docker volume rm enterprise-rag_qdrant_data
docker-compose up
```

The model will be downloaded automatically on first run.

### Model Comparison

| Model | Language | Vector Dims | Best For |
|-------|----------|------------|----------|
| **all-mpnet-base-v2** (default) | 100+ languages | 768D | General purpose, balanced |
| **multilingual-e5-base** | 100+ languages | 768D | Higher semantic accuracy, same dimensions as default |
| **multilingual-e5-large** | 100+ languages | 1024D | Maximum accuracy, higher resources |
| **all-MiniLM-L6-v2** | English only | 384D | Resource-constrained systems |

**Note**: For exact specifications (model size, inference speed, memory requirements), check the official model cards on [Hugging Face](https://huggingface.co/sentence-transformers).

### Vector Dimensions Explained

- **384D**: Small and fast, good for constrained systems but lower semantic precision
- **768D**: Balanced (default) – good semantic quality with reasonable speed and memory
- **1024D**: Larger and slower, maximum semantic accuracy for multilingual content

The default embedding model uses **768D vectors**, providing excellent semantic understanding while maintaining good performance across languages.

## Multilingual Support

The default embedding model (`sentence-transformers/all-mpnet-base-v2`) supports:

- English, Spanish, French, German, Italian
- Chinese, Japanese, Korean
- Arabic, Russian, Hindi
- And 90+ additional languages

This makes it suitable for organizations with multilingual documents or global user bases. If you need even higher semantic accuracy for multilingual content and have sufficient resources, consider upgrading to `intfloat/multilingual-e5-base` or `intfloat/multilingual-e5-large`.
