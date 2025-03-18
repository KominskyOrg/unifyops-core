#!/bin/bash
# Script to deploy Docker container to EC2 using AWS CLI and SSM

# Exit on error
set -e

# Check required environment variables
if [ -z "$AWS_REGION" ] || [ -z "$ECR_REPOSITORY" ] || [ -z "$EC2_INSTANCE_ID" ]; then
  echo "Error: Required environment variables not set."
  echo "Please set: AWS_REGION, ECR_REPOSITORY, EC2_INSTANCE_ID"
  exit 1
fi

# Set default values
IMAGE_TAG=${IMAGE_TAG:-latest}
ECR_REGISTRY=${ECR_REGISTRY:-$(aws ecr describe-repositories --repository-names $ECR_REPOSITORY --query 'repositories[0].repositoryUri' --output text | sed "s/$ECR_REPOSITORY//")}

echo "=== Deployment Configuration ==="
echo "AWS Region: $AWS_REGION"
echo "ECR Registry: $ECR_REGISTRY"
echo "ECR Repository: $ECR_REPOSITORY"
echo "Image Tag: $IMAGE_TAG"
echo "EC2 Instance ID: $EC2_INSTANCE_ID"
echo "==============================="

# Build the Docker image
echo "Building Docker image..."
cd "$(dirname "$0")/.." # Navigate to the project root
docker build -t $ECR_REPOSITORY:$IMAGE_TAG .

# Tag the image for ECR
echo "Tagging image for ECR..."
docker tag $ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY$ECR_REPOSITORY:$IMAGE_TAG

# Login to ECR
echo "Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Push the image to ECR
echo "Pushing image to ECR..."
docker push $ECR_REGISTRY$ECR_REPOSITORY:$IMAGE_TAG

# Deploy to EC2 using SSM
echo "Deploying to EC2 instance $EC2_INSTANCE_ID..."
COMMAND_ID=$(aws ssm send-command \
  --region $AWS_REGION \
  --instance-ids $EC2_INSTANCE_ID \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[
    'aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY',
    'docker pull $ECR_REGISTRY$ECR_REPOSITORY:$IMAGE_TAG',
    'docker stop unifyops-api || true',
    'docker rm unifyops-api || true',
    'docker run -d --name unifyops-api -p 8000:8000 $ECR_REGISTRY$ECR_REPOSITORY:$IMAGE_TAG',
    'docker system prune -af'
  ]" \
  --output text --query "Command.CommandId")

echo "Deployment initiated with command ID: $COMMAND_ID"
echo "Waiting for deployment command to complete..."

# Check the status of the deployment command
while true; do
  COMMAND_STATUS=$(aws ssm list-commands \
    --command-id $COMMAND_ID \
    --query "Commands[0].Status" \
    --output text)
  
  echo "Deployment command status: $COMMAND_STATUS"
  
  if [ "$COMMAND_STATUS" = "Success" ]; then
    echo "Deployment command completed successfully"
    break
  elif [ "$COMMAND_STATUS" = "Failed" ]; then
    echo "Deployment command failed"
    exit 1
  else
    echo "Waiting for deployment to complete..."
    sleep 10
  fi
done

# Check deployment health (optional)
read -p "Do you want to check the deployment health? (y/n) " CHECK_HEALTH
if [[ $CHECK_HEALTH == "y" || $CHECK_HEALTH == "Y" ]]; then
  echo "Running health check via SSM..."
  
  # Run health check inside the EC2 instance
  HEALTH_COMMAND_ID=$(aws ssm send-command \
    --region $AWS_REGION \
    --instance-ids $EC2_INSTANCE_ID \
    --document-name "AWS-RunShellScript" \
    --parameters "commands=[
      'echo \"Waiting for application to start...\"',
      'sleep 5',
      'for i in {1..5}; do',
      '  echo \"Health check attempt $i...\"',
      '  STATUS_CODE=$(curl -s -o /dev/null -w \"%{http_code}\" http://localhost:8000/api/v1/health)',
      '  if [ \"$STATUS_CODE\" = \"200\" ]; then',
      '    echo \"Application is healthy\"',
      '    exit 0',
      '  else',
      '    echo \"Application not ready yet (status: $STATUS_CODE), waiting...\"',
      '    sleep 10',
      '  fi',
      'done',
      'echo \"Health check failed after 5 attempts\"',
      'docker logs unifyops-api',
      'exit 1'
    ]" \
    --output text --query "Command.CommandId")
  
  echo "Health check command ID: $HEALTH_COMMAND_ID"
  
  # Check the status of the health check command
  while true; do
    HEALTH_STATUS=$(aws ssm list-commands \
      --command-id $HEALTH_COMMAND_ID \
      --query "Commands[0].Status" \
      --output text)
    
    echo "Health check command status: $HEALTH_STATUS"
    
    if [ "$HEALTH_STATUS" = "Success" ]; then
      echo "Health check passed! Application is running properly."
      break
    elif [ "$HEALTH_STATUS" = "Failed" ]; then
      echo "Health check failed! Application might not be running correctly."
      
      # Get command output for more details
      aws ssm get-command-invocation \
        --command-id $HEALTH_COMMAND_ID \
        --instance-id $EC2_INSTANCE_ID \
        --query "StandardOutputContent" \
        --output text
      
      exit 1
    else
      echo "Waiting for health check to complete..."
      sleep 10
    fi
  done
fi

echo "Deployment complete!" 