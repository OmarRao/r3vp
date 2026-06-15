# ECS Fargate service for the R3VP API
# Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
# https://www.linkedin.com/in/omarrao/

variable "environment" {}
variable "db_url" {}
variable "api_image" { default = "" }
variable "vpc_id" { default = "" }
variable "private_subnet_ids" { default = [] }
variable "alb_target_group_arn" { default = "" }
variable "auth0_domain" { default = "" }
variable "auth0_audience" { default = "" }
variable "s3_evidence_bucket" { default = "r3vp-evidence" }
variable "aws_region" { default = "us-east-1" }

resource "aws_ecs_cluster" "r3vp" {
  name = "r3vp-${var.environment}"
  tags = {
    Project     = "r3vp"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/r3vp-api-${var.environment}"
  retention_in_days = 30
  tags = {
    Project     = "r3vp"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role" "ecs_task_execution" {
  name = "r3vp-ecs-task-execution-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
  tags = { Project = "r3vp", ManagedBy = "terraform" }
}

resource "aws_iam_role_policy_attachment" "ecs_execution_basic" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task" {
  name = "r3vp-ecs-task-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
  tags = { Project = "r3vp", ManagedBy = "terraform" }
}

resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "r3vp-s3-evidence-${var.environment}"
  role = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
      Resource = "arn:aws:s3:::${var.s3_evidence_bucket}/*"
    }, {
      Effect   = "Allow"
      Action   = ["ses:SendEmail"]
      Resource = "*"
    }]
  })
}

resource "aws_security_group" "ecs" {
  name        = "r3vp-ecs-${var.environment}"
  description = "R3VP ECS tasks"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
    description = "API port from VPC"
  }

  tags = { Project = "r3vp", Environment = var.environment, ManagedBy = "terraform" }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "r3vp-api-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "api"
    image = var.api_image
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    environment = [
      { name = "R3VP_API_DATABASE_URL", value = var.db_url },
      { name = "R3VP_API_AUTH0_DOMAIN", value = var.auth0_domain },
      { name = "R3VP_API_AUTH0_AUDIENCE", value = var.auth0_audience },
      { name = "R3VP_API_S3_EVIDENCE_BUCKET", value = var.s3_evidence_bucket },
      { name = "R3VP_API_AWS_REGION", value = var.aws_region },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = "/ecs/r3vp-api-${var.environment}"
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "api"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  tags = { Project = "r3vp", Environment = var.environment, ManagedBy = "terraform" }
}

resource "aws_ecs_service" "api" {
  name            = "r3vp-api-${var.environment}"
  cluster         = aws_ecs_cluster.r3vp.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  dynamic "load_balancer" {
    for_each = var.alb_target_group_arn != "" ? [1] : []
    content {
      target_group_arn = var.alb_target_group_arn
      container_name   = "api"
      container_port   = 8000
    }
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  tags = { Project = "r3vp", Environment = var.environment, ManagedBy = "terraform" }
}

resource "aws_appautoscaling_target" "api" {
  max_capacity       = 4
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.r3vp.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "api_cpu" {
  name               = "r3vp-api-cpu-${var.environment}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

output "cluster_name" {
  value = aws_ecs_cluster.r3vp.name
}
