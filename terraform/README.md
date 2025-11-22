# A2A Guestbook - Development Infrastructure

Simple Terraform configuration for local development. Creates:
- DynamoDB table for message storage
- Secrets Manager secret for API keys

## Quick Start

1. **Copy and configure variables:**
```bash
cp terraform.tfvars.example terraform.tfvars
```

2. **Generate secure API keys:**
```bash
openssl rand -hex 32  # Run this for each key you need
```

3. **Edit terraform.tfvars** with your generated keys

4. **Deploy:**
```bash
terraform init
terraform apply
```

5. **Get outputs for app configuration:**
```bash
terraform output
```

## What Gets Created

### DynamoDB Table
- Pay-per-request billing (cost-effective)
- GSI for chronological queries
- Server-side encryption enabled
- Point-in-time recovery disabled (dev only)

### Secrets Manager Secret
- Stores API keys in JSON format
- Immediate deletion on destroy (dev only)

## Configuration for Your App

After `terraform apply`, use these environment variables:

```bash
export AWS_REGION=$(terraform output -raw aws_region)
export DYNAMODB_TABLE_NAME=$(terraform output -raw dynamodb_table_name)
export API_KEYS_SECRET_NAME=$(terraform output -raw secret_name)
```

## Updating API Keys

```bash
# Edit terraform.tfvars with new keys
terraform apply
```

Or update directly:
```bash
aws secretsmanager update-secret \
  --secret-id a2a-guestbook/api-keys \
  --secret-string '{"api_keys":["new-key-1","new-key-2"]}'
```

## Cleanup

```bash
terraform destroy
```

## Cost

Minimal for development usage:
- DynamoDB: Pay-per-request (pennies for testing)
- Secrets Manager: ~$0.40/month

## IAM Permissions Needed

Your AWS credentials need:
- `dynamodb:CreateTable`, `dynamodb:DeleteTable`, `dynamodb:DescribeTable`
- `secretsmanager:CreateSecret`, `secretsmanager:DeleteSecret`, `secretsmanager:PutSecretValue`
