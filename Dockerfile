FROM python:3.12-slim

# Set build arguments
ARG ENV=development
ARG BUILD_TIMESTAMP
ARG TERRAFORM_VERSION=1.11.0

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=${ENV} \
    BUILD_TIMESTAMP=${BUILD_TIMESTAMP}

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    gnupg \
    git \
    software-properties-common \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Terraform
RUN curl -fsSL https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip -o terraform.zip \
    && unzip terraform.zip \
    && mv terraform /usr/local/bin/ \
    && rm terraform.zip \
    && terraform --version

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Make sure email-validator is correctly installed (required for Pydantic 2.x)
RUN pip install --no-cache-dir email-validator==2.0.0

# Copy the rest of the application
COPY . .

# Create a non-root user and switch to it
RUN addgroup --system app && adduser --system --group app
RUN chown -R app:app /app
USER app

# Expose the port the app runs on
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run the application directly - migration happens at startup
CMD ["sh", "-c", "if [ \"$API_RELOAD\" = \"true\" ]; then echo 'Running in reload mode...' && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload; else echo 'Running in production mode...' && uvicorn app.main:app --host 0.0.0.0 --port 8000; fi"]