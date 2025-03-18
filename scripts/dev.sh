#!/bin/bash
# Development script for local setup and running

set -e

# Default options
USE_DOCKER=true
CLEAN=false
INSTALL=false
TEST=false
LINT=false
PORT=8000
HOST="0.0.0.0"

# Help message
function show_help {
  echo "UnifyOps Core Development Script"
  echo ""
  echo "Usage: ./scripts/dev.sh [options]"
  echo ""
  echo "Options:"
  echo "  --no-docker     Run directly with Python instead of Docker"
  echo "  --clean         Clean cached files before running"
  echo "  --install       Install dependencies"
  echo "  --test          Run tests"
  echo "  --lint          Run linting checks"
  echo "  --port PORT     Specify port (default: 8000)"
  echo "  --host HOST     Specify host (default: 0.0.0.0)"
  echo "  --help          Show this help message"
  echo ""
  exit 0
}

# Process arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-docker)
      USE_DOCKER=false
      shift
      ;;
    --clean)
      CLEAN=true
      shift
      ;;
    --install)
      INSTALL=true
      shift
      ;;
    --test)
      TEST=true
      shift
      ;;
    --lint)
      LINT=true
      shift
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --host)
      HOST="$2"
      shift 2
      ;;
    --help)
      show_help
      ;;
    *)
      echo "Unknown option: $1"
      show_help
      ;;
  esac
done

# Set up the Python path
# Navigate to the project root directory
cd "$(dirname "$0")/.."
export PYTHONPATH=$PWD

# Clean if requested
if [ "$CLEAN" = true ]; then
  echo "🧹 Cleaning up cached files..."
  find . -type d -name "__pycache__" -exec rm -rf {} +
  find . -type d -name ".pytest_cache" -exec rm -rf {} +
  find . -type f -name "*.pyc" -delete
  rm -rf .coverage htmlcov/
fi

# Install dependencies if requested
if [ "$INSTALL" = true ]; then
  echo "📦 Installing dependencies..."
  if [ -d "venv" ]; then
    # Activate virtual environment if it exists
    source venv/bin/activate
  else
    # Create and activate virtual environment
    echo "Creating virtual environment..."
    python -m venv venv
    source venv/bin/activate
  fi
  pip install -r requirements.txt
  pip install -e .
fi

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Run tests if requested
if [ "$TEST" = true ]; then
  echo "🧪 Running tests..."
  if [ "$USE_DOCKER" = true ]; then
    if command_exists docker-compose; then
      docker-compose run --rm api pytest app/tests/ -v
    else
      echo "Warning: docker-compose not found, falling back to local testing."
      python -m pytest app/tests/ -v
    fi
  else
    python -m pytest app/tests/ -v
  fi
fi

# Run linting if requested
if [ "$LINT" = true ]; then
  echo "🔍 Running linting checks..."
  if [ ! -f ".flake8" ]; then
    echo "Creating .flake8 configuration..."
    cat > .flake8 << EOF
[flake8]
max-line-length = 100
exclude = .git,__pycache__,build,dist,venv
ignore = E203, W503
EOF
  fi
  
  if [ ! -f "pyproject.toml" ]; then
    echo "Creating pyproject.toml for Black..."
    cat > pyproject.toml << EOF
[tool.black]
line-length = 100
target-version = ['py310']
include = '\.pyi?$'
exclude = '''
/(
    \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | venv
  | _build
  | buck-out
  | build
  | dist
)/
'''
EOF
  fi
  
  if [ "$USE_DOCKER" = true ]; then
    docker-compose run --rm api sh -c "pip install flake8 black && flake8 app/ && black app/ --check"
  else
    pip install flake8 black
    flake8 app/
    black app/ --check
  fi
fi

# Start the application
if [ "$TEST" = false ] && [ "$LINT" = false ]; then
  echo "🚀 Starting the application..."
  if [ "$USE_DOCKER" = true ]; then
    echo "Using Docker Compose..."
    docker-compose up
  else
    echo "Using local Python..."
    uvicorn app.main:app --reload --host "$HOST" --port "$PORT"
  fi
fi 
