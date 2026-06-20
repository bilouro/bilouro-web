"""Booking form handler for studio.bilouro.com.

Flow (matches the plan §8.1/§8.7):
  1. Honeypot ('company' field must be empty) — silently accept bots.
  2. Light per-IP rate limit (cache-based).
  3. Validate required fields.
  4. Persist the Booking row FIRST.
  5. Send the notification email to settings.STUDIO_BOOKING_NOTIFY_EMAIL via the
     configured backend (SES in prod, console in dev). A mail failure is logged
     on the row but never loses the lead.
  6. Redirect to the StudioThanksPage (/obrigado).
"""
from __future__ import annotations

import logging
import re

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .models import Booking, StudioThanksPage

log = logging.getLogger("studio.views")

TIME_SLOTS = ["11:00", "12:00", "14:00", "15:00", "16:00", "17:00", "18:00"]

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

RATE_LIMIT_MAX = 5          # submissions ...
RATE_LIMIT_WINDOW = 3600    # ... per IP per hour


def _client_ip(request) -> str | None:
    return request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("REMOTE_ADDR")


def _thanks_url() -> str:
    thanks = StudioThanksPage.objects.live().first()
    return thanks.url if thanks else "/obrigado/"


@require_http_methods(["GET", "POST"])
@csrf_protect
def booking_submit(request):
    """Handle the /agendar form POST. GET redirects back to the booking page."""
    if request.method == "GET":
        return redirect("/agendar/")

    # 1) Honeypot — bots fill every field. Pretend success, store nothing.
    if (request.POST.get("company") or "").strip():
        log.info("studio booking honeypot tripped from %s", _client_ip(request))
        return redirect(_thanks_url())

    ip = _client_ip(request)

    # 2) Rate limit per IP.
    if ip:
        key = f"studio_booking:{ip}"
        count = cache.get(key, 0)
        if count >= RATE_LIMIT_MAX:
            return _render_form_error(
                request, "Too many requests. Please try again later.", status=429
            )
        cache.set(key, count + 1, RATE_LIMIT_WINDOW)

    # 3) Validate.
    name = (request.POST.get("name") or "").strip()[:160]
    email = (request.POST.get("email") or "").strip().lower()[:254]
    phone = (request.POST.get("phone") or "").strip()[:40]
    preferred_date = (request.POST.get("preferred_date") or "").strip()
    preferred_time = (request.POST.get("preferred_time") or "").strip()[:10]
    message = (request.POST.get("message") or "").strip()
    source = (request.POST.get("source") or "agendar").strip()[:120]

    if not name or not EMAIL_RE.match(email) or not message:
        return _render_form_error(request, "Please fill in your name, a valid email, and a short message.")

    date_obj = None
    if preferred_date:
        try:
            date_obj = timezone.datetime.strptime(preferred_date, "%Y-%m-%d").date()
        except ValueError:
            date_obj = None
        else:
            if date_obj.weekday() >= 5:  # Sat/Sun
                return _render_form_error(request, "Please choose a weekday (Mon–Fri).")

    country = (request.headers.get("CF-IPCountry") or "").upper()[:2]

    # 4) Persist first.
    booking = Booking.objects.create(
        name=name,
        email=email,
        phone=phone,
        preferred_date=date_obj,
        preferred_time=preferred_time if preferred_time in TIME_SLOTS else "",
        message=message,
        source=source,
        ip=ip,
        country=country,
    )

    # 5) Notify (best-effort).
    _notify(booking)

    # 6) Done.
    return redirect(_thanks_url())


def _notify(booking: Booking) -> None:
    when = "—"
    if booking.preferred_date:
        when = booking.preferred_date.strftime("%d/%m")
        if booking.preferred_time:
            when += f" {booking.preferred_time}"
    subject = f"🗓 Nova conversa — {booking.name} — {when}"
    body = (
        "Cliente:\n"
        f"  Nome:      {booking.name}\n"
        f"  Email:     {booking.email}\n"
        f"  Telefone:  {booking.phone or '—'}\n\n"
        f"Quando quer:  {when}\n\n"
        "Em palavras dele/dela:\n"
        f"  {booking.message}\n\n"
        "---\n"
        f"Submetido às {booking.created_at:%Y-%m-%d %H:%M} via studio.bilouro.com\n"
        f"IP: {booking.ip or '—'}  ·  País: {booking.country or '—'}\n"
    )
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [settings.STUDIO_BOOKING_NOTIFY_EMAIL],
            fail_silently=False,
        )
        booking.notified = True
        booking.save(update_fields=["notified"])
    except Exception as e:  # noqa: BLE001 — never lose the lead on a mail error
        log.exception("studio booking notification failed for #%s", booking.pk)
        booking.notify_error = str(e)[:500]
        booking.save(update_fields=["notify_error"])


def _render_form_error(request, msg: str, status: int = 400):
    """Re-render the booking page template with an error banner and the entered values."""
    from .models import StudioBookingPage

    page = StudioBookingPage.objects.live().first()
    ctx = {
        "page": page,
        "self": page,
        "time_slots": TIME_SLOTS,
        "form_error": msg,
        "values": {
            "name": request.POST.get("name", ""),
            "email": request.POST.get("email", ""),
            "phone": request.POST.get("phone", ""),
            "preferred_date": request.POST.get("preferred_date", ""),
            "preferred_time": request.POST.get("preferred_time", ""),
            "message": request.POST.get("message", ""),
        },
    }
    return render(request, "studio/booking_page.html", ctx, status=status)
