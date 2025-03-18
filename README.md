# UnifyOps Core

UnifyOps Core is a platform for operations management and automation.

## Components

### Backend API

The backend API is built using FastAPI, a modern Python framework for building APIs. It provides a RESTful interface for the UnifyOps platform.

- [Backend API Documentation](backend/README.md)
- [Docker Deployment Guide](docs/docker-deployment-setup.md)

## Local Development

Each component has its own local development environment:

- [Backend API Local Development](backend/README.md#local-development-setup)

## Deployment

The project includes GitHub Actions workflows for automated deployment:

- [Backend Deployment to EC2](docs/docker-deployment-setup.md)

## Project Structure

```
unifyops-core/
├── backend/             # FastAPI backend application
├── docs/                # Documentation files
├── scripts/             # Utility scripts
├── .github/             # GitHub Actions workflows
└── README.md            # This file
```

## Getting Started

1. Clone the repository
2. Follow the setup instructions in the specific component's README

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and ensure they pass
5. Submit a pull request
