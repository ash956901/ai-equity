#!/usr/bin/env bash
# deploy-ecs.sh
#
# Roll one or more ECS services to a new container image. For each service,
# we copy the current task definition, swap the image of every container,
# register a new revision, and update the service to point at it.
#
# Required env vars:
#   ECS_CLUSTER  - cluster name
#   IMAGE        - fully qualified image (registry/repo:tag)
#   SERVICES     - whitespace-separated list of ECS service names
#
# Why register a new revision instead of just --force-new-deployment?
# `update-service --force-new-deployment` re-pulls the existing task
# definition's image, which is `:latest` only if the task def was authored
# that way. Registering a new revision pinned to an immutable SHA tag is
# the only way to guarantee what actually deploys, and it gives clean
# revision-based rollback (re-point service at the previous revision).

set -euo pipefail

: "${ECS_CLUSTER:?ECS_CLUSTER must be set}"
: "${IMAGE:?IMAGE must be set}"
: "${SERVICES:?SERVICES must be set (whitespace-separated)}"

for service in $SERVICES; do
    echo "::group::Deploying $service -> $IMAGE"

    current_arn="$(aws ecs describe-services \
        --cluster  "$ECS_CLUSTER" \
        --services "$service" \
        --query    'services[0].taskDefinition' \
        --output   text)"

    if [[ -z "$current_arn" || "$current_arn" == "None" ]]; then
        echo "ERROR: service $service not found in cluster $ECS_CLUSTER" >&2
        exit 1
    fi

    # Pull the current task definition and surgically swap every container's
    # image. jq drops the read-only fields the API rejects on register.
    new_def="$(aws ecs describe-task-definition \
        --task-definition "$current_arn" \
        --query 'taskDefinition' \
    | jq --arg IMAGE "$IMAGE" '
        .containerDefinitions |= map(.image = $IMAGE)
        | del(
            .taskDefinitionArn,
            .revision,
            .status,
            .requiresAttributes,
            .compatibilities,
            .registeredAt,
            .registeredBy
          )')"

    new_arn="$(aws ecs register-task-definition \
        --cli-input-json "$new_def" \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text)"

    echo "Registered $new_arn"

    aws ecs update-service \
        --cluster         "$ECS_CLUSTER" \
        --service         "$service" \
        --task-definition "$new_arn" \
        --force-new-deployment \
        --query 'service.deployments[0].id' \
        --output text >/dev/null

    echo "::endgroup::"
done

echo "Waiting for services to reach steady state..."
# shellcheck disable=SC2086
aws ecs wait services-stable \
    --cluster  "$ECS_CLUSTER" \
    --services $SERVICES

echo "All services stable."
