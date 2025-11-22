variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table for messages"
  type        = string
  default     = "a2a-guestbook-messages"
}

variable "secret_name" {
  description = "Name of the Secrets Manager secret for API keys"
  type        = string
  default     = "a2a-guestbook/api-keys"
}

variable "initial_api_keys" {
  description = "Initial API keys to store in Secrets Manager"
  type        = list(string)
  default = [
    "dev-key-change-me",
    "test-key-change-me"
  ]
  sensitive = true
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "A2A-Guestbook"
    ManagedBy   = "Terraform"
    Environment = "dev"
  }
}
