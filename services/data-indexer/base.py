import hashlib
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

EMBEDDINGS_API: Optional[str] = None
QDRANT_API: Optional[str] = None


def configure_endpoints(embeddings_url: str, qdrant_url: str) -> None:
    """Configure service endpoints used by helper utilities."""
    global EMBEDDINGS_API, QDRANT_API
    EMBEDDINGS_API = embeddings_url
    QDRANT_API = qdrant_url


def hash_id(*parts: str) -> int:
    """Create a deterministic 31-bit integer hash from the concatenation of parts."""
    key = "::".join(parts)
    return int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16) % (2**31)


def ensure_collection_exists(collection: str) -> None:
    """Ensure a Qdrant collection with the correct dimensions exists."""
    if not QDRANT_API:
        raise RuntimeError("QDRANT_API endpoint is not configured")

    try:
        resp = requests.get(f"{QDRANT_API}/collections/{collection}", timeout=5)
        if resp.status_code == 200:
            logger.debug("Collection '%s' already present", collection)
            return
    except Exception as exc:
        logger.warning("Collection check failed for '%s': %s", collection, exc)

    payload = {
        "vectors": {
            "size": 1024,
            "distance": "Cosine",
        }
    }
    resp = requests.put(
        f"{QDRANT_API}/collections/{collection}",
        json=payload,
        timeout=10,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create collection '{collection}': {resp.text}")
    logger.info("Collection '%s' ready", collection)


def upsert_document(collection: str, point_id: int, vector: List[float], payload: Dict[str, Any]) -> bool:
    """Upsert a document into Qdrant."""
    if not QDRANT_API:
        raise RuntimeError("QDRANT_API endpoint is not configured")

    resp = requests.put(
        f"{QDRANT_API}/collections/{collection}/points?wait=true",
        json={"points": [{"id": point_id, "vector": vector, "payload": payload}]},
        timeout=10,
    )
    if resp.status_code not in (200, 201):
        logger.error("Failed to upsert document into '%s': %s", collection, resp.text)
        return False
    return True


def embed_text(text: str) -> Optional[List[float]]:
    """Generate embeddings for a text snippet."""
    if not EMBEDDINGS_API:
        raise RuntimeError("EMBEDDINGS_API endpoint is not configured")

    try:
        resp = requests.post(
            EMBEDDINGS_API,
            json={"inputs": [text]},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data[0] if isinstance(data, list) else data
    except Exception as exc:
        logger.error("Embedding request failed: %s", exc)
        return None


@dataclass
class SourceConfig:
    id: str
    type: str
    collection: str
    interval_minutes: int
    settings: Dict[str, Any]


class BaseSourceHandler:
    """Base interface for data source handlers."""

    def __init__(self, config: SourceConfig):
        self.config = config
        ensure_collection_exists(self.config.collection)

    @property
    def interval_minutes(self) -> int:
        return max(self.config.interval_minutes, 1)

    def run(self) -> None:
        """Execute the source-specific refresh."""
        raise NotImplementedError
