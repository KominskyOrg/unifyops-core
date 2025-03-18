#!/bin/bash
# Comprehensive build and deploy script for UnifyOps Core

set -e # Exit on error

# Default values
ENV="dev"
BUILD_IMAGE=true
PUSH_IMAGE=true
DEPLOY=true
IMAGE_TAG="latest"
DEBUG=false

# Process command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --env)
      ENV="$2"
      shift 2
      ;;
    --tag)
      IMAGE_TAG="$2"
      shift 2
      ;;
    --no-build)
      BUILD_IMAGE=false
      shift
      ;;
    --no-push)
      PUSH_IMAGE=false
      shift
      ;;
    --build-only)
      DEPLOY=false
      shift
      ;;
    --deploy-only)
      BUILD_IMAGE=false
      PUSH_IMAGE=false  # Skip push when using --deploy-only as we assume image is already in ECR
      shift
      ;;
    --debug)
      DEBUG=true
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --env ENV        Set deployment environment (dev, staging, prod) [default: dev]"
      echo "  --tag TAG        Set image tag [default: latest]"
      echo "  --no-build       Skip building the Docker image"
      echo "  --no-push        Build image but don't push to ECR"
      echo "  --build-only     Build and push image but don't deploy to EC2"
      echo "  --deploy-only    Only deploy existing image (implies --no-build)"
      echo "  --debug          Enable verbose debugging output"
      echo "  --help           Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Load environment variables from .env file
if [ -f ".env.$ENV" ]; then
  echo "Loading environment variables from .env.$ENV"
  export $(grep -v '^#' .env.$ENV | xargs)
else
  echo "Warning: .env.$ENV file not found. Using default environment variables."
fi

# Check for required environment variables
if [ -z "$AWS_REGION" ] || [ -z "$ECR_REPOSITORY" ]; then
  echo "Error: Required environment variables not set."
  echo "Please set AWS_REGION and ECR_REPOSITORY in .env.$ENV file"
  exit 1
fi

# Set EC2 instance ID based on environment
if [ "$ENV" == "dev" ]; then
  EC2_INSTANCE_ID=${DEV_EC2_INSTANCE_ID:-$EC2_INSTANCE_ID}
elif [ "$ENV" == "staging" ]; then
  EC2_INSTANCE_ID=${STAGING_EC2_INSTANCE_ID:-$EC2_INSTANCE_ID}
elif [ "$ENV" == "prod" ]; then
  EC2_INSTANCE_ID=${PROD_EC2_INSTANCE_ID:-$EC2_INSTANCE_ID}
fi

if [ -z "$EC2_INSTANCE_ID" ] && [ "$DEPLOY" = true ]; then
  echo "Error: EC2_INSTANCE_ID not set for environment $ENV"
  exit 1
fi

# Get AWS ECR registry URI
ECR_REGISTRY=${ECR_REGISTRY:-$(aws ecr describe-repositories --repository-names $ECR_REPOSITORY --query 'repositories[0].repositoryUri' --output text | sed "s|/$ECR_REPOSITORY||")}

echo "==============================================="
echo "UnifyOps Core Build & Deploy"
echo "==============================================="
echo "Environment: $ENV"
echo "AWS Region: $AWS_REGION"
echo "ECR Repository: $ECR_REPOSITORY"
echo "Image Tag: $IMAGE_TAG"
if [ "$DEPLOY" = true ]; then
  echo "EC2 Instance ID: $EC2_INSTANCE_ID"
fi
if [ "$BUILD_IMAGE" = false ]; then
  echo "Build Image: SKIPPED"
fi
if [ "$PUSH_IMAGE" = false ]; then
  echo "Push Image: SKIPPED"
fi
echo "==============================================="

# Get timestamp for the build
TIMESTAMP=$(date +%Y%m%d%H%M%S)

# Set working directory to project root folder
cd "$(dirname "$0")/.." || exit 1

# Build Docker image if required
if [ "$BUILD_IMAGE" = true ]; then
  echo "Building Docker image..."
  docker build -t $ECR_REPOSITORY:$IMAGE_TAG \
    --build-arg ENV=$ENV \
    --build-arg BUILD_TIMESTAMP=$TIMESTAMP \
    .
else
  echo "Skipping Docker image build (--no-build or --deploy-only flag was used)"
fi

if [ "$PUSH_IMAGE" = true ]; then
  # Login to ECR
  echo "Logging into ECR..."
  aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

  # Tag and push Docker image
  echo "Tagging image for ECR..."
  docker tag $ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY$ECR_REPOSITORY:$IMAGE_TAG

  # Push image to ECR
  echo "Pushing image to ECR..."
  docker push $ECR_REGISTRY$ECR_REPOSITORY:$IMAGE_TAG
  
  echo "Image successfully pushed to $ECR_REGISTRY$ECR_REPOSITORY:$IMAGE_TAG"
else
  echo "Skipping Docker image push to ECR (--no-push or --deploy-only flag was used)"
fi

# Deploy to EC2 if requested
if [ "$DEPLOY" = true ]; then
  echo "Deploying to EC2 instance $EC2_INSTANCE_ID..."
  
  # Create container environment variable arguments
  ENV_ARGS=""
  if [ -f ".env.$ENV" ]; then
    # Read environment variables from .env file and format for docker run command
    ENV_ARGS=$(grep -v '^#' .env.$ENV | grep -v '^\s*$' | sed 's/^/-e /' | tr '\n' ' ')
    if [ "$DEBUG" = true ]; then
      echo "Environment arguments: $ENV_ARGS"
    fi
  fi
  
  if [ "$DEBUG" = true ]; then
    echo "DEBUG: Verifying image exists in ECR..."
    aws ecr describe-images --repository-name $ECR_REPOSITORY --image-ids imageTag=$IMAGE_TAG || echo "WARNING: Image with tag $IMAGE_TAG not found in ECR repository"
    
    echo "DEBUG: Verifying EC2 instance exists..."
    aws ec2 describe-instances --instance-ids $EC2_INSTANCE_ID --query "Reservations[].Instances[].State.Name" --output text || echo "WARNING: EC2 instance $EC2_INSTANCE_ID not found or not accessible"
    
    echo "DEBUG: Deployment command to be executed:"
    echo "aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY"
    echo "docker pull $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG"
    echo "docker stop unifyops-api-$ENV || true"
    echo "docker rm unifyops-api-$ENV || true"
    echo "docker run -d --name unifyops-api-$ENV -p 8000:8000 $ENV_ARGS $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG"
    echo "docker system prune -af"
  fi
  
  # Deploy using SSM Run Command
  COMMAND_ID=$(aws ssm send-command \
    --region $AWS_REGION \
    --instance-ids $EC2_INSTANCE_ID \
    --document-name "AWS-RunShellScript" \
    --parameters "commands=[
      'set -x',
      'aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY',
      'docker pull $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG',
      'docker stop unifyops-api-$ENV || true',
      'docker rm unifyops-api-$ENV || true',
      'docker run -d --name unifyops-api-$ENV -p 8000:8000 $ENV_ARGS $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG',
      'docker system prune -af',
      'echo \"Running health check...\"',
      'sleep 5',
      'for i in {1..10}; do',
      '  echo \"Health check attempt $i...\"',
      '  STATUS_CODE=$(curl -s -o /dev/null -w \"%{http_code}\" http://localhost:8000/api/v1/health)',
      '  echo \"Received status code: $STATUS_CODE\"',
      '  if [ \"$STATUS_CODE\" = \"200\" ]; then',
      '    echo \"Application is healthy\"',
      '    exit 0',
      '  else',
      '    echo \"Application not ready yet (status: $STATUS_CODE), waiting...\"',
      '    sleep 3',
      '  fi',
      'done',
      'echo \"Health check failed after 10 attempts\"',
      'docker ps -a',
      'docker logs unifyops-api-$ENV || echo \"No logs available\"',
      'exit 1'
    ]" \
    --output text --query "Command.CommandId")
  
  echo "Deployment initiated with command ID: $COMMAND_ID"
  echo "Waiting for deployment to complete..."
  
  # Wait for command completion
  while true; do
    COMMAND_STATUS=$(aws ssm list-commands \
      --command-id $COMMAND_ID \
      --query "Commands[0].Status" \
      --output text)
    
    echo "Deployment status: $COMMAND_STATUS"
    
    if [ "$COMMAND_STATUS" = "Success" ]; then
      echo "Deployment completed successfully!"
      
      # Run health check
      echo "Running health check..."
      HEALTH_COMMAND_ID=$(aws ssm send-command \
        --region $AWS_REGION \
        --instance-ids $EC2_INSTANCE_ID \
        --document-name "AWS-RunShellScript" \
        --parameters "commands=[
          'for i in {1..10}; do',
          '  echo \"Health check attempt $i...\"',
          '  STATUS_CODE=$(curl -s -o /dev/null -w \"%{http_code}\" http://localhost:8000/api/v1/health)',
          '  if [ \"$STATUS_CODE\" = \"200\" ]; then',
          '    echo \"Application is healthy\"',
          '    exit 0',
          '  else',
          '    echo \"Application not ready yet (status: $STATUS_CODE), waiting...\"',
          '    sleep 3',
          '  fi',
          'done',
          'echo \"Health check failed after 10 attempts\"',
          'docker logs unifyops-api-$ENV',
          'exit 1'
        ]" \
        --output text --query "Command.CommandId")
      
      # Wait for health check to complete
      while true; do
        HEALTH_STATUS=$(aws ssm list-commands \
          --command-id $HEALTH_COMMAND_ID \
          --query "Commands[0].Status" \
          --output text)
        
        if [ "$HEALTH_STATUS" = "Success" ]; then
          echo "Health check passed! Deployment is complete and the application is running."
          break
        elif [ "$HEALTH_STATUS" = "Failed" ]; then
          echo "Health check failed. Fetching logs..."
          aws ssm get-command-invocation \
            --command-id $HEALTH_COMMAND_ID \
            --instance-id $EC2_INSTANCE_ID \
            --query "StandardOutputContent" \
            --output text
          exit 1
        else
          echo "Health check status: $HEALTH_STATUS"
          sleep 5
        fi
      done
      
      break
    elif [ "$COMMAND_STATUS" = "Failed" ]; then
      echo "Deployment failed. Fetching logs..."
      aws ssm get-command-invocation \
        --command-id $COMMAND_ID \
        --instance-id $EC2_INSTANCE_ID \
        --query "StandardOutputContent" \
        --output text
      
      echo "Fetching standard error output..."
      aws ssm get-command-invocation \
        --command-id $COMMAND_ID \
        --instance-id $EC2_INSTANCE_ID \
        --query "StandardErrorContent" \
        --output text
      
      # Additional diagnostic info
      echo "Image tag being deployed: $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG"
      echo "Checking if image exists in ECR..."
      aws ecr describe-images --repository-name $ECR_REPOSITORY --image-ids imageTag=$IMAGE_TAG || echo "Image with tag $IMAGE_TAG not found in ECR repository"
      
      exit 1
    else
      sleep 5
    fi
  done
  
  echo "==============================================="
  echo "Deployment Summary"
  echo "==============================================="
  echo "Environment: $ENV"
  echo "Deployed Image: $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG"
  echo "EC2 Instance ID: $EC2_INSTANCE_ID"
  echo "Status: DEPLOYED"
  echo "==============================================="
fi

echo "Build and deploy process completed!" 