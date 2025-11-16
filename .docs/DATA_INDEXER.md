# Data Indexer Service

The Data Indexer is the core service that automatically synchronizes data from multiple sources into Qdrant for semantic search and RAG context injection.

## Overview

The Data Indexer uses a **handler-based architecture** where each data source (files, APIs, databases, etc.) is managed by a pluggable handler. This allows you to:

- Index local files from directories
- Automatically fetch and index external APIs
- Create custom handlers for any data source
- Keep data synchronized on a schedule
- Manage all sources from a single configuration file

### How it works

```
config/data_sources.json (configuration)
  ↓
Service discovers handlers
  ↓
Each handler runs on schedule
  ↓
Fetch/read data → Generate embeddings → Store in Qdrant
  ↓
Data ready for RAG queries
```

## Configuration

All data sources are defined in `config/data_sources.json`:

```json
{
  "sources": [
    {
      "id": "local_weather_documents",
      "type": "file_source",
      "collection": "documents",
      "interval_minutes": 60,
      "settings": {
        "directory": "/app/weather_documents",
        "patterns": ["*.txt"]
      }
    },
    {
      "id": "open_meteo_spain",
      "type": "weather_open_meteo",
      "collection": "weather_data",
      "interval_minutes": 10,
      "settings": {
        "timezone": "Europe/Madrid",
        "forecast_days": 3,
        "locations": [
          {
            "id": "madrid",
            "name": "Madrid, Spain",
            "latitude": 40.4168,
            "longitude": -3.7038
          }
        ]
      }
    }
  ]
}
```

### Configuration Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| **id** | `string` | Unique identifier for the data source |
| **type** | `string` | Handler type: `file_source` or custom handler name |
| **collection** | `string` | Qdrant collection name where data will be stored |
| **interval_minutes** | `integer` | Refresh interval in minutes (1-1440) |
| **settings** | `object` | Handler-specific configuration (varies by type) |

## Built-in Handlers

### File Source Handler

Indexes local files from a specified directory and keeps them synchronized in Qdrant.

#### Handler Type

Type: **`file_source`**

#### Configuration

```json
{
  "id": "local_docs",
  "type": "file_source",
  "collection": "documents",
  "interval_minutes": 60,
  "settings": {
    "directory": "/path/to/files",
    "patterns": ["*.txt", "*.md"]
  }
}
```

#### Settings

| Setting | Type | Description |
|---------|------|-------------|
| **directory** | `string` | Path to directory inside container |
| **patterns** | `array[string]` | File glob patterns to match (e.g., `["*.txt", "*.md"]`) |

#### Example: Multiple Document Sources

You can configure multiple file sources to index different directories. This is useful when you have documents organized in different locations:

```json
{
  "sources": [
    {
      "id": "local_animal_documents",
      "type": "file_source",
      "collection": "documents",
      "interval_minutes": 60,
      "settings": {
        "directory": "/app/animal_documents",
        "patterns": ["*.txt"]
      }
    },
    {
      "id": "local_data_documents",
      "type": "file_source",
      "collection": "documents",
      "interval_minutes": 60,
      "settings": {
        "directory": "/app/data/documents",
        "patterns": ["*.txt"]
      }
    },
    {
      "id": "knowledge_base_articles",
      "type": "file_source",
      "collection": "documents",
      "interval_minutes": 120,
      "settings": {
        "directory": "/app/knowledge_base",
        "patterns": ["*.txt", "*.md"]
      }
    }
  ]
}
```

In this example:
- **local_animal_documents**: Indexes animal-related files every 60 minutes
- **local_data_documents**: Indexes data files from a separate directory also every 60 minutes
- **knowledge_base_articles**: Indexes markdown and text files from a knowledge base every 2 hours

All documents are stored in the same `documents` collection and become searchable together.

### Weather Open-Meteo Handler

**This is an example custom handler** that demonstrates how to fetch data from an external API (Open-Meteo) and index it into Qdrant. Use this as a reference when building your own custom handlers.

#### Handler Type

Type: **`weather_open_meteo`**

#### Configuration

```json
{
  "id": "open_meteo_spain",
  "type": "weather_open_meteo",
  "collection": "weather_data",
  "interval_minutes": 10,
  "settings": {
    "timezone": "Europe/Madrid",
    "forecast_days": 3,
    "locations": [
      {
        "id": "madrid",
        "name": "Madrid, Spain",
        "latitude": 40.4168,
        "longitude": -3.7038
      }
    ]
  }
}
```

#### Settings

| Setting | Type | Description |
|---------|------|-------------|
| **timezone** | `string` | IANA timezone for timestamp conversion (e.g., `Europe/Madrid`, `UTC`) |
| **forecast_days** | `integer` | Number of days to forecast (1-16) |
| **locations** | `array[object]` | Array of location objects with `id`, `name`, `latitude`, `longitude` |

#### What This Handler Does

The weather handler:

1. For each location, fetches current weather and forecast data from the Open-Meteo API
2. Extracts temperature, humidity, precipitation, and weather codes
3. Generates a natural language document describing the weather
4. Generates embeddings for the document
5. Stores the document in Qdrant's `weather_data` collection
6. Runs automatically at the specified interval

This allows RAG queries to include current weather information as context when answering questions about weather.

## Custom Handlers

The Data Indexer supports custom handlers for any data source:

- **Databases** - MySQL, PostgreSQL, MongoDB, etc.
- **APIs** - Twitter, Slack, REST endpoints, etc.
- **Cloud Storage** - AWS S3, Google Cloud Storage, etc.
- **Streaming** - Kafka, RSS feeds, webhooks, etc.
- **Enterprise Systems** - CRM, ERP, knowledge bases, etc.

### Creating a Custom Handler

For a comprehensive guide on creating custom handlers, see [Creating Custom Handlers](DATA_INDEXER_CUSTOM_HANDLERS.md).
