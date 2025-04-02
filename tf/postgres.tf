locals {
  app_db_username  = "unifyops_user"
  app_db_password  = "${var.org}_${random_password.app_db_password.result}"
  password_version = "4"
}

# Generate a secure password for the application user
resource "random_password" "app_db_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Create an application-specific database user
resource "postgresql_role" "app_user" {
  name     = local.app_db_username
  login    = true
  password = local.app_db_password

  depends_on = [
    data.terraform_remote_state.infra
  ]
}

# Grant appropriate permissions to the application user
resource "postgresql_grant" "app_user_permissions" {
  database    = data.terraform_remote_state.infra.outputs.rds_db_name
  role        = postgresql_role.app_user.name
  schema      = "public"
  object_type = "table"
  privileges  = ["SELECT", "INSERT", "UPDATE", "DELETE"]
}

# Store the application's database connection string in Secrets Manager
resource "aws_secretsmanager_secret" "app_db_url" {
  name        = "${var.infra_env}/app-db-url-v${local.password_version}"
  description = "Database connection string for the ${var.org} application"
}

resource "aws_secretsmanager_secret_version" "app_db_url" {
  secret_id     = aws_secretsmanager_secret.app_db_url.id
  secret_string = "postgresql://${local.app_db_username}:${local.app_db_password}@${data.terraform_remote_state.infra.outputs.rds_endpoint}/${data.terraform_remote_state.infra.outputs.rds_db_name}"

  depends_on = [
    postgresql_role.app_user,
    postgresql_grant.app_user_permissions
  ]
}
