# Postgres 15 to match the dev compose pin (postgres:15-alpine in
# docker-compose.yml). The application config — Settings.database_url —
# defaults to the same DB name `equity_research`, so we keep it.

resource "random_password" "db" {
  length  = 32
  special = false # Postgres URI gets noisy with escapes; alphanumeric is fine.
}

resource "aws_db_subnet_group" "main" {
  name       = "${local.name}-db-subnets"
  subnet_ids = aws_subnet.private[*].id

  tags = { Name = "${local.name}-db-subnets" }
}

resource "aws_db_instance" "main" {
  identifier     = "${local.name}-db"
  engine         = "postgres"
  engine_version = "15"
  instance_class = var.db_instance_class

  db_name  = "equity_research"
  username = var.db_username
  password = random_password.db.result
  port     = 5432

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  multi_az               = false # single-AZ to keep costs predictable; flip for HA
  publicly_accessible    = false

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "Sun:04:30-Sun:05:30"

  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.name}-db-final-${formatdate("YYYYMMDD-hhmmss", timestamp())}"

  deletion_protection = true

  performance_insights_enabled          = true
  performance_insights_retention_period = 7

  apply_immediately = false

  lifecycle {
    ignore_changes = [
      # The password rotation flow lives in Secrets Manager. Don't let drift
      # in the password attribute force-replace the DB.
      password,
      # Same for the snapshot suffix — it's deliberately timestamp-driven.
      final_snapshot_identifier,
    ]
  }
}
