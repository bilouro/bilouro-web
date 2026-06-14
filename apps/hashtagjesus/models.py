"""Pages for hashtag-jesus.com — Christian book launch site, multi-locale by subdomain.

Locales (each with its own Wagtail Site and content tree):
  br.hashtag-jesus.com  → pt-BR
  pt.hashtag-jesus.com  → pt-PT
  en.hashtag-jesus.com  → en
And the apex (hashtag-jesus.com) serves a HjLanguagePickerPage with auto-detect.
"""
from django.db import models
from modelcluster.fields import ParentalKey
from modelcluster.contrib.taggit import ClusterTaggableManager
from taggit.models import TaggedItemBase
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.search import index


# ─── Apex (hashtag-jesus.com) ──────────────────────────────────────────


class HjLanguagePickerPage(Page):
    """Apex landing — shows the 3 locales as cards, auto-highlights via CF-IPCountry.

    Tracks no per-locale content beyond a headline / subtitle; the actual sites
    live under the subdomains.
    """

    headline = models.CharField(
        max_length=200,
        blank=True,
        default="Choose your language",
        help_text="Top headline on the picker landing.",
    )
    subtitle = models.CharField(
        max_length=400,
        blank=True,
        help_text="Sub-headline under the main headline.",
    )

    template = "hashtagjesus/language_picker_page.html"
    max_count = 1
    parent_page_types = ["wagtailcore.Page"]
    subpage_types: list[str] = []

    content_panels = Page.content_panels + [
        FieldPanel("headline"),
        FieldPanel("subtitle"),
    ]

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        from .context import build_picker_context
        build_picker_context(ctx, request)
        return ctx

    def serve(self, request, *args, **kwargs):
        """If we've seen this visitor pick a locale before, send them straight
        there (server-side 302, no JS flash). Bypass when ?pick=1 / ?choose=1
        — used by the 'Other languages' footer link to force re-show the
        picker even with a cookie set."""
        force_show = bool(request.GET.get("pick") or request.GET.get("choose"))
        if not force_show:
            saved = request.COOKIES.get("hj_locale_chosen")
            if saved in ("br", "pt", "en"):
                from django.http import HttpResponseRedirect
                return HttpResponseRedirect(f"https://{saved}.hashtag-jesus.com/")
        return super().serve(request, *args, **kwargs)


# ─── Per-locale (br./pt./en.hashtag-jesus.com) ─────────────────────────


class HjHomePage(Page):
    """Landing page for a locale subdomain. Hero + latest posts + book teaser."""

    tagline = models.CharField(max_length=200, blank=True, help_text="Eyebrow above the hero headline.")
    headline = RichTextField(blank=True, help_text="Hero headline (use <em> for emphasis).")
    intro = RichTextField(blank=True, help_text="Short paragraph under the hero.")
    cta_label = models.CharField(max_length=80, blank=True, default="")
    cta_url = models.CharField(max_length=300, blank=True, default="")

    template = "hashtagjesus/home_page.html"

    content_panels = Page.content_panels + [
        FieldPanel("tagline"),
        FieldPanel("headline"),
        FieldPanel("intro"),
        MultiFieldPanel(
            [FieldPanel("cta_label"), FieldPanel("cta_url")],
            heading="Hero CTA",
        ),
    ]

    parent_page_types = ["wagtailcore.Page"]
    subpage_types = [
        "hashtagjesus.HjBlogIndexPage",
        "hashtagjesus.HjBookTeaserPage",
        "hashtagjesus.HjLegalPage",
    ]

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        from .context import inject_locale_context
        inject_locale_context(ctx, request, self)
        posts_qs = (
            HjBlogPostPage.objects.live().descendant_of(self).order_by("-date", "-first_published_at")
        )
        ctx["recent_posts"] = posts_qs[:6]
        ctx["more_posts"] = posts_qs.count() > 6
        ctx["book_teaser"] = (
            HjBookTeaserPage.objects.live().descendant_of(self).first()
        )
        return ctx


class HjBlogIndexPage(Page):
    """Listing of blog posts under a HomePage."""

    intro = RichTextField(blank=True)

    template = "hashtagjesus/blog_index_page.html"

    content_panels = Page.content_panels + [FieldPanel("intro")]

    subpage_types = ["hashtagjesus.HjBlogPostPage"]
    parent_page_types = ["hashtagjesus.HjHomePage"]

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        from .context import inject_locale_context
        inject_locale_context(ctx, request, self)
        from django.core.paginator import Paginator
        all_posts = (
            HjBlogPostPage.objects.live().descendant_of(self).order_by("-date", "-first_published_at")
        )
        page_obj = Paginator(all_posts, 10).get_page(request.GET.get("page"))
        ctx["posts"] = page_obj
        ctx["page_obj"] = page_obj
        return ctx


class HjBlogPostTag(TaggedItemBase):
    content_object = ParentalKey(
        "hashtagjesus.HjBlogPostPage",
        related_name="tagged_items",
        on_delete=models.CASCADE,
    )


class HjBlogPostPage(Page):
    """A single blog post with book chapter.

    body_md = post storytelling (shown in listing).
    chapter_* fields = book chapter (shown in detail page).
    """

    date = models.DateField("Post date")
    intro = models.CharField(max_length=400, blank=True, help_text="OG/meta description.")
    body_md = models.TextField(blank=True, help_text="Post storytelling (shown in blog listing).")
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Hero image. Also used as the OG / preview image when sharing.",
    )
    youtube_url = models.URLField(
        blank=True,
        default="",
        help_text=(
            "YouTube Short / video URL. When filled, replaces the hero image on the "
            "page (image is still used for the share preview). Accepts youtu.be/<id>, "
            "youtube.com/shorts/<id>, youtube.com/watch?v=<id>, or just the <id>."
        ),
    )
    chapter_title = models.CharField(max_length=200, blank=True, help_text="Book chapter title.")
    biblical_ref = models.CharField(max_length=200, blank=True, help_text="Biblical reference (e.g. Mateus 7:1-5).")
    biblical_text = models.TextField(blank=True, help_text="Biblical text with superscript verse numbers.")
    chapter_reflection = models.TextField(blank=True, help_text="Pastoral reflection (2-4 paragraphs).")
    chapter_exercise = models.TextField(blank=True, help_text="Practical exercise.")
    chapter_question = models.TextField(blank=True, help_text="Reflective question.")
    tags = ClusterTaggableManager(through=HjBlogPostTag, blank=True)

    template = "hashtagjesus/blog_post_page.html"

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("body_md"),
        index.SearchField("chapter_reflection"),
    ]

    content_panels = Page.content_panels + [
        MultiFieldPanel([FieldPanel("date"), FieldPanel("tags")], heading="Meta"),
        FieldPanel("image"),
        FieldPanel("youtube_url"),
        FieldPanel("intro"),
        FieldPanel("body_md"),
        MultiFieldPanel([
            FieldPanel("chapter_title"),
            FieldPanel("biblical_ref"),
            FieldPanel("biblical_text"),
            FieldPanel("chapter_reflection"),
            FieldPanel("chapter_exercise"),
            FieldPanel("chapter_question"),
        ], heading="Book chapter"),
    ]

    @property
    def biblical_ref_short(self) -> str:
        ref = (self.biblical_ref or "").strip()
        if not ref:
            return ""
        return ref.split("|")[0].strip()

    @property
    def youtube_video_id(self) -> str:
        """Extract the 11-char video ID from common YouTube URL formats."""
        import re
        url = (self.youtube_url or "").strip()
        if not url:
            return ""
        # Plain ID (no slashes, short)
        if "/" not in url and 8 <= len(url) <= 20:
            return url
        for pat in (
            r"youtu\.be/([A-Za-z0-9_-]{11})",
            r"youtube\.com/shorts/([A-Za-z0-9_-]{11})",
            r"youtube\.com/embed/([A-Za-z0-9_-]{11})",
            r"youtube\.com/watch\?(?:.*&)?v=([A-Za-z0-9_-]{11})",
        ):
            m = re.search(pat, url)
            if m:
                return m.group(1)
        return ""

    parent_page_types = ["hashtagjesus.HjBlogIndexPage"]

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        from .context import inject_locale_context
        inject_locale_context(ctx, request, self)
        return ctx


class HjBookTeaserPage(Page):
    """Pre-launch teaser page for a single book (one per locale)."""

    subtitle = models.CharField(max_length=200, blank=True)
    summary = RichTextField(blank=True, help_text="2-4 sentences describing the book.")
    cover_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    launch_date = models.DateField(null=True, blank=True, help_text="Expected launch date.")
    waitlist_cta = models.CharField(
        max_length=120,
        blank=True,
        default="Notify me when it launches",
    )
    waitlist_description = RichTextField(
        blank=True,
        help_text="Short paragraph above the waitlist form.",
    )

    template = "hashtagjesus/book_teaser_page.html"

    content_panels = Page.content_panels + [
        FieldPanel("subtitle"),
        FieldPanel("cover_image"),
        FieldPanel("summary"),
        MultiFieldPanel(
            [
                FieldPanel("launch_date"),
                FieldPanel("waitlist_cta"),
                FieldPanel("waitlist_description"),
            ],
            heading="Launch / waitlist",
        ),
    ]

    parent_page_types = ["hashtagjesus.HjHomePage"]
    subpage_types: list[str] = []

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        from .context import inject_locale_context
        inject_locale_context(ctx, request, self)
        return ctx


class HjLegalPage(Page):
    """Static legal text (privacy, terms). One per locale."""

    body = RichTextField()

    template = "hashtagjesus/legal_page.html"

    content_panels = Page.content_panels + [FieldPanel("body")]

    parent_page_types = ["hashtagjesus.HjHomePage"]
    subpage_types: list[str] = []

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        from .context import inject_locale_context
        inject_locale_context(ctx, request, self)
        return ctx


# ─── Newsletter (not a Page; a plain Django model) ──────────────────────


class NewsletterSignup(models.Model):
    """One record per waitlist signup. Source of truth lives in MailerLite,
    but we keep a local copy for audit + retry."""

    LOCALE_CHOICES = [
        ("br", "Português (Brasil)"),
        ("pt", "Português (Portugal)"),
        ("en", "English"),
    ]

    email = models.EmailField()
    locale = models.CharField(max_length=2, choices=LOCALE_CHOICES)
    source = models.CharField(
        max_length=120,
        blank=True,
        help_text="Page slug or campaign that captured this email.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    mailerlite_subscriber_id = models.CharField(max_length=64, blank=True, default="")
    mailerlite_status = models.CharField(max_length=32, blank=True, default="pending")
    mailerlite_error = models.TextField(blank=True, default="")
    ip = models.GenericIPAddressField(null=True, blank=True)
    country = models.CharField(max_length=2, blank=True, default="", help_text="From CF-IPCountry header.")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "locale"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["email", "locale"], name="unique_email_per_locale"
            ),
        ]

    def __str__(self):
        return f"{self.email} [{self.locale}]"
