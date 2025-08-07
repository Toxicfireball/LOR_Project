from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    """
    Usage: {{ form.field|add_class:"my-css-class another-class" }}
    """
    return field.as_widget(attrs={"class": css_class})
