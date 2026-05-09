"""Pages for the autoral vertical (www.bilouro.com — landing + about/CV)."""
from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page


class HomePage(Page):
    """Landing page for www.bilouro.com."""

    intro = RichTextField(blank=True, help_text="Short intro / tagline shown above the fold.")
    body = RichTextField(blank=True, help_text="Optional longer content under the intro.")
    intro_pt = RichTextField(blank=True, help_text="Portuguese version of intro.")
    body_pt = RichTextField(blank=True, help_text="Portuguese version of body.")

    template = "autoral/home_page.html"

    content_panels = Page.content_panels + [
        MultiFieldPanel([FieldPanel("intro"), FieldPanel("body")], heading="EN"),
        MultiFieldPanel([FieldPanel("intro_pt"), FieldPanel("body_pt")], heading="PT"),
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

    title_pt = models.CharField(max_length=255, blank=True)
    headline_pt = models.CharField(max_length=200, blank=True)
    bio_pt = RichTextField(blank=True)
    skills_pt = RichTextField(blank=True)
    experience_pt = RichTextField(blank=True)
    contact_links_pt = RichTextField(blank=True)

    template = "autoral/about_page.html"

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [FieldPanel("headline"), FieldPanel("bio"), FieldPanel("skills"),
             FieldPanel("experience"), FieldPanel("contact_links")],
            heading="EN",
        ),
        MultiFieldPanel(
            [FieldPanel("title_pt"), FieldPanel("headline_pt"), FieldPanel("bio_pt"),
             FieldPanel("skills_pt"), FieldPanel("experience_pt"), FieldPanel("contact_links_pt")],
            heading="PT",
        ),
    ]

    parent_page_types = ["autoral.HomePage"]
