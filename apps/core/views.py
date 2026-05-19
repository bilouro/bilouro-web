"""Site-wide views (search + language switch + admin stats)."""
from django.shortcuts import render
from django.utils import translation
from django.http import HttpResponse, HttpResponseRedirect
from wagtail.admin.auth import require_admin_access
from wagtail.models import Page, Site


@require_admin_access
def stats_dashboard(request):
    """Serve the static GoAccess dashboard, gated by Wagtail admin auth.

    The HTML is at /var/www/stats/index.html on the VM. We use nginx's
    X-Accel-Redirect so the file is served by nginx (fast) but only after
    Django/Wagtail confirms the user has admin access.
    """
    response = HttpResponse()
    response["X-Accel-Redirect"] = "/_internal/stats/"
    # Empty Content-Type lets nginx auto-set it from the served file.
    del response["Content-Type"]
    return response


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
