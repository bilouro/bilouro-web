# Terraform — bilouro-web AWS infrastructure

Region: **eu-west-1** · Profile: **bilouro**

## What this creates

| Resource | Purpose | Cost (post-free-tier) |
|---|---|---|
| 2 AWS Budgets | $20 + $50 monthly alerts | $0 |
| ECR repository | Docker image store | ~$0.10/GB/mo |
| RDS Postgres `db.t4g.micro` | Database | ~$13/mo (free 12 months) |
| S3 bucket (media) | User-uploaded media | <$1/mo |
| Secrets Manager (×2) | DATABASE_URL + SECRET_KEY | $0.80/mo |
| Security groups + DB subnet group | Networking | $0 |
| IAM roles (×2) | App Runner ECR + instance | $0 |
| App Runner service | Web container | $7-25/mo (gated by var) |
| App Runner VPC connector | Reach RDS privately | $0 |

## First-time apply (two-stage)

```bash
cd infra/terraform
terraform init

# Stage 1: everything except App Runner (it needs an image first)
terraform apply

# Stage 2: build + push image — see ../scripts/deploy.sh

# Stage 3: enable App Runner
terraform apply -var enable_apprunner=true
```

## Pause costs

```bash
terraform apply -var enable_apprunner=false   # stops App Runner spend
# RDS keeps running unless you stop or destroy it:
terraform destroy -target aws_db_instance.main   # destructive
```

## Full teardown

```bash
terraform destroy
```

Buckets with content require emptying first.
