# CloudWatch alarms for App Runner — sends email via SNS to alert_email.
#
# Note: after `terraform apply`, AWS sends a "Subscribe to topic" email to
# the alert_email address. You MUST click "Confirm subscription" in that
# email or alarms won't deliver.

resource "aws_sns_topic" "alerts" {
  name = "${local.name_prefix}-alerts"
}

resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

locals {
  apprunner_alarm_dims = {
    ServiceName = "${local.name_prefix}-web"
    ServiceArn  = try(aws_apprunner_service.web[0].arn, "")
  }
}

resource "aws_cloudwatch_metric_alarm" "high_5xx" {
  count               = var.enable_apprunner ? 1 : 0
  alarm_name          = "${local.name_prefix}-5xx-errors"
  alarm_description   = "App Runner: more than 5 HTTP 5xx errors in 5 min"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 5
  period              = 300
  statistic           = "Sum"
  metric_name         = "5xxStatusResponses"
  namespace           = "AWS/AppRunner"
  dimensions          = local.apprunner_alarm_dims
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "high_latency" {
  count               = var.enable_apprunner ? 1 : 0
  alarm_name          = "${local.name_prefix}-latency-p99"
  alarm_description   = "App Runner: p99 latency > 5s for 10 min"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 5000 # ms
  period              = 300
  extended_statistic  = "p99"
  metric_name         = "RequestLatency"
  namespace           = "AWS/AppRunner"
  dimensions          = local.apprunner_alarm_dims
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "scaling_pressure" {
  count               = var.enable_apprunner ? 1 : 0
  alarm_name          = "${local.name_prefix}-scaling-pressure"
  alarm_description   = "App Runner: >= 3 active instances sustained 5 min (traffic spike)"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  threshold           = 3
  period              = 300
  statistic           = "Maximum"
  metric_name         = "ActiveInstances"
  namespace           = "AWS/AppRunner"
  dimensions          = local.apprunner_alarm_dims
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  count               = var.enable_apprunner ? 1 : 0
  alarm_name          = "${local.name_prefix}-cpu"
  alarm_description   = "App Runner: CPU > 80% for 10 min"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 80
  period              = 300
  statistic           = "Average"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/AppRunner"
  dimensions          = local.apprunner_alarm_dims
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

output "sns_alerts_topic_arn" {
  value = aws_sns_topic.alerts.arn
}
