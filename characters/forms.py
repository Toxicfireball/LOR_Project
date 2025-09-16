# forms.py
import json
from django.db.models import Q, Count
from django.contrib.contenttypes.models import ContentType

from django import forms
from .models import Character
from django.db import OperationalError, ProgrammingError
# Define a dictionary for the default skill proficiencies.
# In LOR, during character creation every skill is by default Trained.
from django.db.models import Q
from django_summernote.widgets import SummernoteWidget
# forms.py (app `characters`)
from django import forms
from django_select2.forms import HeavySelect2Widget
from .models import CharacterSubSkillProficiency, CharacterClass, CharacterClassProgress
from django.core.exceptions import ValidationError
from django import forms
from .models import ClassSkillFeatGrant, CharacterClass, MartialMastery, ClassFeat, Race, Subrace, ClassFeature, ClassSubclass, Background, FeatureOption, UniversalLevelFeature, RacialFeature
class CharacterCreationForm(forms.ModelForm):
    # — pick race by its slug/code, not by PK
    race = forms.ModelChoiceField(
        queryset=Race.objects.all(),
        empty_label="— Select a Race —",
        widget=forms.Select(attrs={'id': 'id_race'}),
    )

    subrace = forms.ModelChoiceField(
        queryset=Subrace.objects.none(),
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
            "name",
            "race",
            "subrace",
            "main_background",
            "side_background_1",
            "side_background_2",
            "backstory",
            "strength", "dexterity", "constitution",
            "intelligence", "wisdom", "charisma",
        ]
        # NOTE: extra non-model fields like half_elf_origin and
        # computed_skill_proficiencies are fine; they just aren't saved.

    # Make sure we store codes (strings) in the Character model:
    def clean_main_background(self):
        obj = self.cleaned_data.get("main_background")
        return getattr(obj, "code", "") if obj else ""

    def clean_side_background_1(self):
        obj = self.cleaned_data.get("side_background_1")
        return getattr(obj, "code", "") if obj else ""

    def clean_side_background_2(self):
        obj = self.cleaned_data.get("side_background_2")
        return getattr(obj, "code", "") if obj else ""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        data = self.data or {}
        race_pk = data.get('race') or (getattr(self.instance, 'race_id', None))
        if race_pk:
            self.fields['subrace'].queryset = Subrace.objects.filter(race_id=race_pk)
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

ABILITY_FIELD_CHOICES = [
    ("strength", "Strength"),
    ("dexterity", "Dexterity"),
    ("constitution", "Constitution"),
    ("intelligence", "Intelligence"),
    ("wisdom", "Wisdom"),
    ("charisma", "Charisma"),
]


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
    skill_feat = forms.ModelChoiceField(
        queryset=ClassFeat.objects.none(),
        required=False,
        label="Skill Feat"
    )
# --- FIRST LEVEL IN CLASS → starting skills picker -------------------------
# helper: build allowable (leaf) skill choices the character doesn't already have
    def _starting_skill_choices_for_char(char):
        ct_skill = ContentType.objects.get_for_model(Skill)
        ct_sub   = ContentType.objects.get_for_model(SubSkill)

        # things the character already has a recorded proficiency for
        existing = set(
            char.skill_proficiencies.values_list("selected_skill_type_id", "selected_skill_id")
        )

        # leaf top-level skills (non-advanced AND no subskills)
        leaf_skills = (
            Skill.objects.filter(is_advanced=False)
                         .annotate(n=Count("subskills"))
                         .filter(n=0)
                         .order_by("name")
        )

        # sub-skills under non-advanced parents
        leaf_subs = (
            SubSkill.objects.filter(skill__is_advanced=False)
                            .select_related("skill")
                            .order_by("skill__name", "name")
        )

        choices = []
        for sk in leaf_skills:
            if (ct_skill.id, sk.id) not in existing:
                choices.append((f"sk_{sk.id}", sk.name))

        for ss in leaf_subs:
            if (ct_sub.id, ss.id) not in existing:
                choices.append((f"sub_{ss.id}", f"{ss.skill.name} – {ss.name}"))

        return choices
    def __init__(self, *args, character, to_choose, uni, preview_cls, grants_class_feat=False, **kwargs):
        
        super().__init__(*args, **kwargs)
        self.character = character
        self.uni = uni
        # inside LevelUpForm.__init__ just after super().__init__
        next_level = character.level + 1

        race_names = []
        if getattr(character, "race", None) and getattr(character.race, "name", None):
            race_names.append(character.race.name)
        if getattr(character, "subrace", None) and getattr(character.subrace, "name", None):
            race_names.append(character.subrace.name)
        race_q = Q(race__exact="") | Q(race__isnull=True)
        if race_names:
            token_res = [rf'(^|[,;/\s]){re.escape(n)}([,;/\s]|$)' for n in race_names]
            race_q |= Q(race__iregex="(" + ")|(".join(token_res) + ")")

        # Skill Feat (if this class & level grant one)
        if preview_cls and ClassSkillFeatGrant.objects.filter(
            character_class=preview_cls, at_level=next_level
        ).exists():
            # inside LevelUpForm.__init__
            q = (ClassFeat.objects
                .filter(feat_type__istartswith="Skill")
                .filter(
                    Q(level_prerequisite__isnull=True) |      # ← add this
                    Q(level_prerequisite__exact="") |
                    Q(level_prerequisite__iregex=rf'(^|[,;/\s]){next_level}([,;/\s]|$)')
                )
                .filter(race_q)
                .exclude(pk__in=character.feats.values_list("feat__pk", flat=True))
                .order_by("name"))

            if q.exists():
                self.fields["skill_feat"].queryset = q
                self.fields["skill_feat"].required = True
                self.fields["skill_feat"].widget = forms.Select(attrs={"class": "d-none"})
            else:
                self.fields.pop("skill_feat", None)
        else:
            self.fields.pop("skill_feat", None)

        if character.level == 0:
            qs = CharacterClass.objects.order_by("name")
        elif character.level < 5:
            existing = character.class_progress.values_list("character_class_id", flat=True)
            qs = CharacterClass.objects.filter(pk__in=existing).order_by("name")
        else:
            qs = CharacterClass.objects.order_by("name")
        self.fields["base_class"].queryset = qs
        if preview_cls:
            cp = character.class_progress.filter(character_class=preview_cls).first()
            cls_level_after = (cp.levels if cp else 0) + 1
        else:
            cls_level_after = 1

        if cls_level_after == 1:
            _choices = LevelUpForm._starting_skill_choices_for_char(character)
            if _choices:
                self.fields["starting_skill_picks"] = forms.MultipleChoiceField(
                    choices=_choices,
                    required=False,
                    widget=forms.CheckboxSelectMultiple,
                    label="Starting Skills (non-advanced only)",
                    help_text="Pick from leaf skills: either a skill with no sub-skills, or a specific sub-skill."
                )
        # auto_feats
        self.auto_feats = [f for f in to_choose if isinstance(f, ClassFeature) and f.scope in ("class_feat","subclass_feat")]

        next_level = character.level + 1
        # ----- Ability Score Increase controls -----
        # --- Ability Score Increase controls (hidden; UI handled in template/JS) ---
        # ----- Ability Score Increase controls (hidden; UI handled in template/JS) -----
        if uni and getattr(uni, "grants_asi", False):
            self.fields["asi_mode"] = forms.CharField(required=False, widget=forms.HiddenInput())
            self.fields["asi_a"]    = forms.ChoiceField(choices=ABILITY_FIELD_CHOICES, required=False, widget=forms.HiddenInput())
            self.fields["asi_b"]    = forms.ChoiceField(choices=ABILITY_FIELD_CHOICES, required=False, widget=forms.HiddenInput())
        else:
            for f in ("asi_mode", "asi_a", "asi_b"):
                self.fields.pop(f, None)


        # race/subrace token match used for both General & Class feats



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
        # Subclass choice radios — FIX: use subclass_group and guard when missing
        for feat in to_choose:
            if isinstance(feat, ClassFeature) and feat.scope == "subclass_choice":
                name = f"feat_{feat.pk}_subclass"

                # prefer subclass_group; fall back to .group only if you really have it somewhere
                grp = getattr(feat, "subclass_group", None) or getattr(feat, "group", None)
                subs = grp.subclasses.all() if grp else []

                self.fields[name] = forms.ChoiceField(
                    label=f"Choose {getattr(grp, 'name', 'Subclass')}",
                    choices=[(s.pk, s.name) for s in subs],
                    required=bool(grp and subs),            # require only if there’s something to pick
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
    def clean(self):
        cleaned = super().clean()

        # If this level has no ASI, nothing to validate.
        if "asi_mode" not in self.fields:
            return cleaned

        a    = (cleaned.get("asi_a") or "").strip()
        b    = (cleaned.get("asi_b") or "").strip()
        mode = (cleaned.get("asi_mode") or "").strip()

        # Infer mode if JS didn't fill it
        if not mode:
            if a and b:
                mode = "2" if a == b else "1+1"
            elif a or b:
                mode = "1"
            else:
                raise forms.ValidationError("Assign your ability increase(s) in the table.")

        # Normalize/validate combinations
        if mode == "1+1":
            if not a or not b or a == b:
                raise forms.ValidationError("Pick two different abilities for +1/+1.")
        elif mode == "2":
            # allow a==b (both provided) OR just 'a' set; normalize to both set equal
            if a and b and a != b:
                raise forms.ValidationError("For +2, choose the same ability twice.")
            if not a and not b:
                raise forms.ValidationError("Pick an ability to receive +2.")
            if not b:
                cleaned["asi_b"] = a
                b = a
        elif mode == "1":
            if not (a or b):
                raise forms.ValidationError("Pick one ability to receive +1.")
            if not a and b:
                cleaned["asi_a"], cleaned["asi_b"] = b, ""
                a, b = b, ""
        else:
            raise forms.ValidationError("Choose a valid ability increase configuration.")

        # 20+ restriction: if any affected ability is 20+, only single +1 allowed
        chosen = {x for x in (a, b) if x}
        if any(getattr(self.character, fld) >= 20 for fld in chosen):
            if mode != "1":
                raise forms.ValidationError(
                    "Because one of the selected abilities is 20 or higher, you may only apply +1 to a single ability."
                )

        cleaned["asi_mode"] = mode
        return cleaned


class CharacterDetailsForm(forms.ModelForm):
    class Meta:
        model = Character
        fields = [
            "backstory",
            "worshipped_gods",
            "believers_and_ideals",
            "iconic_strengths",
            "iconic_flaws",
            "bonds_relationships",
            "ties_connections",
            "outlook",
        ]
        widgets = {f: SummernoteWidget() for f in fields}
        labels = {
            "backstory":             "Backstory",
            "worshipped_gods":       "Worshipped Gods",
            "believers_and_ideals":  "Believers and ideals",
            "iconic_strengths":      "Iconic (Strength)",
            "iconic_flaws":          "Iconic (Flaws)",
            "bonds_relationships":   "Bonds/Relationship",
            "ties_connections":      "Ties and Connections",
            "outlook":               "Outlook",
        }

class CharacterClassForm(forms.ModelForm):
    class Meta:
        model  = CharacterClass
        fields = "__all__"  # includes key_abilities



    def clean(self):
        cleaned = super().clean()
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
# forms.py
from django import forms
from .models import ClassFeature, ClassFeat, RacialFeature  # adjust imports as in your project

class ManualGrantForm(forms.Form):
    KIND_CHOICES = [
        ("feat", "Feat"),
        ("class_feature", "Class Feature"),
        ("racial_feature", "Racial Feature"),
    ]
    kind = forms.ChoiceField(choices=KIND_CHOICES)
    feat = forms.ModelChoiceField(queryset=ClassFeat.objects.all(), required=False)
    class_feature = forms.ModelChoiceField(queryset=ClassFeature.objects.all(), required=False)
    racial_feature = forms.ModelChoiceField(queryset=RacialFeature.objects.all(), required=False)
    reason = forms.CharField(widget=forms.Textarea, required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make sure the dropdowns show human names, not raw PKs
        if "feat" in self.fields:
            self.fields["feat"].label_from_instance = lambda o: o.name
        if "class_feature" in self.fields:
            self.fields["class_feature"].label_from_instance = lambda o: (
                f"{o.name}  •  {o.character_class.name}" if getattr(o, "character_class", None) else o.name
            )
        if "racial_feature" in self.fields:
            self.fields["racial_feature"].label_from_instance = lambda o: getattr(o, "name", f"Racial Feature #{o.pk}")


# forms.py
from django import forms
from .models import CharacterFeat, CharacterFeature

class _FeatM2M(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.feat.name} (L{obj.level})"

class _FeatureM2M(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        base = obj.feature.name if obj.feature else "(custom)"
        if obj.option:
            base = obj.option.label
        if obj.subclass:
            base = f"{base} — {obj.subclass.name}"
        return f"{base} (L{obj.level})"

class RemoveItemsForm(forms.Form):
    remove_feats = _FeatM2M(queryset=CharacterFeat.objects.none(), required=False, label="Feats")
    remove_features = _FeatureM2M(queryset=CharacterFeature.objects.none(), required=False, label="Class/Racial Features")
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows":3}), required=True, label="Reason")

    def __init__(self, *args, character, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["remove_feats"].queryset = character.feats.select_related("feat").all()
        self.fields["remove_features"].queryset = character.features.select_related("feature","option","subclass").all()

    def clean(self):
        data = super().clean()
        if not data.get("remove_feats") and not data.get("remove_features"):
            raise forms.ValidationError("Pick at least one item to remove.")
        if not (data.get("reason") or "").strip():
            raise forms.ValidationError("A reason is required.")
        return data
