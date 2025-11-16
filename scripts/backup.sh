#!/bin/bash

# Enterprise RAG System - Backup Script
# Creates backups of Qdrant vectors and MinIO documents

set -e

# Configuration
BACKUP_DIR="${1:-./_backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="enterprise-rag-backup-${TIMESTAMP}"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Function to create backup directory
init_backup_dir() {
    mkdir -p "${BACKUP_DIR}"
    echo -e "${GREEN}✓ Backup directory ready: ${BACKUP_DIR}${NC}"
}

# Function to backup Qdrant
backup_qdrant() {
    local backup_file="${BACKUP_DIR}/${BACKUP_NAME}-qdrant.tar.gz"

    echo -e "${BLUE}Backing up Qdrant vectors...${NC}"

    if docker-compose exec -T qdrant tar czf /tmp/qdrant-backup.tar.gz -C /qdrant/storage . 2>/dev/null; then
        docker cp enterprise-rag-qdrant:/tmp/qdrant-backup.tar.gz "${backup_file}"
        docker exec enterprise-rag-qdrant rm /tmp/qdrant-backup.tar.gz

        local size=$(du -h "${backup_file}" | cut -f1)
        echo -e "${GREEN}✓ Qdrant backup created: $(basename ${backup_file}) (${size})${NC}"
    else
        echo -e "${RED}✗ Qdrant backup failed${NC}"
        return 1
    fi
}

# Function to backup MinIO
backup_minio() {
    local backup_file="${BACKUP_DIR}/${BACKUP_NAME}-minio.tar.gz"

    echo -e "${BLUE}Backing up MinIO documents...${NC}"

    if docker-compose exec -T minio tar czf /tmp/minio-backup.tar.gz -C /data . 2>/dev/null; then
        docker cp enterprise-rag-minio:/tmp/minio-backup.tar.gz "${backup_file}"
        docker exec enterprise-rag-minio rm /tmp/minio-backup.tar.gz

        local size=$(du -h "${backup_file}" | cut -f1)
        echo -e "${GREEN}✓ MinIO backup created: $(basename ${backup_file}) (${size})${NC}"
    else
        echo -e "${RED}✗ MinIO backup failed${NC}"
        return 1
    fi
}

# Function to backup configuration
backup_config() {
    echo -e "${BLUE}Backing up configuration...${NC}"

    tar -czf "${BACKUP_DIR}/${BACKUP_NAME}-config.tar.gz" \
        .env \
        docker-compose.yml \
        config/ \
        2>/dev/null || true

    echo -e "${GREEN}✓ Configuration backup created${NC}"
}

# Function to list backups
list_backups() {
    echo ""
    echo -e "${BLUE}Available backups:${NC}"
    echo ""

    if [ -d "${BACKUP_DIR}" ] && [ "$(ls -A ${BACKUP_DIR})" ]; then
        ls -lh "${BACKUP_DIR}" | tail -n +2 | \
            awk '{printf "%-40s %10s %s\n", $9, $5, $6" "$7" "$8}'
    else
        echo "No backups found"
    fi
}

# Function to restore backup
restore_backup() {
    local backup_prefix=$1

    if [ -z "$backup_prefix" ]; then
        echo -e "${RED}Error: Please specify backup to restore${NC}"
        echo "Usage: $0 restore <backup_prefix>"
        return 1
    fi

    echo -e "${YELLOW}Restoring from: ${backup_prefix}${NC}"
    echo -e "${YELLOW}This will overwrite existing data!${NC}"
    read -p "Continue? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        echo "Cancelled"
        return 0
    fi

    # Restore Qdrant
    if [ -f "${BACKUP_DIR}/${backup_prefix}-qdrant.tar.gz" ]; then
        echo -e "${BLUE}Restoring Qdrant...${NC}"
        docker-compose exec -T qdrant rm -rf /qdrant/storage/collections
        docker cp "${BACKUP_DIR}/${backup_prefix}-qdrant.tar.gz" enterprise-rag-qdrant:/tmp/
        docker exec -T enterprise-rag-qdrant tar xzf /tmp/qdrant-backup.tar.gz -C /qdrant/storage
        echo -e "${GREEN}✓ Qdrant restored${NC}"
    fi

    # Restore MinIO
    if [ -f "${BACKUP_DIR}/${backup_prefix}-minio.tar.gz" ]; then
        echo -e "${BLUE}Restoring MinIO...${NC}"
        docker-compose exec -T minio rm -rf /data/*
        docker cp "${BACKUP_DIR}/${backup_prefix}-minio.tar.gz" enterprise-rag-minio:/tmp/
        docker exec -T enterprise-rag-minio tar xzf /tmp/minio-backup.tar.gz -C /data
        echo -e "${GREEN}✓ MinIO restored${NC}"
    fi

    echo -e "${GREEN}Restore complete!${NC}"
}

# Function to cleanup old backups
cleanup_old() {
    local keep_days=${1:-7}

    echo -e "${BLUE}Cleaning up backups older than ${keep_days} days...${NC}"

    if [ -d "${BACKUP_DIR}" ]; then
        find "${BACKUP_DIR}" -type f -mtime +${keep_days} -delete
        echo -e "${GREEN}✓ Cleanup complete${NC}"
    fi
}

# Main function
main() {
    local command=${1:-backup}

    case "$command" in
        backup)
            echo "╔════════════════════════════════════════════════════════════╗"
            echo "║        Enterprise RAG System - Backup Process             ║"
            echo "╚════════════════════════════════════════════════════════════╝"
            echo ""
            init_backup_dir
            backup_qdrant
            backup_minio
            backup_config
            list_backups
            echo ""
            echo -e "${GREEN}Backup completed successfully!${NC}"
            ;;

        restore)
            restore_backup "$2"
            ;;

        list)
            list_backups
            ;;

        cleanup)
            cleanup_old "${2:-7}"
            ;;

        *)
            echo "Usage: $0 {backup|restore|list|cleanup} [options]"
            echo ""
            echo "Commands:"
            echo "  backup          - Create new backup (default)"
            echo "  restore <name>  - Restore from backup"
            echo "  list            - List available backups"
            echo "  cleanup [days]  - Delete backups older than N days (default: 7)"
            echo ""
            echo "Examples:"
            echo "  $0 backup"
            echo "  $0 list"
            echo "  $0 restore enterprise-rag-backup-20240101_120000"
            echo "  $0 cleanup 30"
            exit 1
            ;;
    esac
}

# Run main
main "$@"
