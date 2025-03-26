variable "region" {
  description = "AWS region to deploy the EC2 instance"
  type        = string
  default     = "us-east-1"
}

variable "ami_id" {
  description = "AMI ID for the EC2 instance (Free tier eligible Amazon Linux 2023)"
  type        = string
  default     = "ami-0f34c5ae932e6f0e4" # Amazon Linux 2023 AMI in us-east-1 (Free Tier eligible)
}

variable "instance_type" {
  description = "EC2 instance type (Free tier: t2.micro or t3.micro where available)"
  type        = string
  default     = "t2.micro" # Free tier eligible
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

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "user_data" {
  description = "User data for the EC2 instance"
  type        = string
  default     = <<-EOT
    #!/bin/bash
    echo "Hello Terraform!"
  EOT
}

# New variables for ec2_complete module

variable "availability_zone" {
  description = "Availability zone for the EC2 instance"
  type        = string
  default     = null
  # Will be determined dynamically if not specified
}

variable "placement_group_name" {
  description = "Placement group name for the EC2 instance"
  type        = string
  default     = null
}

variable "create_placement_group" {
  description = "Whether to create a placement group for the EC2 instance (disabled for Free Tier)"
  type        = bool
  default     = false # Not needed for Free Tier, can generate additional network costs
}

variable "placement_group_strategy" {
  description = "Placement group strategy"
  type        = string
  default     = "cluster"
}

variable "create_eip" {
  description = "Whether to create an Elastic IP for the EC2 instance (Free Tier includes 1 EIP if associated with running instance)"
  type        = bool
  default     = true # Free Tier allows 1 EIP associated with a running instance
}

variable "disable_api_stop" {
  description = "If true, enables EC2 Instance Stop Protection"
  type        = bool
  default     = false
}

variable "create_iam_instance_profile" {
  description = "Whether to create an IAM instance profile"
  type        = bool
  default     = true
}

variable "iam_role_description" {
  description = "Description for the IAM role"
  type        = string
  default     = "IAM role for EC2 instance"
}

variable "iam_role_policies" {
  description = "IAM policies to attach to the IAM role (using more specific policies for Free Tier)"
  type        = map(string)
  default = {
    AmazonSSMManagedInstanceCore = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore" # For SSM connection without SSH
  }
}

variable "hibernation" {
  description = "Whether to enable hibernation for the EC2 instance (disabled for Free Tier as it requires specific instance types)"
  type        = bool
  default     = false # Not required for Free Tier and may not be supported by all instance types
}

variable "enclave_options_enabled" {
  description = "Whether to enable Nitro Enclaves on the instance (disabled for Free Tier)"
  type        = bool
  default     = false # Not supported on t2.micro
}

variable "user_data_replace_on_change" {
  description = "Whether to replace the instance on user_data change"
  type        = bool
  default     = true
}

variable "cpu_core_count" {
  description = "Number of CPU cores for the instance (Free Tier instances have limited options)"
  type        = number
  default     = null # Let AWS determine based on instance type (t2.micro has fixed specification)
}

variable "cpu_threads_per_core" {
  description = "Number of threads per CPU core (Free Tier instances have limited options)"
  type        = number
  default     = null # Let AWS determine based on instance type (t2.micro has fixed specification)
}

variable "enable_volume_tags" {
  description = "Whether to enable volume tags"
  type        = bool
  default     = true # Enable for better resource tracking
}

variable "root_block_device" {
  description = "Root block device configuration (Free Tier: 30GB General Purpose SSD)"
  type = list(object({
    encrypted   = bool
    volume_type = string
    throughput  = number
    volume_size = number
    tags        = map(string)
  }))
  default = [
    {
      encrypted   = false # Encryption may incur additional costs
      volume_type = "gp2" # Free Tier offers General Purpose SSD (gp2)
      throughput  = null  # Not applicable for gp2
      volume_size = 8     # Free Tier offers 30GB total, using 8GB for root
      tags = {
        Name = "root-volume"
      }
    }
  ]
}

variable "ebs_block_device" {
  description = "EBS block device configuration"
  type = list(object({
    device_name = string
    volume_type = string
    volume_size = number
    throughput  = number
    encrypted   = bool
    kms_key_id  = string
    tags        = map(string)
  }))
  default = null # Default to null for Free Tier (will use defaults below if additional volume needed)
}

variable "kms_key_id" {
  description = "KMS key ID for EBS encryption"
  type        = string
  default     = null # Custom key management may incur additional costs
}

# Default EBS block device configuration (used when ebs_block_device is null)
variable "default_ebs_device_name" {
  description = "Default device name for the EBS volume"
  type        = string
  default     = "/dev/sdf"
}

variable "default_ebs_volume_type" {
  description = "Default volume type for the EBS volume (Free Tier: gp2)"
  type        = string
  default     = "gp2" # Free Tier eligible
}

variable "default_ebs_volume_size" {
  description = "Default volume size in GB for the EBS volume (Free Tier: up to 30GB total)"
  type        = number
  default     = 20 # Using 20GB here to stay within Free Tier 30GB total (with 8GB root)
}

variable "default_ebs_throughput" {
  description = "Default throughput in MB/s for the EBS volume"
  type        = number
  default     = null # Not applicable for gp2 volumes
}

variable "default_ebs_encrypted" {
  description = "Whether the default EBS volume should be encrypted (disabled for Free Tier)"
  type        = bool
  default     = false # Encryption may incur additional costs
}

variable "default_ebs_tags" {
  description = "Default tags for the EBS volume"
  type        = map(string)
  default = {
    Name       = "data-volume"
    MountPoint = "/mnt/data"
  }
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    ManagedBy = "terraform"
    Tier      = "free-tier"
  }
}
