# -----------------------------
# Refactored Makefile
# -----------------------------

.PHONY: help 
# Development Commands
.PHONY: install dev clean format init-db init-db-direct setup-db-permissions db-migration db-migrate
# Testing Commands
.PHONY: test lint coverage test-db-setup test-db-teardown
# Docker Commands
.PHONY: docker-build docker-up docker-down docker-logs docker-shell docker-exec docker-restart docker-prune
# CI/CD Commands
.PHONY: ci-build ci-test ci-lint ci-ecr-login ci-ecr-push ci-deploy
# Terraform Commands
.PHONY: tf-init tf-plan tf-apply tf-destroy tf-output
# ECS Utilities
.PHONY: ecs-status ecs-logs ecs-exec ecs-deploy ecs-rollback

# Environment variables with defaults
ENV ?= local
AWS_REGION ?= us-east-1
ECR_REPOSITORY ?= $(ENV)-unifyops-api-repo
ECR_REGISTRY ?= $(AWS_ACCOUNT).dkr.ecr.us-east-1.amazonaws.com
IMAGE_TAG ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo "latest")
TF_DIR ?= ./tf

# Help command
help:
	@echo "UnifyOps Core Makefile - Development Utilities"
	@echo ""
	@echo "DEVELOPMENT COMMANDS:"
	@echo "  make install       Install development dependencies"
	@echo "  make dev           Run the API in development mode"
	@echo "  make init-db       Initialize the database"
	@echo "  make init-db-direct Initialize the database directly"
	@echo "  make setup-db-permissions Set up database permissions"
	@echo "  make clean         Remove cache and temporary files"
	@echo "  make format        Format code with black"
	@echo "  make db-migration  Create a new database migration"
	@echo "  make db-migrate    Apply database migrations"
	@echo ""
	@echo "TESTING COMMANDS:"
	@echo "  make test          Run tests locally"
	@echo "  make lint          Run linting checks"
	@echo "  make coverage      Run tests with coverage report"
	@echo ""
	@echo "DOCKER COMMANDS:"
	@echo "  make docker-build  Build the Docker container"
	@echo "  make docker-up     Start containers in foreground"
	@echo "  make docker-up-d   Start containers in background"
	@echo "  make docker-down   Stop the containers"
	@echo "  make docker-logs   View container logs"
	@echo "  make docker-shell  Get a shell into the API container"
	@echo "  make docker-exec CMD=\"command\"  Execute command in API container"
	@echo "  make docker-restart Restart the containers"
	@echo "  make docker-prune  Remove unused Docker resources"
	@echo "  make docker-test   Run tests inside Docker"
	@echo "  make docker-lint   Run linting inside Docker"
	@echo ""
	@echo "CI/CD COMMANDS:"
	@echo "  make ci-build      Build container for CI"
	@echo "  make ci-test       Run tests for CI"
	@echo "  make ci-lint       Run linting for CI"
	@echo "  make ci-ecr-login  Login to ECR"
	@echo "  make ci-ecr-push   Push container to ECR"
	@echo "  make ci-deploy     Deploy to ECS"
	@echo ""
	@echo "TERRAFORM COMMANDS:"
	@echo "  make tf-init       Initialize Terraform"
	@echo "  make tf-plan       Plan Terraform changes"
	@echo "  make tf-apply      Apply Terraform changes"
	@echo "  make tf-destroy    Destroy Terraform resources"
	@echo "  make tf-output     Show Terraform outputs"
	@echo ""
	@echo "ECS UTILITIES:"
	@echo "  make ecs-status    Check ECS service status"
	@echo "  make ecs-logs      View ECS task logs"
	@echo "  make ecs-exec      Execute command in running ECS task"
	@echo "  make ecs-deploy    Deploy to ECS manually"
	@echo "  make ecs-rollback  Rollback to previous ECS deployment"
	@echo ""
	@echo "Environment: ${ENV}"

# ----- Development Commands -----

install:
	pip install -r requirements.txt
	pip install -e .
	pip install pytest pytest-cov black

dev:
	./scripts/dev.sh

init-db:
	./scripts/init_db.sh

init-db-direct:
	./scripts/init_db.sh --direct

setup-db-permissions:
	./scripts/setup_db_permissions.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov/ .terraform/ .terraform.lock.hcl

format:
	black app/

db-migration:
	@echo "Creating database migration via Docker..."
	@read -p "Enter migration name: " migration_name && \
	read -p "Is this a fresh migration (reset alembic history)? (y/n): " reset_history && \
	if [ "$$reset_history" = "y" ]; then \
		echo "Resetting alembic history..." && \
		docker-compose exec api alembic stamp base && \
		docker-compose exec api alembic revision --autogenerate -m "$$migration_name"; \
	else \
		docker-compose exec api alembic revision --autogenerate -m "$$migration_name"; \
	fi

db-migrate:
	@echo "Applying database migrations..."
	docker-compose exec api alembic upgrade head

# ----- Testing Commands -----

test-db-setup:
	@echo "Setting up test PostgreSQL database..."
	@docker-compose exec db psql -U postgres -c "DROP DATABASE IF EXISTS unifyops_test;"
	@docker-compose exec db psql -U postgres -c "CREATE DATABASE unifyops_test;"
	@echo "Running migrations on test database..."
	@docker-compose exec -e SQLALCHEMY_DATABASE_URL="postgresql://postgres:postgres@db:5432/unifyops_test" api alembic upgrade head
	@echo "Test database created and migrated successfully."

test-db-teardown:
	@echo "Tearing down test PostgreSQL database..."
	@docker-compose exec db psql -U postgres -c "DROP DATABASE IF EXISTS unifyops_test;"
	@echo "Test database removed successfully."

test: test-db-setup
	@echo "Running tests with PostgreSQL database..."
	docker-compose exec api python -m pytest app/tests/ -v
	@make test-db-teardown

test-coverage: test-db-setup
	@echo "Running test coverage with PostgreSQL database..."
	docker-compose exec api python -m pytest --cov=app app/tests/ --cov-report=term --cov-report=html
	@make test-db-teardown

lint:
	black --check app/
	flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics

lint-fix:
	black app/
	flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics

# ----- Docker Commands -----

docker-build-base:
	docker build --platform=linux/amd64 -t unifyops-core-base:latest -f docker/Dockerfile.base .

docker-build-local: docker-build-base
	docker build --platform=linux/amd64 -t unifyops-core:local -f docker/Dockerfile.local \
		--build-arg BUILD_TIMESTAMP=$(shell date -u +'%Y-%m-%dT%H:%M:%SZ') \
		.

docker-build-dev: docker-build-base
	docker build --platform=linux/amd64 -t unifyops-core:dev -f docker/Dockerfile.dev \
		--build-arg BUILD_TIMESTAMP=$(shell date -u +'%Y-%m-%dT%H:%M:%SZ') \
		.

docker-build-staging: docker-build-base
	docker build --platform=linux/amd64 -t unifyops-core:staging -f docker/Dockerfile.staging \
		--build-arg BUILD_TIMESTAMP=$(shell date -u +'%Y-%m-%dT%H:%M:%SZ') \
		.

docker-build-prod: docker-build-base
	docker build --platform=linux/amd64 -t unifyops-core:prod -f docker/Dockerfile.prod \
		--build-arg BUILD_TIMESTAMP=$(shell date -u +'%Y-%m-%dT%H:%M:%SZ') \
		.

docker-build: docker-build-$(ENV)

docker-up:
	ENV_FILE=.env.$(ENV) docker-compose up

docker-up-d:
	ENV_FILE=.env.$(ENV) docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-shell:
	docker-compose exec api /bin/bash

docker-exec:
	docker-compose exec api $(CMD)

docker-restart:
	docker-compose restart

docker-prune:
	docker system prune -f
	docker volume prune -f

docker-test:
	docker-compose run --rm api pytest app/tests/ -v

docker-lint:
	docker-compose run --rm api black --check app/

# ----- CI/CD Commands -----

ci-build:
	# Build the base image
	docker build --platform=linux/amd64 -t unifyops-core-base:latest -f docker/Dockerfile.base .
	
	# Build the environment-specific image using the local base image
	docker build --platform=linux/amd64 -t $(ECR_REPOSITORY):$(IMAGE_TAG) \
		-f docker/Dockerfile.$(ENV) \
		--build-arg ENV=$(ENV) \
		--build-arg BUILD_TIMESTAMP=$(shell date -u +'%Y-%m-%dT%H:%M:%SZ') \
		.

ci-test:
	python -m pytest app/tests/ -v

ci-lint:
	black --check app/
	flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics

ci-ecr-login:
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_REGISTRY)

ci-ecr-push: ci-ecr-login
	@echo "Pushing to ECR repository: $(ECR_REGISTRY)/$(ECR_REPOSITORY):$(IMAGE_TAG)"
	docker tag $(ECR_REPOSITORY):$(IMAGE_TAG) $(ECR_REGISTRY)/$(ECR_REPOSITORY):$(IMAGE_TAG)
	docker tag $(ECR_REPOSITORY):$(IMAGE_TAG) $(ECR_REGISTRY)/$(ECR_REPOSITORY):latest
	docker push $(ECR_REGISTRY)/$(ECR_REPOSITORY):$(IMAGE_TAG)
	docker push $(ECR_REGISTRY)/$(ECR_REPOSITORY):latest
	@echo "Verifying image exists in ECR..."
	aws ecr describe-images --region $(AWS_REGION) --repository-name $(ECR_REPOSITORY) --image-ids imageTag=$(IMAGE_TAG)

ci-deploy: tf-init tf-plan tf-apply

# ----- Terraform Commands -----

tf-init:
	cd $(TF_DIR) && terraform init \
		-backend-config="bucket=${TF_STATE_BUCKET}" \
		-backend-config="key=core/terraform_state.tfstate" \
		-backend-config="region=${AWS_REGION}" \
		-backend-config="dynamodb_table=${TF_STATE_LOCK_TABLE}"

tf-plan:
	cd $(TF_DIR) && terraform plan \
		-var="infra_env=$(ENV)" \
		-var="container_image_tag=$(IMAGE_TAG)" \
		-out=tfplan

tf-apply:
	cd $(TF_DIR) && terraform apply -auto-approve tfplan

tf-destroy:
	cd $(TF_DIR) && terraform destroy \
		-var="infra_env=$(ENV)" \
		-var="container_image_tag=$(IMAGE_TAG)"

tf-output:
	cd $(TF_DIR) && terraform output

# ----- ECS Utilities -----

ecs-status:
	@ECS_CLUSTER=$$(cd $(TF_DIR) && terraform output -raw ecs_cluster_name 2>/dev/null) && \
	ECS_SERVICE=$$(cd $(TF_DIR) && terraform output -raw ecs_service_name 2>/dev/null) && \
	if [ -z "$$ECS_CLUSTER" ] || [ -z "$$ECS_SERVICE" ]; then \
		echo "Error: Cluster or service name not found. Run make tf-output first."; \
	else \
		echo "Checking ECS service status for $$ECS_SERVICE in cluster $$ECS_CLUSTER..." && \
		aws ecs describe-services --cluster $$ECS_CLUSTER --services $$ECS_SERVICE --query 'services[0].{Status:status,RunningTasks:runningCount,DesiredTasks:desiredCount,PendingTasks:pendingCount,Events:events[0:3]}' --output table; \
	fi

ecs-logs:
	@ECS_CLUSTER=$$(cd $(TF_DIR) && terraform output -raw ecs_cluster_name 2>/dev/null) && \
	if [ -z "$$ECS_CLUSTER" ]; then \
		echo "Error: Cluster name not found. Run make tf-output first."; \
	else \
		TASK_ID=$$(aws ecs list-tasks --cluster $$ECS_CLUSTER --query 'taskArns[0]' --output text | awk -F'/' '{print $$3}') && \
		if [ "$$TASK_ID" = "None" ] || [ -z "$$TASK_ID" ]; then \
			echo "No running tasks found in cluster $$ECS_CLUSTER"; \
		else \
			echo "Retrieving logs for task $$TASK_ID in cluster $$ECS_CLUSTER..." && \
			LOG_GROUP=$$(aws ecs describe-task-definition --task-definition $$(aws ecs describe-tasks --cluster $$ECS_CLUSTER --tasks $$TASK_ID --query 'tasks[0].taskDefinitionArn' --output text | awk -F'/' '{print $$2}') --query 'taskDefinition.containerDefinitions[0].logConfiguration.options."awslogs-group"' --output text) && \
			LOG_STREAM="$${LOG_GROUP}/api/$${TASK_ID}" && \
			echo "Log stream: $$LOG_STREAM" && \
			aws logs get-log-events --log-group $$LOG_GROUP --log-stream-name $$LOG_STREAM --query 'events[*].[timestamp,message]' --output table; \
		fi; \
	fi

ecs-exec:
	@if [ -z "$(CMD)" ]; then \
		echo "Error: Command not specified. Use make ecs-exec CMD=\"your command\""; \
	else \
		ECS_CLUSTER=$$(cd $(TF_DIR) && terraform output -raw ecs_cluster_name 2>/dev/null) && \
		if [ -z "$$ECS_CLUSTER" ]; then \
			echo "Error: Cluster name not found. Run make tf-output first."; \
		else \
			TASK_ID=$$(aws ecs list-tasks --cluster $$ECS_CLUSTER --query 'taskArns[0]' --output text | awk -F'/' '{print $$3}') && \
			if [ "$$TASK_ID" = "None" ] || [ -z "$$TASK_ID" ]; then \
				echo "No running tasks found in cluster $$ECS_CLUSTER"; \
			else \
				echo "Executing command in task $$TASK_ID in cluster $$ECS_CLUSTER..." && \
				aws ecs execute-command --cluster $$ECS_CLUSTER --task $$TASK_ID --container api --command "/bin/bash" --interactive; \
			fi; \
		fi; \
	fi

ecs-deploy:
	@echo "Deploying to ECS..."
	@ECS_CLUSTER=$$(cd $(TF_DIR) && terraform output -raw ecs_cluster_name 2>/dev/null) && \
	ECS_SERVICE=$$(cd $(TF_DIR) && terraform output -raw ecs_service_name 2>/dev/null) && \
	if [ -z "$$ECS_CLUSTER" ] || [ -z "$$ECS_SERVICE" ]; then \
		echo "Error: Cluster or service name not found. Run make tf-output first."; \
	else \
		aws ecs update-service --cluster $$ECS_CLUSTER --service $$ECS_SERVICE --force-new-deployment && \
		echo "Deployment triggered. Check status with 'make ecs-status'"; \
	fi

ecs-rollback:
	@echo "Rolling back to previous ECS deployment..."
	@ECS_CLUSTER=$$(cd $(TF_DIR) && terraform output -raw ecs_cluster_name 2>/dev/null) && \
	ECS_SERVICE=$$(cd $(TF_DIR) && terraform output -raw ecs_service_name 2>/dev/null) && \
	if [ -z "$$ECS_CLUSTER" ] || [ -z "$$ECS_SERVICE" ]; then \
		echo "Error: Cluster or service name not found. Run make tf-output first."; \
	else \
		TASK_DEF=$$(aws ecs describe-services --cluster $$ECS_CLUSTER --services $$ECS_SERVICE --query 'services[0].deployments[1].taskDefinition' --output text) && \
		if [ "$$TASK_DEF" = "None" ] || [ -z "$$TASK_DEF" ]; then \
			echo "No previous deployment found for rollback"; \
		else \
			aws ecs update-service --cluster $$ECS_CLUSTER --service $$ECS_SERVICE --task-definition $$TASK_DEF && \
			echo "Rollback triggered to $$TASK_DEF. Check status with 'make ecs-status'"; \
		fi; \
	fi