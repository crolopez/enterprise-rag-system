#!/usr/bin/env python3
"""
Open WebUI Document Uploader
Uploads weather documents to Open WebUI's knowledge base automatically
This ensures RAG works in the chat interface
"""

import os
import time
import logging
import requests
import base64
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
WEBUI_URL = os.getenv("WEBUI_URL", "http://webui:8080")
WEBUI_ADMIN_EMAIL = os.getenv("WEBUI_ADMIN_EMAIL", "admin@localhost")
WEBUI_ADMIN_PASSWORD = os.getenv("WEBUI_ADMIN_PASSWORD", "admin123")
MAX_RETRIES = 30
RETRY_DELAY = 2

# Documents to upload
DOCUMENTS = [
    {
        "path": "/app/weather_documents/madrid_weather.txt",
        "name": "Madrid Weather",
        "collection": "weather_data"
    },
    {
        "path": "/app/weather_documents/barcelona_weather.txt",
        "name": "Barcelona Weather",
        "collection": "weather_data"
    }
]


class OpenWebUIDocumentUploader:
    """Uploads documents to Open WebUI"""

    def __init__(self):
        self.webui_url = WEBUI_URL
        self.session = requests.Session()
        self.token = None

    def wait_for_webui(self) -> bool:
        """Wait for Open WebUI to be ready"""
        logger.info(f"Waiting for Open WebUI at {self.webui_url}")

        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(f"{self.webui_url}/", timeout=5)
                if response.status_code in [200, 301, 302]:
                    logger.info("Open WebUI is ready")
                    return True
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    logger.error(f"Open WebUI not ready: {e}")
                    return False
                time.sleep(RETRY_DELAY)

        return False

    def authenticate(self) -> bool:
        """Authenticate with Open WebUI"""
        try:
            logger.info("Authenticating with Open WebUI...")

            # Try to login
            response = self.session.post(
                f"{self.webui_url}/api/v1/auth/login",
                json={
                    "email": WEBUI_ADMIN_EMAIL,
                    "password": WEBUI_ADMIN_PASSWORD
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                logger.info("Authentication successful")
                return True
            else:
                logger.warning(f"Authentication failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    def upload_document(self, doc_info: dict) -> bool:
        """Upload a document to Open WebUI"""
        try:
            doc_path = doc_info["path"]
            doc_name = doc_info["name"]

            # Check if file exists
            if not Path(doc_path).exists():
                logger.warning(f"Document not found: {doc_path}")
                return False

            # Read file
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()

            logger.info(f"Uploading document: {doc_name} ({len(content)} bytes)")

            # Upload to Open WebUI using different endpoints
            endpoints = [
                # Try knowledge base endpoint
                {
                    "url": f"{self.webui_url}/api/v1/knowledge",
                    "method": "post",
                    "data": {
                        "filename": Path(doc_path).name,
                        "name": doc_name,
                        "content": content,
                    }
                },
                # Try documents endpoint
                {
                    "url": f"{self.webui_url}/api/v1/documents",
                    "method": "post",
                    "files": {
                        "file": (Path(doc_path).name, content, "text/plain")
                    }
                },
                # Try RAG documents endpoint
                {
                    "url": f"{self.webui_url}/api/v1/rag/documents",
                    "method": "post",
                    "json": {
                        "name": doc_name,
                        "content": content,
                    }
                }
            ]

            for endpoint in endpoints:
                try:
                    if endpoint["method"] == "post":
                        if "files" in endpoint:
                            response = self.session.post(
                                endpoint["url"],
                                files=endpoint["files"],
                                timeout=10
                            )
                        elif "json" in endpoint:
                            response = self.session.post(
                                endpoint["url"],
                                json=endpoint["json"],
                                timeout=10
                            )
                        else:
                            response = self.session.post(
                                endpoint["url"],
                                json=endpoint["data"],
                                timeout=10
                            )

                        if response.status_code in [200, 201]:
                            logger.info(f"Document uploaded successfully: {doc_name}")
                            return True
                except Exception as e:
                    continue

            logger.warning(f"Could not upload document via standard endpoints: {doc_name}")
            return False

        except Exception as e:
            logger.error(f"Error uploading document {doc_info['name']}: {e}")
            return False

    def upload_all_documents(self) -> int:
        """Upload all documents"""
        logger.info(f"Starting document upload for {len(DOCUMENTS)} documents")

        success_count = 0
        for doc_info in DOCUMENTS:
            if self.upload_document(doc_info):
                success_count += 1

        logger.info(f"Document upload complete: {success_count}/{len(DOCUMENTS)} uploaded")
        return success_count

    def inject_documents_to_qdrant(self) -> bool:
        """Directly inject documents to Qdrant (fallback method)"""
        try:
            logger.info("Injecting documents directly to Qdrant...")

            qdrant_url = os.getenv("QDRANT_API", "http://qdrant:6333")
            embeddings_url = os.getenv("EMBEDDINGS_API", "http://embeddings:80/embed")

            for doc_info in DOCUMENTS:
                doc_path = doc_info["path"]

                if not Path(doc_path).exists():
                    continue

                with open(doc_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Get embeddings
                response = requests.post(
                    embeddings_url,
                    json={"inputs": [content]},
                    timeout=30
                )

                if response.status_code != 200:
                    logger.warning(f"Failed to get embeddings for {doc_info['name']}")
                    continue

                embeddings = response.json()[0]

                # Upload to Qdrant
                import hashlib
                doc_id = int(hashlib.md5(
                    f"weather-{doc_info['name']}".encode()
                ).hexdigest(), 16) % (2**31)

                point = {
                    "id": doc_id,
                    "vector": embeddings,
                    "payload": {
                        "document_id": doc_id,
                        "filename": Path(doc_path).name,
                        "doc_name": doc_info['name'],
                        "content": content,
                        "source": "weather_data",
                        "type": "weather"
                    }
                }

                response = requests.put(
                    f"{qdrant_url}/collections/documents/points?wait=true",
                    json={"points": [point]},
                    timeout=10
                )

                if response.status_code in [200, 201]:
                    logger.info(f"Injected to Qdrant: {doc_info['name']}")

            return True

        except Exception as e:
            logger.error(f"Error injecting documents to Qdrant: {e}")
            return False

    def run(self) -> bool:
        """Run uploader"""
        logger.info("="*60)
        logger.info("OPEN WEBUI DOCUMENT UPLOADER")
        logger.info("="*60)

        if not self.wait_for_webui():
            logger.error("Open WebUI not ready")
            # Still try to inject to Qdrant as fallback
            self.inject_documents_to_qdrant()
            return False

        # Try to authenticate (may not be critical)
        self.authenticate()

        # Try to upload via API
        upload_count = self.upload_all_documents()

        # Also ensure documents are in Qdrant (critical for RAG)
        self.inject_documents_to_qdrant()

        logger.info("="*60)
        logger.info("DOCUMENT UPLOADER COMPLETE")
        logger.info("="*60)

        return True


def main():
    """Main entry point"""
    uploader = OpenWebUIDocumentUploader()
    success = uploader.run()
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
