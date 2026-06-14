variable "environment" {}

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
