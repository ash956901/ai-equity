# Infrastructure

Cloud and CI artifacts for the ai-equity stack.

| Folder | Purpose |
|---|---|
| [docker/](docker/)       | Dockerfiles for backend and frontend, the nginx config that serves the SPA, and a `docker-compose.prod.yml` for local prod-image smoke tests. |
| [ci_cd/](ci_cd/)         | Helper scripts and documentation for the deploy pipeline. The actual GitHub Actions workflow lives at [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) (Actions discovers workflows under `.github/workflows/` only). |
| [terraform/](terraform/) | AWS provisioning for the production environment (ECS Fargate, RDS, ElastiCache, EC2-hosted Qdrant, S3, Secrets Manager, ALB, IAM, CloudWatch). |

## Topology

```
                       Internet
                          │
                       ALB (public)
            ┌─────────────┴─────────────┐
            │                           │
   /api/* /auth/* /healthz             default
            │                           │
   ECS Service: api          ECS Service: frontend
   (uvicorn :8001, x2)       (nginx :80, x2)
            │
            ├─── ECS Service: worker  (celery worker)
            ├─── ECS Service: beat    (celery beat, x1)
            └─── ECS Task     : migrate (one-shot, alembic upgrade head)
                                │
        ┌───────────────────────┼─────────────────────────┐
        ▼                       ▼                         ▼
   RDS Postgres 15      ElastiCache Redis 7       EC2 host: Qdrant
   (private subnets)    (private subnets)         (private subnets, EBS)

   Secrets Manager: DATABASE_URL, AUTH_JWT_SECRET, vendor API keys
   S3:              ai-equity-prod-uploads-* (document uploads)
```

## Where each env var goes

[`backend-ai/.env.example`](../backend-ai/.env.example) is the source of
truth for the backend's runtime config. In the cloud:

- **Non-secret values** (`API_HOST`, `API_PORT`, `LLM_PROVIDER`, embedding
  config, `EMAIL_*`, `WORKFLOW_RUNS_DIR`, `S3_UPLOADS_BUCKET`, etc.) live
  in the `environment` block of each ECS task definition. See
  [`terraform/ecs.tf`](terraform/ecs.tf) → `local.backend_env`.
- **Secrets** (`DATABASE_URL`, `AUTH_JWT_SECRET`, all vendor API keys)
  live in AWS Secrets Manager. The ECS agent injects them at task launch
  via the container's `secrets` block. See
  [`terraform/secrets.tf`](terraform/secrets.tf).

## Running locally

The dev `docker compose up` flow at the repo root is unchanged — Postgres,
Redis, and Qdrant boot from the original [`docker-compose.yml`](../docker-compose.yml)
and the API + worker run on the host.

To test the production images before pushing:

```bash
docker compose -f infrastructure/docker/docker-compose.prod.yml up --build
```

Hits: <http://localhost:8001/healthz> (api), <http://localhost:8080/> (frontend).
