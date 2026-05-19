"""Thin MailerLite client (https://developers.mailerlite.com).

Reads the API token from env var MAILERLITE_API_TOKEN. Group IDs per locale
are read from MAILERLITE_GROUP_ID_BR / _PT / _EN. Stays a thin layer — no
retries here; caller decides.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error

log = logging.getLogger("hashtagjesus.mailerlite")

BASE_URL = "https://connect.mailerlite.com/api"


def _token() -> str | None:
    return os.environ.get("MAILERLITE_API_TOKEN") or None


def _group_id(locale: str) -> str | None:
    return os.environ.get(f"MAILERLITE_GROUP_ID_{locale.upper()}") or None


def _request(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    token = _token()
    if not token:
        raise RuntimeError("MAILERLITE_API_TOKEN not set")
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read() or b"{}")
        except Exception:
            payload = {"error": str(e)}
        return e.code, payload


def subscribe(email: str, locale: str, ip: str | None = None) -> tuple[bool, dict]:
    """Subscribe email to the locale's group. Returns (ok, payload)."""
    group_id = _group_id(locale)
    body: dict = {
        "email": email,
        "fields": {},
    }
    if group_id:
        body["groups"] = [group_id]
    if ip:
        body["ip_address"] = ip

    status, payload = _request("POST", "/subscribers", body)
    ok = status in (200, 201)
    if not ok:
        log.warning("MailerLite subscribe failed: status=%s body=%s", status, payload)
    return ok, payload
