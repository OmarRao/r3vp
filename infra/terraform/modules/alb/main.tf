# Application Load Balancer for R3VP API
# Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy

variable "environment" {}
variable "vpc_id" { default = "" }
variable "public_subnet_ids" { default = [] }
variable "certificate_arn" { default = "" }

resource "aws_security_group" "alb" {
  name        = "r3vp-alb-${var.environment}"
  description = "R3VP ALB security group"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP redirect"
  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Project = "r3vp", Environment = var.environment, ManagedBy = "terraform" }
}

resource "aws_lb" "api" {
  name               = "r3vp-api-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids
  tags = { Project = "r3vp", Environment = var.environment, ManagedBy = "terraform" }
}

resource "aws_lb_target_group" "api" {
  name        = "r3vp-api-${var.environment}"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/health"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
    matcher             = "200"
  }
  tags = { Project = "r3vp", Environment = var.environment, ManagedBy = "terraform" }
}

resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.api.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.api.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

output "alb_dns_name" {
  value = aws_lb.api.dns_name
}

output "target_group_arn" {
  value = aws_lb_target_group.api.arn
}
