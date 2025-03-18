.PHONY: help install dev test lint format clean docker-build docker-up docker-down ci-ecr-push

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