"""Pages for the autoral vertical (www.bilouro.com — landing + about/CV)."""
from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page


class HomePage(Page):
    """Landing page for www.bilouro.com."""

    intro = RichTextField(blank=True, help_text="Short intro / tagline shown above the fold.")
    body = RichTextField(blank=True, help_text="Optional longer content under the intro.")

    template = "autoral/home_page.html"

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("body"),
    ]

    subpage_types = ["autoral.AboutPage"]
    parent_page_types = ["wagtailcore.Page"]


class AboutPage(Page):
    """CV / about page — public-safe (no PII)."""

    headline = models.CharField(max_length=200, blank=True)
    bio = RichTextField(blank=True)
    skills = RichTextField(blank=True, help_text="Stack and skills (markdown-friendly).")
    experience = RichTextField(blank=True, help_text="Career highlights, no employer-PII.")
    contact_links = RichTextField(blank=True, help_text="LinkedIn / GitHub / email-button.")

    template = "autoral/about_page.html"

    content_panels = Page.content_panels + [
        FieldPanel("headline"),
        FieldPanel("bio"),
        FieldPanel("skills"),
        FieldPanel("experience"),
        FieldPanel("contact_links"),
    ]

    parent_page_types = ["autoral.HomePage"]
