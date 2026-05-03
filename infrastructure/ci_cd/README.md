# CI/CD

GitHub Actions drives the deploy pipeline. The workflow files live under
[.github/workflows/](../../.github/workflows/) (where Actions discovers them);
this folder holds the helper scripts the workflows shell out to and the
documentation for the pipeline as a whole.

## Pipeline overview

```
PR opened ──▶ backend.yml + frontend.yml          (lint / type-check / tests)
push main ──▶ deploy.yml
                │
                ├── build-backend  ──▶ ECR (sha + latest)
                ├── build-frontend ──▶ ECR (sha + latest)
                ├── migrate         ──▶ ECS run-task (alembic upgrade head)
                └── deploy          ──▶ ECS register new task def + update services
                                          (api, worker, beat, frontend)
```

[backend.yml](../../.github/workflows/backend.yml) and
[frontend.yml](../../.github/workflows/frontend.yml) keep their existing role
as PR gates — they are not modified by this folder. Image builds are gated
behind `push: branches: [main]` plus manual `workflow_dispatch` so a broken
PR can never reach ECR.

## Required GitHub configuration

Set these under **Settings → Secrets and variables → Actions**.

| Kind   | Name                  | Value                                                |
|--------|-----------------------|------------------------------------------------------|
| secret | `AWS_ROLE_ARN`        | OIDC role ARN — created by [terraform/iam.tf](../terraform/iam.tf) |
| var    | `AWS_REGION`          | e.g. `ap-south-1`                                    |
| var    | `ECR_REGISTRY`        | `<acct-id>.dkr.ecr.<region>.amazonaws.com`           |
| var    | `ECS_CLUSTER`         | `ai-equity-prod`                                     |
| var    | `ECS_API_SERVICE`     | `ai-equity-api`                                      |
| var    | `ECS_WORKER_SERVICE`  | `ai-equity-worker`                                   |
| var    | `ECS_BEAT_SERVICE`    | `ai-equity-beat`                                     |
| var    | `ECS_FRONTEND_SERVICE`| `ai-equity-frontend`                                 |
| var    | `ECS_MIGRATE_TASK`    | `ai-equity-migrate`                                  |
| var    | `ECS_MIGRATE_SUBNETS` | `subnet-aaa,subnet-bbb` (private)                    |
| var    | `ECS_MIGRATE_SG`      | `sg-xxx` (the ECS task SG)                           |
| var    | `VITE_BACKEND_URL`    | public API origin baked into the SPA                 |

The first eight values are produced by `terraform output` after the
infrastructure is provisioned. The OIDC role trusts the repo's
`token.actions.githubusercontent.com` and is restricted to the `ref:refs/heads/main`
condition.

## Helper scripts

### [deploy-ecs.sh](deploy-ecs.sh)

Idempotent rolling deploy:
1. Reads each service's current task definition.
2. Rewrites every container's `image` to the new SHA-tagged image.
3. Registers a new task definition revision.
4. Calls `update-service` against the new revision.
5. Blocks on `aws ecs wait services-stable`.

We do **not** rely on `update-service --force-new-deployment` against
`:latest`, because that pattern has no commit-correlation and makes
rollback ambiguous. Each deploy produces a numbered revision tied to a
commit SHA.

### [run-migrate.sh](run-migrate.sh)

Runs the one-shot migration container with the image just pushed. Uses
`run-task` with a container override so we don't have to register a new
revision of the migrate task on every deploy. Blocks until the task exits
and surfaces a non-zero exit code if `alembic upgrade head` fails — that
fails the workflow before any service is rolled.

## Rollback

The CI history shows which commit produced which task-definition revision.
To roll back:

```bash
aws ecs update-service \
  --cluster  ai-equity-prod \
  --service  ai-equity-api \
  --task-definition ai-equity-api:NN   # NN = previous revision number
```

For a multi-service rollback, point all four (`api`, `worker`, `beat`,
`frontend`) at their respective previous revisions. Repeat per service —
revisions are independent. Migrations are forward-only; a code rollback
that is incompatible with the current schema needs a corresponding down
migration authored by hand.

## Local validation before pushing

```bash
# Build images locally and run the prod compose stack.
docker compose -f infrastructure/docker/docker-compose.prod.yml up --build

# Hit the API and frontend.
curl -f http://localhost:8001/healthz
curl -f http://localhost:8080/
```
