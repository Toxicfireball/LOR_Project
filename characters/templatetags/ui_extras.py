from django import template
register = template.Library()
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag(takes_context=True)
def editable_num(context, value, key):
    overrides = context.get('field_overrides', {})
    display = overrides.get(key, value)
    return mark_safe(f'<span class="editable-number" data-key="{key}" role="button" tabindex="0">{display}</span>')

@register.simple_tag(takes_context=True)
def note_icon(context, key):
    notes = context.get('field_notes', {})
    if key in notes and notes[key]:
        return mark_safe('<span class="ms-1 text-warning" title="Has note">📝</span>')
    return ""

@register.filter
def get_item(d, key):
    if d is None:
        return None
    try:
        return d.get(int(key))
    except Exception:
        return d.get(key)
