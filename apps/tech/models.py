"""Pages for the tech vertical (tech.bilouro.com — developer blog)."""
from django.db import models
from modelcluster.fields import ParentalKey
from modelcluster.contrib.taggit import ClusterTaggableManager
from taggit.models import TaggedItemBase
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.search import index


class BlogIndexPage(Page):
    """Listing of tech blog posts."""

    intro = RichTextField(blank=True)

    template = "tech/blog_index_page.html"

    content_panels = Page.content_panels + [FieldPanel("intro")]

    subpage_types = ["tech.BlogPostPage", "tech.ProjectIndexPage"]
    parent_page_types = ["wagtailcore.Page"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["posts"] = (
            BlogPostPage.objects.live()
            .descendant_of(self)
            .order_by("-date", "-first_published_at")
        )
        return context


class ProjectIndexPage(Page):
    """Catalogue of projects (OSS + professional + side)."""

    intro = RichTextField(blank=True)

    template = "tech/project_index_page.html"

    content_panels = Page.content_panels + [FieldPanel("intro")]

    subpage_types = ["tech.ProjectPage"]
    parent_page_types = ["tech.BlogIndexPage", "wagtailcore.Page"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["projects"] = (
            ProjectPage.objects.live().descendant_of(self).order_by("sort_order")
        )
        return context


class ProjectPage(Page):
    """A single project — open source, professional, or personal."""

    KIND_CHOICES = [
        ("oss", "Open Source"),
        ("work", "Professional"),
        ("personal", "Personal / Side"),
    ]

    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="oss")
    period = models.CharField(max_length=100, blank=True, help_text="e.g. '2022-2025'")
    summary = models.CharField(max_length=300, help_text="One-line description shown on cards")
    description = RichTextField(blank=True)
    tech_stack = models.CharField(
        max_length=300, blank=True, help_text="Comma-separated, e.g. 'Python, AWS, Postgres'"
    )
    github_url = models.URLField(blank=True)
    live_url = models.URLField(blank=True)
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    sort_order = models.IntegerField(default=0)

    template = "tech/project_page.html"

    search_fields = Page.search_fields + [
        index.SearchField("summary"),
        index.SearchField("description"),
        index.SearchField("tech_stack"),
    ]

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("kind"),
                FieldPanel("period"),
                FieldPanel("tech_stack"),
                FieldPanel("sort_order"),
            ],
            heading="Meta",
        ),
        FieldPanel("image"),
        FieldPanel("summary"),
        FieldPanel("description"),
        MultiFieldPanel(
            [FieldPanel("github_url"), FieldPanel("live_url")], heading="Links"
        ),
    ]

    parent_page_types = ["tech.ProjectIndexPage"]


class BlogPostTag(TaggedItemBase):
    content_object = ParentalKey(
        "tech.BlogPostPage",
        related_name="tagged_items",
        on_delete=models.CASCADE,
    )


class BlogPostPage(Page):
    """A single blog post (markdown body rendered to HTML at template time)."""

    date = models.DateField("Post date")
    intro = models.CharField(max_length=400, blank=True)
    body_md = models.TextField(blank=True, help_text="Markdown source.")
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    tags = ClusterTaggableManager(through=BlogPostTag, blank=True)

    template = "tech/blog_post_page.html"

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("body_md"),
    ]

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [FieldPanel("date"), FieldPanel("tags")],
            heading="Meta",
        ),
        FieldPanel("image"),
        FieldPanel("intro"),
        FieldPanel("body_md"),
    ]

    parent_page_types = ["tech.BlogIndexPage"]
