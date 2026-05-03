#!/usr/bin/env bash
# run-migrate.sh
#
# Runs `alembic upgrade head` against RDS by overriding the migrate task
# definition's container image to the freshly built backend image. Blocks
# until the task exits and surfaces the exit code.
#
# Required env vars:
#   ECS_CLUSTER          - cluster name
#   ECS_MIGRATE_TASK     - task definition family for the one-shot migrate task
#   ECS_MIGRATE_SUBNETS  - comma-separated private subnet IDs
#   ECS_MIGRATE_SG       - security group ID matching the ECS task SG
#   IMAGE                - backend image to run

set -euo pipefail

: "${ECS_CLUSTER:?}"
: "${ECS_MIGRATE_TASK:?}"
: "${ECS_MIGRATE_SUBNETS:?}"
: "${ECS_MIGRATE_SG:?}"
: "${IMAGE:?}"

# Normalize the comma-separated subnet list into the array shape the API needs.
subnets="${ECS_MIGRATE_SUBNETS//,/\",\"}"
network_config="awsvpcConfiguration={subnets=[\"${subnets}\"],securityGroups=[\"${ECS_MIGRATE_SG}\"],assignPublicIp=DISABLED}"

# Find the container name in the task definition (first container).
container_name="$(aws ecs describe-task-definition \
    --task-definition "$ECS_MIGRATE_TASK" \
    --query 'taskDefinition.containerDefinitions[0].name' \
    --output text)"

overrides="$(jq -nc --arg name "$container_name" --arg image "$IMAGE" '
    {
      containerOverrides: [
        { name: $name, image: $image }
      ]
    }')"

echo "Starting migrate task with image $IMAGE"
task_arn="$(aws ecs run-task \
    --cluster        "$ECS_CLUSTER" \
    --task-definition "$ECS_MIGRATE_TASK" \
    --launch-type    FARGATE \
    --network-configuration "$network_config" \
    --overrides      "$overrides" \
    --query 'tasks[0].taskArn' \
    --output text)"

if [[ -z "$task_arn" || "$task_arn" == "None" ]]; then
    echo "ERROR: failed to start migrate task" >&2
    exit 1
fi

echo "Task: $task_arn"
echo "Waiting for migration to complete..."
aws ecs wait tasks-stopped --cluster "$ECS_CLUSTER" --tasks "$task_arn"

exit_code="$(aws ecs describe-tasks \
    --cluster "$ECS_CLUSTER" \
    --tasks   "$task_arn" \
    --query   'tasks[0].containers[0].exitCode' \
    --output  text)"

reason="$(aws ecs describe-tasks \
    --cluster "$ECS_CLUSTER" \
    --tasks   "$task_arn" \
    --query   'tasks[0].stoppedReason' \
    --output  text)"

echo "Migration container exitCode=$exit_code, stoppedReason=$reason"

if [[ "$exit_code" != "0" ]]; then
    echo "ERROR: migration failed" >&2
    exit 1
fi
