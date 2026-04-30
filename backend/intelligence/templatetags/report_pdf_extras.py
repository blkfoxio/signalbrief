"""Template filters for the PDF report template."""

from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Look up a value in a dict by key. Tries str(key) too since JSON keys come back as strings."""
    if not isinstance(mapping, dict):
        return None
    if key in mapping:
        return mapping[key]
    return mapping.get(str(key))


@register.filter
def sub(a, b):
    """Subtract b from a (used for '+N more' counts)."""
    try:
        return int(a) - int(b)
    except (TypeError, ValueError):
        return ""


@register.filter
def intcomma(value):
    """Format an integer with thousands separators (avoids pulling in django.contrib.humanize)."""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return value
