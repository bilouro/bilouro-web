"""Pages for studio.bilouro.com — Bilouro Studio (tech studio / services site).

i18n follows the project convention: EN is the base field, `<field>_pt` is the
Portuguese sibling, and templates render via the `{% tr %}` / `{% tr_richtext %}`
tags (apps/core/templatetags/i18n_fields.py). Page-level fields are filled by
`manage.py translate_pages`; the inline cards/steps/cases are translated by the
same command (see the `inlines` spec in that command).

Phase 1 (MVP):
  studio.bilouro.com/
  ├── /            → StudioHomePage  (hero + 5 services + process + 3 cases + about + CTA)
  ├── /agendar     → StudioBookingPage  (booking form)
  └── /obrigado    → StudioThanksPage   (post-submit confirmation)

The booking form POSTs to /api/studio/booking (apps/studio/views.py). Leads are
persisted to the `Booking` model BEFORE the notification email is attempted, so a
mail failure never loses a lead.
"""
from django.db import models
from django.shortcuts import get_object_or_404
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.fields import RichTextField
from wagtail.models import Orderable, Page
from wagtail.search import index


# ─── Home (studio.bilouro.com root) ────────────────────────────────────


class StudioHomePage(Page):
    """Long-form home: hero · services · process · cases · about · closing CTA."""

    # Hero
    hero_eyebrow = models.CharField(max_length=160, blank=True, help_text="Small eyebrow above the hero headline.")
    hero_headline = RichTextField(blank=True, help_text="Hero headline (use <em> for emphasis).")
    hero_subhead = RichTextField(blank=True, help_text="Short paragraph under the hero headline.")
    cta_label = models.CharField(max_length=80, blank=True, default="Book a conversation")

    # Section headings / intros
    services_heading = models.CharField(max_length=160, blank=True)
    services_intro = RichTextField(blank=True)
    process_heading = models.CharField(max_length=160, blank=True)
    process_intro = RichTextField(blank=True)
    cases_heading = models.CharField(max_length=160, blank=True)
    cases_intro = RichTextField(blank=True)
    about_heading = models.CharField(max_length=160, blank=True)
    about_body = RichTextField(blank=True)
    closing_heading = models.CharField(max_length=200, blank=True)
    closing_body = RichTextField(blank=True)
    stack_note = RichTextField(blank=True, help_text="Small 'stack' line in the footer (cloud/tools).")

    # PT siblings
    hero_eyebrow_pt = models.CharField(max_length=160, blank=True)
    hero_headline_pt = RichTextField(blank=True)
    hero_subhead_pt = RichTextField(blank=True)
    cta_label_pt = models.CharField(max_length=80, blank=True)
    services_heading_pt = models.CharField(max_length=160, blank=True)
    services_intro_pt = RichTextField(blank=True)
    process_heading_pt = models.CharField(max_length=160, blank=True)
    process_intro_pt = RichTextField(blank=True)
    cases_heading_pt = models.CharField(max_length=160, blank=True)
    cases_intro_pt = RichTextField(blank=True)
    about_heading_pt = models.CharField(max_length=160, blank=True)
    about_body_pt = RichTextField(blank=True)
    closing_heading_pt = models.CharField(max_length=200, blank=True)
    closing_body_pt = RichTextField(blank=True)
    stack_note_pt = RichTextField(blank=True)

    template = "studio/home_page.html"

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("hero_eyebrow"),
                FieldPanel("hero_headline"),
                FieldPanel("hero_subhead"),
                FieldPanel("cta_label"),
            ],
            heading="Hero (EN)",
        ),
        MultiFieldPanel([FieldPanel("services_heading"), FieldPanel("services_intro")], heading="Services (EN)"),
        InlinePanel("service_cards", label="Service card"),
        MultiFieldPanel([FieldPanel("process_heading"), FieldPanel("process_intro")], heading="Process (EN)"),
        InlinePanel("process_steps", label="Process step"),
        MultiFieldPanel([FieldPanel("cases_heading"), FieldPanel("cases_intro")], heading="Cases (EN)"),
        InlinePanel("cases", label="Case"),
        MultiFieldPanel([FieldPanel("about_heading"), FieldPanel("about_body")], heading="About (EN)"),
        MultiFieldPanel([FieldPanel("closing_heading"), FieldPanel("closing_body"), FieldPanel("stack_note")], heading="Closing CTA / footer (EN)"),
        MultiFieldPanel(
            [
                FieldPanel("hero_eyebrow_pt"),
                FieldPanel("hero_headline_pt"),
                FieldPanel("hero_subhead_pt"),
                FieldPanel("cta_label_pt"),
                FieldPanel("services_heading_pt"),
                FieldPanel("services_intro_pt"),
                FieldPanel("process_heading_pt"),
                FieldPanel("process_intro_pt"),
                FieldPanel("cases_heading_pt"),
                FieldPanel("cases_intro_pt"),
                FieldPanel("about_heading_pt"),
                FieldPanel("about_body_pt"),
                FieldPanel("closing_heading_pt"),
                FieldPanel("closing_body_pt"),
                FieldPanel("stack_note_pt"),
            ],
            heading="PT",
            classname="collapsed",
        ),
    ]

    search_fields = Page.search_fields + [
        index.SearchField("hero_headline"),
        index.SearchField("about_body"),
    ]

    parent_page_types = ["wagtailcore.Page"]
    subpage_types = [
        "studio.StudioBookingPage",
        "studio.StudioThanksPage",
        "studio.StudioBlogIndexPage",
        "studio.StudioProjectIndexPage",
        "studio.StudioSolutionPage",
    ]

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        ctx["service_cards"] = self.service_cards.all()
        ctx["process_steps"] = self.process_steps.all()
        ctx["cases"] = self.cases.all()
        ctx["booking_page"] = StudioBookingPage.objects.live().descendant_of(self).first()
        return ctx


class StudioServiceCard(Orderable):
    """One of the service cards on the home page."""

    page = ParentalKey(StudioHomePage, on_delete=models.CASCADE, related_name="service_cards")
    image = models.ForeignKey(
        "wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    title = models.CharField(max_length=120)
    subtitle = models.CharField(max_length=255, blank=True)
    output = models.TextField(blank=True, help_text="The typical deliverable / outcome.")
    title_pt = models.CharField(max_length=120, blank=True)
    subtitle_pt = models.CharField(max_length=255, blank=True)
    output_pt = models.TextField(blank=True)

    panels = [
        FieldPanel("image"),
        FieldPanel("title"),
        FieldPanel("subtitle"),
        FieldPanel("output"),
        MultiFieldPanel(
            [FieldPanel("title_pt"), FieldPanel("subtitle_pt"), FieldPanel("output_pt")],
            heading="PT",
            classname="collapsed",
        ),
    ]


class StudioProcessStep(Orderable):
    """One step of the 'how we work' process."""

    page = ParentalKey(StudioHomePage, on_delete=models.CASCADE, related_name="process_steps")
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    title_pt = models.CharField(max_length=120, blank=True)
    description_pt = models.TextField(blank=True)

    panels = [
        FieldPanel("title"),
        FieldPanel("description"),
        MultiFieldPanel(
            [FieldPanel("title_pt"), FieldPanel("description_pt")],
            heading="PT",
            classname="collapsed",
        ),
    ]


class StudioCase(Orderable):
    """A highlighted case / proof on the home page."""

    page = ParentalKey(StudioHomePage, on_delete=models.CASCADE, related_name="cases")
    image = models.ForeignKey(
        "wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    title = models.CharField(max_length=160)
    body = RichTextField(blank=True)
    link_url = models.CharField(
        max_length=300,
        blank=True,
        help_text="Optional — when set, the case links to this URL with a 'see more' hint.",
    )
    title_pt = models.CharField(max_length=160, blank=True)
    body_pt = RichTextField(blank=True)

    panels = [
        FieldPanel("image"),
        FieldPanel("title"),
        FieldPanel("body"),
        FieldPanel("link_url"),
        MultiFieldPanel(
            [FieldPanel("title_pt"), FieldPanel("body_pt")],
            heading="PT",
            classname="collapsed",
        ),
    ]


# ─── Booking page (/agendar) ───────────────────────────────────────────


class StudioBookingPage(Page):
    """Booking form page. The form itself is rendered by the template and POSTs
    to /api/studio/booking; copy below is editable."""

    heading = models.CharField(max_length=160, blank=True, default="Book a conversation")
    intro = RichTextField(blank=True)
    hours_note = models.CharField(max_length=200, blank=True, help_text="e.g. 'Weekdays, 11:00–19:00.'")
    heading_pt = models.CharField(max_length=160, blank=True)
    intro_pt = RichTextField(blank=True)
    hours_note_pt = models.CharField(max_length=200, blank=True)

    template = "studio/booking_page.html"
    max_count = 1

    content_panels = Page.content_panels + [
        MultiFieldPanel([FieldPanel("heading"), FieldPanel("intro"), FieldPanel("hours_note")], heading="EN"),
        MultiFieldPanel(
            [FieldPanel("heading_pt"), FieldPanel("intro_pt"), FieldPanel("hours_note_pt")],
            heading="PT",
            classname="collapsed",
        ),
    ]

    parent_page_types = ["studio.StudioHomePage"]
    subpage_types: list[str] = []

    def get_context(self, request, *args, **kwargs):
        from .views import TIME_SLOTS

        ctx = super().get_context(request, *args, **kwargs)
        ctx["time_slots"] = TIME_SLOTS
        ctx["thanks_page"] = StudioThanksPage.objects.live().first()
        return ctx


class StudioThanksPage(Page):
    """Post-submit confirmation page (/obrigado)."""

    heading = models.CharField(max_length=160, blank=True, default="We got it")
    body = RichTextField(blank=True)
    heading_pt = models.CharField(max_length=160, blank=True)
    body_pt = RichTextField(blank=True)

    template = "studio/thanks_page.html"
    max_count = 1

    content_panels = Page.content_panels + [
        MultiFieldPanel([FieldPanel("heading"), FieldPanel("body")], heading="EN"),
        MultiFieldPanel([FieldPanel("heading_pt"), FieldPanel("body_pt")], heading="PT", classname="collapsed"),
    ]

    parent_page_types = ["studio.StudioHomePage"]
    subpage_types: list[str] = []

    def get_sitemap_urls(self, request=None):
        # Post-submit confirmation page — never index.
        return []


# ─── Blog + Projects (read tech's content, render in studio style) ─────
#
# These index pages do NOT own any posts/projects — they read the existing
# tech BlogPostPage / ProjectPage rows (single shared DB) and render them under
# studio URLs with studio templates. No cross-links to tech.bilouro.com.


class StudioBlogIndexPage(RoutablePageMixin, Page):
    """studio.bilouro.com/blog — same posts as tech, studio style, studio URLs."""

    intro = RichTextField(blank=True)
    intro_pt = RichTextField(blank=True)

    template = "studio/blog_index_page.html"
    max_count = 1
    parent_page_types = ["studio.StudioHomePage"]
    subpage_types: list[str] = []

    content_panels = Page.content_panels + [
        MultiFieldPanel([FieldPanel("intro")], heading="EN"),
        MultiFieldPanel([FieldPanel("intro_pt")], heading="PT", classname="collapsed"),
    ]

    def _posts(self):
        from apps.tech.models import BlogPostPage

        return BlogPostPage.objects.live().order_by("-date", "-first_published_at")

    @path("")
    def index_route(self, request):
        return self.render(request, context_overrides={"posts": self._posts()})

    @path("<slug:slug>/")
    def post_route(self, request, slug):
        from apps.tech.models import BlogPostPage

        post = get_object_or_404(BlogPostPage.objects.live(), slug=slug)
        return self.render(
            request,
            context_overrides={"post": post},
            template="studio/blog_post_page.html",
        )

    def get_sitemap_urls(self, request=None):
        base = self.get_full_url(request)
        if not base:
            return []
        if not base.endswith("/"):
            base += "/"
        urls = [{"location": base}]
        for post in self._posts():
            entry = {"location": f"{base}{post.slug}/"}
            if post.last_published_at:
                entry["lastmod"] = post.last_published_at
            urls.append(entry)
        return urls


class StudioProjectIndexPage(RoutablePageMixin, Page):
    """studio.bilouro.com/projects — same projects as tech, studio style/URLs."""

    intro = RichTextField(blank=True)
    intro_pt = RichTextField(blank=True)

    template = "studio/project_index_page.html"
    max_count = 1
    parent_page_types = ["studio.StudioHomePage"]
    subpage_types: list[str] = []

    content_panels = Page.content_panels + [
        MultiFieldPanel([FieldPanel("intro")], heading="EN"),
        MultiFieldPanel([FieldPanel("intro_pt")], heading="PT", classname="collapsed"),
    ]

    def _projects(self):
        from apps.tech.models import ProjectPage

        return ProjectPage.objects.live().order_by("sort_order")

    @path("")
    def index_route(self, request):
        return self.render(request, context_overrides={"projects": self._projects()})

    @path("<slug:slug>/")
    def project_route(self, request, slug):
        from apps.tech.models import ProjectPage

        project = get_object_or_404(ProjectPage.objects.live(), slug=slug)
        return self.render(
            request,
            context_overrides={"project": project},
            template="studio/project_page.html",
        )

    def get_sitemap_urls(self, request=None):
        base = self.get_full_url(request)
        if not base:
            return []
        if not base.endswith("/"):
            base += "/"
        urls = [{"location": base}]
        for project in self._projects():
            entry = {"location": f"{base}{project.slug}/"}
            if project.last_published_at:
                entry["lastmod"] = project.last_published_at
            urls.append(entry)
        return urls


# ─── Solution page (business-facing infographic) ───────────────────────


class StudioSolutionPage(Page):
    """A business-facing 'solution' page — infographic style, no jargon.
    Reached from the Proof section ('see more'). Indexed in the sitemap."""

    hero_eyebrow = models.CharField(max_length=160, blank=True)
    hero_headline = RichTextField(blank=True, help_text="Use <em> for emphasis.")
    hero_sub = RichTextField(blank=True)
    problem_heading = models.CharField(max_length=160, blank=True)
    problem_body = RichTextField(blank=True)
    solution_heading = models.CharField(max_length=160, blank=True)
    solution_body = RichTextField(blank=True)
    steps_heading = models.CharField(max_length=160, blank=True)
    benefits_heading = models.CharField(max_length=160, blank=True)
    stats_heading = models.CharField(max_length=160, blank=True)
    proof_note = RichTextField(blank=True, help_text="Small 'live in production' trust line.")
    closing_heading = models.CharField(max_length=200, blank=True)
    closing_body = RichTextField(blank=True)
    cta_label = models.CharField(max_length=80, blank=True, default="Book a conversation")
    price_heading = models.CharField(max_length=120, blank=True)
    price_value = models.CharField(max_length=80, blank=True, help_text="e.g. 'from €1,000'")
    price_note = RichTextField(blank=True)

    hero_eyebrow_pt = models.CharField(max_length=160, blank=True)
    hero_headline_pt = RichTextField(blank=True)
    hero_sub_pt = RichTextField(blank=True)
    problem_heading_pt = models.CharField(max_length=160, blank=True)
    problem_body_pt = RichTextField(blank=True)
    solution_heading_pt = models.CharField(max_length=160, blank=True)
    solution_body_pt = RichTextField(blank=True)
    steps_heading_pt = models.CharField(max_length=160, blank=True)
    benefits_heading_pt = models.CharField(max_length=160, blank=True)
    stats_heading_pt = models.CharField(max_length=160, blank=True)
    proof_note_pt = RichTextField(blank=True)
    closing_heading_pt = models.CharField(max_length=200, blank=True)
    closing_body_pt = RichTextField(blank=True)
    cta_label_pt = models.CharField(max_length=80, blank=True)
    price_heading_pt = models.CharField(max_length=120, blank=True)
    price_value_pt = models.CharField(max_length=80, blank=True)
    price_note_pt = RichTextField(blank=True)

    template = "studio/solution_page.html"
    parent_page_types = ["studio.StudioHomePage"]
    subpage_types: list[str] = []

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [FieldPanel("hero_eyebrow"), FieldPanel("hero_headline"), FieldPanel("hero_sub")],
            heading="Hero (EN)",
        ),
        MultiFieldPanel([FieldPanel("problem_heading"), FieldPanel("problem_body")], heading="Problem (EN)"),
        MultiFieldPanel([FieldPanel("solution_heading"), FieldPanel("solution_body")], heading="Solution (EN)"),
        FieldPanel("steps_heading"),
        InlinePanel("steps", label="How-it-works step"),
        FieldPanel("benefits_heading"),
        InlinePanel("benefits", label="Benefit"),
        FieldPanel("stats_heading"),
        InlinePanel("stats", label="Stat"),
        FieldPanel("proof_note"),
        MultiFieldPanel([FieldPanel("price_heading"), FieldPanel("price_value"), FieldPanel("price_note")], heading="Investment (EN)"),
        MultiFieldPanel([FieldPanel("closing_heading"), FieldPanel("closing_body"), FieldPanel("cta_label")], heading="Closing CTA (EN)"),
        MultiFieldPanel(
            [
                FieldPanel("hero_eyebrow_pt"), FieldPanel("hero_headline_pt"), FieldPanel("hero_sub_pt"),
                FieldPanel("problem_heading_pt"), FieldPanel("problem_body_pt"),
                FieldPanel("solution_heading_pt"), FieldPanel("solution_body_pt"),
                FieldPanel("steps_heading_pt"), FieldPanel("benefits_heading_pt"), FieldPanel("stats_heading_pt"),
                FieldPanel("proof_note_pt"),
                FieldPanel("price_heading_pt"), FieldPanel("price_value_pt"), FieldPanel("price_note_pt"),
                FieldPanel("closing_heading_pt"), FieldPanel("closing_body_pt"), FieldPanel("cta_label_pt"),
            ],
            heading="PT",
            classname="collapsed",
        ),
    ]

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        ctx["steps"] = self.steps.all()
        ctx["benefits"] = self.benefits.all()
        ctx["stats"] = self.stats.all()
        return ctx


class StudioSolutionStep(Orderable):
    page = ParentalKey(StudioSolutionPage, on_delete=models.CASCADE, related_name="steps")
    icon = models.CharField(max_length=8, blank=True, help_text="Emoji.")
    title = models.CharField(max_length=120)
    body = models.TextField(blank=True)
    title_pt = models.CharField(max_length=120, blank=True)
    body_pt = models.TextField(blank=True)

    panels = [
        FieldPanel("icon"), FieldPanel("title"), FieldPanel("body"),
        MultiFieldPanel([FieldPanel("title_pt"), FieldPanel("body_pt")], heading="PT", classname="collapsed"),
    ]


class StudioSolutionBenefit(Orderable):
    page = ParentalKey(StudioSolutionPage, on_delete=models.CASCADE, related_name="benefits")
    icon = models.CharField(max_length=8, blank=True, help_text="Emoji.")
    title = models.CharField(max_length=120)
    body = models.TextField(blank=True)
    title_pt = models.CharField(max_length=120, blank=True)
    body_pt = models.TextField(blank=True)

    panels = [
        FieldPanel("icon"), FieldPanel("title"), FieldPanel("body"),
        MultiFieldPanel([FieldPanel("title_pt"), FieldPanel("body_pt")], heading="PT", classname="collapsed"),
    ]


class StudioSolutionStat(Orderable):
    page = ParentalKey(StudioSolutionPage, on_delete=models.CASCADE, related_name="stats")
    value = models.CharField(max_length=40, help_text="e.g. '24/7'")
    label = models.CharField(max_length=120, blank=True)
    label_pt = models.CharField(max_length=120, blank=True)

    panels = [
        FieldPanel("value"), FieldPanel("label"),
        MultiFieldPanel([FieldPanel("label_pt")], heading="PT", classname="collapsed"),
    ]


# ─── Booking (plain Django model — leads) ──────────────────────────────


class Booking(models.Model):
    """One record per booking-form submission. Persisted before the notification
    email is sent, so leads survive an email-delivery failure."""

    name = models.CharField(max_length=160)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    preferred_date = models.DateField(null=True, blank=True)
    preferred_time = models.CharField(max_length=10, blank=True)
    message = models.TextField(blank=True)
    source = models.CharField(max_length=120, blank=True, help_text="Page slug / campaign that captured this lead.")
    created_at = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    country = models.CharField(max_length=2, blank=True, default="", help_text="From CF-IPCountry header.")
    notified = models.BooleanField(default=False, help_text="Notification email sent successfully.")
    notify_error = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["-created_at"])]

    def __str__(self):
        return f"{self.name} <{self.email}> ({self.created_at:%Y-%m-%d})"
