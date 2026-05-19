"""Wagtail admin extras for hashtagjesus: snippet for NewsletterSignup."""
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import NewsletterSignup


class NewsletterSignupSnippet(SnippetViewSet):
    model = NewsletterSignup
    icon = "mail"
    menu_label = "Newsletter signups"
    menu_order = 200
    add_to_admin_menu = True
    list_display = ("email", "locale", "mailerlite_status", "country", "created_at")
    list_filter = ("locale", "mailerlite_status", "country")
    search_fields = ("email", "source")


register_snippet(NewsletterSignupSnippet)
