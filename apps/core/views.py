"""Site-wide views (search + language switch + admin stats)."""
from django.shortcuts import render
from django.utils import translation
from django.http import HttpResponse, HttpResponseRedirect
from wagtail.admin.auth import require_admin_access
from wagtail.models import Page, Site


def _stats_redirect(target_file: str) -> HttpResponse:
    """Tell nginx to serve a file from /var/www/stats via X-Accel-Redirect."""
    response = HttpResponse()
    response["X-Accel-Redirect"] = f"/_internal/stats/{target_file}"
    del response["Content-Type"]
    return response


@require_admin_access
def stats_dashboard(request):
    """All hosts combined — GoAccess /var/www/stats/index.html"""
    return _stats_redirect("index.html")


@require_admin_access
def stats_bilouro(request):
    """*.bilouro.com only."""
    return _stats_redirect("bilouro.html")


@require_admin_access
def stats_hashtag_jesus(request):
    """*.hashtag-jesus.com only."""
    return _stats_redirect("hashtag-jesus.html")


def search(request):
    """Per-site search using Wagtail's search backend.
    - tech.* searches descendants of the tech BlogIndexPage
    - books.* searches descendants of the BookCatalogPage
    - www.* / apex searches everything
    """
    query = (request.GET.get("q") or "").strip()
    site = Site.find_for_request(request) or Site.objects.filter(is_default_site=True).first()

    results = []
    total = 0
    if query and site:
        host = request.get_host().split(":")[0]
        if host.startswith("www") or host == "bilouro.com":
            qs = Page.objects.live().public()  # all sites
        else:
            qs = Page.objects.live().public().descendant_of(site.root_page)
        results_qs = qs.search(query)[:30]
        results = list(results_qs)
        total = len(results)

    return render(
        request,
        "search.html",
        {"query": query, "results": results, "total": total, "site": site},
    )


def set_language(request):
    """Language switcher — POST or GET ?lang=en|pt&next=/path/."""
    lang = request.POST.get("language") or request.GET.get("lang")
    next_url = request.POST.get("next") or request.GET.get("next") or "/"
    if lang and lang in dict(__import__("django.conf").conf.settings.LANGUAGES):
        translation.activate(lang)
        response = HttpResponseRedirect(next_url)
        response.set_cookie(
            "django_language",
            lang,
            max_age=60 * 60 * 24 * 365,
            samesite="Lax",
        )
        return response
    return HttpResponseRedirect(next_url)
