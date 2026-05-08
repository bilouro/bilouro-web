variable "aws_region" {
  type    = string
  default = "eu-west-1"
}

variable "aws_profile" {
  type    = string
  default = "bilouro"
}

variable "project" {
  type    = string
  default = "bilouro"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "alert_email" {
  type        = string
  description = "Where billing/error alerts go."
  default     = "bilouro@bilouro.com"
}

variable "monthly_budget_usd" {
  type    = number
  default = 20
}

variable "domain" {
  type    = string
  default = "bilouro.com"
}

variable "subdomains" {
  type    = list(string)
  default = ["www", "tech", "books"]
}

locals {
  name_prefix = "${var.project}-${var.environment}"
  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
