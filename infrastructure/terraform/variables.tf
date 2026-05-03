variable "environment" {
  description = "Environment name used in tags and resource names (e.g. prod, staging)."
  type        = string
  default     = "prod"
}

variable "region" {
  description = "AWS region."
  type        = string
}

variable "name_prefix" {
  description = "Prefix for resource names. All resources are named <prefix>-<environment>-..."
  type        = string
  default     = "ai-equity"
}

# ------------------------------------------------------------------
# Networking
# ------------------------------------------------------------------

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.40.0.0/16"
}

variable "az_count" {
  description = "Number of AZs to span. 2 is the minimum for an ALB."
  type        = number
  default     = 2

  validation {
    condition     = var.az_count >= 2 && var.az_count <= 3
    error_message = "az_count must be 2 or 3."
  }
}

# ------------------------------------------------------------------
# Compute sizing
# ------------------------------------------------------------------

variable "db_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.small"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GiB. Autoscales up to db_max_allocated_storage."
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "Upper bound for RDS storage autoscaling."
  type        = number
  default     = 100
}

variable "db_username" {
  description = "RDS master username."
  type        = string
  default     = "equity_admin"
}

variable "redis_node_type" {
  description = "ElastiCache node type."
  type        = string
  default     = "cache.t4g.micro"
}

variable "qdrant_instance_type" {
  description = "EC2 instance type for the Qdrant host."
  type        = string
  default     = "t4g.small"
}

variable "qdrant_volume_size" {
  description = "EBS volume size in GiB attached to Qdrant for /qdrant/storage."
  type        = number
  default     = 50
}

# ------------------------------------------------------------------
# ECS task sizing (Fargate CPU/memory pairs must be valid combos —
# see https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html)
# ------------------------------------------------------------------

variable "api_cpu" {
  description = "Fargate CPU units for the api service."
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "Fargate memory (MiB) for the api service."
  type        = number
  default     = 1024
}

variable "api_desired_count" {
  type    = number
  default = 2
}

variable "worker_cpu" {
  type    = number
  default = 1024
}

variable "worker_memory" {
  type    = number
  default = 2048
}

variable "worker_desired_count" {
  type    = number
  default = 1
}

variable "beat_cpu" {
  type    = number
  default = 256
}

variable "beat_memory" {
  type    = number
  default = 512
}

variable "frontend_cpu" {
  type    = number
  default = 256
}

variable "frontend_memory" {
  type    = number
  default = 512
}

variable "frontend_desired_count" {
  type    = number
  default = 2
}

# ------------------------------------------------------------------
# Application config (non-secret)
# ------------------------------------------------------------------

variable "llm_provider" {
  description = "LLM_PROVIDER passed to the backend."
  type        = string
  default     = "groq"
}

variable "embedding_provider" {
  description = "EMBEDDING_PROVIDER. Note: ollama embeddings require a self-hosted Ollama reachable from ECS — switch to a hosted embedding provider for cloud."
  type        = string
  default     = "ollama"
}

variable "embedding_model" {
  type    = string
  default = "nomic-embed-text"
}

variable "embedding_dim" {
  type    = number
  default = 768
}

variable "ollama_base_url" {
  description = "Optional URL of an external Ollama service. Empty string disables it."
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Optional FQDN for the ALB. If set, an ACM cert is provisioned and HTTPS:443 is added. Empty string serves HTTP:80 only."
  type        = string
  default     = ""
}

variable "image_tag" {
  description = "Image tag used in initial task definitions. Updated by CI on each deploy via deploy-ecs.sh."
  type        = string
  default     = "latest"
}
