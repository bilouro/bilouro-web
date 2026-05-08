resource "random_password" "django_secret" {
  length  = 64
  special = true
  override_special = "!#$%&*+-=?@^_"
}

resource "aws_secretsmanager_secret" "db_url" {
  name                    = "${local.name_prefix}/db-url"
  description             = "Postgres connection string for the Wagtail app"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "db_url" {
  secret_id     = aws_secretsmanager_secret.db_url.id
  secret_string = "postgres://${aws_db_instance.main.username}:${random_password.db.result}@${aws_db_instance.main.endpoint}/${aws_db_instance.main.db_name}"
}

resource "aws_secretsmanager_secret" "django_secret_key" {
  name                    = "${local.name_prefix}/django-secret-key"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "django_secret_key" {
  secret_id     = aws_secretsmanager_secret.django_secret_key.id
  secret_string = random_password.django_secret.result
}
