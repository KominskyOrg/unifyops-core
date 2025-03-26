variable "region" {
  description = "AWS region to deploy the EC2 instance"
  type        = string
  default     = "us-east-1"
}

variable "ami_id" {
  description = "AMI ID for the EC2 instance"
  type        = string
  default     = "ami-0261755bbcb8c4a84" # Ubuntu 20.04 LTS in us-east-1
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}

variable "subnet_id" {
  description = "Subnet ID where the EC2 instance will be deployed"
  type        = string
}

variable "key_name" {
  description = "EC2 key pair name for SSH access"
  type        = string
  default     = null
}

variable "security_group_ids" {
  description = "Security group IDs to attach to the EC2 instance"
  type        = list(string)
}

variable "name" {
  description = "Name for the EC2 instance"
  type        = string
  default     = "unifyops-api"
}

variable "environment" {
  description = "Environment (e.g., development, staging, production)"
  type        = string
  default     = "development"
}

variable "docker_image" {
  description = "Docker image for the UnifyOps API"
  type        = string
  default     = "unifyops-api:latest"
}

variable "log_level" {
  description = "Log level for the API"
  type        = string
  default     = "info"
}

variable "cors_origins" {
  description = "CORS origins allowed for the API"
  type        = string
  default     = "*"
} 
