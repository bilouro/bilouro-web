"""JSON-LD for studio.bilouro.com (schema.org), built in Python so every
string is escaped correctly. Language follows request.LANGUAGE_CODE."""
from __future__ import annotations

import json

from django import template
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

register = template.Library()

ORG_NAME = "Bilouro Studio"


def _t(obj, field, lang):
    if lang == "pt":
        v = getattr(obj, f"{field}_pt", None)
        if v:
            return str(v)
    return str(getattr(obj, field, "") or "")


def _plain(html: str) -> str:
    return " ".join(strip_tags(html or "").split())


def _base_url(request) -> str:
    return f"{request.scheme}://{request.get_host()}"


def _page_url(request, page, lang) -> str:
    path = page.get_url(request=request) or "/"
    if path.startswith("http"):
        return path
    return _base_url(request) + ("/en" if lang == "en" else "") + path


def _script(data) -> str:
    payload = json.dumps(data, ensure_ascii=False, indent=None).replace("</", "<\\/")
    return f'<script type="application/ld+json">{payload}</script>'


def _organization(request) -> dict:
    return {
        "@type": "Organization",
        "@id": _base_url(request) + "/#org",
        "name": ORG_NAME,
        "url": _base_url(request) + "/",
        "email": "consulting@bilouro.com",
        "areaServed": {"@type": "Country", "name": "Portugal"},
    }


@register.simple_tag(takes_context=True)
def studio_home_jsonld(context, page):
    request = context["request"]
    lang = getattr(request, "LANGUAGE_CODE", "pt")
    graph = [
        _organization(request),
        {
            "@type": "WebSite",
            "@id": _base_url(request) + "/#site",
            "url": _base_url(request) + "/",
            "name": ORG_NAME,
            "inLanguage": "en" if lang == "en" else "pt-PT",
            "publisher": {"@id": _base_url(request) + "/#org"},
        },
    ]
    return mark_safe(_script({"@context": "https://schema.org", "@graph": graph}))


@register.simple_tag(takes_context=True)
def studio_solution_jsonld(context, page):
    request = context["request"]
    lang = getattr(request, "LANGUAGE_CODE", "pt")
    url = _page_url(request, page, lang)
    name = _t(page, "seo_title", lang) or page.title
    description = _t(page, "search_description", lang) or _plain(_t(page, "hero_sub", lang))
    app = {
        "@type": "SoftwareApplication",
        "@id": url + "#app",
        "name": "Studio App",
        "alternateName": name,
        "description": description,
        "url": url,
        "applicationCategory": "BusinessApplication",
        "applicationSubCategory": "Gym and fitness studio management software",
        "operatingSystem": "Web, iOS, Android (PWA)",
        "inLanguage": ["pt-PT", "en"],
        "areaServed": {"@type": "Country", "name": "Portugal"},
        "provider": {"@id": _base_url(request) + "/#org"},
        "featureList": [_t(f, "title", lang) for f in page.features.all()]
        + [_t(x, "title", lang) for x in page.extras.all()],
    }
    if getattr(page, "image", None):
        rendition = page.image.get_rendition("width-1200")
        app["image"] = rendition.url if rendition.url.startswith("http") else _base_url(request) + rendition.url
    graph = [_organization(request), app]

    crumbs = [{"@type": "ListItem", "position": 1, "name": ORG_NAME, "item": _base_url(request) + ("/en/" if lang == "en" else "/")}]
    if page.parent_solution and page.parent_solution.live:
        crumbs.append({"@type": "ListItem", "position": 2, "name": _t(page.parent_solution, "nav_label", lang) or page.parent_solution.title,
                       "item": _page_url(request, page.parent_solution, lang)})
    crumbs.append({"@type": "ListItem", "position": len(crumbs) + 1, "name": _t(page, "nav_label", lang) or page.title, "item": url})
    graph.append({"@type": "BreadcrumbList", "itemListElement": crumbs})

    faqs = list(page.faqs.all())
    if faqs:
        graph.append({
            "@type": "FAQPage",
            "@id": url + "#faq",
            "mainEntity": [
                {"@type": "Question", "name": _t(q, "question", lang),
                 "acceptedAnswer": {"@type": "Answer", "text": _plain(_t(q, "answer", lang))}}
                for q in faqs
            ],
        })
    return mark_safe(_script({"@context": "https://schema.org", "@graph": graph}))


@register.simple_tag
def studio_articles_index():
    """The live /artigos index, or None — the nav link only shows once it is published."""
    from apps.studio.models import StudioArticleIndexPage

    return StudioArticleIndexPage.objects.live().first()


@register.simple_tag(takes_context=True)
def studio_article_jsonld(context, page):
    request = context["request"]
    lang = getattr(request, "LANGUAGE_CODE", "pt")
    url = _page_url(request, page, lang)
    post = {
        "@type": "BlogPosting",
        "@id": url + "#article",
        "headline": _t(page, "title", lang)[:110],
        "description": _t(page, "search_description", lang) or _t(page, "intro", lang),
        "datePublished": page.date.isoformat(),
        "dateModified": (page.last_published_at or page.latest_revision_created_at).date().isoformat()
        if (page.last_published_at or page.latest_revision_created_at) else page.date.isoformat(),
        "inLanguage": "en" if lang == "en" else "pt-PT",
        "mainEntityOfPage": url,
        "author": {"@type": "Person", "name": page.author or "Victor Bilouro"},
        "publisher": {"@id": _base_url(request) + "/#org"},
    }
    if page.image:
        r = page.image.get_rendition("fill-1200x630")
        post["image"] = r.url if r.url.startswith("http") else _base_url(request) + r.url
    index_page = page.get_parent().specific
    crumbs = {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": ORG_NAME, "item": _base_url(request) + ("/en/" if lang == "en" else "/")},
        {"@type": "ListItem", "position": 2, "name": _t(index_page, "title", lang) or index_page.title, "item": _page_url(request, index_page, lang)},
        {"@type": "ListItem", "position": 3, "name": _t(page, "title", lang), "item": url},
    ]}
    return mark_safe(_script({"@context": "https://schema.org", "@graph": [_organization(request), post, crumbs]}))
