"""Pages for the shop vertical (books.bilouro.com — book catalogue + product pages)."""
from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page


class BookCatalogPage(Page):
    """Catalogue page that lists BookPage children."""

    intro = RichTextField(blank=True)

    template = "shop/book_catalog_page.html"

    content_panels = Page.content_panels + [FieldPanel("intro")]

    subpage_types = ["shop.BookPage"]
    parent_page_types = ["wagtailcore.Page"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["books"] = (
            BookPage.objects.live().descendant_of(self).order_by("-first_published_at")
        )
        return context


class BookPage(Page):
    """A book product page."""

    LANGUAGE_CHOICES = [("pt", "Português"), ("en", "English")]

    subtitle = models.CharField(max_length=200, blank=True)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default="pt")
    description = RichTextField(blank=True)
    price_eur = models.DecimalField(max_digits=8, decimal_places=2, default=0)
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
            [FieldPanel("subtitle"), FieldPanel("language"), FieldPanel("price_eur")],
            heading="Meta",
        ),
        FieldPanel("cover_image"),
        FieldPanel("description"),
        FieldPanel("buy_url"),
    ]

    parent_page_types = ["shop.BookCatalogPage"]
