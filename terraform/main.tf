terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# DynamoDB Table for Messages
resource "aws_dynamodb_table" "guestbook_messages" {
  name           = var.dynamodb_table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "message_id"
  range_key      = "timestamp"

  attribute {
    name = "message_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "entity_type"
    type = "S"
  }

  # GSI for chronological queries
  global_secondary_index {
    name            = "timestamp-index"
    hash_key        = "entity_type"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = false
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(
    var.tags,
    {
      Name = var.dynamodb_table_name
    }
  )
}

# Secrets Manager Secret for API Keys
resource "aws_secretsmanager_secret" "api_keys" {
  name                    = var.secret_name
  description             = "API keys for A2A Guestbook agents (development)"
  recovery_window_in_days = 0

  tags = merge(
    var.tags,
    {
      Name = var.secret_name
    }
  )
}

# Initial secret value with example API keys
resource "aws_secretsmanager_secret_version" "api_keys" {
  secret_id = aws_secretsmanager_secret.api_keys.id
  secret_string = jsonencode({
    api_keys = var.initial_api_keys
  })
}
