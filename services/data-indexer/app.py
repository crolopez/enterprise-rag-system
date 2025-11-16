#!/usr/bin/env python3
"""
Unified Data Indexer Service

Loads handlers dynamically based on configuration to keep data sources
(files, APIs, databases, etc.) synchronized in Qdrant. Drop new handler
modules into `handlers/` and reference them from `config/data_sources.json`.
"""

import importlib
import json
import logging
import os
import pkgutil
import time
from pathlib import Path
from typing import Any, Dict, Optional, Type

import schedule

from base import BaseSourceHandler, SourceConfig, configure_endpoints

# Logging & environment

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("data-indexer")

EMBEDDINGS_API = os.getenv("EMBEDDINGS_API", "http://embeddings:80/embed")
QDRANT_API = os.getenv("QDRANT_API", "http://qdrant:6333")
CONFIG_PATH = Path(os.getenv("DATA_INDEXER_CONFIG", "/app/config/data_sources.json"))
HANDLERS_PACKAGE = os.getenv("DATA_INDEXER_HANDLERS_PACKAGE", "handlers")

# Utilities

def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Data indexer configuration not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def discover_handlers(package_name: str) -> Dict[str, Type[BaseSourceHandler]]:
    """Discover handler classes exported by modules inside the package."""
    registry: Dict[str, Type[BaseSourceHandler]] = {}

    try:
        package = importlib.import_module(package_name)
    except ImportError as exc:
        logger.error("Cannot import handlers package '%s': %s", package_name, exc)
        return registry

    for _, module_name, ispkg in pkgutil.iter_modules(package.__path__):
        if ispkg:
            continue

        full_name = f"{package.__name__}.{module_name}"
        try:
            module = importlib.import_module(full_name)
        except Exception as exc:
            logger.error("Failed to import handler module '%s': %s", full_name, exc)
            continue

        handler_type = getattr(module, "HANDLER_TYPE", None)
        handler_cls = getattr(module, "HANDLER_CLASS", None)

        if not handler_type or not handler_cls:
            logger.debug("Module '%s' does not expose HANDLER_TYPE/HANDLER_CLASS", full_name)
            continue

        if not issubclass(handler_cls, BaseSourceHandler):
            logger.warning(
                "Handler '%s' must extend BaseSourceHandler; skipping", full_name
            )
            continue

        registry[handler_type] = handler_cls
        logger.info("Registered handler '%s' from %s", handler_type, full_name)

    return registry

# Service

class DataIndexerService:
    """Coordinates handler instantiation and scheduling."""

    def __init__(self, config_path: Path, handlers_package: str):
        self.config_path = config_path
        self.handlers_package = handlers_package
        self.registry = discover_handlers(handlers_package)
        self.handlers: list[BaseSourceHandler] = []

    def load_handlers(self) -> None:
        if not self.registry:
            logger.warning("No handlers discovered in package '%s'", self.handlers_package)

        config = load_json(self.config_path)
        sources = config.get("sources", [])
        if not sources:
            raise ValueError("No data sources defined in configuration")

        for source in sources:
            try:
                handler = self._create_handler(source)
            except Exception as exc:
                logger.error("Failed to configure source '%s': %s", source.get("id"), exc)
                continue

            if handler:
                self.handlers.append(handler)
                logger.info(
                    "Configured source '%s' (%s) -> collection '%s' every %d min",
                    handler.config.id,
                    handler.config.type,
                    handler.config.collection,
                    handler.interval_minutes,
                )

    def _create_handler(self, cfg: Dict[str, Any]) -> Optional[BaseSourceHandler]:
        handler_type = cfg.get("type", "")
        handler_cls = self.registry.get(handler_type)
        if not handler_cls:
            logger.warning("No handler registered for type '%s'", handler_type)
            return None

        source_cfg = SourceConfig(
            id=cfg.get("id", "unnamed"),
            type=handler_type,
            collection=cfg.get("collection", "data"),
            interval_minutes=int(cfg.get("interval_minutes", 10)),
            settings=cfg.get("settings", {}),
        )
        return handler_cls(source_cfg)

    def run(self) -> None:
        if not self.handlers:
            logger.warning("No handlers loaded; nothing to do")
            return

        logger.info("Running initial update for %d handlers", len(self.handlers))
        for handler in self.handlers:
            handler.run()

        for handler in self.handlers:
            schedule.every(handler.interval_minutes).minutes.do(handler.run)

        logger.info("Scheduled all handlers; entering loop")
        while True:
            try:
                schedule.run_pending()
                time.sleep(30)
            except KeyboardInterrupt:
                logger.info("Data Indexer stopping")
                break
            except Exception as exc:
                logger.error("Error in scheduler loop: %s", exc)
                time.sleep(60)

# Entrypoint

def main() -> int:
    logger.info("="*60)
    logger.info("Data Indexer Service")
    logger.info("="*60)
    logger.info("Embeddings API: %s", EMBEDDINGS_API)
    logger.info("Qdrant API: %s", QDRANT_API)
    logger.info("Config path: %s", CONFIG_PATH)
    logger.info("="*60)

    configure_endpoints(EMBEDDINGS_API, QDRANT_API)

    service = DataIndexerService(CONFIG_PATH, HANDLERS_PACKAGE)
    service.load_handlers()
    service.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
