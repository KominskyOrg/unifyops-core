# CI/CD Workflow Documentation

This document outlines the Continuous Integration and Continuous Deployment (CI/CD) process for the UnifyOps backend application.

## Overview

The CI/CD pipeline automates the deployment of the backend application to the EC2 instance whenever changes are pushed to the main branch. The workflow handles testing, deployment, and verification of the deployment through health checks.

## Workflow Configuration

The CI/CD workflow is implemented using GitHub Actions and is defined in `.github/workflows/deploy-backend.yml`.

### Trigger Events

The workflow is triggered by the following events:

- A push to the `main` branch that includes changes to files in the `backend/` directory
- A merged pull request to the `main` branch that includes changes to files in the `backend/` directory

### Steps in the Workflow

1. **Checkout code**: Retrieves the latest code from the repository
2. **Set up Python**: Configures the Python environment
3. **Install dependencies**: Installs required Python packages
4. **Run tests**: Executes the test suite to ensure code quality
5. **Configure SSH**: Sets up SSH for secure deployment
6. **Deploy to EC2**: Transfers and sets up the application on the EC2 instance
7. **Health check**: Verifies the application is running correctly after deployment

## Required Secrets

The following secrets must be configured in GitHub repository settings:

- `EC2_SSH_PRIVATE_KEY`: The SSH private key for connecting to the EC2 instance
- `EC2_HOST`: The hostname or IP address of the EC2 instance
- `EC2_USERNAME`: The username for SSH connection to the EC2 instance

Optional secrets:

- `APP_DIR`: The directory where the application should be deployed (defaults to `/home/ec2-user/unifyops-backend`)
- `HEALTH_CHECK_URL`: The URL to check for application health (defaults to `http://<EC2_HOST>:8000/api/v1/health`)

## Error Handling

The workflow includes several error handling mechanisms:

### Deployment Failures

If the deployment to EC2 fails, the workflow will terminate and report the failure. Common causes of deployment failures include:

- SSH connection issues (incorrect credentials or network problems)
- Insufficient permissions on the EC2 instance
- Disk space limitations on the EC2 instance

### Health Check Failures

The health check will retry up to 5 times with a 10-second delay between attempts if the application is not responding. If all retries fail, the workflow will report a failure.

## Monitoring and Logs

- The status of each workflow run can be viewed in the "Actions" tab of the GitHub repository
- Detailed logs for each step are available within each workflow run
- For application-specific logs, check the log files on the EC2 instance (typically in `/var/log/unifyops-backend/` or as configured in the systemd service)

## Rollback Procedure

In case of a deployment failure:

1. Identify the issue from the GitHub Actions logs
2. If necessary, manually restore the previous version on the EC2 instance:
   ```bash
   ssh <EC2_USERNAME>@<EC2_HOST>
   cd <APP_DIR>
   git reset --hard <previous-commit-hash>
   sudo systemctl restart unifyops-backend.service
   ```
3. Fix the issue in a new commit/PR
4. Test thoroughly before merging to main

## Setting Up the EC2 Environment

For this CI/CD pipeline to work correctly, ensure:

1. The EC2 instance has Python 3.8+ installed
2. A systemd service (`unifyops-backend.service`) is configured to run the application
3. The EC2 instance has proper networking and security group rules to allow:
   - SSH access from GitHub Actions runners
   - HTTP/HTTPS access on the application port (typically 8000)
4. The user specified by `EC2_USERNAME` has appropriate permissions to:
   - Write to the application directory
   - Restart the systemd service (typically requires sudo access)

## API Structure

The backend application uses a versioned API structure with all endpoints prefixed with `/api/v1/`. This versioning approach allows for future API changes without breaking backward compatibility.

### Key Endpoints

- `/api/v1/health`: Health check endpoint used by the deployment workflow to verify application status
- `/api/v1/`: Root API endpoint providing API information
- `/`: Root application endpoint (not versioned) providing general application information and links

## Health Check Endpoint

The backend application implements a health check endpoint (`/api/v1/health`) that returns a 200 OK status when the application is running correctly. This endpoint should:

- Be lightweight and respond quickly
- Check critical dependencies (database, cache, etc.)
- Return appropriate HTTP status codes (200 for healthy, non-200 for unhealthy)
