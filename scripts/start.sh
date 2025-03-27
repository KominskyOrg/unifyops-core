#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
# Use PYTHONPATH to ensure 'app' module can be found
export PYTHONPATH=$PYTHONPATH:/app
alembic upgrade head

# Start the application
echo "Starting application..."
if [ "$API_RELOAD" = "true" ]; then
    echo "Running in reload mode..."
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
    echo "Running in production mode..."
    uvicorn app.main:app --host 0.0.0.0 --port 8000
fi 