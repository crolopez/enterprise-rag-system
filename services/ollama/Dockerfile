FROM ollama/ollama:latest

# Install CA certificates and curl for better SSL support
RUN apt-get update && apt-get install -y ca-certificates curl && rm -rf /var/lib/apt/lists/*

# Copy entrypoint script
COPY services/ollama/entrypoint.sh /usr/local/bin/entrypoint.sh

# Make script executable
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
