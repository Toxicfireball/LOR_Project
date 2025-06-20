from django.db import models
from django.forms import fields

import bleach
from django_summernote.settings import ALLOWED_TAGS, ATTRIBUTES, STYLES
from django_summernote.widgets import SummernoteWidget
from bleach.css_sanitizer import CSSSanitizer
from bleach.sanitizer import ALLOWED_PROTOCOLS
css_sanitizer = CSSSanitizer(allowed_css_properties=STYLES)

# REPLACE LOR_Website\venv\Lib\site-packages\django_summernote\fields.py WITH THIS 
class SummernoteTextFormField(fields.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.update({'widget': SummernoteWidget()})
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        value = super().to_python(value)
        return bleach.clean(
            value,
            tags=ALLOWED_TAGS,
            attributes=ATTRIBUTES,
            css_sanitizer=css_sanitizer,
            protocols=ALLOWED_PROTOCOLS,
            strip=False,
        )


class SummernoteTextField(models.TextField):
    def formfield(self, **kwargs):
        kwargs.update({'form_class': SummernoteTextFormField})
        return super().formfield(**kwargs)

    def to_python(self, value):
        value = super().to_python(value)
        # exactly like the FormField version:
        return bleach.clean(
            value,
            tags=ALLOWED_TAGS,
            attributes=ATTRIBUTES,
            css_sanitizer=css_sanitizer,
            protocols=ALLOWED_PROTOCOLS,
            strip=False,
        )
