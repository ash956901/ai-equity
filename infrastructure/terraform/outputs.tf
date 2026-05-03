output "alb_dns_name" {
  description = "Public DNS for the ALB. CNAME your domain to this."
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "ALB hosted zone ID for Route53 alias records."
  value       = aws_lb.main.zone_id
}

output "ecr_backend_repo_url" {
  description = "Backend image registry URL — paste into deploy.yml ECR_REGISTRY var."
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_repo_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "ecr_registry" {
  description = "ECR registry hostname — value for the ECR_REGISTRY GitHub Actions var."
  value       = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com"
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_services" {
  description = "Service names — paste into the matching ECS_*_SERVICE GitHub vars."
  value = {
    api      = aws_ecs_service.api.name
    worker   = aws_ecs_service.worker.name
    beat     = aws_ecs_service.beat.name
    frontend = aws_ecs_service.frontend.name
  }
}

output "ecs_migrate_task_family" {
  value = aws_ecs_task_definition.migrate.family
}

output "ecs_migrate_subnets" {
  description = "Comma-separated private subnet IDs for ECS_MIGRATE_SUBNETS."
  value       = join(",", aws_subnet.private[*].id)
}

output "ecs_migrate_security_group" {
  value = aws_security_group.ecs_tasks.id
}

output "rds_endpoint" {
  description = "Postgres endpoint (host only)."
  value       = aws_db_instance.main.address
  sensitive   = true
}

output "redis_endpoint" {
  value = aws_elasticache_cluster.main.cache_nodes[0].address
}

output "qdrant_private_ip" {
  value = aws_instance.qdrant.private_ip
}

output "uploads_bucket" {
  value = aws_s3_bucket.uploads.bucket
}

output "github_actions_role_arn" {
  description = "Set as the AWS_ROLE_ARN GitHub secret. Empty if github_org/github_repo not set."
  value       = length(aws_iam_role.github_actions) > 0 ? aws_iam_role.github_actions[0].arn : ""
}
