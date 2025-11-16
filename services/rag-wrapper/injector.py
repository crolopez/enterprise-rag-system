#!/usr/bin/env python3
"""
RAG Prompt Injector - Intercepts Ollama requests and adds Qdrant context
This ensures RAG works automatically in Open WebUI
"""

import os
import json
import logging
import requests
import hashlib
from typing import Dict, Any, List
from flask import Flask, request, Response
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
EMBEDDINGS_URL = os.getenv("EMBEDDINGS_URL", "http://embeddings:80/embed")
PROXY_PORT = int(os.getenv("PROXY_PORT", "11435"))
COLLECTION_NAME = "documents"

app = Flask(__name__)


class RAGContextInjector:
    """Injects Qdrant context into prompts"""

    def __init__(self):
        self.ollama_url = OLLAMA_URL
        self.qdrant_url = QDRANT_URL
        self.embeddings_url = EMBEDDINGS_URL

    def search_context(self, query: str, limit: int = 2) -> List[str]:
        """Search for relevant documents in Qdrant"""
        try:
            # Get embeddings for the query
            response = requests.post(
                self.embeddings_url,
                json={"inputs": [query]},
                timeout=30
            )

            if response.status_code != 200:
                logger.warning(f"Failed to get embeddings: {response.status_code}")
                return []

            embeddings = response.json()[0]

            # Search in Qdrant
            response = requests.post(
                f"{self.qdrant_url}/collections/{COLLECTION_NAME}/points/search",
                json={
                    "vector": embeddings,
                    "limit": limit,
                    "with_payload": True,
                    "score_threshold": 0.3
                },
                timeout=10
            )

            if response.status_code != 200:
                logger.warning(f"Failed to search Qdrant: {response.status_code}")
                return []

            results = response.json()
            documents = []

            if "result" in results:
                for hit in results["result"]:
                    if "payload" in hit and "content" in hit["payload"]:
                        content = hit["payload"]["content"]
                        documents.append(content)

            return documents

        except Exception as e:
            logger.error(f"Error searching context: {e}")
            return []

    def inject_context(self, prompt: str) -> str:
        """Inject Qdrant context into prompt"""
        try:
            # Check if prompt is about weather
            weather_keywords = ["tiempo", "weather", "temperatura", "climate", "climático",
                              "madrid", "barcelona", "valencia", "españa", "spain",
                              "lluvia", "rain", "nublado", "cloudy", "soleado", "sunny"]

            query_lower = prompt.lower()
            is_weather_query = any(keyword in query_lower for keyword in weather_keywords)

            if not is_weather_query:
                return prompt

            # Search for relevant context
            documents = self.search_context(prompt)

            if not documents:
                return prompt

            # Build context
            context = "INFORMACIÓN RELEVANTE:\n\n"
            for doc in documents:
                context += doc + "\n\n"

            context += "---\n\n"

            # Inject context before the user's question
            injected_prompt = context + f"Basándote en la información anterior, responde: {prompt}"

            logger.info(f"Injected context for query: {prompt[:50]}...")
            return injected_prompt

        except Exception as e:
            logger.error(f"Error injecting context: {e}")
            return prompt

    def process_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Ollama request and inject context"""
        try:
            # Check if this is a generate request
            if data.get("stream") is False:  # Non-streaming request
                prompt = data.get("prompt", "")
                if prompt:
                    injected_prompt = self.inject_context(prompt)
                    data["prompt"] = injected_prompt

            return data

        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return data


injector = RAGContextInjector()


@app.route("/api/generate", methods=["POST"])
def generate():
    """Proxy /api/generate to Ollama with RAG injection"""
    try:
        data = request.json

        # Inject context
        data = injector.process_request(data)

        # Forward to Ollama
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=data,
            stream=data.get("stream", False),
            timeout=300
        )

        if data.get("stream"):
            # Stream response
            def generate_stream():
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        yield chunk

            return Response(generate_stream(), content_type=response.headers.get("content-type", "application/json"))
        else:
            # Non-stream response
            return response.json(), response.status_code

    except Exception as e:
        logger.error(f"Error in generate endpoint: {e}")
        return {"error": str(e)}, 500


@app.route("/api/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy(path):
    """Proxy all other requests to Ollama"""
    try:
        url = f"{OLLAMA_URL}/api/{path}"

        if request.method == "GET":
            response = requests.get(url, timeout=30)
        elif request.method == "POST":
            response = requests.post(url, json=request.json, timeout=30)
        elif request.method == "PUT":
            response = requests.put(url, json=request.json, timeout=30)
        elif request.method == "DELETE":
            response = requests.delete(url, timeout=30)

        return response.json(), response.status_code

    except Exception as e:
        logger.error(f"Error proxying request: {e}")
        return {"error": str(e)}, 500


@app.route("/health", methods=["GET"])
def health():
    """Health check"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            return {"status": "ok"}, 200
    except:
        pass

    return {"status": "error"}, 500


def main():
    """Main entry point"""
    logger.info("="*60)
    logger.info("RAG PROMPT INJECTOR")
    logger.info("="*60)
    logger.info(f"Ollama URL: {OLLAMA_URL}")
    logger.info(f"Qdrant URL: {QDRANT_URL}")
    logger.info(f"Embeddings URL: {EMBEDDINGS_URL}")
    logger.info(f"Proxy listening on port {PROXY_PORT}")
    logger.info("="*60)

    app.run(host="0.0.0.0", port=PROXY_PORT, debug=False)


if __name__ == "__main__":
    main()
