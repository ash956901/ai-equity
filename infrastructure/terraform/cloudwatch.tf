resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${local.api_service}"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${local.worker_service}"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "beat" {
  name              = "/ecs/${local.beat_service}"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/${local.frontend_service}"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "migrate" {
  name              = "/ecs/${local.migrate_task_name}"
  retention_in_days = 30
}
