terraform {
  required_version = ">= 1.8"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket = "r3vp-terraform-state"
    key    = "infra/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}

module "rds" {
  source             = "./modules/rds"
  environment        = var.environment
  vpc_id             = var.vpc_id
  subnet_ids         = var.private_subnet_ids
  db_password        = var.db_password
}

module "s3" {
  source      = "./modules/s3"
  environment = var.environment
}

module "alb" {
  source            = "./modules/alb"
  environment       = var.environment
  vpc_id            = var.vpc_id
  public_subnet_ids = var.public_subnet_ids
  certificate_arn   = var.certificate_arn
}

module "ecs" {
  source               = "./modules/ecs"
  environment          = var.environment
  db_url               = module.rds.connection_url
  api_image            = var.api_image
  vpc_id               = var.vpc_id
  private_subnet_ids   = var.private_subnet_ids
  alb_target_group_arn = module.alb.target_group_arn
  auth0_domain         = var.auth0_domain
  auth0_audience       = var.auth0_audience
  s3_evidence_bucket   = module.s3.bucket_name
  aws_region           = var.aws_region
}

module "cloudfront" {
  source       = "./modules/cloudfront"
  environment  = var.environment
  alb_dns_name = module.alb.alb_dns_name
}

# Reference outputs from modules for the outputs.tf file
locals {
  api_url           = "https://${module.alb.alb_dns_name}"
  cloudfront_domain = module.cloudfront.domain_name
}
