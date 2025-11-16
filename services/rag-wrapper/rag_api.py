#!/usr/bin/env python3
"""Ollama-compatible API wrapper with RAG"""
from flask import Flask, request, jsonify, Response
import requests
import json

app = Flask(__name__)

OLLAMA_URL = "http://ollama:11434"
QDRANT_URL = "http://qdrant:6333"
EMBEDDINGS_URL = "http://embeddings:80/embed"

def get_rag_context(query):
    """Get context from Qdrant"""
    try:
        import unicodedata

        # Normalize unicode characters for embeddings service
        # Replace special characters while keeping meaning
        normalized = query.replace("¿", "").replace("?", "").lower()
        # Remove accents for embeddings compatibility
        normalized = ''.join(
            c for c in unicodedata.normalize('NFD', normalized)
            if unicodedata.category(c) != 'Mn'
        )

        resp = requests.post(EMBEDDINGS_URL,
            json={"inputs": [normalized]}, timeout=30)
        if resp.status_code != 200:
            return None
        embeddings = resp.json()[0]

        resp = requests.post(
            f"{QDRANT_URL}/collections/documents/points/search",
            json={"vector": embeddings, "limit": 2, "with_payload": True},
            timeout=10)

        if resp.status_code != 200:
            return None

        docs = []
        for hit in resp.json().get("result", []):
            if "content" in hit["payload"]:
                docs.append(hit["payload"]["content"])

        return "\n\n".join(docs) if docs else None
    except Exception as e:
        import sys
        print(f"RAG Error: {e}", file=sys.stderr)
        return None

@app.route("/api/generate", methods=["POST"])
def generate():
    """Ollama-compatible generate endpoint with RAG"""
    data = request.json
    prompt = data.get("prompt", "")

    # Try to add RAG context
    context = get_rag_context(prompt)
    if context:
        data["prompt"] = f"INFORMACION:\n{context}\n\n---\n\nBasandote en la informacion anterior:\n{prompt}"

    # Forward to Ollama (timeout=600 to allow model download on first request)
    resp = requests.post(f"{OLLAMA_URL}/api/generate", json=data, timeout=600)
    return resp.json()

@app.route("/api/chat", methods=["POST"])
def chat_with_rag():
    """Ollama-compatible chat endpoint with RAG"""
    data = request.json
    messages = data.get("messages", [])

    # Extract the last user message as the query
    prompt_for_rag = ""
    if messages and isinstance(messages, list):
        for msg in reversed(messages):
            if msg.get("role") == "user":
                prompt_for_rag = msg.get("content", "")
                break

    # Try to add RAG context to the last user message
    if prompt_for_rag:
        context = get_rag_context(prompt_for_rag)
        if context:
            # Inject context into the last user message
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    original_content = msg.get("content", "")
                    msg["content"] = f"[Context Information]\n{context}\n\n[Question]\n{original_content}"
                    break

    # Forward to Ollama
    resp = requests.post(f"{OLLAMA_URL}/api/chat", json=data, timeout=600)

    # Check response status
    if resp.status_code >= 400:
        # For error responses, try to parse JSON, otherwise return error
        try:
            return Response(resp.json(), mimetype='application/json')
        except:
            return {"error": "Failed to get response from Ollama"}, resp.status_code

    # Handle both JSON and streaming responses
    try:
        return resp.json()
    except:
        # If JSON parsing fails, return raw response as is
        # This handles streaming responses with multiple JSON objects
        return Response(resp.text, mimetype='application/json')

@app.route("/api/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy(path):
    """Proxy all other requests to Ollama"""
    url = f"{OLLAMA_URL}/api/{path}"

    if request.method == "GET":
        resp = requests.get(url, timeout=30)
    elif request.method == "POST":
        resp = requests.post(url, json=request.json, timeout=600)
    elif request.method == "PUT":
        resp = requests.put(url, json=request.json, timeout=30)
    else:
        resp = requests.delete(url, timeout=30)

    try:
        return resp.json()
    except:
        return resp.text

@app.route("/health", methods=["GET"])
def health():
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return {"status": "ok"}
    except:
        return {"status": "error"}, 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=11436, debug=False)
