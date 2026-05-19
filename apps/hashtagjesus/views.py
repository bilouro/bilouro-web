"""Views for hashtag-jesus.com — country picker + newsletter signup + robots."""
from __future__ import annotations

import logging
import re

from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .mailerlite import subscribe as ml_subscribe
from .models import NewsletterSignup

log = logging.getLogger("hashtagjesus.views")

# Country code → locale → subdomain mapping.
COUNTRY_TO_LOCALE = {
    "BR": "br",
    "PT": "pt",
    # All others default to en
}

LOCALE_TO_SUBDOMAIN = {
    "br": "br.hashtag-jesus.com",
    "pt": "pt.hashtag-jesus.com",
    "en": "en.hashtag-jesus.com",
}

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def detect_locale(request) -> str:
    """Return 'br'/'pt'/'en' from CF-IPCountry header (default 'en')."""
    cc = (request.headers.get("CF-IPCountry") or "").upper()
    return COUNTRY_TO_LOCALE.get(cc, "en")


def host_locale(request) -> str | None:
    """Return 'br'/'pt'/'en' if the request host is a known subdomain, else None."""
    host = request.get_host().split(":")[0].lower()
    for locale, subdomain in LOCALE_TO_SUBDOMAIN.items():
        if host == subdomain:
            return locale
    return None


@require_http_methods(["GET", "POST"])
@csrf_protect
def newsletter_subscribe(request):
    """POST email + locale → save local + push to MailerLite. JSON for AJAX, redirect for form."""
    is_json = request.content_type == "application/json" or "application/json" in request.headers.get("Accept", "")

    if request.method == "GET":
        # Render a standalone thank-you page if user lands here by mistake
        return render(request, "hashtagjesus/newsletter_thanks.html", status=200)

    email = (request.POST.get("email") or "").strip().lower()
    locale = (request.POST.get("locale") or host_locale(request) or detect_locale(request)).lower()
    source = (request.POST.get("source") or "").strip()[:120]

    if not EMAIL_RE.match(email):
        msg = _("Please enter a valid email.")
        if is_json:
            return JsonResponse({"ok": False, "error": str(msg)}, status=400)
        return render(request, "hashtagjesus/newsletter_form.html",
                      {"error": msg, "email": email}, status=400)

    if locale not in {"br", "pt", "en"}:
        locale = "en"

    ip = request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("REMOTE_ADDR")
    country = (request.headers.get("CF-IPCountry") or "").upper()[:2]

    # 1) Save local first (idempotent on (email, locale))
    signup, created = NewsletterSignup.objects.get_or_create(
        email=email,
        locale=locale,
        defaults={"source": source, "ip": ip, "country": country},
    )
    if not created and signup.mailerlite_status == "active":
        # Already subscribed
        return _success_response(request, is_json, already=True)

    # 2) Push to MailerLite
    try:
        ok, payload = ml_subscribe(email, locale, ip=ip)
    except Exception as e:
        log.exception("MailerLite raised for %s/%s", email, locale)
        signup.mailerlite_status = "error"
        signup.mailerlite_error = str(e)[:500]
        signup.save(update_fields=["mailerlite_status", "mailerlite_error"])
        ok, payload = False, {}

    if ok:
        sub_data = (payload or {}).get("data") or {}
        signup.mailerlite_subscriber_id = str(sub_data.get("id") or "")[:64]
        signup.mailerlite_status = sub_data.get("status") or "active"
        signup.mailerlite_error = ""
    else:
        signup.mailerlite_status = "error"
        signup.mailerlite_error = (str(payload)[:500] if payload else "unknown")
    signup.save(update_fields=["mailerlite_subscriber_id", "mailerlite_status", "mailerlite_error"])

    return _success_response(request, is_json, already=False)


def _success_response(request, is_json: bool, already: bool):
    if is_json:
        return JsonResponse({"ok": True, "already": already})
    return render(request, "hashtagjesus/newsletter_thanks.html", {"already": already})


def robots_for_hashtagjesus(request) -> HttpResponse:
    """Per-host robots.txt for hashtag-jesus.com and its subdomains.

    Only invoked when the request host is one of the hashtag-jesus.* names.
    The router in config.urls picks the appropriate robots view by host.
    """
    host = request.get_host().split(":")[0]
    body = (
        "User-agent: *\n"
        "Disallow: /admin/\n"
        "Disallow: /django-admin/\n"
        "Disallow: /api/\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: https://{host}/sitemap.xml\n"
    )
    return HttpResponse(body, content_type="text/plain; charset=utf-8")
