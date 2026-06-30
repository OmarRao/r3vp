variable "environment" {}
variable "vpc_id" { default = "" }
variable "subnet_ids" { default = [] }
variable "db_password" {
  default   = ""
  sensitive = true
}

resource "aws_db_instance" "r3vp" {
  identifier        = "r3vp-${var.environment}"
  engine            = "postgres"
  engine_version    = "16.3"
  instance_class    = "db.t4g.medium"
  allocated_storage = 50
  db_name           = "r3vp"
  username          = "r3vp"
  password          = random_password.db.result
  storage_encrypted = true
  deletion_protection = true
  skip_final_snapshot = false

  # Ship Postgres logs to CloudWatch so security-relevant events are retained
  # and auditable (CWE-311: missing logging).
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  tags = { Environment = var.environment }
}

resource "random_password" "db" {
  length  = 32
  special = false
}

output "connection_url" {
  value     = "postgresql+asyncpg://${aws_db_instance.r3vp.username}:${random_password.db.result}@${aws_db_instance.r3vp.endpoint}/r3vp"
  sensitive = true
}

output "endpoint" {
  value     = aws_db_instance.r3vp.endpoint
  sensitive = true
}
