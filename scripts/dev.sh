#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Starting UnifyOps Core Development Environment ===${NC}"

# Check if .env.local exists and copy from .env.dev if not
if [ ! -f .env.local ]; then
    echo -e "${GREEN}Creating .env.local from .env.dev...${NC}"
    cp .env.dev .env.local
    echo "# Local overrides" >> .env.local
    echo "Created .env.local - feel free to customize it for your local environment."
fi

# Build the containers if not built already
if ! docker images | grep -q "unifyops-core.*dev"; then
    echo -e "${GREEN}Building Docker images...${NC}"
    make docker-build-dev
fi

# Start the containers
echo -e "${GREEN}Starting development containers...${NC}"
ENV=dev make docker-up

echo -e "${BLUE}=== Development Environment Started ===${NC}" 