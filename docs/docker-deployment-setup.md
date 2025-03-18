# Docker Deployment Setup Guide

This guide outlines the steps to set up an EC2 instance for Docker container deployment using AWS Systems Manager (SSM) without SSH.

## EC2 Instance Requirements

1. **EC2 Instance Configuration**:

   - Amazon Linux 2 or Ubuntu Server recommended
   - At least t2.micro (for minimal workloads) or t2.small/medium for better performance
   - Ensure ports 8000 (application) and 443 (HTTPS) are open in the security group

2. **IAM Role Configuration**:

   Create an IAM role for your EC2 instance with the following policies:

   - `AmazonSSMManagedInstanceCore` (for SSM management)
   - `AmazonECR-FullAccess` (for Docker image pull access)

   Example policy for ECR access:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "ecr:GetDownloadUrlForLayer",
           "ecr:BatchGetImage",
           "ecr:BatchCheckLayerAvailability",
           "ecr:GetAuthorizationToken"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

## Instance Setup Steps

1. **Install SSM Agent**:

   The SSM Agent is pre-installed on Amazon Linux 2 AMIs. For other distributions, follow the AWS documentation:
   https://docs.aws.amazon.com/systems-manager/latest/userguide/ssm-agent.html

2. **Install Docker**:

   ```bash
   # For Amazon Linux 2
   sudo yum update -y
   sudo amazon-linux-extras install docker -y
   sudo systemctl enable docker
   sudo systemctl start docker
   sudo usermod -a -G docker ec2-user
   ```

   ```bash
   # For Ubuntu
   sudo apt-get update -y
   sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
   sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
   sudo apt-get update -y
   sudo apt-get install -y docker-ce
   sudo systemctl enable docker
   sudo systemctl start docker
   sudo usermod -a -G docker ubuntu
   ```

3. **Install AWS CLI v2**:

   ```bash
   # For Amazon Linux 2
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   ```

   ```bash
   # For Ubuntu
   sudo apt-get install -y unzip
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   ```

4. **Test Docker and AWS CLI**:

   ```bash
   docker --version
   aws --version
   ```

## GitHub Secrets Configuration

Add the following secrets to your GitHub repository for the GitHub Actions workflow:

- `AWS_ACCESS_KEY_ID`: Your AWS access key with ECR and SSM permissions
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `AWS_REGION`: Your AWS region (e.g., us-east-1)
- `ECR_REPOSITORY`: The name of your ECR repository
- `EC2_INSTANCE_ID`: The ID of your EC2 instance (e.g., i-0123456789abcdef0)

## Health Check Implementation

The deployment process includes health checks that verify the application is running correctly after deployment. These health checks are executed from within the EC2 instance using AWS SSM Run Command instead of attempting to connect to the application over HTTP from outside the instance.

This approach has several advantages:

1. **No need for public ports**: The application doesn't need to expose port 8000 to the internet
2. **Works with private subnets**: EC2 instances in private subnets can be verified
3. **More secure**: No external access to the application API is required for deployment verification

The health check:

1. Runs a curl command from inside the EC2 instance to the localhost endpoint
2. Checks for a 200 HTTP status code from the `/api/v1/health` endpoint
3. Retries multiple times with delays between attempts
4. Reports success or failure back to the deployment process

To debug health check issues, you can view the command output in the AWS Systems Manager Run Command console or using the AWS CLI:

```bash
aws ssm get-command-invocation \
  --command-id <command-id> \
  --instance-id <instance-id> \
  --query "StandardOutputContent" \
  --output text
```

## Amazon ECR Repository Setup

1. Create an ECR repository:

   ```bash
   aws ecr create-repository --repository-name unifyops-backend --region <your-region>
   ```

2. Note the repository URI for the GitHub secret:

   ```
   <aws-account-id>.dkr.ecr.<region>.amazonaws.com/unifyops-backend
   ```

## Troubleshooting

1. **Deployment failure with AWS SSM**:

   - Check the instance's SSM status in the AWS Systems Manager console
   - Verify the instance has the correct IAM role attached
   - Check the instance's connection status in Fleet Manager

2. **Docker container not starting**:

   - Check Docker daemon status: `sudo systemctl status docker`
   - View Docker container logs: `docker logs unifyops-backend`
   - Check if the port is already in use: `sudo netstat -tuln | grep 8000`

3. **ECR access issues**:

   - Verify the IAM role permissions include ECR access
   - Check the AWS region configuration matches your ECR repository
   - Ensure the ECR repository exists in the specified region

4. **Health check failures**:
   - Check if the container is running: `docker ps -a`
   - View container logs: `docker logs unifyops-backend`
   - Verify the health endpoint is implemented correctly in the FastAPI app
   - Try accessing the health endpoint manually from inside the EC2 instance:
     ```bash
     curl http://localhost:8000/api/v1/health
     ```

## Monitoring

1. View container logs:

   ```bash
   docker logs unifyops-backend
   ```

2. Check container status:

   ```bash
   docker ps -a
   ```

3. Monitor application health from within the EC2 instance:

   ```bash
   curl http://localhost:8000/api/v1/health
   ```

## Optional: Exposing the API Externally

If you need to expose the API externally for client applications:

1. Configure an Application Load Balancer (ALB) in front of the EC2 instance
2. Set up TLS/SSL termination on the ALB
3. Configure security groups to only allow traffic from the ALB to the EC2 instance
4. Update the container port mapping if needed (e.g., to use port 80 internally)

This setup provides better security and scalability than directly exposing the application port.
