"""
File Source Handler

Indexes local files from a specified directory and keeps them
synchronized in Qdrant for semantic search.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from base import (
    BaseSourceHandler,
    SourceConfig,
    embed_text,
    hash_id,
    upsert_document,
)

logger = logging.getLogger(__name__)

HANDLER_TYPE = "file_source"


class FileSourceHandler(BaseSourceHandler):
    """Index local files from a directory."""

    def __init__(self, config: SourceConfig):
        super().__init__(config)
        settings = config.settings or {}
        self.directory = settings.get("directory")
        self.patterns = settings.get("patterns", ["*.txt"])

        if not self.directory:
            raise ValueError("File source handler requires 'directory' in settings")

        self.dir_path = Path(self.directory)
        if not self.dir_path.exists():
            logger.warning("Directory does not exist: %s", self.directory)

    def run(self) -> None:
        logger.info("Indexing files from %s (source=%s)", self.directory, self.config.id)

        if not self.dir_path.exists():
            logger.warning("Directory does not exist, skipping: %s", self.directory)
            return

        files_indexed = 0

        # Iterate through all patterns
        for pattern in self.patterns:
            for file_path in self.dir_path.glob(pattern):
                if file_path.is_file():
                    if self._index_file(file_path):
                        files_indexed += 1

        logger.info("Indexed %d files from %s", files_indexed, self.directory)

    def _index_file(self, file_path: Path) -> bool:
        """Index a single file to Qdrant."""
        try:
            # Read file content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                logger.debug("Skipping empty file: %s", file_path)
                return False

            logger.debug("Indexing file: %s (%d bytes)", file_path.name, len(content))

            # Generate embeddings
            vector = embed_text(content)
            if not vector:
                logger.error("Failed to get embeddings for %s", file_path.name)
                return False

            # Create deterministic point ID
            point_id = hash_id(self.config.id, str(file_path))

            # Prepare payload
            payload = {
                "source": self.config.id,
                "filename": file_path.name,
                "file_path": str(file_path),
                "content": content,
                "content_length": len(content),
                "metadata": {
                    "collection": self.config.collection,
                    "handler": HANDLER_TYPE,
                    "type": "file",
                },
            }

            # Upsert to Qdrant
            if upsert_document(self.config.collection, point_id, vector, payload):
                logger.info("Indexed file: %s", file_path.name)
                return True
            else:
                logger.error("Failed to upsert file to Qdrant: %s", file_path.name)
                return False

        except Exception as exc:
            logger.error("Error indexing file %s: %s", file_path.name, exc)
            return False


HANDLER_CLASS = FileSourceHandler
