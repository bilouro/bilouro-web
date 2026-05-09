output "s3_media_bucket" {
  value       = aws_s3_bucket.media.id
  description = "S3 bucket for Wagtail media — used by Lightsail."
}

output "aws_account_id" {
  value = data.aws_caller_identity.current.account_id
}
