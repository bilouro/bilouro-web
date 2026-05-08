output "ecr_repository_url" {
  value       = aws_ecr_repository.web.repository_url
  description = "Push images here."
}

output "ecr_login_command" {
  value       = "aws ecr get-login-password --region ${var.aws_region} --profile ${var.aws_profile} | docker login --username AWS --password-stdin ${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com"
  description = "Run this to authenticate Docker with ECR."
}

output "rds_endpoint" {
  value       = aws_db_instance.main.endpoint
  description = "Postgres endpoint (private — only reachable from App Runner VPC connector)."
  sensitive   = true
}

output "s3_media_bucket" {
  value = aws_s3_bucket.media.id
}

output "secret_db_url_arn" {
  value     = aws_secretsmanager_secret.db_url.arn
  sensitive = true
}

output "secret_django_secret_key_arn" {
  value     = aws_secretsmanager_secret.django_secret_key.arn
  sensitive = true
}

output "apprunner_service_url" {
  value       = try(aws_apprunner_service.web[0].service_url, null)
  description = "Public App Runner URL (null until enable_apprunner=true)."
}

output "aws_account_id" {
  value = data.aws_caller_identity.current.account_id
}
