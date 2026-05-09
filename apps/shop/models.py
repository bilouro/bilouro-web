"""Pages for the shop vertical (books.bilouro.com — book catalogue + product + posts)."""
from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.search import index


class BookCatalogPage(Page):
    """Catalogue page that lists BookPage children."""

    intro = RichTextField(blank=True)
    intro_pt = RichTextField(blank=True)

    template = "shop/book_catalog_page.html"

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("intro_pt"),
    ]

    subpage_types = ["shop.BookPage"]
    parent_page_types = ["wagtailcore.Page"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["books"] = (
            BookPage.objects.live().descendant_of(self).order_by("-first_published_at")
        )
        # Aggregate posts from ALL books — newest first
        context["posts"] = (
            BookPostPage.objects.live()
            .descendant_of(self)
            .order_by("-date", "-first_published_at")[:10]
        )
        return context


class BookPage(Page):
    """A book product page that also acts as the index for pre-launch posts."""

    LANGUAGE_CHOICES = [("pt", "Português"), ("en", "English")]

    subtitle = models.CharField(max_length=200, blank=True)
    subtitle_pt = models.CharField(max_length=200, blank=True)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default="pt")
    description = RichTextField(blank=True)
    description_pt = RichTextField(blank=True)
    price_eur = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    coming_soon = models.BooleanField(
        default=True,
        help_text="If true, page shows 'coming soon' and the buy button is hidden.",
    )
    cover_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    buy_url = models.URLField(
        blank=True,
        help_text="External purchase link (Gumroad / Stripe / Lemon Squeezy / Polar).",
    )

    template = "shop/book_page.html"

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("subtitle"),
                FieldPanel("language"),
                FieldPanel("price_eur"),
                FieldPanel("coming_soon"),
            ],
            heading="Meta",
        ),
        FieldPanel("cover_image"),
        MultiFieldPanel(
            [FieldPanel("subtitle"), FieldPanel("description")], heading="EN content"
        ),
        MultiFieldPanel(
            [FieldPanel("subtitle_pt"), FieldPanel("description_pt")], heading="PT content"
        ),
        FieldPanel("buy_url"),
    ]

    subpage_types = ["shop.BookPostPage"]
    parent_page_types = ["shop.BookCatalogPage"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["posts"] = (
            BookPostPage.objects.live()
            .descendant_of(self)
            .order_by("-date", "-first_published_at")
        )
        return context


class BookPostPage(Page):
    """A pre-launch blog post under a BookPage (mirrors LinkedIn cadence)."""

    date = models.DateField("Post date")
    ref = models.CharField(
        max_length=200,
        blank=True,
        help_text="Bible reference, e.g. 'João 13:1-17'.",
    )
    body_md = models.TextField(blank=True, help_text="Markdown source.")
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    template = "shop/book_post_page.html"

    search_fields = Page.search_fields + [
        index.SearchField("ref"),
        index.SearchField("body_md"),
    ]

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [FieldPanel("date"), FieldPanel("ref")],
            heading="Meta",
        ),
        FieldPanel("image"),
        FieldPanel("body_md"),
    ]

    parent_page_types = ["shop.BookPage"]
