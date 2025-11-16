FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck and requests for HTTP calls
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir requests

# Copy configurator script
COPY services/openwebui-config/app.py ./app.py

# Run configurator
CMD ["python", "app.py"]
