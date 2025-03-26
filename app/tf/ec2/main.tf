# Simple EC2 instance module for UnifyOps API
provider "aws" {
  region = var.region
}

resource "aws_instance" "api_server" {
  ami           = var.ami_id
  instance_type = var.instance_type
  subnet_id     = var.subnet_id
  key_name      = var.key_name

  vpc_security_group_ids = var.security_group_ids

  tags = {
    Name        = var.name
    Environment = var.environment
    Managed     = "terraform"
  }

  user_data = <<-EOF
    #!/bin/bash
    echo "Setting up API server"
    sudo apt-get update -y
    sudo apt-get install -y docker.io
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo docker pull ${var.docker_image}
    sudo docker run -d -p 80:8000 --name unifyops-api \
      -e ENVIRONMENT=${var.environment} \
      -e LOG_LEVEL=${var.log_level} \
      -e API_HOST=0.0.0.0 \
      -e API_PORT=8000 \
      -e API_RELOAD=false \
      -e CORS_ORIGINS=${var.cors_origins} \
      ${var.docker_image}
  EOF

  lifecycle {
    create_before_destroy = true
  }
}

# Output the instance ID and public IP
output "instance_id" {
  value = aws_instance.api_server.id
}

output "public_ip" {
  value = aws_instance.api_server.public_ip
}

output "public_dns" {
  value = aws_instance.api_server.public_dns
}

output "health_check_url" {
  value = "http://${aws_instance.api_server.public_dns}/api/v1/health"
} 
