# Terraform — AWS provisioning

Provisions the cloud target for the ai-equity stack: a VPC, an ECS Fargate
cluster running the four services, RDS Postgres, ElastiCache Redis, a
self-hosted Qdrant on EC2, an S3 uploads bucket, Secrets Manager entries
mirroring [backend-ai/.env.example](../../backend-ai/.env.example), an
ALB with HTTP/HTTPS termination, IAM roles (including the GitHub OIDC role
the deploy workflow assumes), and CloudWatch log groups.

Single root module — flat file split keeps the wiring readable at this
size. If you add a second environment, fork the directory rather than
introducing a workspaces dance.

## File map

| File | What's in it |
|---|---|
| [versions.tf](versions.tf)             | Provider pins + the (commented) S3 backend block |
| [providers.tf](providers.tf)           | AWS provider with default tags |
| [variables.tf](variables.tf)           | All input variables |
| [locals.tf](locals.tf)                 | Naming conventions, data sources |
| [networking.tf](networking.tf)         | VPC, subnets, route tables, NAT, security groups |
| [ecr.tf](ecr.tf)                       | Two image repos with lifecycle policy |
| [rds.tf](rds.tf)                       | Postgres 15 with subnet group, encryption, snapshots |
| [elasticache.tf](elasticache.tf)       | Redis 7 single-node |
| [qdrant.tf](qdrant.tf)                 | EC2 host + EBS volume, systemd-managed Docker |
| [s3.tf](s3.tf)                         | Uploads bucket (versioning + SSE + public-block) |
| [secrets.tf](secrets.tf)               | Secrets Manager: managed (DB URL, JWT) + external (vendor keys) |
| [iam.tf](iam.tf)                       | Task execution role, task role, GitHub Actions OIDC role |
| [alb.tf](alb.tf)                       | ALB, two target groups, listener rules |
| [cloudwatch.tf](cloudwatch.tf)         | One log group per service |
| [ecs.tf](ecs.tf)                       | Cluster + four task definitions + four services + migrate task |
| [outputs.tf](outputs.tf)               | Values to wire into GitHub Actions vars |
| [terraform.tfvars.example](terraform.tfvars.example) | Sample inputs |

## Bootstrap order

This module assumes its remote state already exists. The flow:

### 1. Create the state backend (one-time, manual)

```bash
aws s3api create-bucket \
  --bucket ai-equity-tfstate \
  --region ap-south-1 \
  --create-bucket-configuration LocationConstraint=ap-south-1

aws s3api put-bucket-versioning \
  --bucket ai-equity-tfstate \
  --versioning-configuration Status=Enabled

aws dynamodb create-table \
  --table-name ai-equity-tflock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-south-1
```

Then uncomment the `backend "s3"` block in [versions.tf](versions.tf).

### 2. First apply — ECR only

CI needs somewhere to push the first image. Apply ECR before everything
else so the image push and the rest of the infra can proceed in parallel.

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars     # edit values
terraform init
terraform apply -target=aws_ecr_repository.backend -target=aws_ecr_repository.frontend
```

### 3. Push initial images

Run [.github/workflows/deploy.yml](../../.github/workflows/deploy.yml) via
`workflow_dispatch` with `skip_migrate: "true"` (RDS doesn't exist yet),
**or** push images locally:

```bash
aws ecr get-login-password --region ap-south-1 \
  | docker login --username AWS --password-stdin <ECR_REGISTRY>

docker build -f infrastructure/docker/backend.Dockerfile -t <ECR_REGISTRY>/ai-equity-backend:latest backend-ai
docker push <ECR_REGISTRY>/ai-equity-backend:latest

docker build \
  -f infrastructure/docker/frontend.Dockerfile \
  --build-context infra=infrastructure/docker \
  --build-arg VITE_BACKEND_URL=https://api.example.com \
  -t <ECR_REGISTRY>/ai-equity-frontend:latest frontend
docker push <ECR_REGISTRY>/ai-equity-frontend:latest
```

### 4. Full apply

```bash
terraform apply
```

### 5. Populate vendor secrets

Terraform creates the Secrets Manager entries empty — fill them in:

```bash
aws secretsmanager put-secret-value \
  --secret-id ai-equity-prod/GROQ_API_KEY \
  --secret-string "gsk_..."

# repeat for OPENAI_API_KEY, GEMINI_API_KEY, FMP_API_KEY, NEWS_API_KEY,
# UPSTOX_*, KITE_*, etc. (see secrets.tf for the full list)
```

`DATABASE_URL` and `AUTH_JWT_SECRET` are already populated by Terraform.

### 6. Run the first migration

```bash
bash infrastructure/ci_cd/run-migrate.sh
```

(Or trigger the deploy workflow with `skip_migrate: "false"`.)

### 7. Wire up GitHub Actions

Copy `terraform output` values into repo settings — see
[../ci_cd/README.md](../ci_cd/README.md) for the full table.

## Verify

```bash
terraform fmt -check -recursive
terraform validate
terraform plan          # should show no changes after a clean apply
```

## Tear down

```bash
# RDS has deletion_protection = true — disable in tfvars first, then:
terraform apply -var=db_deletion_protection=false   # (add the var if you wire one)
terraform destroy
```

The S3 uploads bucket has versioning on; Terraform will refuse to delete a
non-empty bucket. Empty it manually first:

```bash
aws s3 rm s3://<uploads-bucket> --recursive
```
