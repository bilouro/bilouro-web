"""Tags for picking a translatable field by current LANGUAGE_CODE.

Usage:
    {% load i18n_fields %}
    {{ page|tr:"intro" }}
    {% tr_richtext page "body" %}
"""
from django import template
from django.utils.safestring import mark_safe
from wagtail.templatetags.wagtailcore_tags import richtext

register = template.Library()


def _value(page, field, request):
    if not page or not field:
        return ""
    lang = (getattr(request, "LANGUAGE_CODE", "") or "en").split("-")[0]
    if lang == "pt":
        v = getattr(page, f"{field}_pt", None)
        if v:
            return v
    return getattr(page, field, "") or ""


@register.simple_tag(takes_context=True)
def tr(context, page, field):
    """Plain text — returns _pt variant if cookie says pt and field exists."""
    return _value(page, field, context.get("request"))


@register.simple_tag(takes_context=True)
def tr_richtext(context, page, field):
    """RichText — same logic but expanded to <p> etc."""
    val = _value(page, field, context.get("request"))
    return richtext(val) if val else ""
