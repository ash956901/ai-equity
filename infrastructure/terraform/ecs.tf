# ECS Fargate cluster, four long-running services, and one standalone
# migrate task definition that the deploy workflow invokes via run-task.
#
# All four backend tasks (api, worker, beat, migrate) share the same image
# but override `command`. The frontend service uses the frontend image.

resource "aws_ecs_cluster" "main" {
  name = local.cluster_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name       = aws_ecs_cluster.main.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
  }
}

# ------------------------------------------------------------------
# Shared environment & secrets blocks for backend containers
# ------------------------------------------------------------------

locals {
  backend_image  = "${aws_ecr_repository.backend.repository_url}:${var.image_tag}"
  frontend_image = "${aws_ecr_repository.frontend.repository_url}:${var.image_tag}"

  # Non-secret env. The full keys map to backend-ai/.env.example.
  backend_env = [
    { name = "APP_ENV", value = var.environment },
    { name = "API_HOST", value = "0.0.0.0" },
    { name = "API_PORT", value = "8001" },
    { name = "DEBUG", value = "false" },
    { name = "REDIS_URL", value = "redis://${aws_elasticache_cluster.main.cache_nodes[0].address}:6379/0" },
    { name = "CELERY_BROKER_URL", value = "redis://${aws_elasticache_cluster.main.cache_nodes[0].address}:6379/0" },
    { name = "QDRANT_URL", value = "http://${aws_instance.qdrant.private_ip}:6333" },
    { name = "LLM_PROVIDER", value = var.llm_provider },
    { name = "EMBEDDING_PROVIDER", value = var.embedding_provider },
    { name = "EMBEDDING_MODEL", value = var.embedding_model },
    { name = "EMBEDDING_DIM", value = tostring(var.embedding_dim) },
    { name = "OLLAMA_BASE_URL", value = var.ollama_base_url },
    { name = "WORKFLOW_RUNS_DIR", value = "/tmp/workflow_runs" },
    { name = "S3_UPLOADS_BUCKET", value = aws_s3_bucket.uploads.bucket },
    { name = "AWS_REGION", value = data.aws_region.current.name },
    { name = "AUTH_JWT_ALGORITHM", value = "HS256" },
    { name = "EMAIL_SENDER", value = "stub" },
    { name = "EMAIL_FROM", value = "no-reply@${var.domain_name == "" ? "equityai.local" : var.domain_name}" },
    { name = "EMAIL_APP_BASE_URL", value = var.domain_name == "" ? "http://localhost:5173" : "https://${var.domain_name}" },
  ]

  backend_secrets = [
    for env_name, arn in local.task_secrets_map :
    { name = env_name, valueFrom = arn }
  ]
}

# ------------------------------------------------------------------
# Task definitions
# ------------------------------------------------------------------

# API
resource "aws_ecs_task_definition" "api" {
  family                   = local.api_service
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = local.backend_image
    essential = true
    portMappings = [{
      containerPort = 8001
      protocol      = "tcp"
    }]
    environment = local.backend_env
    secrets     = local.backend_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.api.name
        awslogs-region        = data.aws_region.current.name
        awslogs-stream-prefix = "api"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "curl -fsS http://127.0.0.1:8001/healthz || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 30
    }
  }])

  lifecycle {
    # Image is updated by deploy-ecs.sh registering new revisions.
    ignore_changes = [container_definitions]
  }
}

# Worker
resource "aws_ecs_task_definition" "worker" {
  family                   = local.worker_service
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name        = "worker"
    image       = local.backend_image
    essential   = true
    command     = ["celery", "-A", "src.celery_app", "worker", "-l", "INFO"]
    environment = local.backend_env
    secrets     = local.backend_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.worker.name
        awslogs-region        = data.aws_region.current.name
        awslogs-stream-prefix = "worker"
      }
    }
  }])

  lifecycle {
    ignore_changes = [container_definitions]
  }
}

# Beat
resource "aws_ecs_task_definition" "beat" {
  family                   = local.beat_service
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.beat_cpu
  memory                   = var.beat_memory
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name        = "beat"
    image       = local.backend_image
    essential   = true
    command     = ["celery", "-A", "src.celery_app", "beat", "-l", "INFO"]
    environment = local.backend_env
    secrets     = local.backend_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.beat.name
        awslogs-region        = data.aws_region.current.name
        awslogs-stream-prefix = "beat"
      }
    }
  }])

  lifecycle {
    ignore_changes = [container_definitions]
  }
}

# Migrate (one-shot — invoked by run-migrate.sh, never as a service)
resource "aws_ecs_task_definition" "migrate" {
  family                   = local.migrate_task_name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name        = "migrate"
    image       = local.backend_image
    essential   = true
    command     = ["alembic", "upgrade", "head"]
    environment = local.backend_env
    secrets     = local.backend_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.migrate.name
        awslogs-region        = data.aws_region.current.name
        awslogs-stream-prefix = "migrate"
      }
    }
  }])

  lifecycle {
    ignore_changes = [container_definitions]
  }
}

# Frontend
resource "aws_ecs_task_definition" "frontend" {
  family                   = local.frontend_service
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.frontend_cpu
  memory                   = var.frontend_memory
  execution_role_arn       = aws_iam_role.task_execution.arn

  container_definitions = jsonencode([{
    name      = "frontend"
    image     = local.frontend_image
    essential = true
    portMappings = [{
      containerPort = 80
      protocol      = "tcp"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.frontend.name
        awslogs-region        = data.aws_region.current.name
        awslogs-stream-prefix = "frontend"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "wget -qO- http://127.0.0.1/healthz || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 15
    }
  }])

  lifecycle {
    ignore_changes = [container_definitions]
  }
}

# ------------------------------------------------------------------
# Services
# ------------------------------------------------------------------

resource "aws_ecs_service" "api" {
  name            = local.api_service
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8001
  }

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = 60

  lifecycle {
    # CI rolls these by registering new task definition revisions.
    ignore_changes = [task_definition, desired_count]
  }

  depends_on = [aws_lb_listener.http]
}

resource "aws_ecs_service" "worker" {
  name            = local.worker_service
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.worker_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 0 # workers are stateless; allow brief gaps
  deployment_maximum_percent         = 200

  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }
}

resource "aws_ecs_service" "beat" {
  name            = local.beat_service
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.beat.arn
  desired_count   = 1 # never run more than one beat scheduler
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  # Beat is single-instance; force replacement, never overlap.
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  lifecycle {
    ignore_changes = [task_definition]
  }
}

resource "aws_ecs_service" "frontend" {
  name            = local.frontend_service
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = var.frontend_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 80
  }

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = 30

  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  depends_on = [aws_lb_listener.http]
}
