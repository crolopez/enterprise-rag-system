#!/bin/bash

# Enterprise RAG System - Health Check Script
# Monitors and reports health status of all services

set -e

# Configuration
OLLAMA_API="http://localhost:32101"
QDRANT_API="http://localhost:6333"
EMBEDDINGS_API="http://localhost:8080"
MINIO_API="http://localhost:9000"
WEBUI_API="http://localhost:3000"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Function to check service health
check_health() {
    local service_name=$1
    local api_url=$2
    local health_endpoint=$3

    echo -n "Checking ${service_name}... "

    if response=$(curl -s -m 5 "${api_url}${health_endpoint}" 2>/dev/null); then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        return 1
    fi
}

# Function to get service stats
get_stats() {
    echo ""
    echo -e "${BLUE}Container Statistics:${NC}"
    echo ""
    docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.CPUPerc}}"
}

# Function to check disk space
check_disk() {
    echo ""
    echo -e "${BLUE}Disk Space:${NC}"
    echo ""
    docker exec enterprise-rag-qdrant df -h /qdrant/storage 2>/dev/null | tail -1 | \
        awk '{printf "Qdrant Storage: %s / %s (%s)\n", $3, $2, $5}'

    docker exec enterprise-rag-minio df -h /data 2>/dev/null | tail -1 | \
        awk '{printf "MinIO Storage:  %s / %s (%s)\n", $3, $2, $5}'
}

# Main health check
main() {
    clear
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║     Enterprise RAG System - Health Check Dashboard         ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo -e "${BLUE}Service Health Status:${NC}"
    echo ""

    check_health "Ollama" "${OLLAMA_API}" "/api/tags"
    check_health "Qdrant" "${QDRANT_API}" "/health"
    check_health "Embeddings" "${EMBEDDINGS_API}" "/health"
    check_health "MinIO" "${MINIO_API}" "/minio/health/live"
    check_health "Web UI" "${WEBUI_API}" "/health" 2>/dev/null || check_health "Web UI" "${WEBUI_API}" ""

    get_stats
    check_disk

    echo ""
    echo -e "${BLUE}Recent Logs:${NC}"
    echo ""
    docker-compose logs --tail=5 2>/dev/null | tail -20

    echo ""
    echo -e "${YELLOW}Tip: Run 'docker-compose logs -f' for live logs${NC}"
}

# Run main
main "$@"
