# characters/widgets.py
import json
from django.forms.widgets import Textarea
from django.utils.safestring import mark_safe
from django import forms

from .models import CharacterClass
# characters/widgets.py
class FormulaBuilderWidget(Textarea):

    class Media:
        js  = ("characters/js/formula_builder.js",)
        css = {"all": ("characters/css/formula_builder.css",)}

    def __init__(self, *, variables, dice, **kwargs):
        super().__init__(**kwargs)
        self.variables = variables
        self.dice      = dice

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs["data-vars"] = json.dumps(self.variables)
        attrs["data-dice"] = json.dumps(self.dice)
        textarea = super().render(name, value, attrs, renderer)
        # inject a datalist for variables:
        vars_list = "\n".join(f'<option value="{v}">' for v in self.variables)
        return mark_safe(f"""
          <div class="formula-builder">
            
            <!-- dropdown for vars -->
            <input list="fb-vars" class="fb-var-dropdown" placeholder="Insert variable…"/>
            <datalist id="fb-vars">
              {vars_list}
            </datalist>
            {textarea}
            <div class="fb-error" style="display:none;color:#e44;">Invalid formula</div>
          </div>
        """)

from django import forms
from .models import CharacterClass

class CharacterClassSelect(forms.Select):
    def create_option(self, *args, **kwargs):
        option = super().create_option(*args, **kwargs)

        # Django may have stored a ModelChoiceIteratorValue here.
        raw_val = option.get("value")
        if raw_val is not None:
            # coerce it to the string Django would have used in HTML:
            raw_pk = str(raw_val)
            try:
                cls = CharacterClass.objects.get(pk=raw_pk)
                option["attrs"]["data-class-id"] = cls.class_ID
            except (CharacterClass.DoesNotExist, ValueError):
                pass

        return option