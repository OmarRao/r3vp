variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "vpc_id" {
  description = "VPC ID for the deployment"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS tasks and RDS"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for the ALB"
  type        = list(string)
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS"
  type        = string
}

variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

variable "api_image" {
  description = "ECR image URI for the API container"
  type        = string
  default     = "123456789012.dkr.ecr.us-east-1.amazonaws.com/r3vp-api:latest"
}

variable "auth0_domain" {
  description = "Auth0 domain for JWT verification"
  type        = string
  default     = ""
}

variable "auth0_audience" {
  description = "Auth0 API audience"
  type        = string
  default     = ""
}
