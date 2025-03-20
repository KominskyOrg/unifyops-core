# ===========================================
# ECS Task Definitions and Service Resources
# ===========================================

# Add a variable for the container image tag
variable "container_image_tag" {
  description = "The tag of the container image to deploy"
  type        = string
  default     = "latest" # Default to latest if not specified
}

# ECS Task Definition for EC2 launch type (Free Tier)
resource "aws_ecs_task_definition" "app_ec2" {
  family       = "${local.name}-app-ec2"
  network_mode = "bridge"

  # Reference execution and task roles from the infrastructure remote state
  execution_role_arn = data.terraform_remote_state.infra.outputs.ecs_task_execution_role_arn
  task_role_arn      = data.terraform_remote_state.infra.outputs.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name      = "app-container"
      image     = "${aws_ecr_repository.core_app_repo.repository_url}:${var.container_image_tag}"
      essential = true

      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "ENVIRONMENT"
          value = var.infra_env
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = data.terraform_remote_state.infra.outputs.ecs_log_group_name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "app"
        }
      }
    }
  ])

  tags = local.tags
}

# ECS Service definition for EC2 launch type
resource "aws_ecs_service" "app_service" {
  name            = "${local.name}-app-service"
  cluster         = data.terraform_remote_state.infra.outputs.ecs_cluster_id
  task_definition = aws_ecs_task_definition.app_ec2.arn
  desired_count   = 1
  launch_type     = "EC2"

  tags = local.tags
}

# Output the service ARN and name for reference
output "ecs_service_arn" {
  description = "The ARN of the ECS service"
  value       = aws_ecs_service.app_service.id
}

output "ecs_service_name" {
  description = "The name of the ECS service"
  value       = aws_ecs_service.app_service.name
}

output "task_definition_arn" {
  description = "The ARN of the active task definition"
  value       = aws_ecs_task_definition.app_ec2.arn
}

# Add cluster name output for the GitHub Actions workflow
output "ecs_cluster_name" {
  description = "The name of the ECS cluster"
  value       = data.terraform_remote_state.infra.outputs.ecs_cluster_name
}
