# forms.py
import json
from django import forms
from .models import Character
from django.db import OperationalError, ProgrammingError
# Define a dictionary for the default skill proficiencies.
# In LOR, during character creation every skill is by default Trained.

# forms.py (app `characters`)
from django import forms
from .models import CharacterSubSkillProficiency, CharacterClass, CharacterClassProgress
from django.core.exceptions import ValidationError
from django import forms
from .models import CharacterClass,    Race,Subrace, ClassFeature, ClassSubclass,Background, FeatureOption, UniversalLevelFeature
class CharacterCreationForm(forms.ModelForm):
    # — pick race by its slug/code, not by PK
    race = forms.ModelChoiceField(
        queryset=Race.objects.all(),
        to_field_name='code',
        empty_label="— Select a Race —",
        widget=forms.Select(attrs={'id': 'id_race'}),
    )
    # — will be filtered in __init__
    subrace = forms.ModelChoiceField(
        queryset=Subrace.objects.none(),
        to_field_name='code',
        required=False,
        empty_label="— Select a Subrace —",
        widget=forms.Select(attrs={'id': 'id_subrace'}),
    )

    # backgrounds all come from the DB
    main_background = forms.ModelChoiceField(
        queryset=Background.objects.all(),
        to_field_name='code',
        empty_label="— Select Main Background —",
        widget=forms.Select(attrs={'id': 'id_main_background'}),
    )
    side_background_1 = forms.ModelChoiceField(
        queryset=Background.objects.all(),
        to_field_name='code',
        required=False,
        empty_label="— Select Side Background 1 —",
        widget=forms.Select(attrs={'id': 'id_side_background_1'}),
    )
    side_background_2 = forms.ModelChoiceField(
        queryset=Background.objects.all(),
        to_field_name='code',
        required=False,
        empty_label="— Select Side Background 2 —",
        widget=forms.Select(attrs={'id': 'id_side_background_2'}),
    )

    # for half-elf “fully” origin
    half_elf_origin = forms.ChoiceField(
        choices=[
            ('high', 'High Elf (+1 Int)'),
            ('wood', 'Wood Elf (+1 Wis)'),
            ('dark', 'Dark Elf (+1 Str)'),
        ],
        required=False,
        widget=forms.Select(attrs={'id': 'id_half_elf_origin'}),
    )

    # hidden JSON blob of computed skill proficiencies
    computed_skill_proficiencies = forms.CharField(
        widget=forms.HiddenInput(), required=False
    )

    class Meta:
        model = Character
        fields = [
            'name',
            'race', 'subrace', 'half_elf_origin',
            'main_background', 'side_background_1', 'side_background_2',
            'strength', 'dexterity', 'constitution',
            'intelligence', 'wisdom', 'charisma',
            'backstory',
            'computed_skill_proficiencies',
        ]
        widgets = {
            'backstory': forms.Textarea(attrs={'rows': 4, 'cols': 40}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # if the form is bound, filter subrace queryset to that race
        data = self.data or {}
        race_code = data.get('race') or getattr(self.instance.race, 'code', None)
        if race_code:
            self.fields['subrace'].queryset = Subrace.objects.filter(race__code=race_code)
        else:
            self.fields['subrace'].queryset = Subrace.objects.none()

    def clean(self):
        cleaned = super().clean()

        # enforce that if half_elf_origin is set, race/subrace must be the "fully half-elf" code
        origin = cleaned.get('half_elf_origin')
        race   = cleaned.get('race')
        if origin and race and race.code != 'half_elf_fully':
            raise ValidationError({
                'half_elf_origin': "You can only pick a Half-Elf origin when your race is the fully-customizable Half-Elf."
            })

        return cleaned





from django import forms
from django.contrib.contenttypes.models import ContentType
from .models import Skill, SubSkill
# at top of file
from django.db import OperationalError, ProgrammingError
from django import forms
from .models import Skill, SubSkill

class CombinedSkillWidget(forms.Select):
    def __init__(self, attrs=None):
        try:
            # list every Skill
            skill_qs = Skill.objects.order_by("name") \
                                     .values_list("pk", "name")
            skill_choices = [
                (f"skill-{pk}", name)
                for pk, name in skill_qs
            ]

            # list every SubSkill
            sub_qs = (
                SubSkill.objects
                        .select_related("skill")
                        .order_by("skill__name", "name")
                        .values_list("pk", "skill__name", "name")
            )
            sub_choices = [
                (f"subskill-{pk}", f"{skill_name} → {subskill_name}")
                for pk, skill_name, subskill_name in sub_qs
            ]

            choices = [("", "---------")] + skill_choices + sub_choices
        except (OperationalError, ProgrammingError):
            # pre-migrate state
            choices = [("", "---------")]

        super().__init__(attrs, choices=choices)





class CombinedSkillField(forms.Field):
    widget = CombinedSkillWidget

    def prepare_value(self, value):
        # if we're rendering a Skill/SubSkill instance as the initial value,
        # convert it into the "<prefix>-<pk>" that our widget expects.
        if isinstance(value, Skill):
            return f"skill-{value.pk}"
        if isinstance(value, SubSkill):
            return f"subskill-{value.pk}"
        return super().prepare_value(value)

    def to_python(self, value):
        if not value:
            return None
        prefix, pk = value.split("-", 1)
        pk = int(pk)
        if prefix == "skill":
            return Skill.objects.get(pk=pk)
        if prefix == "subskill":
            return SubSkill.objects.get(pk=pk)
        raise forms.ValidationError("Unknown selection")




class LevelUpForm(forms.Form):
    base_class    = forms.ModelChoiceField(
        queryset=CharacterClass.objects.none(),
        required=False,
        label="New Base Class"
    )
    advance_class = forms.ModelChoiceField(
        queryset=CharacterClass.objects.none(),
        required=False,
        label="Advance / Multiclass Into"
    )

    def __init__(self, *args, character=None, to_choose=None, uni=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.character = character

        # --- 1) Filter class‐selection fields ---
        all_classes = CharacterClass.objects.all()
        taken_pks   = [cp.character_class.pk for cp in character.class_progress.all()]

        if character.level == 0:
            # very first level
            self.fields['base_class'].queryset    = all_classes
            self.fields['advance_class'].widget   = forms.HiddenInput()
        else:
            # leveling existing class
            self.fields['base_class'].widget      = forms.HiddenInput()
            if character.level < 5:
                # levels 1–4: can only pick an existing class
                self.fields['advance_class'].queryset = all_classes.filter(pk__in=taken_pks)
            else:
                # level ≥5: allow any class (= multiclass)
                self.fields['advance_class'].queryset = all_classes

        # --- 2) Prepare feature list safely ---
        to_choose = to_choose or []
        uni       = uni or UniversalLevelFeature(level=character.level)

        # --- 3) Dynamically add feature fields ---
        for feat in to_choose:
            # universal flags
            if feat == "general_feat":
                self.fields['general_feat'] = forms.BooleanField(
                    label="Select a General Feat", required=False
                )
                continue

            if feat == "asi":
                self.fields['asi'] = forms.BooleanField(
                    label="Ability Score Increase", required=False
                )
                continue

            # subclass_choice: pick a specialization
            if isinstance(feat, ClassFeature) and feat.scope == "subclass_choice":
                group   = feat.subclass_group
                choices = [(sc.pk, sc.name) for sc in group.subclasses.all()]
                self.fields[f"feat_{feat.pk}_subclass"] = forms.ChoiceField(
                    label=f"Choose your {group.name}",
                    choices=choices,
                    required=True
                )
                continue

            # features with options
            if isinstance(feat, ClassFeature) and feat.has_options:
                opts = [(o.pk, o.label) for o in feat.options.all()]
                self.fields[f"feat_{feat.pk}_option"] = forms.ChoiceField(
                    label=feat.name,
                    choices=opts,
                    required=True
                )
                continue

            # plain feature: a simple tick
            if isinstance(feat, ClassFeature):
                self.fields[f"feat_{feat.pk}"] = forms.BooleanField(
                    label=feat.name,
                    required=False
                )



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


class BackgroundForm(forms.ModelForm):
    primary_selection_mode = forms.ChoiceField(
        choices=Background.SELECTION_MODES,
        label="Primary Skill → grant mode"
    )
    secondary_selection_mode = forms.ChoiceField(
        choices=Background.SELECTION_MODES,
        label="Secondary Skill → grant mode",
        required=False
    )
    primary_selection   = CombinedSkillField(label="Primary Skill or SubSkill")
    secondary_selection = CombinedSkillField(label="Secondary Skill or SubSkill")

    class Meta:
        model  = Background
        fields = [
          "code","name","description",
          "primary_ability","primary_bonus","primary_selection_mode","primary_selection",
          "secondary_ability","secondary_bonus","secondary_selection_mode","secondary_selection",
        ]


    def save(self, commit=True):
        inst = super().save(commit=False)
        inst.primary_selection_mode   = self.cleaned_data["primary_selection_mode"]
        inst.secondary_selection_mode = self.cleaned_data["secondary_selection_mode"]

        sel = self.cleaned_data["primary_selection"]
        inst.primary_skill_type = ContentType.objects.get_for_model(sel)
        inst.primary_skill_id   = sel.pk

        sel2 = self.cleaned_data["secondary_selection"]
        inst.secondary_skill_type = ContentType.objects.get_for_model(sel2)
        inst.secondary_skill_id   = sel2.pk

        if commit:
            inst.save()
        return inst
