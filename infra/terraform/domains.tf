# App Runner has built-in support for custom domains with auto-managed
# certificates — simpler than CloudFront for low/medium traffic.
#
# Each custom_domain_association produces TWO sets of DNS records the user
# must create on Locaweb:
#   1. Certificate-validation CNAMEs (one or more `_xxx.<host> → _xxx.acm-validations.aws.`)
#   2. A routing CNAME pointing the host to the App Runner service URL.
#
# Outputs print everything you need to copy into Locaweb.

resource "aws_apprunner_custom_domain_association" "domain" {
  for_each = var.enable_apprunner ? toset(var.subdomains) : toset([])

  domain_name          = "${each.value}.${var.domain}"
  service_arn          = aws_apprunner_service.web[0].arn
  enable_www_subdomain = false # avoid conflict on www.bilouro.com
}

output "dns_records_for_locaweb" {
  description = "Add these CNAMEs in the Locaweb DNS panel (one per subdomain)."
  value = [
    for sd in var.subdomains : {
      subdomain = sd
      records = (
        var.enable_apprunner ? [
          {
            name  = "${sd}.${var.domain}"
            type  = "CNAME"
            value = aws_apprunner_custom_domain_association.domain[sd].dns_target
            note  = "Routing — point traffic to App Runner."
          },
          ] : []
      )
      validation_records = (
        var.enable_apprunner ?
        aws_apprunner_custom_domain_association.domain[sd].certificate_validation_records :
        []
      )
    }
  ]
}
