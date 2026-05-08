resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_security_group" "rds" {
  name        = "${local.name_prefix}-rds"
  description = "Postgres access for the App Runner VPC connector"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_security_group" "apprunner_vpc" {
  name        = "${local.name_prefix}-apprunner-vpc"
  description = "App Runner VPC connector egress"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group_rule" "rds_from_apprunner" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = aws_security_group.apprunner_vpc.id
  description              = "Postgres from App Runner VPC connector"
}

resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnets"
  subnet_ids = data.aws_subnets.default.ids
}

resource "aws_db_instance" "main" {
  identifier             = "${local.name_prefix}-pg"
  engine                 = "postgres"
  engine_version         = "16.13"
  instance_class         = "db.t4g.micro"
  allocated_storage      = 20
  storage_type           = "gp3"
  storage_encrypted      = true
  db_name                = "bilouro"
  username               = "bilouro"
  password               = random_password.db.result
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  skip_final_snapshot    = true
  deletion_protection    = false
  backup_retention_period = 7
  apply_immediately      = true
}
