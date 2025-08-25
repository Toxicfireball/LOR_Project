from django import template
register = template.Library()

@register.filter
def to(start, end):
    # usage: {% for x in 1|to:5 %} -> 1..5
    return range(int(start), int(end) + 1)