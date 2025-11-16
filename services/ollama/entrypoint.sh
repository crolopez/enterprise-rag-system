#!/bin/bash

# Start Ollama in the background
/bin/ollama serve &

# Get the Ollama process PID
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "Waiting for Ollama to be ready..."
for i in {1..60}; do
  if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Ollama is ready!"
    break
  fi
  echo "Waiting... ($i/60)"
  sleep 1
done

# Pull the model if OLLAMA_MODEL is set
if [ -n "$OLLAMA_MODEL" ]; then
  echo "Pulling model: $OLLAMA_MODEL"
  /bin/ollama pull "$OLLAMA_MODEL"
  if [ $? -eq 0 ]; then
    echo "Model pulled successfully: $OLLAMA_MODEL"
  else
    echo "Warning: Failed to pull model $OLLAMA_MODEL (may retry on demand)"
  fi
else
  echo "OLLAMA_MODEL not set, skipping automatic model pull"
fi

# Keep Ollama running in foreground
wait $OLLAMA_PID
