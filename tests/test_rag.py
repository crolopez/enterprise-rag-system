#!/usr/bin/env python3
"""
Enterprise RAG System - Integration Tests

Tests for the complete RAG pipeline and individual components.
"""

import requests
import json
import time
from typing import List, Dict
import unittest


class TestRAGSystem(unittest.TestCase):
    """Test suite for RAG system components"""

    # Service endpoints
    OLLAMA_URL = "http://localhost:32101"
    QDRANT_URL = "http://localhost:6333"
    EMBEDDINGS_URL = "http://localhost:8080"
    MINIO_URL = "http://localhost:9000"
    WEBUI_URL = "http://localhost:3000"

    @classmethod
    def setUpClass(cls):
        """Setup test fixtures"""
        # Wait for services to be ready
        cls._wait_for_services()

    @classmethod
    def _wait_for_services(cls, timeout=60):
        """Wait for all services to be healthy"""
        services = [
            ("Ollama", f"{cls.OLLAMA_URL}/api/tags"),
            ("Qdrant", f"{cls.QDRANT_URL}/health"),
            ("Embeddings", f"{cls.EMBEDDINGS_URL}/health"),
            ("MinIO", f"{cls.MINIO_URL}/minio/health/live"),
        ]

        start_time = time.time()
        for service_name, url in services:
            while time.time() - start_time < timeout:
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code in [200, 204]:
                        print(f"✓ {service_name} is ready")
                        break
                except requests.exceptions.RequestException:
                    time.sleep(2)
            else:
                raise RuntimeError(f"Service {service_name} failed to start")

    # ============================================================================
    # Ollama Tests
    # ============================================================================

    def test_ollama_health(self):
        """Test Ollama service health"""
        response = requests.get(f"{self.OLLAMA_URL}/api/tags")
        self.assertEqual(response.status_code, 200)
        self.assertIn("models", response.json())

    def test_ollama_list_models(self):
        """Test listing available Ollama models"""
        response = requests.get(f"{self.OLLAMA_URL}/api/tags")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data["models"], list)

    def test_ollama_generate(self):
        """Test Ollama text generation"""
        prompt = "What is artificial intelligence?"
        response = requests.post(
            f"{self.OLLAMA_URL}/api/generate",
            json={
                "model": "llama2",
                "prompt": prompt,
                "stream": False,
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            self.assertIn("response", data)
            self.assertGreater(len(data["response"]), 0)
        else:
            # Skip if model not available
            self.skipTest("llama2 model not available")

    # ============================================================================
    # Qdrant Tests
    # ============================================================================

    def test_qdrant_health(self):
        """Test Qdrant service health"""
        response = requests.get(f"{self.QDRANT_URL}/health")
        self.assertEqual(response.status_code, 200)

    def test_qdrant_create_collection(self):
        """Test creating a Qdrant collection"""
        collection_name = "test_collection"

        # Create collection
        response = requests.put(
            f"{self.QDRANT_URL}/collections/{collection_name}?timeout=30",
            json={
                "vectors": {
                    "size": 1024,
                    "distance": "Cosine"
                }
            }
        )

        # Should return 200 or already exists error
        self.assertIn(response.status_code, [200, 400, 409])

        # Check collection exists
        response = requests.get(f"{self.QDRANT_URL}/collections")
        self.assertEqual(response.status_code, 200)

        # Cleanup
        requests.delete(f"{self.QDRANT_URL}/collections/{collection_name}")

    def test_qdrant_insert_vectors(self):
        """Test inserting vectors into Qdrant"""
        collection_name = "test_vectors"

        # Create collection
        requests.put(
            f"{self.QDRANT_URL}/collections/{collection_name}?timeout=30",
            json={
                "vectors": {
                    "size": 1024,
                    "distance": "Cosine"
                }
            }
        )

        # Insert vectors
        vectors = [
            [0.1] * 1024,
            [0.2] * 1024,
            [0.3] * 1024,
        ]

        response = requests.put(
            f"{self.QDRANT_URL}/collections/{collection_name}/points",
            json={
                "points": [
                    {
                        "id": i,
                        "vector": vec,
                        "payload": {"text": f"Document {i}"}
                    }
                    for i, vec in enumerate(vectors)
                ]
            }
        )

        self.assertEqual(response.status_code, 200)

        # Cleanup
        requests.delete(f"{self.QDRANT_URL}/collections/{collection_name}")

    # ============================================================================
    # Embeddings Tests
    # ============================================================================

    def test_embeddings_health(self):
        """Test Embeddings service health"""
        response = requests.get(f"{self.EMBEDDINGS_URL}/health")
        self.assertEqual(response.status_code, 200)

    def test_embeddings_single(self):
        """Test generating single embedding"""
        response = requests.post(
            f"{self.EMBEDDINGS_URL}/embed",
            json={"inputs": "This is a test sentence"},
            timeout=30
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("embeddings", data)
        self.assertEqual(len(data["embeddings"]), 1)
        self.assertEqual(len(data["embeddings"][0]), 1024)

    def test_embeddings_batch(self):
        """Test generating batch embeddings"""
        texts = [
            "First document about machine learning",
            "Second document about neural networks",
            "Third document about deep learning",
        ]

        response = requests.post(
            f"{self.EMBEDDINGS_URL}/embed",
            json={"inputs": texts},
            timeout=30
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("embeddings", data)
        self.assertEqual(len(data["embeddings"]), 3)
        for embedding in data["embeddings"]:
            self.assertEqual(len(embedding), 1024)

    # ============================================================================
    # RAG Pipeline Tests
    # ============================================================================

    def test_rag_pipeline(self):
        """Test complete RAG pipeline"""
        query = "What is machine learning?"
        collection_name = "rag_test"

        # 1. Create collection
        requests.put(
            f"{self.QDRANT_URL}/collections/{collection_name}?timeout=30",
            json={
                "vectors": {
                    "size": 1024,
                    "distance": "Cosine"
                }
            }
        )

        # 2. Generate embedding for documents
        documents = [
            "Machine learning is a branch of artificial intelligence",
            "Deep learning uses neural networks with multiple layers",
            "Natural language processing is a subfield of AI",
        ]

        embed_response = requests.post(
            f"{self.EMBEDDINGS_URL}/embed",
            json={"inputs": documents},
            timeout=30
        )
        self.assertEqual(embed_response.status_code, 200)
        embeddings = embed_response.json()["embeddings"]

        # 3. Insert vectors into Qdrant
        points = [
            {
                "id": i,
                "vector": embedding,
                "payload": {"text": doc, "document_id": f"doc_{i}"}
            }
            for i, (embedding, doc) in enumerate(zip(embeddings, documents))
        ]

        insert_response = requests.put(
            f"{self.QDRANT_URL}/collections/{collection_name}/points",
            json={"points": points}
        )
        self.assertEqual(insert_response.status_code, 200)

        # 4. Search for similar documents
        query_embed_response = requests.post(
            f"{self.EMBEDDINGS_URL}/embed",
            json={"inputs": query},
            timeout=30
        )
        query_embedding = query_embed_response.json()["embeddings"][0]

        search_response = requests.post(
            f"{self.QDRANT_URL}/collections/{collection_name}/points/search",
            json={
                "vector": query_embedding,
                "limit": 2,
                "score_threshold": 0.0
            }
        )

        self.assertEqual(search_response.status_code, 200)
        results = search_response.json()["result"]
        self.assertGreater(len(results), 0)
        self.assertIn("payload", results[0])
        self.assertIn("text", results[0]["payload"])

        # Cleanup
        requests.delete(f"{self.QDRANT_URL}/collections/{collection_name}")

    # ============================================================================
    # Performance Tests
    # ============================================================================

    def test_embedding_performance(self):
        """Test embedding generation performance"""
        texts = ["Test document"] * 10
        start_time = time.time()

        response = requests.post(
            f"{self.EMBEDDINGS_URL}/embed",
            json={"inputs": texts},
            timeout=60
        )

        elapsed = time.time() - start_time

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 10, "Batch embedding took too long")
        print(f"Generated 10 embeddings in {elapsed:.2f} seconds")

    def test_search_performance(self):
        """Test vector search performance"""
        collection_name = "perf_test"

        # Setup
        requests.put(
            f"{self.QDRANT_URL}/collections/{collection_name}?timeout=30",
            json={"vectors": {"size": 1024, "distance": "Cosine"}}
        )

        # Insert vectors
        points = [
            {
                "id": i,
                "vector": [(i % 10) * 0.1] * 1024,
                "payload": {"text": f"Document {i}"}
            }
            for i in range(100)
        ]
        requests.put(
            f"{self.QDRANT_URL}/collections/{collection_name}/points",
            json={"points": points}
        )

        # Search
        start_time = time.time()
        for _ in range(10):
            requests.post(
                f"{self.QDRANT_URL}/collections/{collection_name}/points/search",
                json={"vector": [0.5] * 1024, "limit": 5}
            )

        elapsed = time.time() - start_time

        # Cleanup
        requests.delete(f"{self.QDRANT_URL}/collections/{collection_name}")

        self.assertLess(elapsed, 5, "10 searches took too long")
        print(f"Performed 10 searches in {elapsed:.2f} seconds")


class TestAPIIntegration(unittest.TestCase):
    """Integration tests for API endpoints"""

    WEBUI_URL = "http://localhost:3000"

    def test_webui_health(self):
        """Test Web UI accessibility"""
        try:
            response = requests.get(self.WEBUI_URL, timeout=5)
            # Page should be accessible (200 or 404 is OK, service is running)
            self.assertIn(response.status_code, [200, 302, 404])
        except requests.exceptions.ConnectionError:
            self.skipTest("Web UI not accessible")


def run_tests():
    """Run all tests"""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    run_tests()
