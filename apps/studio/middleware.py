"""URL-based language for studio.bilouro.com (SEO).

PT is the default and lives at the bare path (/studio-app/); EN lives under
/en/ (/en/studio-app/). The language comes from the URL only — never from the
cookie or Accept-Language — so Googlebot (no cookie) indexes both versions as
separate URLs, linked by hreflang (see templates/studio/_base.html).

How it works, for the studio host only (other sites keep cookie switching):
  1. request: strip a leading /en from path_info, so Wagtail serves the same
     page; activate the language; expose the unprefixed path for hreflang.
  2. response (EN only, HTML only): prefix root-relative links with /en so the
     visitor stays in English while navigating.
Must sit AFTER LocaleMiddleware (it overrides what LocaleMiddleware picked).
"""
from __future__ import annotations

import re

from django.utils import translation

EN_PREFIX = "/en"
# Root-relative hrefs that must NOT get the /en prefix.
_SKIP = ("en/", "en\"", "static/", "media/", "admin/", "django-admin/", "documents/",
         "api/", "i18n/", "sitemap.xml", "robots.txt", "feed", "healthz", "__debug__/")
_HREF_RE = re.compile(r'href="/(?!/)([^"]*)"')


def is_studio_host(request) -> bool:
    return request.get_host().split(":")[0].startswith("studio.")


def _prefix_links(html: str) -> str:
    def repl(m: re.Match) -> str:
        rest = m.group(1)
        if rest.startswith(_SKIP) or rest == "en":
            return m.group(0)
        return f'href="{EN_PREFIX}/{rest}"'

    return _HREF_RE.sub(repl, html)


class StudioLanguageFromPathMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not is_studio_host(request):
            return self.get_response(request)

        path = request.path_info
        if path == EN_PREFIX or path.startswith(EN_PREFIX + "/"):
            lang = "en"
            request.path_info = path[len(EN_PREFIX):] or "/"
        else:
            lang = "pt"
        request.studio_path = request.path_info  # unprefixed, for hreflang
        translation.activate(lang)
        request.LANGUAGE_CODE = lang

        response = self.get_response(request)

        response.headers["Content-Language"] = lang
        if (
            lang == "en"
            and not getattr(response, "streaming", False)
            and response.get("Content-Type", "").startswith("text/html")
        ):
            response.content = _prefix_links(response.content.decode(response.charset)).encode(response.charset)
            if response.has_header("Content-Length"):
                response["Content-Length"] = str(len(response.content))
        return response
