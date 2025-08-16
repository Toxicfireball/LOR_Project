# forms.py
import json
from django import forms
from .models import Character
from django.db import OperationalError, ProgrammingError
# Define a dictionary for the default skill proficiencies.
# In LOR, during character creation every skill is by default Trained.
from django.db.models import Q
# forms.py (app `characters`)
from django import forms
from django_select2.forms import HeavySelect2Widget
from .models import CharacterSubSkillProficiency, CharacterClass, CharacterClassProgress
from django.core.exceptions import ValidationError
from django import forms
from .models import CharacterClass, MartialMastery,ClassFeat,   Race,Subrace, ClassFeature, ClassSubclass,Background, FeatureOption, UniversalLevelFeature
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

class PreviewForm(forms.Form):
    base_class = forms.ModelChoiceField(
        queryset=CharacterClass.objects.order_by("name"),
        label="Preview a different class",
        widget=forms.Select(),  # we'll style in __init__
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["base_class"].widget.attrs.update({
            "class":    "form-select",
            "id":       "preview_class_select",
            "onchange": "this.form.submit()",   # ← auto-submit when user picks
        })



# forms.py
import re
from django import forms
from django.db.models import Q
from django_select2.forms import HeavySelect2Widget

from .models import (
    CharacterClass, ClassFeat, ClassFeature, MartialMastery
)

class LevelUpForm(forms.Form):
    # always declare fields so they have .queryset and can be filtered in the view
    base_class      = forms.ModelChoiceField(
        queryset=CharacterClass.objects.none(),
        label="Choose class to gain this level",
        widget=forms.Select(attrs={"class": "form-select", "onchange": "this.form.submit()"})
    )
    general_feat    = forms.ModelChoiceField(queryset=ClassFeat.objects.none(),
                                            required=False, label="General Feat")
    class_feat_pick = forms.ModelChoiceField(queryset=ClassFeat.objects.none(),
                                            required=False, label="Class Feat")
    martial_mastery = forms.ModelChoiceField(queryset=MartialMastery.objects.none(),
                                            required=False, label="Martial Mastery")
    asi             = forms.BooleanField(required=False, label="Ability Score Increase")

    def __init__(self, *args, character, to_choose, uni, preview_cls, grants_class_feat=False, **kwargs):

        super().__init__(*args, **kwargs)

        # base_class queryset (unchanged)
        if character.level == 0:
            qs = CharacterClass.objects.order_by("name")
        elif character.level < 5:
            existing = character.class_progress.values_list("character_class_id", flat=True)
            qs = CharacterClass.objects.filter(pk__in=existing).order_by("name")
        else:
            qs = CharacterClass.objects.order_by("name")
        self.fields["base_class"].queryset = qs

        # auto_feats
        self.auto_feats = [f for f in to_choose if isinstance(f, ClassFeature) and f.scope in ("class_feat","subclass_feat")]

        next_level = character.level + 1

        # race/subrace token match used for both General & Class feats
        race_names = []
        if getattr(character, "race", None) and getattr(character.race, "name", None):
            race_names.append(character.race.name)
        if getattr(character, "subrace", None) and getattr(character.subrace, "name", None):
            race_names.append(character.subrace.name)
        race_q = Q(race__exact="") | Q(race__isnull=True)
        if race_names:
            token_res = [rf'(^|[,;/\s]){re.escape(n)}([,;/\s]|$)' for n in race_names]
            race_q |= Q(race__iregex="(" + ")|(".join(token_res) + ")")

        # General Feat (only when universal grants)
        if uni and uni.grants_general_feat:
            lvl = uni.level
            q = (ClassFeat.objects
                 .filter(feat_type__iexact="General")
                 .filter(Q(level_prerequisite__exact="") |
                         Q(level_prerequisite__iregex=rf'(^|[,;/\s]){lvl}([,;/\s]|$)'))
                 .filter(race_q)
                 .exclude(pk__in=character.feats.values_list("feat__pk", flat=True))
                 .order_by("name"))
            self.fields["general_feat"].queryset = q
            self.fields["general_feat"].required = True
            self.fields["general_feat"].widget = forms.Select(attrs={"class": "d-none"})
        else:
            self.fields.pop("general_feat", None)

        # Subclass choice radios (unchanged)
        for feat in to_choose:
            if isinstance(feat, ClassFeature) and feat.scope == "subclass_choice":
                name = f"feat_{feat.pk}_subclass"
                choices = [(s.pk, s.name) for s in feat.subclass_group.subclasses.all()]
                self.fields[name] = forms.ChoiceField(
                    label=f"Choose {feat.subclass_group.name}",
                    choices=choices,
                    required=True,
                    widget=forms.RadioSelect
                )

        # Option pickers (unchanged)
        for feat in to_choose:
            if isinstance(feat, ClassFeature) and feat.has_options:
                name = f"feat_{feat.pk}_option"
                opts = [(o.pk, o.label) for o in feat.options.all()]
                self.fields[name] = forms.ChoiceField(label=feat.name, choices=opts, required=False)

        # === Class Feat availability tied to the PREVIEWED class + level ===
        next_level = character.level + 1
        if grants_class_feat and preview_cls:
            cls_re = rf'(^|[,;/\s]){re.escape(preview_cls.name)}(\s*\([^)]+\))?([,;/\s]|$)'

            avail = (ClassFeat.objects
                    .filter(feat_type__iexact="Class")
                    .filter(level_prerequisite__iregex=rf'(^|[,;/\s]){next_level}([,;/\s]|$)')
                    .filter(class_name__iregex=cls_re)
                    .filter(race_q)
                    .order_by("name"))

            if avail.exists():
                self.fields["class_feat_pick"].queryset = avail
                # hide the select; the template renders a table
                self.fields["class_feat_pick"].widget = forms.Select(attrs={"class": "d-none"})
            else:
                self.fields.pop("class_feat_pick", None)
        else:
            self.fields.pop("class_feat_pick", None)

        # ASI
        if not (uni and uni.grants_asi):
            self.fields.pop("asi", None)

        # Martial Mastery (unchanged, but distinct())
        mm = MartialMastery.objects.filter(level_required__lte=next_level)
        if preview_cls:
            mm = mm.filter(Q(all_classes=True) | Q(classes=preview_cls))
        else:
            mm = mm.filter(all_classes=True)
        mm = mm.distinct()
        if mm.exists():
            self.fields["martial_mastery"].queryset = mm
        else:
            self.fields.pop("martial_mastery", None)

        # light bootstrap classes
        for f in self.fields.values():
            w = f.widget
            if isinstance(w, forms.Select):
                w.attrs["class"] = (w.attrs.get("class", "") + " form-select").strip()
            elif isinstance(w, forms.RadioSelect):
                w.attrs["class"] = (w.attrs.get("class", "") + " form-check-input").strip()
            elif isinstance(w, forms.CheckboxInput):
                w.attrs["class"] = (w.attrs.get("class", "") + " form-check-input").strip()
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
