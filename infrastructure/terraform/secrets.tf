# Secrets Manager entries for everything the backend reads from env that
# is sensitive. Names match keys in backend-ai/.env.example so an operator
# can copy values in directly.
#
# DATABASE_URL is constructed from RDS attributes + the random password.
# The rest start as empty placeholders — operator updates the value via
# `aws secretsmanager put-secret-value`. Empty entries are tolerated by
# the application (Settings uses Optional types for vendor keys).

locals {
  database_url = format(
    "postgresql://%s:%s@%s:%d/%s",
    var.db_username,
    random_password.db.result,
    aws_db_instance.main.address,
    aws_db_instance.main.port,
    aws_db_instance.main.db_name,
  )

  # Keys that are filled by Terraform vs. populated out-of-band. The bool
  # is whether terraform manages the value.
  managed_secrets = {
    "DATABASE_URL"    = local.database_url
    "AUTH_JWT_SECRET" = random_password.jwt.result
  }

  external_secrets = [
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
    "DEEPSEEK_API_KEY",
    "GEMINI_API_KEY",
    "TAVILY_API_KEY",
    "FMP_API_KEY",
    "ALPHA_VANTAGE_API_KEY",
    "FRED_API_KEY",
    "NEWS_API_KEY",
    "NEWSDATA_API_KEY",
    "UPSTOX_API_KEY",
    "UPSTOX_API_SECRET",
    "UPSTOX_ACCESS_TOKEN",
    "KITE_API_KEY",
    "KITE_API_SECRET",
    "KITE_ACCESS_TOKEN",
    "QDRANT_API_KEY",
  ]
}

resource "random_password" "jwt" {
  length  = 64
  special = false
}

# Terraform-managed secrets (DATABASE_URL, AUTH_JWT_SECRET).
resource "aws_secretsmanager_secret" "managed" {
  for_each = local.managed_secrets
  name     = "${local.name}/${each.key}"
}

resource "aws_secretsmanager_secret_version" "managed" {
  for_each      = local.managed_secrets
  secret_id     = aws_secretsmanager_secret.managed[each.key].id
  secret_string = each.value
}

# Out-of-band secrets — created empty, populated manually after first apply.
resource "aws_secretsmanager_secret" "external" {
  for_each = toset(local.external_secrets)
  name     = "${local.name}/${each.key}"
}

resource "aws_secretsmanager_secret_version" "external_placeholder" {
  for_each      = toset(local.external_secrets)
  secret_id     = aws_secretsmanager_secret.external[each.key].id
  secret_string = "REPLACE_ME"

  lifecycle {
    # Operators update these values directly; do not let TF clobber them.
    ignore_changes = [secret_string]
  }
}

# Aggregate all secret ARNs for IAM + ECS task definitions.
locals {
  all_secret_arns = concat(
    [for s in aws_secretsmanager_secret.managed : s.arn],
    [for s in aws_secretsmanager_secret.external : s.arn],
  )

  # Map of env-var-name -> secret ARN for use in container `secrets` blocks.
  task_secrets_map = merge(
    { for k, s in aws_secretsmanager_secret.managed : k => s.arn },
    { for k, s in aws_secretsmanager_secret.external : k => s.arn },
  )
}
