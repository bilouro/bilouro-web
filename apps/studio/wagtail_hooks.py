"""Wagtail admin extras for studio: snippet to view booking leads."""
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import Booking


class BookingSnippet(SnippetViewSet):
    model = Booking
    icon = "calendar-alt"
    menu_label = "Studio bookings"
    menu_order = 210
    add_to_admin_menu = True
    list_display = ("name", "email", "preferred_date", "preferred_time", "notified", "created_at")
    list_filter = ("notified", "country", "preferred_date")
    search_fields = ("name", "email", "message")


register_snippet(BookingSnippet)
