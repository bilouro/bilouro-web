# AWS CodeBuild — builds the Docker image in the cloud and pushes to ECR.
# Useful when local Docker Desktop is unreliable.

resource "aws_s3_bucket" "build_source" {
  bucket = "${local.name_prefix}-build-source-${var.aws_region}"
}

resource "aws_s3_bucket_lifecycle_configuration" "build_source" {
  bucket = aws_s3_bucket.build_source.id
  rule {
    id     = "expire-old-uploads"
    status = "Enabled"
    filter {}
    expiration { days = 7 }
  }
}

resource "aws_iam_role" "codebuild" {
  name = "${local.name_prefix}-codebuild"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "codebuild.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "codebuild" {
  name = "${local.name_prefix}-codebuild"
  role = aws_iam_role.codebuild.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents",
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject", "s3:GetObjectVersion", "s3:ListBucket",
        ]
        Resource = [
          aws_s3_bucket.build_source.arn,
          "${aws_s3_bucket.build_source.arn}/*",
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:CompleteLayerUpload",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
        ]
        Resource = aws_ecr_repository.web.arn
      },
    ]
  })
}

resource "aws_cloudwatch_log_group" "codebuild" {
  name              = "/aws/codebuild/${local.name_prefix}-build"
  retention_in_days = 14
}

resource "aws_codebuild_project" "build" {
  name          = "${local.name_prefix}-build"
  service_role  = aws_iam_role.codebuild.arn
  build_timeout = 30

  artifacts { type = "NO_ARTIFACTS" }

  environment {
    compute_type    = "BUILD_GENERAL1_SMALL"
    image           = "aws/codebuild/standard:7.0"
    type            = "LINUX_CONTAINER"
    privileged_mode = true # required for docker

    environment_variable {
      name  = "AWS_REGION"
      value = var.aws_region
    }
    environment_variable {
      name  = "ECR_REGISTRY"
      value = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com"
    }
    environment_variable {
      name  = "ECR_REPOSITORY"
      value = aws_ecr_repository.web.name
    }
  }

  source {
    type      = "S3"
    location  = "${aws_s3_bucket.build_source.bucket}/source.zip"
    buildspec = "buildspec.yml"
  }

  logs_config {
    cloudwatch_logs {
      group_name = aws_cloudwatch_log_group.codebuild.name
    }
  }
}

output "codebuild_project_name" {
  value = aws_codebuild_project.build.name
}

output "build_source_bucket" {
  value = aws_s3_bucket.build_source.bucket
}
