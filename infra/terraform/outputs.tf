output "api_url" {
  description = "HTTPS URL for the R3VP API"
  value       = "https://${module.alb.alb_dns_name}"
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain"
  value       = module.cloudfront.domain_name
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = module.rds.endpoint
  sensitive   = true
}

output "s3_evidence_bucket" {
  description = "S3 bucket name for evidence storage"
  value       = module.s3.bucket_name
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}
