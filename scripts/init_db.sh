#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Database Initialization Script ===${NC}"

# Parse command line arguments
DIRECT_MODE=false
if [[ "$*" == *"--direct"* ]]; then
    DIRECT_MODE=true
    echo -e "${YELLOW}Direct table creation mode enabled${NC}"
fi

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Load environment variables if exists
if [ -f .env.local ]; then
    echo -e "${GREEN}Loading environment from .env.local${NC}"
    export $(grep -v '^#' .env.local | xargs)
elif [ -f .env.dev ]; then
    echo -e "${GREEN}Loading environment from .env.dev${NC}"
    export $(grep -v '^#' .env.dev | xargs)
fi

# Check if Docker is running
if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}Checking if PostgreSQL container is running...${NC}"
    
    if ! docker ps | grep -q "postgres"; then
        echo -e "${YELLOW}PostgreSQL container not found. Do you want to start docker-compose? (y/n)${NC}"
        read -r response
        if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            echo -e "${GREEN}Starting docker-compose...${NC}"
            docker-compose up -d db
            echo -e "${GREEN}Waiting for PostgreSQL to start...${NC}"
            sleep 5
        else
            echo "Continuing without starting PostgreSQL container."
        fi
    else
        echo -e "${GREEN}PostgreSQL container is running.${NC}"
    fi
else
    echo -e "${YELLOW}Docker not running. Make sure your database is accessible.${NC}"
fi

# Set up Python path
export PYTHONPATH=$PYTHONPATH:$(pwd)

echo -e "${GREEN}Running database initialization script...${NC}"
if [ "$DIRECT_MODE" = true ]; then
    python ./scripts/initialize_db.py --direct
else
    python ./scripts/initialize_db.py
fi

EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo -e "${RED}Initialization failed with exit code $EXIT_CODE${NC}"
    echo -e "${YELLOW}Trying again with direct table creation mode...${NC}"
    python ./scripts/initialize_db.py --direct
    EXIT_CODE=$?
    if [ $EXIT_CODE -ne 0 ]; then
        echo -e "${RED}Direct initialization also failed with exit code $EXIT_CODE${NC}"
        echo -e "${RED}=== Database Initialization Failed ===${NC}"
        exit $EXIT_CODE
    fi
fi

echo -e "${GREEN}=== Database Initialization Complete ===${NC}" 