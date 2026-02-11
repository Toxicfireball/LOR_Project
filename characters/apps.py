# characters/apps.py
from django.apps import AppConfig

class CharactersConfig(AppConfig):
    name = "characters"

    def ready(self):
        try:
            from . import audit_signals  # noqa
            from django_summernote.fields import SummernoteTextField
            orig = SummernoteTextField.to_python

            def to_python(self, html, *args, **kwargs):
                """
                Drop any extra args (mask) or kwargs (styles),
                then call the original to_python(self, html).
                """
                return orig(self, html)

            SummernoteTextField.to_python = to_python
        except ImportError:
            pass
