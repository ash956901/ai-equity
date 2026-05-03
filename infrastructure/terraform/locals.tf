locals {
  name = "${var.name_prefix}-${var.environment}"

  # Standardize resource naming so cross-file references don't drift.
  cluster_name      = "${local.name}-cluster"
  api_service       = "${local.name}-api"
  worker_service    = "${local.name}-worker"
  beat_service      = "${local.name}-beat"
  frontend_service  = "${local.name}-frontend"
  migrate_task_name = "${local.name}-migrate"

  ecr_backend_repo  = "${local.name}-backend"
  ecr_frontend_repo = "${local.name}-frontend"
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}
