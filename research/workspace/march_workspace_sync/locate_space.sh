#!/usr/bin/env bash
# READ-ONLY. Run in AWS CloudShell, not in a new SageMaker space.
set -euo pipefail
export AWS_PAGER=""
REGION="us-west-2"
SPACE="march-mania-dev"
DOMAIN_ID="$(aws sagemaker list-spaces --region "$REGION" \
  --cli-connect-timeout 10 --cli-read-timeout 30 \
  --query "Spaces[?SpaceName=='${SPACE}'].DomainId" --output text)"
if [[ -z "$DOMAIN_ID" || "$DOMAIN_ID" == "None" || "$DOMAIN_ID" == *$'\t'* || "$DOMAIN_ID" == *$'\n'* ]]; then
  echo "STOP: expected exactly one matching space. No resources were changed."
  aws sagemaker list-spaces --region "$REGION" --output table \
    --query 'Spaces[].[DomainId,SpaceName,Status]'
  exit 1
fi
aws sagemaker describe-domain --region "$REGION" --domain-id "$DOMAIN_ID" \
  --cli-connect-timeout 10 --cli-read-timeout 30 \
  --query '{DomainName:DomainName,DomainId:DomainId}' --output table
aws sagemaker describe-space --region "$REGION" --domain-id "$DOMAIN_ID" --space-name "$SPACE" \
  --cli-connect-timeout 10 --cli-read-timeout 30 \
  --query '{Space:SpaceName,Status:Status,OwnerProfile:OwnershipSettings.OwnerUserProfileName,InstanceType:SpaceSettings.JupyterLabAppSettings.DefaultResourceSpec.InstanceType}' \
  --output table
printf '\nSelect that domain and owner profile in SageMaker AI -> Studio, then open the existing %s space.\n' "$SPACE"
printf 'Do not create a replacement domain, delete the space, or run project commands in CloudShell.\n'
