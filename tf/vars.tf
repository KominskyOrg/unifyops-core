###############################################################################
# Core Infrastructure Variables
###############################################################################

variable "org" {
  type        = string
  description = "The organization name"
  default     = "unifyops"
}

variable "project_name" {
  type        = string
  description = "The project name"
  default     = "api"
}

variable "region" {
  type        = string
  description = "The region to deploy the resources"
  default     = "us-east-1"
}

variable "infra_env" {
  type        = string
  description = "The infrastructure environment"
  default     = "dev"
}

variable "db_password" {
  type        = string
  description = "The password for the database"
}
