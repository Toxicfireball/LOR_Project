# characters/templatetags/ui_extras.py
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag(takes_context=True)
def editable_num(context, value, key):
    overrides = context.get('field_overrides', {})
    display = overrides.get(key, value)
    return mark_safe(
        f'<span class="editable-number" data-key="{key}" role="button" tabindex="0">{display}</span>'
    )

@register.simple_tag(takes_context=True)
def note_icon(context, key):
    """
    Render a small note icon. Safe no-op if key is blank.
    """
    if not key:
        return ""

    notes = context.get("notes") or context.get("notes_with_keys") or {}
    has = bool(notes.get(key)) if isinstance(notes, dict) else False
    title = "Has note" if has else "Add note"

    html = (
        f'<button type="button" title="{title}" '
        f'class="btn btn-xs btn-outline-secondary note-btn" '
        f'data-note-key="{escape(key)}" data-has-note="{1 if has else 0}">🗒️</button>'
    )
    return mark_safe(html)

@register.filter
def get_item(d, key):
    if d is None:
        return None
    try:
        return d.get(int(key))
    except Exception:
        try:
            return d.get(key)
        except Exception:
            return None

@register.filter
def dict_get(d, key):
    try:
        return d.get(key, [])
    except Exception:
        return []
