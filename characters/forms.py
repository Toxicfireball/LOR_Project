# forms.py
import json
from django import forms
from .models import Character

# Define a dictionary for the default skill proficiencies.
# In LOR, during character creation every skill is by default Trained.

# forms.py (app `characters`)
from django import forms
from .models import CharacterClass, CharacterClassProgress
from django.core.exceptions import ValidationError
class LevelUpForm(forms.Form):
    # For level 0: choose base class
    base_class = forms.ModelChoiceField(
        queryset=CharacterClass.objects.all(),
        required=False,
        label="Choose a Class"
    )
    # For existing: choose which class to advance
    advance_class = forms.ModelChoiceField(
        queryset=CharacterClass.objects.none(),
        required=False,
        label="Advance which Class"
    )

    def __init__(self, *args, character=None, **kwargs):
        super().__init__(*args, **kwargs)
        if character:
            qs = CharacterClassProgress.objects.filter(character=character)
            self.fields['advance_class'].queryset = CharacterClass.objects.filter(
                pk__in=[p.character_class.pk for p in qs]
            )
        else:
            self.fields['advance_class'].queryset = CharacterClass.objects.none()

class CharacterClassForm(forms.ModelForm):
    class Meta:
        model  = CharacterClass
        fields = "__all__"  # includes key_abilities

    def clean_key_abilities(self):
        abilities = self.cleaned_data.get("key_abilities")
        if not abilities:
            raise ValidationError("You must select at least one key ability score.")
        if abilities.count() not in (1, 2):
            raise ValidationError("Select exactly one or two key ability scores.")
        return abilities

    def clean(self):
        cleaned = super().clean()
        # Model.clean() also runs, but this ensures form‐level validation first.
        return cleaned
class CharacterCreationForm(forms.ModelForm):
    """
    Form for creating a new character.
    This form collects basic information (name, race, subrace, background combo, etc.),
    ability scores (calculated via a point-buy system), a free-form backstory,
    and skill proficiencies (as a JSON string).
    
    The skill_proficiencies field is hidden from the user because it is computed
    from background selections and other bonuses. However, if no value is provided,
    we default all skills to "Trained".
    """


    class Meta:
        model = Character
        fields = [
            "name",
            "race",
            "subrace",
            "half_elf_origin",
            "bg_combo",
            "main_background",
            "side_background_1",
            "side_background_2",
            "backstory",
            "strength",
            "dexterity",
            "constitution",
            "intelligence",
            "wisdom",
            "charisma",
        ]
        widgets = {
            "main_background": forms.Select(attrs={"id": "main_background", "name": "main_background"}),
            "side_background_1": forms.Select(attrs={"id": "side_background_1", "name": "side_background_1"}),
            "side_background_2": forms.Select(attrs={"id": "side_background_2", "name": "side_background_2"}),
            "backstory": forms.Textarea(attrs={"rows": 4, "cols": 40}),
            # Other fields may be rendered as hidden if handled entirely via JS.
        }

    def __init__(self, *args, **kwargs):
        """
        Initialize the form.
        You can set initial default values for ability scores here if needed.
        For example, set the base ability scores to 8.
        """
        super().__init__(*args, **kwargs)
        # Set initial ability scores for point-buy system.
        self.fields["strength"].initial = 8
        self.fields["dexterity"].initial = 8
        self.fields["constitution"].initial = 8
        self.fields["intelligence"].initial = 8
        self.fields["wisdom"].initial = 8
        self.fields["charisma"].initial = 8

        # Optionally, if you want to default skill_proficiencies to the default dictionary,
        # you can set the initial value as a JSON string.

    def clean_skill_proficiencies(self):
        """
        Ensure the skill_proficiencies field returns a valid mapping.
        If the field is empty, we assign the default skill proficiencies.
        """
        data = self.cleaned_data.get("skill_proficiencies")

    def clean(self):
        """
        You can include additional cross-field validations here.
        For example, you could check that the total background bonus does not exceed a limit.
        """
        cleaned_data = super().clean()
        # Example: Ensure that if bg_combo is not "0", then side background selections are provided.
        bg_combo = cleaned_data.get("bg_combo")
        main_bg = cleaned_data.get("main_background")
        if bg_combo and bg_combo != "0":
            if not cleaned_data.get("side_background_1"):
                self.add_error("side_background_1", "This field is required for the selected background combination.")
            if bg_combo == "2" and not cleaned_data.get("side_background_2"):
                self.add_error("side_background_2", "This field is required when selecting 2 side backgrounds.")
        return cleaned_data
# characters/forms.py
from django import forms
from .models import ClassFeature
from .widgets import FormulaBuilderWidget
from django.apps import apps
# Pull these in just once so you don’t repeat them in two places:
from characters.models import CharacterClass
from django.db import connection
def safe_class_level_vars():
    try:
        if not apps.ready:
            return []
        if CharacterClass._meta.db_table not in connection.introspection.table_names():
            return []
        return [f"{cls.name.lower()}_level" for cls in CharacterClass.objects.all()]
    except Exception:
        return []
# build your var list here once:
BASE_VARS = [
    "level", "class_level", "proficiency_modifier",
] + safe_class_level_vars() + [
    "reflex_save", "fortitude_save", "will_save",
    "initiative", "perception", "dodge",
    "spell_attack", "spell_dc", "weapon_attack",
]


DICE = ["d4","d6","d8","d10","d12","d20"]
def build_variable_list():
    base = [
        "level","class_level","proficiency_modifier",
        "hp","temp_hp",
        "reflex_save","fortitude_save","will_save",
        "initiative","perception","dodge",
        "spell_attack","spell_dc","weapon_attack",
    ]
    base += safe_class_level_vars()
    base +=BASE_VARS
    return base
# characters/forms.py
from django import forms
from .models import ClassFeature, CharacterClass
from .widgets import FormulaBuilderWidget

class ClassChoiceWithIDField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        # "WZ ‑ Wizard", "FD ‑ Fighter", etc.
        return f"{obj.class_ID} – {obj.name}"
    

class Meta:
    model  = ClassFeature
    fields = "__all__"
    widgets = {}          # ← leave empty; we assign in __init__

    class Media:
        js  = ("characters/js/formula_builder.js",)
        css = {"all": ("characters/css/formula_builder.css",)}
