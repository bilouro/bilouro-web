"""Top-level URLs.

Wagtail handles routing per-Site at the lowest level (catch-all). Health,
admin, sitemaps, RSS and locale-aware routes go above that.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.contrib.sitemaps.views import sitemap
from wagtail.documents import urls as wagtaildocs_urls

from apps.core.feeds import BooksFeed, CombinedFeed, TechBlogFeed
from apps.core.views import search as search_view, set_language as set_lang_view


def healthz(_request):
    return HttpResponse("ok", content_type="text/plain")


def feed_dispatch(request, *args, **kwargs):
    """Pick the right feed by hostname:
    - books.* → BooksFeed
    - tech.*  → TechBlogFeed
    - other (www, apex) → CombinedFeed (everything)
    """
    host = request.get_host().split(":")[0]
    if host.startswith("books"):
        return BooksFeed()(request, *args, **kwargs)
    if host.startswith("tech"):
        return TechBlogFeed()(request, *args, **kwargs)
    return CombinedFeed()(request, *args, **kwargs)


def robots_txt(request):
    host = request.get_host()
    body = (
        "User-agent: *\n"
        "Disallow: /admin/\n"
        "Disallow: /django-admin/\n"
        "Disallow: /documents/\n"
        "Allow: /\n\n"
        f"Sitemap: https://{host}/sitemap.xml\n"
    )
    return HttpResponse(body, content_type="text/plain")


urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("healthz", healthz),
    path("robots.txt", robots_txt, name="robots"),
    path("sitemap.xml", sitemap, name="sitemap"),
    path("feed/", feed_dispatch, name="feed"),
    path("feed", feed_dispatch),
    path("search/", search_view, name="search"),
    path("i18n/setlang/", set_lang_view, name="set_language"),
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    # Wagtail catch-all (must be last)
    path("", include(wagtail_urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar  # noqa: F401

        urlpatterns = [path("__debug__/", include("debug_toolbar.urls"))] + urlpatterns
    except ImportError:
        pass
