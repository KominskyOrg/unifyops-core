.PHONY: help install dev test lint format clean docker-build docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make install       Install development dependencies"
	@echo "  make dev           Run the API in development mode"
	@echo "  make test          Run tests"
	@echo "  make lint          Run linting checks"
	@echo "  make format        Format code"
	@echo "  make clean         Remove cache and temporary files"
	@echo "  make docker-build  Build the Docker container"
	@echo "  make docker-up     Start the Docker container"
	@echo "  make docker-down   Stop the Docker container"

install:
	pip install -r requirements.txt
	pip install -e .

dev:
	./scripts/dev.sh

test:
	./scripts/dev.sh --test --no-docker

ci-test:
	python -m pytest app/tests/ -v

lint:
	./scripts/dev.sh --lint

format:
	black app/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov/

docker-build:
	docker-compose build

docker-up:
	docker-compose up

docker-down:
	docker-compose down 