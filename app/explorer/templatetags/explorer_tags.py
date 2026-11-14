from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe

from .. import docs
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
    """Number with a fixed number of decimals; None as a dash."""
    if value is None:
        return "–"
    return f"{value:.{int(digits)}f}"


@register.filter
def label(value):
    """Readable form of a stored value, e.g. lu_psma_617 -> lu psma 617."""
    return display(value)


@register.filter
def cite(value):
    """Text with its citations, such as "Basch et al. (2022)", linked to the
    entries of the reference list."""
    if not value:
        return value
    return mark_safe(docs.cite(str(value), reverse("document", args=["references"])))
