# Creating Custom Handlers

This guide explains how to create custom handlers for the Data Indexer to index data from any source.

## Overview

A handler is a Python class that fetches data from a source and indexes it into Qdrant. The Data Indexer automatically discovers and runs handlers based on configuration in `data_sources.json`.

### Handler responsibilities
1. Fetch data from the source
2. Transform data into documents
3. Generate embeddings for documents
4. Store documents in Qdrant

## Handler Structure

Every handler must extend `BaseSourceHandler` and implement the `run()` method.

#### File Location

```
services/data-indexer/handlers/
├── __init__.py
├── file_source_handler.py          (example)
├── weather_open_meteo.py           (example)
└── my_custom_handler.py            (your handler here)
```

#### Basic Template

```python
from base import (
    BaseSourceHandler,
    SourceConfig,
    embed_text,
    hash_id,
    upsert_document,
)
import logging

logger = logging.getLogger(__name__)

# Required: Unique handler type identifier
HANDLER_TYPE = "my_data_source"


class MySourceHandler(BaseSourceHandler):
    """Description of what this handler does."""

    def __init__(self, config: SourceConfig):
        """Initialize handler with configuration."""
        super().__init__(config)

        # Validate and store settings
        self.setting_one = config.settings.get("setting_one")
        self.setting_two = config.settings.get("setting_two", "default_value")

        # Validate required settings
        if not self.setting_one:
            raise ValueError("'setting_one' is required")

    def run(self) -> None:
        """Fetch data and index to Qdrant."""
        logger.info("Indexing from my data source (id=%s)", self.config.id)

        try:
            # 1. Fetch data from your source
            data = self._fetch_data()

            # 2. Process and index each item
            for item in data:
                self._index_item(item)

        except Exception as e:
            logger.error("Error in handler: %s", e)

    def _fetch_data(self):
        """Fetch data from your source."""
        # Implement your data fetching logic
        # Return list of items to index
        pass

    def _index_item(self, item):
        """Index a single item to Qdrant."""
        # 1. Generate embeddings
        vector = embed_text(item["text"])
        if not vector:
            logger.warning("Failed to embed item: %s", item.get("id"))
            return

        # 2. Create deterministic point ID
        point_id = hash_id(self.config.id, item.get("id", "unknown"))

        # 3. Prepare payload
        payload = {
            "source": self.config.id,
            "content": item["text"],
            "metadata": {
                "type": "my_type",
                "collection": self.config.collection,
            },
        }

        # 4. Upsert to Qdrant
        if upsert_document(
            self.config.collection,
            point_id,
            vector,
            payload
        ):
            logger.debug("Indexed item: %s", item.get("id"))
        else:
            logger.error("Failed to upsert item: %s", item.get("id"))


# Required: Export the handler class
HANDLER_CLASS = MySourceHandler
```

## Handler Configuration

After creating a handler, configure it in `config/data_sources.json`:

```json
{
  "id": "my_source_instance",
  "type": "my_data_source",
  "collection": "my_collection",
  "interval_minutes": 10,
  "settings": {
    "setting_one": "value",
    "setting_two": "another_value"
  }
}
```

The handler is automatically:
1. Discovered by the service
2. Instantiated with the configuration
3. Registered and scheduled
4. Executed at the specified interval

## Common Handler Patterns

### REST API Handler

Fetch data from a REST API:

```python
import requests

class RESTAPIHandler(BaseSourceHandler):
    def __init__(self, config: SourceConfig):
        super().__init__(config)
        self.api_url = config.settings.get("url")
        self.api_key = config.settings.get("api_key")

    def run(self) -> None:
        logger.info("Fetching from API: %s", self.api_url)

        try:
            response = requests.get(
                self.api_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            for item in data.get("items", []):
                self._index_item(item)

        except requests.RequestException as e:
            logger.error("API request failed: %s", e)
```

#### Configuration

```json
{
  "id": "rest_api_source",
  "type": "rest_api",
  "collection": "api_data",
  "interval_minutes": 60,
  "settings": {
    "url": "https://api.example.com/data",
    "api_key": "your-api-key-here"
  }
}
```

### Database Handler

Fetch data from a database:

```python
import sqlite3

class DatabaseHandler(BaseSourceHandler):
    def __init__(self, config: SourceConfig):
        super().__init__(config)
        self.db_path = config.settings.get("db_path")
        self.query = config.settings.get("query")

    def run(self) -> None:
        logger.info("Querying database: %s", self.db_path)

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(self.query)
            for row in cursor.fetchall():
                item = {
                    "id": row["id"],
                    "text": row["content"]
                }
                self._index_item(item)

            conn.close()

        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
```

#### Configuration

```json
{
  "id": "local_database",
  "type": "database",
  "collection": "db_data",
  "interval_minutes": 120,
  "settings": {
    "db_path": "/app/data/mydb.sqlite",
    "query": "SELECT id, content FROM articles WHERE updated > datetime('now', '-1 day')"
  }
}
```

### File Crawler Handler

Recursively index files from a directory:

```python
from pathlib import Path

class FileCrawlerHandler(BaseSourceHandler):
    def __init__(self, config: SourceConfig):
        super().__init__(config)
        self.directory = Path(config.settings.get("directory"))
        self.extensions = config.settings.get("extensions", ["*.txt"])

    def run(self) -> None:
        logger.info("Crawling directory: %s", self.directory)

        files_processed = 0

        for extension in self.extensions:
            for file_path in self.directory.rglob(extension):
                if file_path.is_file():
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()

                        item = {
                            "id": str(file_path),
                            "text": content,
                            "filename": file_path.name
                        }
                        self._index_item(item)
                        files_processed += 1

                    except Exception as e:
                        logger.error("Error reading file %s: %s", file_path, e)

        logger.info("Processed %d files", files_processed)
```

## Helper Functions

The `base` module provides utility functions:

#### `embed_text(text: str) -> List[float]`

Generate embeddings for text.

```python
vector = embed_text("Your text here")
if vector:
    print(f"Generated {len(vector)}-dimensional vector")
else:
    print("Failed to generate embedding")
```

#### `hash_id(*parts: str) -> int`

Create deterministic point IDs from multiple parts.

```python
# Same inputs = same ID (idempotent)
point_id = hash_id(self.config.id, item["id"], str(item["timestamp"]))
```

#### `upsert_document(collection: str, point_id: int, vector: List[float], payload: Dict) -> bool`

Store document in Qdrant.

```python
success = upsert_document(
    collection="my_collection",
    point_id=12345,
    vector=[0.1, 0.2, 0.3, ...],
    payload={
        "source": "my_source",
        "content": "Document text",
        "metadata": {"type": "article"}
    }
)
```

#### `ensure_collection_exists(collection: str) -> None`

Called automatically by `BaseSourceHandler.__init__()`, but can be called manually:

```python
from base import ensure_collection_exists

ensure_collection_exists("my_collection")
```

## Best Practices

#### 1. Deterministic IDs

Always use `hash_id()` to create deterministic point IDs. This ensures:
- Idempotent indexing (running twice indexes once)
- Easy deduplication
- Consistent updates

```python
# Good: deterministic
point_id = hash_id(self.config.id, item["id"])

# Bad: random or timestamp-based
import time
point_id = int(time.time() * 1000)  # ❌ Different each run
```

#### 2. Error Handling

Always wrap logic in try-except blocks:

```python
def run(self) -> None:
    try:
        data = self._fetch_data()
        for item in data:
            self._index_item(item)
    except Exception as e:
        logger.error("Handler error: %s", e)
        # Don't raise - let the scheduler handle retries
```

#### 3. Logging

Use logging extensively for debugging:

```python
logger.debug("Processing item: %s", item_id)
logger.info("Indexed %d documents", count)
logger.warning("Missing field: %s", field_name)
logger.error("Failed to fetch: %s", error)
```

#### 4. Timeout Handling

Set reasonable timeouts for network operations:

```python
response = requests.get(url, timeout=30)  # 30 seconds
```

#### 5. Rate Limiting

Be respectful to external APIs:

```python
import time

for item in items:
    self._index_item(item)
    time.sleep(0.1)  # 100ms delay between requests
```

#### 6. Validation

Validate configuration on initialization:

```python
def __init__(self, config: SourceConfig):
    super().__init__(config)

    self.required_setting = config.settings.get("required_setting")
    if not self.required_setting:
        raise ValueError("'required_setting' is required")

    self.optional_setting = config.settings.get("optional_setting", "default")
```

## Testing Your Handler

### Manual Testing

Test your handler locally before deploying:

```python
from handlers.my_handler import MySourceHandler, HANDLER_TYPE
from base import SourceConfig, configure_endpoints

# Configure endpoints
configure_endpoints(
    "http://localhost:8080/embed",
    "http://localhost:6333"
)

# Create test config
config = SourceConfig(
    id="test_run",
    type=HANDLER_TYPE,
    collection="test_collection",
    interval_minutes=10,
    settings={"setting_one": "test_value"}
)

# Run handler
handler = MySourceHandler(config)
handler.run()
```

### Docker Testing

Test in Docker container:

```bash
# Rebuild with your changes
docker-compose up -d --build data-indexer

# Check logs
docker-compose logs -f data-indexer

# Verify data indexed
curl http://localhost:6333/collections/my_collection
```

## Debugging

#### Enable Debug Logging

Edit `docker-compose.yml`:

```yaml
data-indexer:
  environment:
    - LOG_LEVEL=DEBUG
```

Then rebuild and check logs:

```bash
docker-compose up -d --build data-indexer
docker-compose logs -f data-indexer
```

#### Inspect Handler Discovery

Check if handler is registered:

```bash
docker-compose logs data-indexer | grep "Registered handler"
```

#### Check Configuration

Verify your configuration is valid:

```bash
docker-compose exec data-indexer python -m json.tool /app/config/data_sources.json
```

## Common Patterns and Examples

### Incrementally Fetching Data

Only index new/updated items:

```python
def run(self) -> None:
    # Load last successful timestamp
    last_run = self._get_last_run_time()

    # Fetch only newer items
    data = self._fetch_data(since=last_run)

    # Index items
    for item in data:
        self._index_item(item)

    # Save current time
    self._save_last_run_time(datetime.now())
```

### Batch Processing

Process items in batches:

```python
def run(self) -> None:
    data = self._fetch_data()

    batch = []
    for item in data:
        batch.append(item)

        if len(batch) >= 100:
            self._index_batch(batch)
            batch = []

    # Index remaining items
    if batch:
        self._index_batch(batch)
```

### Fallback/Retry Logic

Retry failed items:

```python
def _index_item(self, item, retry_count=0):
    max_retries = 3

    try:
        vector = embed_text(item["text"])
        if not vector:
            raise Exception("Embedding failed")

        upsert_document(...)

    except Exception as e:
        if retry_count < max_retries:
            logger.warning("Retry %d for item %s", retry_count + 1, item["id"])
            time.sleep(2 ** retry_count)  # Exponential backoff
            self._index_item(item, retry_count + 1)
        else:
            logger.error("Failed after %d retries: %s", max_retries, e)
```

## Handler Examples in Repository

Check the built-in handlers for reference:

- **File Source**: `services/data-indexer/handlers/file_source_handler.py`
- **Weather Open-Meteo**: `services/data-indexer/handlers/weather_open_meteo.py`

## Troubleshooting

#### Handler Not Discovered

1. Check filename matches pattern: `*_handler.py` or `*.py`
2. Verify exports: `HANDLER_TYPE` and `HANDLER_CLASS`
3. Check for Python syntax errors: `python -m py_compile my_handler.py`
4. Check logs: `docker-compose logs data-indexer | grep HANDLER_TYPE`

#### Data Not Indexed

1. Check configuration is correct in `data_sources.json`
2. Verify `embed_text()` returns vectors: `LOG_LEVEL=DEBUG`
3. Check Qdrant is healthy: `curl http://localhost:6333/healthz`
4. Review handler logs for errors: `docker-compose logs data-indexer`

#### Performance Issues

1. Add delays between API calls
2. Reduce batch sizes
3. Increase `interval_minutes` to reduce frequency
4. Check embeddings service performance: `docker stats`

## Summary

Creating a custom handler is straightforward:

1. **Extend `BaseSourceHandler`**
2. **Implement `run()` method**
3. **Fetch data from your source**
4. **Generate embeddings with `embed_text()`**
5. **Store in Qdrant with `upsert_document()`**
6. **Configure in `data_sources.json`**
7. **The service discovers and runs it automatically**

See examples in the repository for reference implementations.
