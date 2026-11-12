from django import template

from ..cohort import display

register = template.Library()


@register.filter
def pct(value, digits=1):
    """0.1234 -> "12.3%"; None -> "–"."""
    if value is None:
        return "–"
    return f"{100 * value:.{int(digits)}f}%"


@register.filter
def num(value, digits=2):
    if value is None:
        return "–"
    return f"{value:.{int(digits)}f}"


@register.filter
def label(value):
    return display(value)
