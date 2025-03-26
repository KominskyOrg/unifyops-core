.PHONY: help install dev test lint format clean docker-build docker-up docker-down ci-ecr-push docker-logs docker-shell docker-restart docker-prune docker-test docker-lint

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
	@echo "  make ci-ecr-push   Push the Docker container to ECR"
	@echo "  make docker-logs   View the Docker container logs"
	@echo "  make docker-shell  Get a shell into the running container"
	@echo "  make docker-restart Restart the Docker containers"
	@echo "  make docker-prune  Remove unused Docker resources"
	@echo "  make docker-test   Run tests inside Docker"
	@echo "  make docker-lint   Run linting inside Docker"

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

# CI-friendly alternative that doesn't use docker-compose
ci-docker-build:
	docker build -t unifyops-api:latest \
		--build-arg ENV=${ENV:-development} \
		--build-arg BUILD_TIMESTAMP=$(shell date +%Y%m%d%H%M%S) \
		.

docker-up:
	docker-compose up

docker-down:
	docker-compose down

# ECR-specific target for CI environments
ci-ecr-push:
	@echo "Pushing to ECR repository: $(ECR_REGISTRY)/$(ECR_REPOSITORY):$(IMAGE_TAG)"
	@echo "Checking AWS ECR login..."
	aws ecr get-login-password --region $${AWS_REGION} | docker login --username AWS --password-stdin $(ECR_REGISTRY)
	@echo "Tagging image..."
	docker tag unifyops-api:latest $(ECR_REGISTRY)/$(ECR_REPOSITORY):$(IMAGE_TAG)
	@echo "Pushing image..."
	docker push $(ECR_REGISTRY)/$(ECR_REPOSITORY):$(IMAGE_TAG)
	@echo "Verifying image exists in ECR..."
	aws ecr describe-images --repository-name $(ECR_REPOSITORY) --image-ids imageTag=$(IMAGE_TAG)

docker-logs:
	docker-compose logs -f

docker-shell:
	docker-compose exec api /bin/bash

docker-restart:
	docker-compose restart

docker-prune:
	docker system prune -f
	docker volume prune -f

docker-test:
	docker-compose run --rm api pytest app/tests/ -v

docker-lint:
	docker-compose run --rm api black --check app/