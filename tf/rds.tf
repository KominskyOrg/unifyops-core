resource "aws_db_subnet_group" "unifyops" {
  name       = "unifyops-db-subnet-group"
  subnet_ids = data.terraform_remote_state.infra.outputs.private_subnets

  tags = {
    Name = "UnifyOps DB subnet group"
  }
}

# Define a security group for the database
resource "aws_security_group" "db" {
  name        = "unifyops-db-sg"
  description = "Allow traffic from ECS to RDS"
  vpc_id      = data.terraform_remote_state.infra.outputs.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [data.terraform_remote_state.infra.outputs.ecs_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "UnifyOps DB Security Group"
  }
}

# Create the RDS instance
resource "aws_db_instance" "unifyops" {
  identifier              = var.org
  engine                  = "postgres"
  engine_version          = "14.6"
  instance_class          = "db.t3.micro"
  allocated_storage       = 20
  max_allocated_storage   = 20
  storage_encrypted       = false
  db_name                 = var.org
  username                = "postgres"
  password                = var.db_password
  parameter_group_name    = "default.postgres14"
  db_subnet_group_name    = aws_db_subnet_group.unifyops.name
  vpc_security_group_ids  = [aws_security_group.db.id]
  publicly_accessible     = false
  skip_final_snapshot     = true
  backup_retention_period = 1
  deletion_protection     = false
  apply_immediately       = false

  tags = {
    Name        = "UnifyOps Database"
    Environment = "Development"
  }
}

# Create a secret for the database URL
resource "aws_secretsmanager_secret" "db_url" {
  name = "unifyops/db-url"
}

resource "aws_secretsmanager_secret_version" "db_url" {
  secret_id     = aws_secretsmanager_secret.db_url.id
  secret_string = "postgresql://${aws_db_instance.unifyops.username}:${var.db_password}@${aws_db_instance.unifyops.endpoint}/${aws_db_instance.unifyops.db_name}"
}
