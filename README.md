# UnifyOps Core

UnifyOps Core is a platform for operations management and infrastructure automation.

## Components

### Backend API

The backend API is built using FastAPI, a modern Python framework for building APIs. It provides a RESTful interface for the UnifyOps platform.

## Local Development

### Prerequisites

- Python 3.8+
- PostgreSQL (or use the SQLite default for development)
- Docker and Docker Compose (for containerized deployment)

### Setup

1. Clone the repository
2. Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up environment variables (using .env.local for local development)
4. Run database migrations:

```bash
alembic upgrade head
```

5. Start the development server:

```bash
uvicorn app.main:app --reload
```

## Deployment

The project supports multiple deployment methods:

- Docker container deployment
- AWS ECS deployment (using Terraform infrastructure in /tf directory)

## Project Structure

```
unifyops-core/
├── app/                # FastAPI backend application
│   ├── core/           # Core functionality (config, logging, exceptions)
│   ├── db/             # Database models and initialization
│   ├── models/         # SQLAlchemy ORM models
│   ├── routers/        # API route definitions
│   ├── schemas/        # Pydantic models for request/response validation
│   └── main.py         # Application entry point
├── alembic/            # Database migration scripts
├── logs/               # Application logs
│   └── background_tasks/ # Background task execution logs
├── scripts/            # Utility scripts
├── tf/                 # Terraform infrastructure as code
├── docker/             # Docker configuration files
├── .github/            # GitHub Actions workflows
└── Makefile            # Build and deployment automation
```

## Makefile Commands

The project includes a Makefile to simplify common tasks. Use `make help` to see available commands.

## Background Task Logging

The system includes a log viewer script to help you read and monitor task logs:

```bash
./read_task_logs.py --list
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and ensure they pass
5. Submit a pull request
