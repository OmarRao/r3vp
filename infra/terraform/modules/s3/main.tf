# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

variable "environment" {}

resource "aws_s3_bucket" "evidence" {
  bucket = "r3vp-evidence-${var.environment}"
  tags   = { Environment = var.environment }
}

resource "aws_s3_bucket_versioning" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  rule {
    id     = "expire-old-evidence"
    status = "Enabled"
    expiration { days = 365 }
  }
}

output "bucket_name" {
  value = aws_s3_bucket.evidence.bucket
}
