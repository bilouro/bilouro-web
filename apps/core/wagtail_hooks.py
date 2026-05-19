"""Wagtail admin hooks: custom URLs + sidebar menu items."""
from django.urls import path
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from .views import stats_dashboard


@hooks.register("register_admin_urls")
def register_stats_url():
    """Mount /admin/stats/ — the GoAccess dashboard, gated by admin auth."""
    return [
        path("stats/", stats_dashboard, name="goaccess_stats"),
    ]


@hooks.register("register_admin_menu_item")
def register_stats_menu():
    """Sidebar entry pointing to the GoAccess dashboard."""
    return MenuItem(
        "Stats",
        "/admin/stats/",
        icon_name="site",
        order=10000,
    )
