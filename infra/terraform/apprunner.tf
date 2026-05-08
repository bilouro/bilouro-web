# App Runner is gated behind a variable so we can apply infra first,
# then build/push the image, then enable the service in a second apply.

variable "enable_apprunner" {
  type        = bool
  default     = false
  description = "Set to true after the Docker image has been pushed to ECR."
}

variable "image_tag" {
  type    = string
  default = "latest"
}

resource "aws_apprunner_vpc_connector" "main" {
  count              = var.enable_apprunner ? 1 : 0
  vpc_connector_name = "${local.name_prefix}-vpc-connector"
  subnets            = data.aws_subnets.default.ids
  security_groups    = [aws_security_group.apprunner_vpc.id]
}

resource "aws_apprunner_service" "web" {
  count        = var.enable_apprunner ? 1 : 0
  service_name = "${local.name_prefix}-web"

  source_configuration {
    auto_deployments_enabled = true

    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access.arn
    }

    image_repository {
      image_identifier      = "${aws_ecr_repository.web.repository_url}:${var.image_tag}"
      image_repository_type = "ECR"

      image_configuration {
        port = "8000"

        runtime_environment_variables = {
          DJANGO_SETTINGS_MODULE = "config.settings.prod"
          ALLOWED_HOSTS          = "*"
          AWS_STORAGE_BUCKET_NAME = aws_s3_bucket.media.id
          AWS_S3_REGION_NAME      = var.aws_region
          AWS_SES_REGION_NAME     = var.aws_region
          DEFAULT_FROM_EMAIL      = "hello@${var.domain}"
          WAGTAILADMIN_BASE_URL   = "https://www.${var.domain}"
          SECURE_SSL_REDIRECT     = "True"
          CSRF_TRUSTED_ORIGINS    = join(",", [for sd in var.subdomains : "https://${sd}.${var.domain}"])
        }

        runtime_environment_secrets = {
          DATABASE_URL = aws_secretsmanager_secret.db_url.arn
          SECRET_KEY   = aws_secretsmanager_secret.django_secret_key.arn
        }
      }
    }
  }

  instance_configuration {
    cpu               = "256"
    memory            = "512"
    instance_role_arn = aws_iam_role.apprunner_instance.arn
  }

  network_configuration {
    egress_configuration {
      egress_type       = "VPC"
      vpc_connector_arn = aws_apprunner_vpc_connector.main[0].arn
    }

    ingress_configuration {
      is_publicly_accessible = true
    }
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/healthz/"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }
}
