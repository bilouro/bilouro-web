"""Wagtail admin hooks: custom URLs + sidebar menu items for GoAccess stats."""
from django.urls import path
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from .views import stats_bilouro, stats_dashboard, stats_hashtag_jesus


@hooks.register("register_admin_urls")
def register_stats_urls():
    """Mount /admin/stats/{,bilouro,hashtag-jesus}/ — GoAccess reports gated by auth."""
    return [
        path("stats/",               stats_dashboard,    name="goaccess_stats"),
        path("stats/bilouro/",       stats_bilouro,      name="goaccess_stats_bilouro"),
        path("stats/hashtag-jesus/", stats_hashtag_jesus, name="goaccess_stats_hashtag_jesus"),
    ]


@hooks.register("register_admin_menu_item")
def register_stats_menu_all():
    return MenuItem("Stats · all hosts", "/admin/stats/", icon_name="site", order=10000)


@hooks.register("register_admin_menu_item")
def register_stats_menu_bilouro():
    return MenuItem("Stats · bilouro.com", "/admin/stats/bilouro/", icon_name="site", order=10010)


@hooks.register("register_admin_menu_item")
def register_stats_menu_hashtagjesus():
    return MenuItem("Stats · hashtag-jesus", "/admin/stats/hashtag-jesus/", icon_name="site", order=10020)
