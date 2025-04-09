#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Creating Resources Table ===${NC}"

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Get database connection parameters
DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-postgres}
DB_NAME=${DB_NAME:-unifyops}

# Print info
echo -e "${GREEN}Using database: $DB_NAME on $DB_HOST:$DB_PORT${NC}"

# Execute SQL file
echo -e "${GREEN}Running SQL script to create resources table...${NC}"
export PGPASSWORD=$DB_PASSWORD

# Check if inside Docker (if psql is available)
if [ -x "$(command -v psql)" ]; then
    echo -e "${GREEN}Using local psql client${NC}"
    psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f scripts/create_resources_table.sql
else
    echo -e "${YELLOW}Local psql not found, trying via Docker...${NC}"
    # Try with docker exec
    if [ -x "$(command -v docker)" ]; then
        echo -e "${GREEN}Using docker exec to run psql${NC}"
        docker exec -i $(docker ps -qf "name=db") psql -U $DB_USER -d $DB_NAME -c "$(cat scripts/create_resources_table.sql)"
    else
        echo -e "${RED}Neither psql nor docker are available${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}=== Resources Table Creation Complete ===${NC}" 