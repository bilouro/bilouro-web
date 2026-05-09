"""RSS / Atom feeds — adapt to the current Wagtail Site by Host header.

3 feeds, one per subdomain:
  - https://www.bilouro.com/feed/   → "geral" (everything: tech posts + book posts)
  - https://tech.bilouro.com/feed/  → tech BlogPostPage only
  - https://books.bilouro.com/feed/ → book posts only (aggregated across all books)
"""
from itertools import chain

from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from wagtail.models import Site

from apps.shop.models import BookPostPage
from apps.tech.models import BlogPostPage


class _SiteAwareFeed(Feed):
    feed_type = Atom1Feed

    def get_object(self, request, *args, **kwargs):
        return Site.find_for_request(request) or Site.objects.filter(is_default_site=True).first()

    def title(self, site):
        return f"{site.site_name}"

    def link(self, site):
        return f"https://{site.hostname}/"

    def description(self, site):
        return f"Latest posts from {site.hostname}"


class TechBlogFeed(_SiteAwareFeed):
    """tech.bilouro.com — BlogPostPage only."""

    def items(self, site):
        return (
            BlogPostPage.objects.live()
            .descendant_of(site.root_page)
            .order_by("-date", "-first_published_at")[:20]
        )

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.intro or (item.body_md or "")[:300]

    def item_link(self, item):
        return item.full_url

    def item_pubdate(self, item):
        return item.first_published_at


class BooksFeed(_SiteAwareFeed):
    """books.bilouro.com — BookPostPage from all books."""

    def items(self, site):
        return (
            BookPostPage.objects.live()
            .descendant_of(site.root_page)
            .order_by("-date", "-first_published_at")[:20]
        )

    def item_title(self, item):
        parent = item.get_parent().specific
        book = parent.title if parent else ""
        return f"{item.title} — {book}" if book else item.title

    def item_description(self, item):
        return (item.body_md or "")[:300] if item.body_md else (item.ref or "")

    def item_link(self, item):
        return item.full_url

    def item_pubdate(self, item):
        return item.first_published_at


class CombinedFeed(_SiteAwareFeed):
    """www.bilouro.com — geral feed: tech posts + book posts merged by date."""

    def title(self, site):
        return "bilouro.com — geral"

    def description(self, site):
        return "Tudo: tech posts + reflexões dos livros."

    def items(self, site):
        tech = BlogPostPage.objects.live().order_by("-date")[:20]
        books = BookPostPage.objects.live().order_by("-date")[:20]
        merged = sorted(
            chain(tech, books),
            key=lambda p: (p.date, p.first_published_at or p.date),
            reverse=True,
        )
        return merged[:20]

    def item_title(self, item):
        if isinstance(item, BookPostPage):
            parent = item.get_parent().specific
            book = parent.title if parent else ""
            return f"[Books] {item.title}" + (f" — {book}" if book else "")
        return f"[Tech] {item.title}"

    def item_description(self, item):
        if hasattr(item, "intro") and item.intro:
            return item.intro
        return (item.body_md or "")[:300]

    def item_link(self, item):
        return item.full_url

    def item_pubdate(self, item):
        return item.first_published_at
