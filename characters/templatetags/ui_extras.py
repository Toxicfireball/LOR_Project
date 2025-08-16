from django import template
register = template.Library()

@register.filter
def get_item(d, key):
    if d is None:
        return None
    try:
        return d.get(int(key))
    except Exception:
        return d.get(key)
