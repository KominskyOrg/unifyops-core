terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {}
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Terraform   = "true"
      Environment = "${var.infra_env}"
      Project     = "${var.org}-${var.project_name}"
      Region      = "${var.region}"
      Org         = "${var.org}"
    }
  }
}

locals {
  name = "${var.infra_env}-${var.org}-${var.project_name}"
  tags = {}
}

# Amazon ECR repository for core service container images
resource "aws_ecr_repository" "core_app_repo" {
  name                 = "${local.name}-repo"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.tags
}

# ECR Lifecycle Policy - keep up to 10 images
resource "aws_ecr_lifecycle_policy" "core_app_lifecycle" {
  repository = aws_ecr_repository.core_app_repo.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
