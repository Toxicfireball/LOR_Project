# home/admin.py

from django.contrib import admin
from django import forms

from characters.models import (
    CharacterClass,
    ClassTag,
    ClassSubclass,
    ClassProficiencyProgress,
    ClassLevelFeature,
    ProficiencyTier,
    ClassLevel,
    ClassFeature,
    FeatureOption,
    SubclassGroup,
    MartialMastery,
    SpellSlotRow , 
    ResourceType, ClassResource, CharacterResource, Spell, SubclassMasteryUnlock, 
)
from django.contrib.contenttypes.models import ContentType
from django.urls import resolve
from django.contrib.admin.widgets import FilteredSelectMultiple
from characters.widgets import FormulaBuilderWidget, CharacterClassSelect
from characters.models import EquipmentSlot, WearableSlot ,SpecialItem, SpecialItemTraitValue,Language,Armor, ArmorTrait, CharacterSkillProficiency, LoremasterArticle, LoremasterImage, RulebookPage, Rulebook, RacialFeature, Rulebook, RulebookPage,AbilityScore,Background, ResourceType,Weapon, SubSkill, UniversalLevelFeature, Skill, WeaponTraitValue,WeaponTrait, ClassResource, CharacterResource, SubclassGroup, SubclassTierLevel
from characters.forms import BackgroundForm,CharacterClassForm, CombinedSkillField
from django.utils.html import format_html
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError
from characters.models import PROFICIENCY_TYPES, Skill
from django.contrib import admin
import json
# admin.py
from django.contrib.admin import SimpleListFilter
from django.db.models import Q
class SubclassTierLevelInline(admin.TabularInline):
    model = SubclassTierLevel
    extra = 1
    fields = ("tier", "unlock_level")
    verbose_name        = "Tier → Level Mapping"
    verbose_name_plural = "Tier → Level Mappings"
    help_text           = (
        "For this SubclassGroup, specify which tier index is unlocked at which class level.\n"
        "e.g. Tier=1 unlock_level=1,  Tier=2 unlock_level=3, Tier=3 unlock_level=5, etc."
    )
class FeatureOptionInline(admin.TabularInline):
    model   = FeatureOption
    fk_name = "feature"
    extra   = 1
    verbose_name = "Feature option"
    verbose_name_plural = "Feature options"

# ─── Inline for Pages ─────────────────────────────────────────────────────────
from django_summernote.widgets import SummernoteWidget
from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin
class SpecialItemForm(forms.ModelForm):
    class Meta:
        model  = SpecialItem
        fields = "__all__"   # or list exactly the fields you show in your fieldsets




@admin.register(LoremasterImage)
class LoremasterImageAdmin(admin.ModelAdmin):
    list_display = ("__str__",)
    search_fields = ("caption",)

@admin.register(LoremasterArticle)
class LoremasterArticleAdmin(SummernoteModelAdmin):
    list_display    = ("title", "published", "created_at")
    list_filter     = ("published", "created_at")
    search_fields   = ("title", "excerpt", "content")
    prepopulated_fields = {"slug": ("title",)}
    summernote_fields = ("content",)
    filter_horizontal  = ("gallery",)

@admin.register(Rulebook)
class RulebookAdmin(admin.ModelAdmin):
    list_display  = ("name",)
    search_fields = ("name",)


@admin.register(RulebookPage)
class RulebookPageAdmin(SummernoteModelAdmin):
    list_display        = ("rulebook", "order", "title")
    list_filter         = ("rulebook",)
    ordering            = ("rulebook__name", "order")
    search_fields       = ("title", "rulebook__name")
    autocomplete_fields = ("rulebook",)
    fields = (
        "rulebook",
        "order",
        "title",
        "content",  # this is already a SummernoteTextField in your model
        "image",
    )
    summernote_fields = ("content",)

class ModularLinearFeatureFormSet(BaseInlineFormSet):
    """
    For any SubclassGroup with system_type="modular_linear", enforce that:
    - If you assign a tier N feature at level L, a tier (N-1) feature in that same group
      must already have been assigned at some lower level < L.
    """

    def clean(self):
        super().clean()

        this_level = self.instance.level
        cls = self.instance.character_class

        picks = []
        dupes = []
        seen = set()

        for form in self.forms:
            if self.can_delete and form.cleaned_data.get("DELETE"):
                continue
            feature = form.cleaned_data.get("feature")
            if not feature:
                continue

            grp = feature.subclass_group
            if not grp or grp.system_type != SubclassGroup.SYSTEM_MODULAR_LINEAR:
                # If it isn’t a modular_linear subclass_feat, skip it.
                continue

            # Extract tier from the code suffix
            # (Assumes code always ends in "_<integer>".)
            try:
                tier = int(feature.code.rsplit("_", 1)[1])
            except (ValueError, IndexError):
                raise ValidationError(
                    f"Feature code {feature.code!r} does not end in _<tier>."
                    " Modular‐linear subclass_feats must follow code='something_<tier>'."
                )

            # Check for duplicates at the same class level
            if feature in seen:
                dupes.append(feature)
            seen.add(feature)
            picks.append((feature, grp, tier))

        if dupes:
            names = ", ".join(str(f) for f in dupes)
            raise ValidationError(f"Duplicate feature selected more than once at this level: {names}")

        # Now enforce the “previous tier exists at lower level” rule:
        from django.db.models import Q

        for feature, grp, tier in picks:
            if tier == 1:
                # Tier 1 never requires a prior tier.
                continue

            needed_suffix = f"_{tier - 1}"
            exists_lower_tier = ClassLevelFeature.objects.filter(
                class_level__character_class=cls,
                class_level__level__lt=this_level,
                feature__subclass_group=grp,
                feature__code__endswith=needed_suffix
            ).exists()

            if not exists_lower_tier:
                raise ValidationError(
                    f"You tried to assign Tier {tier} ({feature.code!r}) at level {this_level}, "
                    f"but no Tier {tier - 1} feature for {grp.name!r} was assigned at any lower level.")
            


      

class CombinedSkillAdminMixin:
    def get_form(self, request, obj=None, **kwargs):
        Form = super().get_form(request,obj,**kwargs)
        class F(Form):
            def __init__(self,*args,**kws):
                super().__init__(*args,**kws)
                for fld in ("primary_skill","secondary_skill","selected_skill"):
                    if fld in self.fields:
                        self.fields[fld] = CombinedSkillField(label=self.fields[fld].label,
                                                               required=self.fields[fld].required)
        return F
  
class SpellInline(admin.StackedInline):
    model       = Spell
    fk_name     = "class_feature"
    extra       = 0
    max_num     = 1
    can_delete  = False
    classes     = ["spell-inline"]  
    # hide the four fields you don't want
    exclude     = ("last_synced", "mastery_req", "sub_origin", "origin")
    verbose_name        = "Inherent Spell Data"
    verbose_name_plural = "Inherent Spell Data"


class SubSkillInline(admin.TabularInline):
    model = SubSkill
    extra = 1
    fields = ("name",)




@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display  = ("name", "ability", "secondary_ability", "is_advanced")
    list_filter   = ("ability", "secondary_ability", "is_advanced")
    search_fields = ("name",)
    fields        = ("name", "ability", "secondary_ability", "description", "is_advanced")



@admin.register(SubSkill)
class SubSkillAdmin(admin.ModelAdmin):
    list_display       = ("name", "skill", "description")
    search_fields      = ("name", "skill__name")
    autocomplete_fields= ("skill",)
    fields             = ("skill", "name", "description")



class SubclassGroupForm(forms.ModelForm):
    """
    Form for editing SubclassGroup in the admin.
    """
    subclasses = forms.ModelMultipleChoiceField(
        queryset=ClassSubclass.objects.none(),
        required=False,
        widget=admin.widgets.FilteredSelectMultiple("subclasses", is_stacked=True),
        help_text="↪ Move right to add existing ClassSubclass rows to this group."
    )

    class Meta:
        model = SubclassGroup
        fields = ("character_class", "name", "code", "system_type")
        labels = {
            "character_class": "Parent Class",
            "name":             "Umbrella Name",
            "code":             "Identifier Code",
            "system_type":      "Progression System",
        }
        help_texts = {
            "character_class": "Choose the CharacterClass this group belongs to.",
            "name":             "Display name for this subclass umbrella (e.g. “Moon Circle”).",
            "code":             "Shorthand code for referencing this group in features or JSON.",
            "system_type":      (
                "How do these subclasses progress?\n"
                "• linear: fixed-level features\n"
                "• modular_linear: pick one of N at each level\n"
                "• modular_mastery: modules → mastery tiers"
            ),
        }

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        # limit subclasses to those of the chosen class
        cls = (
            self.instance.character_class
            if self.instance.pk
            else CharacterClass.objects.filter(
                pk=self.data.get("character_class")
                or self.initial.get("character_class")
            ).first()
        )
        if cls:
            qs = ClassSubclass.objects.filter(base_class=cls)
            self.fields["subclasses"].queryset = qs

            # magic help_text for modular_linear groups:
            if cls.subclass_groups.filter(system_type="modular_linear").exists():
                n = qs.count()
                self.fields["subclasses"].help_text = (
                    f"Select exactly {n} subclasses — these will become the {n} "
                    f"options that players choose between at each pick-level."
                )

            # prefill if editing
            if self.instance.pk:
                base_cls = self.instance.character_class
                self.fields["subclasses"].queryset = ClassSubclass.objects.filter(base_class=base_cls)
                self.fields["subclasses"].initial = self.instance.subclasses.all()
            else:
                self.fields["subclasses"].queryset = ClassSubclass.objects.none()

        # apply sizing to the widget so it’s not postage-stamp
        w = self.fields["subclasses"].widget
        w.attrs["style"] = "width:30em; height:15em;"
        w.attrs["size"] = 10
    def save(self, commit=True):
        # First, save the SubclassGroup itself:
        group = super().save(commit=commit)
        # Then link any selected ClassSubclass rows
        # (so “move right” in that M2M widget) → set group= this instance on them:
        chosen = self.cleaned_data.get("subclasses") or []
        for sub in chosen:
            sub.group = group
            sub.save()
        return group



# characters/admin.py
class SubclassMasteryUnlockInline(admin.TabularInline):
    model = SubclassMasteryUnlock
    extra = 1
    fields = ("rank", "unlock_level", "modules_required")
    verbose_name = "Mastery Rank Gate"
    verbose_name_plural = "Mastery Rank Gates"

@admin.register(SubclassGroup)
class SubclassGroupAdmin(admin.ModelAdmin):
    list_display = ("character_class", "name", "code", "system_type")
    list_filter  = ("character_class", "system_type")
    inlines      = (SubclassTierLevelInline, SubclassMasteryUnlockInline)  # ← add here
    fields       = ("character_class", "name", "code", "system_type", "modules_per_mastery", "modular_rules")

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        grp = form.instance
        chosen = form.cleaned_data.get("subclasses", [])
        chosen_ids = [s.pk for s in chosen]
        # Link selected subclasses to this group
        ClassSubclass.objects.filter(pk__in=chosen_ids).update(group=grp)
        # Unlink any other that used to be in this group
        ClassSubclass.objects.filter(group=grp).exclude(pk__in=chosen_ids).update(group=None)
class ClassProficiencyProgressInline(admin.TabularInline):
    model  = ClassProficiencyProgress
    extra  = 1
    fields = ('proficiency_type', 'at_level', 'tier')



class MartialMasteryForm(forms.ModelForm):
    # ==== existing ====
    allowed_weapons = forms.ModelMultipleChoiceField(
        label="Allowed weapons",
        queryset=Weapon.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Shown only if ‘Weapon restriction’ is enabled."
    )

    # ---- NEW: Damage types multi-pick ----
    allowed_damage_types = forms.MultipleChoiceField(
        label="Allowed damage types",
        choices=Weapon.DAMAGE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Shown only if ‘Damage restriction’ is enabled."
    )

    # ---- UX improvement: explicit ‘Class restriction’ switch ----
    restrict_to_classes = forms.BooleanField(
        required=False,
        label="Class restriction",
        help_text="When checked, limit to specific classes below."
    )
    allowed_traits = forms.ModelMultipleChoiceField(
        label="Allowed traits",
        queryset=WeaponTrait.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Shown only if ‘Trait restriction’ is enabled."
    )
    class Meta:
        model = MartialMastery
        fields = "__all__"


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # keep your existing stuff (hiding all_classes, initial for restrict_to_classes, etc.)
        if "all_classes" in self.fields:
            self.fields["all_classes"].widget = forms.HiddenInput()
        inst = getattr(self, "instance", None)
        if inst and inst.pk:
            self.fields["restrict_to_classes"].initial = not bool(inst.all_classes)



    def clean(self):
        cleaned = super().clean()

        # Enforce picks if toggles are on
        if cleaned.get("restrict_to_weapons") and not cleaned.get("allowed_weapons"):
            self.add_error("allowed_weapons", "Select at least one weapon or uncheck ‘Weapon restriction’.")
        if cleaned.get("restrict_to_damage") and not cleaned.get("allowed_damage_types"):
            self.add_error("allowed_damage_types", "Select at least one damage type or uncheck ‘Damage restriction’.")
        # class restriction: if on, require classes
        if cleaned.get("restrict_to_classes") and not cleaned.get("classes"):
            self.add_error("classes", "Select at least one class or uncheck ‘Class restriction’.")
        return cleaned

    def save(self, commit=True):
        inst = super().save(commit=False)
        # Map synthetic toggle → stored field
        restrict = bool(self.cleaned_data.get("restrict_to_classes"))
        inst.all_classes = not restrict
        if commit:
            inst.save()
            self.save_m2m()
        return inst


@admin.register(MartialMastery)
class MartialMasteryAdmin(SummernoteModelAdmin):
    form = MartialMasteryForm
    summernote_fields = ('description',)

    filter_horizontal = ('classes',)

    list_display = (
        'name', 'level_required', 'points_cost', 'action_cost',
        'is_rare',
        'all_classes', 'restrict_to_weapons', 'restrict_to_damage', 'restrict_to_traits',
        'restriction_summary'
    )
    list_filter  = (
        'is_rare',
        'all_classes', 'restrict_to_weapons', 'restrict_to_damage', 'restrict_to_traits'
    )

    fieldsets = [
        (None, {
            "fields": (
                "name", "level_required", "points_cost", "action_cost",
                "description",
                "is_rare",
                # class restriction UX: synthetic toggle + M2M, real field hidden in the form
                "restrict_to_classes", "classes",
            ),
        }),
    
        ("Restrictions (optional)", {
            "fields": (
                "restrict_to_weapons", "allowed_weapons",
                "restrict_to_damage",  "allowed_damage_types",
                "restrict_to_traits",  "allowed_traits",
                "all_classes",  # hidden by form; kept here so admin saves it
            ),
        }),
    ]

    def restriction_summary(self, obj):
        parts = []
        if obj.restrict_to_weapons:
            parts.append(f"Weapons({obj.allowed_weapons.count()})")
        if getattr(obj, "restrict_to_damage", False):
            parts.append(f"Damage({len(obj.allowed_damage_types or [])})")
        if obj.restrict_to_traits:
            parts.append(f"Traits({obj.allowed_traits.count()})")
        if not obj.all_classes:
            parts.append(f"Classes({obj.classes.count()})")
        return ", ".join(parts) or "—"
    restriction_summary.short_description = "Restrictions"

    class Media:
       js = (
           "characters/js/martialmastery_admin.js",
           "characters/js/formula_builder.js",
       )
       css = {"all": ("characters/css/formula_builder.css",)}


class ClassSubclassForm(forms.ModelForm):
    class Meta:
        model = ClassSubclass
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # figure out which base_class is in play (either from POST or from the instance)
        base_cls_id = (
            self.data.get("base_class")
            or getattr(self.instance, "base_class_id", None)
        )

        if base_cls_id:
            # limit the group choices to exactly those SubclassGroups for that CharacterClass
            self.fields["group"].queryset = SubclassGroup.objects.filter(
                character_class_id=base_cls_id
            )
        else:
            # no class selected yet → no group choices
            self.fields["group"].queryset = SubclassGroup.objects.none()

@admin.register(Spell)
class SpellAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'origin')
    search_fields = ('name',  'origin')




# ─── Tag & Subclass admins ──────────────────────────────────────────────────────

@admin.register(ClassTag)
class ClassTagAdmin(admin.ModelAdmin):
    list_display   = ('name',)
    search_fields  = ('name',)


# characters/admin.py
# characters/admin.py
from django.contrib import admin

# characters/admin.py


@admin.register(ClassSubclass)
class ClassSubclassAdmin(admin.ModelAdmin):
    form = ClassSubclassForm
    list_display  = ("base_class","name","group","system_type","code")
    list_filter   = ("base_class","group__system_type","group")
    search_fields = ("name","code")
    list_editable = ("group",)
    class Media:
        js = ("characters/js/classsubclass_admin.js",)

    def get_form(self, request, obj=None, **kwargs):
        Base = super().get_form(request, obj, **kwargs)
        # look in POST *or* GET *or* fallback to the instance
        base_pk = (
            request.POST.get("base_class")
            or request.GET.get("base_class")
            or (obj.base_class_id if obj else None)
        )

        class ChainedForm(Base):
            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)
                if base_pk:
                    self.fields["group"].queryset = SubclassGroup.objects.filter(
                        character_class_id=base_pk
                    )
                else:
                    self.fields["group"].queryset = SubclassGroup.objects.none()

        return ChainedForm

 




class SubclassGroupInline(admin.TabularInline):
    model  = SubclassGroup
    extra  = 1
    fields = ("name", "code", "system_type")   # ← added
# ─── CharacterClass, Tiers & Levels ─────────────────────────────────────────────




@admin.register(ProficiencyTier)
class ProficiencyTierAdmin(admin.ModelAdmin):
    list_display   = ('name', 'bonus')
    search_fields  = ('name',)






# ─── ClassFeature ────────────────────────────────────────────────────────────────
from django.apps import apps
from django.db import models
from django.db.models import IntegerField
DICE = ["d4","d6","d8","d10","d12","d20"]
Character = apps.get_model("characters", "Character")
ABILITY_NAMES = ("strength","dexterity","constitution","intelligence","wisdom","charisma")
ABILITY_FIELDS = [
     f.name
     for f in Character._meta.get_fields()
     if isinstance(f, models.IntegerField) and f.name in ABILITY_NAMES
 ]

ALL_INT_FIELDS = [
    f.name
    for f in Character._meta.get_fields()
    if isinstance(f, IntegerField)
]
# the rest of your VARS (levels, saves, class_level, plus any “_level” fields)
from django.db import connection


def get_other_vars():
    try:
        from characters.models import CharacterClass
        if CharacterClass._meta.db_table in connection.introspection.table_names():
            class_fields = [f"{cls.name.lower()}_level" for cls in CharacterClass.objects.all()]
        else:
            class_fields = []
    except Exception:
        class_fields = []

    return [
        "level", "class_level", "proficiency_modifier",
        "hp", "temp_hp",
    ] + class_fields + [
        "reflex_save", "fortitude_save", "will_save",
        "initiative", "weapon_attack", "spell_attack", "spell_dc",
        "perception", "dodge",
    ]


VARS = ABILITY_FIELDS + get_other_vars() + ALL_INT_FIELDS
class ClassResourceForm(forms.ModelForm):
    class Meta:
        model = ClassResource
        fields = ("resource_type", "formula")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from characters.models import ResourceType

        try:
            resource_vars = [f"{rt.code}_points" for rt in ResourceType.objects.all()]
        except Exception:
            resource_vars = []

        self.fields["formula"].widget = FormulaBuilderWidget(
            variables=VARS + resource_vars,
            dice=DICE,
            attrs={"rows": 2, "cols": 40},
        )


class ClassFeatureForm(forms.ModelForm):

    gain_resistance_types = forms.MultipleChoiceField(
        choices=ClassFeature.DAMAGE_TYPE_CHOICES,     # same tuple of (value, label)
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select which damage types you resist/reduce."
    )

    gain_proficiency_target = forms.ChoiceField(
        choices=[("", "---------")]
                + list(PROFICIENCY_TYPES)
                + [(f"skill_{s.pk}", s.name) for s in Skill.objects.all()],
        required=False,
        label="Gain Proficiency Target",
        help_text="Which proficiency (or skill) does this feature grant?"
    )
    gain_proficiency_amount = forms.ModelChoiceField(
        queryset=ProficiencyTier.objects.all(),
        required=False,
        label="Gain Proficiency Amount",
        help_text="What tier of proficiency does the character gain?"
    )

    
    class Meta:
        model  = ClassFeature
        fields = "__all__"
        labels = {
            "character_class": "Applies To Class",
            "feature_type":    "Feature Category",
            "activity_type":   "Active / Passive",
            "subclass_group":  "Umbrella (if subclass-related)",
            "subclasses":      "Which Subclasses",
            "code":            "Unique Code",
            "name":            "Feature Name",
            "description":     "Description / Fluff",
            "has_options":     "Has Options?",
            "formula":         "Dice Formula",
            "uses":            "Usage Frequency",
            "formula_target":  "Roll Type",
            "action_type":     "Action Required",
            "modify_proficiency_amount": "Override Proficiency Tier",
        }
        help_texts = {
            "character_class": "Which CharacterClass grants this feature.",
            "kind": (
                "• class_trait: always active trait\n"
                "• class_feat: pickable class feat\n"
                "• subclass_choice: present options from umbrella\n"
                "• subclass_feat: actual subclass-specific feature"
            ),
            "activity_type": "Select active (uses) or passive (static bonus).",
            "subclass_group": (
                "If this is a subclass_choice or subclass_feat, pick the umbrella here."
            ),
            "subclasses": (
                "For subclass_feat only: which subclasses receive it?"
            ),
            "code":       "Short identifier used in formulas and JSON.",
            "name":       "Human-readable name shown to players.",
            "has_options":"Check to add FeatureOption inlines below.",
            "formula":    "Dice+attribute expression, e.g. '1d10+level'.",
            "uses":       "How many times? e.g. 'level/3 round down +1'.",
            "formula_target": "What kind of roll this formula applies to.",
            "modify_proficiency_amount": "Select the tier you want instead of the character’s base.",
            "action_type":"Choose whether this ability takes your Action, Bonus Action or Reaction.",
        }
        widgets = {
            "character_class": CharacterClassSelect(),
            "formula":         FormulaBuilderWidget(variables=VARS, dice=DICE, attrs={"rows":4,"cols":40}),
            "uses":            FormulaBuilderWidget(variables=VARS, dice=DICE, attrs={"rows":4,"cols":40}),
            "cantrips_formula":    FormulaBuilderWidget(variables=VARS, dice=DICE, attrs={"rows":2,"cols":40}),
            "spells_known_formula": FormulaBuilderWidget(variables=VARS, dice=DICE, attrs={"rows":2,"cols":40}),
            "spells_prepared_formula": FormulaBuilderWidget(variables=VARS, dice=DICE, attrs={"rows":2,"cols":40}),
            # ✅ new
            "martial_points_formula":       FormulaBuilderWidget(variables=VARS, dice=DICE, attrs={"rows":2,"cols":40}),
            "available_masteries_formula":  FormulaBuilderWidget(variables=VARS, dice=DICE, attrs={"rows":2,"cols":40}),
            "gain_subskills": FilteredSelectMultiple("Sub-skills", is_stacked=True),
            "subclasses": FilteredSelectMultiple("Subclasses", is_stacked=True),
            "description": SummernoteWidget(),
        }


        # ... 
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ─────────────────────────────────────────────────────────────────
        # 1) **DO NOT** hide tier or mastery_rank in Python.  The JS will do that.
        #
        #    In other words, do NOT include lines like:
        #
        #        self.fields["tier"].widget = forms.HiddenInput()
        #        self.fields["mastery_rank"].widget = forms.HiddenInput()
        #
        #    Those lines must be removed (or commented out). Otherwise Django
        #    never renders the “.field-tier” wrapper.
        # ─────────────────────────────────────────────────────────────────

        #
        # 2) Figure out which umbrella was “pre‐selected”:
        #    - raw_data (POST) or initial (GET) or from instance
        #

          # ───────────────────────────────────────────────────────────────
        if getattr(self.instance, "pk", None):
            self.fields["code"].initial = self.instance.code      
        raw_data = self.data or {}
        initial  = self.initial or {}

        grp_id = (
            raw_data.get("subclass_group")
            or initial.get("subclass_group")
            or getattr(self.instance, "subclass_group_id", None)
        )

        system_t = ""
        if grp_id:
            try:
                system_t = SubclassGroup.objects.get(pk=grp_id).system_type
            except SubclassGroup.DoesNotExist:
                system_t = ""

        #
        # 3) **Always** inject data-system-type on the <select id="id_subclass_group">
        #    This is how JS will know whether the chosen Umbrella is “modular_linear”,
        #    “modular_mastery”, or “linear”.
        #
        self.fields["subclass_group"].widget.attrs["data-system-type"] = system_t

    def clean(self):
        cleaned = super().clean()
        scope_val  = cleaned.get("scope")
        grp        = cleaned.get("subclass_group")
        tier_val   = cleaned.get("tier")
        master_val = cleaned.get("mastery_rank")

        # 1) If scope is some subclass‐flow, force them to pick a group
        if scope_val in ("subclass_choice", "subclass_feat", "gain_subclass_feat") and grp is None:
            self.add_error("subclass_group", "Pick an umbrella …")
                # Hide/clear MM formulas at the server if not a martial mastery feature
        if cleaned.get("kind") != "martial_mastery":
            cleaned["martial_points_formula"] = ""
            cleaned["available_masteries_formula"] = ""
        if grp and scope_val not in ("subclass_choice", "subclass_feat", "gain_subclass_feat"):
            self.add_error("subclass_group", "Only subclass_feats (or subclass_choices) may set a subclass_group.")

        # 2) If they are in subclass_feat/gain_subclass_feat, enforce tier/mastery rules:
        if scope_val in ("subclass_feat", "gain_subclass_feat"):
            if grp:
                if grp.system_type == SubclassGroup.SYSTEM_LINEAR:
                    if tier_val is not None:
                        self.add_error("tier", "Only modular_linear features may have a Tier.")
                    if master_val is not None:
                        self.add_error("mastery_rank", "Only modular_mastery features may have a Mastery Rank.")
                elif grp.system_type == SubclassGroup.SYSTEM_MODULAR_LINEAR:
                    if tier_val is None:
                        self.add_error("tier", "This modular_linear feature must have a Tier (1,2,3… ).")
                    if master_val is not None:
                        self.add_error("mastery_rank", "Modular_linear features may not have a Mastery Rank.")
                elif grp.system_type == SubclassGroup.SYSTEM_MODULAR_MASTERY:
                    if master_val is None:
                        self.add_error("mastery_rank", "This modular_mastery feature must have a Mastery Rank (0…4).")
                    if tier_val is not None:
                        self.add_error("tier", "Modular_mastery features may not have a Tier.")
        return cleaned


class MasteryChoiceFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        for form in self.forms:
            if self.can_delete and form.cleaned_data.get("DELETE"):
                continue
            feat = form.cleaned_data.get("feature")
            if not feat:
                continue
            if (
                feat.scope == "subclass_choice"
                and feat.subclass_group
                and feat.subclass_group.system_type == SubclassGroup.SYSTEM_MODULAR_MASTERY
            ):
                picks = form.cleaned_data.get("num_picks") or 0
                if picks < 1:
                    raise ValidationError(
                        f"‘{feat.name}’ is a modular-mastery choice; set num_picks ≥ 1."
                    )


from characters.models import ClassLevelFeature

# characters/admin.py
class ClassLevelFeatureInline(admin.TabularInline):
    model  = ClassLevelFeature
    extra  = 1
    fields = ("feature", "num_picks")   # ← show it
    formset = MasteryChoiceFormSet      # ← validate it

    verbose_name = "Feature granted at this level"
    verbose_name_plural = "Features granted at this level"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "feature":
            kwargs["queryset"] = ClassFeature.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)



@admin.register(ArmorTrait)
class ArmorTraitAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

class ArmorTraitInline(admin.TabularInline):
    model = Armor.traits.through
    autocomplete_fields = ("armortrait",)
    extra = 1

@admin.register(Armor)
class ArmorAdmin(admin.ModelAdmin):
    list_display = ("name","armor_value","type","speed_penalty","dex_cap","hinderance","strength_requirement")
    list_filter  = ("type","traits")
    search_fields= ("name",)
    inlines      = [ArmorTraitInline]
    

# characters/admin.py
class SpellSlotRowForm(forms.ModelForm):
    level = forms.IntegerField(disabled=True)

    class Meta:
        model  = SpellSlotRow
        fields = "__all__"
        labels = {f"slot{i}": f"Level {i}" for i in range(1, 11)}

# admin.py (SpellSlotRowInline)
class SpellSlotRowInline(admin.TabularInline):
    form       = SpellSlotRowForm
    model      = SpellSlotRow
    fields     = ["level"] + [f"slot{i}" for i in range(1, 11)]
    can_delete = False
    min_num    = 20
    max_num    = 20
    extra      = 0
    classes    = ["spell-slot-inline"]
    verbose_name        = "Spell Slots for Level"
    verbose_name_plural = "Spell Slots Table"

    def has_delete_permission(self, request, obj=None):
        return False

    def get_extra(self, request, obj=None, **kwargs):
        # Only prefill the 20 rows if this feature is a spell table
        if obj is None or getattr(obj, "kind", None) == "spell_table":
            return 20
        return 0


@admin.register(ResourceType)
class ResourceTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")



@admin.register(ClassFeature)
class ClassFeatureAdmin(admin.ModelAdmin):
    prepopulated_fields = {"code": ("name",)}
    search_fields = ("name", "code")
    form         = ClassFeatureForm
    inlines = [FeatureOptionInline, SpellSlotRowInline]    
    list_display = (
        'character_class','scope','kind','subclass_group',
        'code','name','formula_target','has_options',
        'formula','uses',
    )

    list_filter  = ('character_class','scope','kind','subclass_group',)
    autocomplete_fields = ('subclasses',)
    base_fields = [
        "character_class",
        "scope",      
        "kind",       
        "activity_type",
        "action_type",

        "subclass_group",
        "subclasses",
        "code",
        "name",
        "description",
        "has_options",
        "formula_target",
        "damage_type",   
        "formula",
        "uses",
        "gain_subskills",
        "modify_proficiency_target",
        "modify_proficiency_amount",
        "cantrips_formula",
        "spells_known_formula",
        "spells_prepared_formula",   
        "modify_proficiency_target",
        "modify_proficiency_amount",
        "saving_throw_required",
        "saving_throw_type",
        "saving_throw_granularity",
        "saving_throw_basic_success",
        "saving_throw_basic_failure",
        "saving_throw_critical_success",
        "saving_throw_success",
        "saving_throw_failure",
        "saving_throw_critical_failure",

        
    ]
    def get_fieldsets(self, request, obj=None):
        base = [
            (None, {
                "fields": [
                    "character_class","scope","kind","gain_subskills","activity_type",
                    "action_type","subclass_group","subclasses",
                    "code","name","description","has_options",
                    "tier","mastery_rank","formula_target","formula","uses",
                    "spell_list","modify_proficiency_target",
                    "modify_proficiency_amount","cantrips_formula",
                    "spells_known_formula","spells_prepared_formula",
                ],
            }),
            ("Saving Throw (optional)", { "fields": [
                "saving_throw_required","saving_throw_type","saving_throw_granularity",
                "saving_throw_basic_success","saving_throw_basic_failure",
                "saving_throw_critical_success","saving_throw_success",
                "saving_throw_failure","saving_throw_critical_failure",
            ]}),
            ("Damage / Formula (optional)", { "fields": ["damage_type","formula","uses"]}),
            ("Resistance (optional)", { "fields": [
                "gain_resistance_mode","gain_resistance_types","gain_resistance_amount",
            ]}),
        ]

        # ✅ Add this small fieldset for martial mastery formulas
        base.append((
            "Martial Mastery (optional)",
            { "fields": ["martial_points_formula", "available_masteries_formula"] }
        ))

        return base

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # Force a <select> for modify_proficiency_target even though the model is CharField
        if db_field.name == "modify_proficiency_target":
            from django import forms
            from characters.models import PROFICIENCY_TYPES, Skill

            # 1) build the combined list: base prof types + all Skill names
            base = list(PROFICIENCY_TYPES)
            skill_choices = [(f"skill_{s.pk}", s.name) for s in Skill.objects.all()]
            all_choices = [("", "---------")] + base + skill_choices

            # 2) return a ChoiceField (renders as <select>) instead of default TextInput
            return forms.ChoiceField(
                choices=all_choices,
                required=not db_field.blank,
                widget=forms.Select,
                label=db_field.verbose_name,
                help_text=db_field.help_text,
            )
        if db_field.name == "gain_proficiency_target":
                from django import forms
                from characters.models import PROFICIENCY_TYPES, Skill
                base = list(PROFICIENCY_TYPES)
                skill_choices = [(f"skill_{s.pk}", s.name) for s in Skill.objects.all()]
                all_choices = [("", "---------")] + base + skill_choices
                return forms.ChoiceField(
                    choices=all_choices,
                    required=not db_field.blank,
                    widget=forms.Select,
                    label=db_field.verbose_name,
                    help_text=db_field.help_text,
                )
        

        return super().formfield_for_dbfield(db_field, request, **kwargs)




    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        # If ?scope=​… is in the URL, copy it into initial
        if "scope" in request.GET:
            initial["scope"] = request.GET["scope"]
        # If ?subclass_group=​… is in the URL, copy it into initial
        if "subclass_group" in request.GET:
            initial["subclass_group"] = request.GET["subclass_group"]
        return initial

    def get_inline_instances(self, request, obj=None):
        inlines = super().get_inline_instances(request, obj)
        # If the user has not checked “has_options,” remove the FeatureOptionInline entirely:
        if request.method == "POST":
            want = request.POST.get("has_options") in ("1", "true", "on")
            kind = request.POST.get("kind")
            if not want:
                inlines = [i for i in inlines if not isinstance(i, FeatureOptionInline)]
            
        else:
            kind = getattr(obj, "kind", None)

        if kind == "inherent_spell":
            inlines.append(SpellInline(self.model, self.admin_site))

        return inlines
    def get_form(self, request, obj=None, **kwargs):
        BaseForm = super().get_form(request, obj, **kwargs)

        class WrappedForm(BaseForm):
            def __init__(self, *args, **inner_kwargs):
                super().__init__(*args, **inner_kwargs)

                # ── preserve existing code on edit ──
                if getattr(self.instance, "pk", None):
                    self.fields["code"].initial = self.instance.code

                # figure out which umbrella was pre‐selected
                raw_data = self.data or {}
                initial  = self.initial or {}
                grp_id = (
                    raw_data.get("subclass_group")
                    or initial.get("subclass_group")
                    or getattr(self.instance, "subclass_group_id", None)
                )

                # look up its system_type
                system_t = ""
                if grp_id:
                    try:
                        system_t = SubclassGroup.objects.get(pk=grp_id).system_type or ""
                    except SubclassGroup.DoesNotExist:
                        pass

                # inject data-system-type *and* full group→type map
                if "subclass_group" in self.fields:
                    widget = self.fields["subclass_group"].widget
                    widget.attrs["data-system-type"] = system_t
                    # full map for in-place updates
                    mapping = {
                        str(g.pk): g.system_type
                        for g in SubclassGroup.objects.all()
                    }
                    widget.attrs["data-group-types"] = json.dumps(mapping)

        return WrappedForm
    

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "modify_proficiency_target":
            # 1) grab your old armor/dodge/etc list
            base_choices = list(db_field.choices)
            # 2) append one tuple per Skill
            skill_choices = [(f"skill_{s.pk}", s.name) for s in Skill.objects.all()]
            kwargs["choices"] = base_choices + skill_choices
        return super().formfield_for_choice_field(db_field, request, **kwargs)  
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Whenever Django is about to render the ForeignKey “subclass_group” field,
        this method will be called.  We can intercept it, figure out which SubclassGroup
        is “pre-selected,” look up its .system_type, and then attach it as
        `data-system-type="..."` on the HTML <select> widget.
        """
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)

        # Only do this injection when rendering the `subclass_group` dropdown:
        if db_field.name == "subclass_group":
            # 1) Find the “currently selected” SubclassGroup ID.  
            #    - If we’re editing, the URL is something like /admin/…/classfeature/123/change/,
            #      so we can pull obj_id from request.resolver_match.kwargs.
            #    - If we’re on an “Add” page with a GET param ?subclass_group=XYZ, pick that.
            #    - If the form has already been POSTed, `request.POST["subclass_group"]` will be the new value.
            #
            #    Note:  you might not need all three of these steps at once.  Typically:
            #    • On “Add” (no instance yet), you read request.GET.get("subclass_group").
            #    • On “Change” (instance exists), you read obj.subclass_group_id.
            #    • On a POST (validation errors), you read request.POST["subclass_group"].
            #
            selected_id = None

            #  A) If this is a POST submission with an error (re-rendering the form),
            #     read the posted value:
            if request.method == "POST" and "subclass_group" in request.POST:
                selected_id = request.POST.get("subclass_group")

            #  B) Otherwise, if they passed ?subclass_group=… in the URL (e.g. after picking “scope”):
            if not selected_id:
                selected_id = request.GET.get("subclass_group")

            #  C) If we’re editing an existing ClassFeature (URL = …/classfeature/123/change/),
            #     fetch the object from the DB to see which SubclassGroup is already set:
            if not selected_id:
                # Extract the “object_id” from the URL resolver (if present):
                match = resolve(request.path_info)
                obj_id = match.kwargs.get("object_id")
                if obj_id:
                    try:
                        cf = ClassFeature.objects.get(pk=obj_id)
                        selected_id = cf.subclass_group_id
                    except ClassFeature.DoesNotExist:
                        selected_id = None

            # Now, if we found a valid ID, look it up in SubclassGroup and read .system_type:
            system_t = ""
            if selected_id:
                try:
                    sg = SubclassGroup.objects.get(pk=selected_id)
                    # sg.system_type is one of: "linear", "modular_linear", "modular_mastery"
                    system_t = sg.system_type or ""
                except SubclassGroup.DoesNotExist:
                    system_t = ""

            # Finally: attach the exact ASCII-hyphen key "data-system-type" to the <select>:
            field.widget.attrs["data-system-type"] = system_t

        return field    
    


    class Media:
        js = (
            'characters/js/formula_builder.js',
            'characters/js/classfeature_admin.js',
        )
        css = {
            'all': ('characters/css/formula_builder.css',)
        }
# characters/admin.py


@admin.register(ContentType)
class ContentTypeAdmin(admin.ModelAdmin):
    list_display  = ("app_label", "model")
    search_fields = ("app_label", "model")
@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display    = ("code", "name", "description")
    search_fields   = ("code", "name")
    fields        = ("code", "name", "description")


@admin.register(Background)
class BackgroundAdmin(admin.ModelAdmin):
    form   = BackgroundForm
    fields = [
      "code","name","description",
      ("primary_ability","primary_bonus","primary_selection_mode","primary_selection"),
      ("secondary_ability","secondary_bonus","secondary_selection_mode","secondary_selection"),
    ]
    list_filter = ("primary_ability","secondary_ability")


@admin.register(AbilityScore)
class AbilityScoreAdmin(admin.ModelAdmin):
    search_fields = ("name",)
# characters/admin.py

@admin.register(ClassLevel)
class ClassLevelAdmin(admin.ModelAdmin):
    list_display = ("character_class", "level")
    # inlines = ( … remove the inline that previously forced you to pick subclass_feats … )
    readonly_fields = ("subclass_features_at_this_level",)
    inlines = [ClassLevelFeatureInline]

    def subclass_features_at_this_level(self, obj):
        """
        This method will now show any *placeholder* “Gain Subclass Feature (Tier N)”
        that is attached to this ClassLevel.  You do not need to change it.
        """
        qs = ClassFeature.objects.filter(
            character_class=obj.character_class,
            scope="subclass_choice",
            classlevelfeature__class_level=obj
        )
        if not qs.exists():
            return "(no subclass-choice feature on this level)"
        html = "<ul>" + "".join(
            f"<li><b>[Tier {f.tier or f.mastery_rank}]</b> {f.name} ({f.code})</li>"
            for f in qs
        ) + "</ul>"
        return format_html(html)

    

    class Media:
        js = ("characters/js/classlevel_admin.js","characters/js/classlevelfeature_admin.js",)


class ClassResourceInline(admin.TabularInline):
    model = ClassResource
    form  = ClassResourceForm
    extra = 1
    fields = ("resource_type","formula")
    # no more max_points here!
@admin.register(CharacterClass)
class CharacterClassAdmin(admin.ModelAdmin):
    form = CharacterClassForm
    list_display      = (
        "name", "hit_die", "class_ID", "display_key_abilities",
        "secondary_thumbnail", "tertiary_thumbnail"
    )
    search_fields     = ("name", "tags__name")
    list_filter       = ("tags", "key_abilities")
    filter_horizontal = ("tags", "key_abilities")  # use horizontal filter for the M2M

    inlines = [
        ClassProficiencyProgressInline,
        SubclassGroupInline,
        ClassResourceInline,
    ]

    # show fields in the order you like: primary, secondary, tertiary images plus previews
    fields = (
        "name",
        "description",
        "class_ID",
        "hit_die",
        "tags",
        "key_abilities",                 # new multi‐select field
        "primary_image",   "primary_preview",
        "secondary_image", "secondary_preview",
        "tertiary_image",  "tertiary_preview",
        # … any other existing CharacterClass fields …
    )
    readonly_fields = ("primary_preview", "secondary_preview", "tertiary_preview")

    def primary_preview(self, obj):
        if obj.primary_image:
            return format_html(
                '<img src="{}" style="max-height:120px; border:1px solid #ccc;" />',
                obj.primary_image.url
            )
        return "(no primary image)"
    primary_preview.short_description = "Primary Preview"

    def secondary_preview(self, obj):
        if obj.secondary_image:
            return format_html(
                '<img src="{}" style="max-height:120px; border:1px solid #ccc;" />',
                obj.secondary_image.url
            )
        return "(no secondary image)"
    secondary_preview.short_description = "Secondary Preview"

    def tertiary_preview(self, obj):
        if obj.tertiary_image:
            return format_html(
                '<img src="{}" style="max-height:120px; border:1px solid #ccc;" />',
                obj.tertiary_image.url
            )
        return "(no tertiary image)"
    tertiary_preview.short_description = "Tertiary Preview"

    # Tiny 40×40 thumbnails for change‐list
    def secondary_thumbnail(self, obj):
        if obj.secondary_image:
            return format_html(
                '<img src="{}" style="height:40px;width:40px;object-fit:cover;border-radius:4px;" />',
                obj.secondary_image.url
            )
        return "—"
    secondary_thumbnail.short_description = "2° Img"

    def tertiary_thumbnail(self, obj):
        if obj.tertiary_image:
            return format_html(
                '<img src="{}" style="height:40px;width:40px;object-fit:cover;border-radius:4px;" />',
                obj.tertiary_image.url
            )
        return "—"
    tertiary_thumbnail.short_description = "3° Img"

    def display_key_abilities(self, obj):
        """
        Show the chosen ability(ies) in the changelist
        """
        return ", ".join([a.name for a in obj.key_abilities.all()])
    display_key_abilities.short_description = "Key Abilities"



# characters/admin.py

from django.contrib import admin
from characters.models import Race, Subrace, RacialFeature, RaceFeatureOption, RaceTag
from django.contrib import admin





@admin.register(Race)
class RaceAdmin(admin.ModelAdmin):
    list_display = (
        "name","code","size","speed",
        "secondary_thumbnail","tertiary_thumbnail",
    )
    search_fields    = ("name","code")
    list_filter      = ("size",)
    filter_horizontal = ("tags","languages")

    readonly_fields = (
        "primary_preview","secondary_preview","tertiary_preview",
    )
    fieldsets = [
        (None, {
            "fields": [
                "code","name","description","size","speed",
                "starting_hp",# fixed bonuses
                ("strength_bonus","dexterity_bonus","constitution_bonus"),
                ("intelligence_bonus","wisdom_bonus","charisma_bonus"),
                # ← our new budget settings
                "bonus_budget",
                "free_points",
                "max_bonus_per_ability",
                "tags",
                "languages",
                "primary_image","primary_preview",
                "secondary_image","secondary_preview",
                "tertiary_image","tertiary_preview",
            ]
        }),
    ]

    def primary_preview(self, obj):
        if obj.primary_image:
            return format_html('<img src="{}" style="max-height:120px;border:1px solid #ccc;" />', obj.primary_image.url)
        return "(no primary image)"
    primary_preview.short_description = "Primary Preview"

    def secondary_preview(self, obj):
        if obj.secondary_image:
            return format_html(
                '<img src="{}" style="max-height:120px;border:1px solid #ccc;" />',
                obj.secondary_image.url
            )
        return "(no secondary image)"
    secondary_preview.short_description = "Secondary Preview"

    def tertiary_preview(self, obj):
        if obj.tertiary_image:
            return format_html(
                '<img src="{}" style="max-height:120px;border:1px solid #ccc;" />',
                obj.tertiary_image.url
            )
        return "(no tertiary image)"
    tertiary_preview.short_description = "Tertiary Preview"

    def secondary_thumbnail(self, obj):
        if obj.secondary_image:
            return format_html(
                '<img src="{}" style="height:40px;width:40px;object-fit:cover;border-radius:4px;" />',
                obj.secondary_image.url
            )
        return "—"
    secondary_thumbnail.short_description = "2° Img"

    def tertiary_thumbnail(self, obj):
        if obj.tertiary_image:
            return format_html(
                '<img src="{}" style="height:40px;width:40px;object-fit:cover;border-radius:4px;" />',
                obj.tertiary_image.url
            )
        return "—"
    tertiary_thumbnail.short_description = "3° Img"



@admin.register(Subrace)
class SubraceAdmin(RaceAdmin):
    search_fields     = ("name", "code")       # for autocomplete on RacialFeatureAdmin
    list_display      = ("name", "race", "code")
    list_filter       = ("race", "size")
    filter_horizontal = ("tags",)

    fieldsets = [
        (None, {
            "fields": [
                "race",     # parent selector first
                "code", "name", "description",
                "size", "speed",
                ("strength_bonus", "dexterity_bonus", "constitution_bonus"),
                ("intelligence_bonus", "wisdom_bonus", "charisma_bonus"),
                "bonus_budget", "free_points", "max_bonus_per_ability",
                "tags",
                "primary_image", "primary_preview",
                "secondary_image", "secondary_preview",
                "tertiary_image",  "tertiary_preview",
            ]
        }),
    ]

    readonly_fields = (
        "primary_preview",
        "secondary_preview",
        "tertiary_preview",
    )

class RaceFeatureOptionInline(admin.TabularInline):
    model = RaceFeatureOption
    fk_name = "feature"
    extra = 1
    autocomplete_fields = ("grants_feature",)


class RaceFeatureForm(ClassFeatureForm):
    class Meta(ClassFeatureForm.Meta):
        model = RacialFeature
        fields = "__all__"

    # extra selects for proficiency (OK to keep here)
    gain_proficiency_target = forms.ChoiceField(
        choices=[("", "---------")] + list(PROFICIENCY_TYPES)
                + [(f"skill_{s.pk}", s.name) for s in Skill.objects.all()],
        required=False,
        label="Gain Proficiency Target",
        help_text="Which proficiency (or skill) does this feature grant?",
    )
    gain_proficiency_amount = forms.ModelChoiceField(
        queryset=ProficiencyTier.objects.all(),
        required=False,
        label="Gain Proficiency Amount",
        help_text="What tier of proficiency does the character gain?",
    )

    def __init__(self, *args, **kwargs):
        # bypass ClassFeatureForm.__init__ (as you intended)
        forms.ModelForm.__init__(self, *args, **kwargs)

        # drop class-only fields
        for f in ("character_class", "subclass_group", "subclasses", "tier", "mastery_rank"):
            self.fields.pop(f, None)

        # tweak scope labels
        self.fields["scope"].choices = [
            ("class_feat",   "Race Feature"),
            ("subclass_feat","Subrace Feature"),
        ]

        # limit subrace list to chosen race
        race_val = (
            self.data.get("race")
            or self.initial.get("race")
            or getattr(self.instance, "race_id", None)
        )
        if "subrace" in self.fields:
            self.fields["subrace"].queryset = (
                Subrace.objects.filter(race_id=race_val) if race_val else Subrace.objects.none()
            )

        # preserve code when editing
        if getattr(self.instance, "pk", None):
            self.fields["code"].initial = self.instance.code

    def clean(self):
        cleaned = super(ClassFeatureForm, self).clean()  # intentionally skip CFForm.clean
        if cleaned.get("scope") == "subclass_feat" and not cleaned.get("subrace"):
            self.add_error("subrace", "Please select a Subrace for a Subrace Feature.")
        return cleaned

@admin.register(RacialFeature)
class RacialFeatureAdmin(ClassFeatureAdmin):
    form = RaceFeatureForm
    inlines = [RaceFeatureOptionInline]
    exclude = ("character_class", "subclasses")

    fieldsets = [
        (None, {
            "fields": [
                "race","subrace","scope","kind","gain_subskills",
                "code","name","description","has_options",
                "modify_proficiency_target","modify_proficiency_amount",
                "cantrips_formula","spells_known_formula","spells_prepared_formula",
            ],
        }),
        ("Saving Throw (optional)", {
            
            "fields": [
                "saving_throw_required","saving_throw_type",
                "saving_throw_granularity","saving_throw_basic_success",
                "saving_throw_basic_failure","saving_throw_critical_success",
                "saving_throw_success","saving_throw_failure",
                "saving_throw_critical_failure",
            ],
        }),
        ("Damage / Formula (optional)", {
            "fields": ["damage_type","formula","uses"],
        }),
        ("Resistance (optional)", {
               "fields": [
                   "gain_resistance_mode",
                   "gain_resistance_types",
                   "gain_resistance_amount",
               ],
           }),
    ]

    def get_fieldsets(self, request, obj=None):
        # Force the admin to use *this* class’s fieldsets
        return self.fieldsets

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == 'subrace':
            race_id = request.POST.get('race') or request.GET.get('race')
            field.queryset = (
                Subrace.objects.filter(race_id=race_id)
                if race_id else Subrace.objects.none()
            )
        return field
    

    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # Force a <select> for modify_proficiency_target even though the model is CharField
        if db_field.name == "modify_proficiency_target":
            from django import forms
            from characters.models import PROFICIENCY_TYPES, Skill

            # 1) build the combined list: base prof types + all Skill names
            base = list(PROFICIENCY_TYPES)
            skill_choices = [(f"skill_{s.pk}", s.name) for s in Skill.objects.all()]
            all_choices = [("", "---------")] + base + skill_choices

            # 2) return a ChoiceField (renders as <select>) instead of default TextInput
            return forms.ChoiceField(
                choices=all_choices,
                required=not db_field.blank,
                widget=forms.Select,
                label=db_field.verbose_name,
                help_text=db_field.help_text,
            )
        if db_field.name == "gain_proficiency_target":
            from django import forms
            from characters.models import PROFICIENCY_TYPES, Skill
            base = list(PROFICIENCY_TYPES)
            skill_choices = [(f"skill_{s.pk}", s.name) for s in Skill.objects.all()]
            all_choices = [("", "---------")] + base + skill_choices
            return forms.ChoiceField(
                choices=all_choices,
                required=not db_field.blank,
                widget=forms.Select,
                label=db_field.verbose_name,
                help_text=db_field.help_text,
            )        



        return super().formfield_for_dbfield(db_field, request, **kwargs)


    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "modify_proficiency_target":
            # 1) grab your old armor/dodge/etc list
            base_choices = list(db_field.choices)
            # 2) append one tuple per Skill
            skill_choices = [(f"skill_{s.pk}", s.name) for s in Skill.objects.all()]
            kwargs["choices"] = base_choices + skill_choices
        return super().formfield_for_choice_field(db_field, request, **kwargs)
    @property
    def media(self):
        return forms.Media(
            js = ["characters/js/formula_builder.js"],
            css= {"all": ["characters/css/formula_builder.css"]}
        )

# in characters/admin.py

from django.contrib import admin
@admin.register(UniversalLevelFeature)
class UniversalLevelFeatureAdmin(admin.ModelAdmin):
    list_display  = ("level", "grants_general_feat", "grants_asi")
    list_editable = ("grants_general_feat", "grants_asi")
    list_per_page = 25

    search_fields = ("level",)
    ordering      = ("level",)

    fields = ("level", "grants_general_feat", "grants_asi")


class CSPForm(forms.ModelForm):
    selected_skill = CombinedSkillField(label="Skill or SubSkill")

    class Meta:
        model  = CharacterSkillProficiency
        # don't list selected_skill_type/id here:
        fields = ("character","proficiency")

    def save(self, commit=True):
        inst = super().save(commit=False)
        obj  = self.cleaned_data["selected_skill"]
        inst.selected_skill_type = ContentType.objects.get_for_model(obj)
        inst.selected_skill_id   = obj.pk
        if commit:
            inst.save()
        return inst


        
@admin.register(CharacterSkillProficiency)
class CharacterSkillProficiencyAdmin(CombinedSkillAdminMixin, admin.ModelAdmin):
    form = CSPForm
    list_display = ("character","selected_skill","proficiency")



@admin.register(WeaponTrait)
class WeaponTraitAdmin(admin.ModelAdmin):
    list_display = ("name", "requires_value")
    search_fields = ("name",)

class WeaponTraitValueInline(admin.TabularInline):
    model = WeaponTraitValue
    extra = 1
    fields = ("trait", "value")


@admin.register(EquipmentSlot)
class EquipmentSlotAdmin(admin.ModelAdmin):
    list_display   = ("name",)
    search_fields  = ("name",)

# characters/admin.py
@admin.register(WearableSlot)
class WearableSlotAdmin(admin.ModelAdmin):
    list_display         = ("code","name")
    search_fields        = ("code","name")
    prepopulated_fields  = {"code": ("name",)}

# admin.py
class SpecialItemTraitValueForm(forms.ModelForm):
    # ACTIVE (match model types)
    formula_target = forms.ChoiceField(
        choices=ClassFeature._meta.get_field("formula_target").choices,
        required=False,
        label="Roll Type",
    )
    formula = forms.CharField(
        widget=FormulaBuilderWidget(variables=VARS, dice=DICE, attrs={"rows":2,"cols":40}),
        required=False,
    )
    uses = forms.CharField(
        widget=FormulaBuilderWidget(variables=VARS, dice=DICE, attrs={"rows":2,"cols":40}),
        required=False,
    )
    action_type = forms.ChoiceField(
        choices=ClassFeature._meta.get_field("action_type").choices,
        required=False,
        label="Action Required",
    )
    # ↓ SINGLE choice to match CharField on the model
    damage_type = forms.ChoiceField(
        choices=ClassFeature.DAMAGE_TYPE_CHOICES,
        required=False,
        label="Damage Type",
    )

    # SAVES (all present on the model)
    saving_throw_required = forms.BooleanField(required=False, label="Saving Throw?")
    saving_throw_type = forms.ChoiceField(
        choices=SpecialItemTraitValue._meta.get_field("saving_throw_type").choices,
        required=False
    )
    saving_throw_granularity = forms.ChoiceField(
        choices=SpecialItemTraitValue._meta.get_field("saving_throw_granularity").choices,
        required=False
    )
    saving_throw_basic_success    = forms.CharField(required=False)
    saving_throw_basic_failure    = forms.CharField(required=False)
    saving_throw_critical_success = forms.CharField(required=False)
    saving_throw_success          = forms.CharField(required=False)
    saving_throw_failure          = forms.CharField(required=False)
    saving_throw_critical_failure = forms.CharField(required=False)

    # PASSIVE (match model types that actually exist)
    modify_proficiency_target = forms.ChoiceField(
        choices=[("", "---------")] + list(PROFICIENCY_TYPES)
                + [(f"skill_{s.pk}", s.name) for s in Skill.objects.all()],
        required=False,
    )
    modify_proficiency_amount = forms.ModelChoiceField(
        queryset=ProficiencyTier.objects.all(),
        required=False,
    )
    gain_resistance_mode = forms.ChoiceField(
        choices=SpecialItemTraitValue._meta.get_field("gain_resistance_mode").choices,
        widget=forms.RadioSelect, required=False,
    )
    # ⚠️ Removed gain_resistance_types / gain_resistance_amount here,
    # because they are not on the model.

    class Meta:
        model = SpecialItemTraitValue
        fields = [
            "name", "active",
            "formula_target", "formula", "uses", "action_type", "damage_type",
            "saving_throw_required", "saving_throw_type", "saving_throw_granularity",
            "saving_throw_basic_success", "saving_throw_basic_failure",
            "saving_throw_critical_success", "saving_throw_success",
            "saving_throw_failure", "saving_throw_critical_failure",
            "modify_proficiency_target", "modify_proficiency_amount",
            "gain_resistance_mode",
            "description",
        ]


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ensure attrs/original_attrs exist so classfeature_admin.js can hook them
        for f in self.fields.values():
            w = f.widget
            if getattr(w, "attrs", None) is None:
                w.attrs = {}
            if getattr(w, "original_attrs", None) is None:
                w.original_attrs = {}
            if hasattr(w, "choices") and w.choices is None:
                w.choices = []

class SpecialItemTraitValueFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen = set()
        for form in self.forms:
            if self.can_delete and form.cleaned_data.get("DELETE"):
                continue
            trait = form.cleaned_data.get("trait")
            if trait:
                if trait in seen:
                    raise ValidationError("You can only assign each Trait once per item.")
                seen.add(trait)





class SpecialItemTraitValueInline(admin.StackedInline):
    model   = SpecialItemTraitValue
    form    = SpecialItemTraitValueForm
    extra   = 1
    classes = ["specialitemtraitvalue-inline"]

    fieldsets = [
        (None, {
            "fields": [
              # always visible:
              "name", "active",

              # active-only:
              "formula_target","formula","uses","action_type","damage_type",
              "saving_throw_required","saving_throw_type","saving_throw_granularity",
              "saving_throw_basic_success","saving_throw_basic_failure",
              "saving_throw_critical_success","saving_throw_success",
              "saving_throw_failure","saving_throw_critical_failure",

              # passive-only:
              "modify_proficiency_target","modify_proficiency_amount",
              "gain_resistance_mode","gain_resistance_types","gain_resistance_amount",

              # always visible
              "description",
            ],
        }),
    ]

@admin.register(SpecialItem)
class SpecialItemAdmin(admin.ModelAdmin):
    form = SpecialItemForm   # ← add this line
    list_display    = ("name","item_type","base_object","rarity")
    list_filter     = ("item_type","rarity")
    fieldsets = [
      (None, {
        "fields": ["attunement","name","item_type"],
      }),
      ("Weapon Settings", {
        "classes": ("weapon-group",),
        "fields": ("weapon",),
      }),
      ("Armor Settings", {
        "classes": ("armor-group",),
        "fields": ("armor",),
      }),
      ("Wearable Settings", {
        "classes": ("wearable-group",),
        "fields": ("wearable_slot",),
      }),
      ("General", {
        "fields": ("enhancement_bonus","rarity","description"),
     }),
    ]
    inlines = [SpecialItemTraitValueInline]
    autocomplete_fields = ("weapon","armor","wearable_slot",)

    def base_object(self, obj):
        if obj.item_type=="weapon":   return obj.weapon
        if obj.item_type=="armor":    return obj.armor
        if obj.item_type=="wearable": return obj.wearable_slot
        return "–"
    base_object.short_description = "Base"
    def get_form(self, request, obj=None, **kwargs):
        BaseForm = super().get_form(request, obj, **kwargs)
        class WrappedForm(BaseForm):
            def __init__(self, *args, **inner_kwargs):
                super().__init__(*args, **inner_kwargs)
                for field in self.fields.values():
                    w = field.widget

                    # 1) ensure attrs is a dict
                    if getattr(w, "attrs", None) is None:
                        w.attrs = {}

                    # 2) ensure original_attrs is a dict
                    if getattr(w, "original_attrs", None) is None:
                        w.original_attrs = {}
                    # 3) if this widget has .choices, make it an iterable
                    if hasattr(w, "choices") and w.choices is None:
                        w.choices = []
        return WrappedForm
    class Media:
        js = ("characters/js/specialitem_admin.js",)


class WeaponForm(forms.ModelForm):
    # render as multi-check
    damage_types = forms.MultipleChoiceField(
        choices=Weapon.DAMAGE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Damage types",
    )
    class Meta:
        model  = Weapon
        fields = "__all__"

@admin.register(Weapon)
class WeaponAdmin(admin.ModelAdmin):
    form = WeaponForm
    inlines = [WeaponTraitValueInline]
    list_display  = ("name","category","damage","range_type","range_normal","range_max","damage_types_list")
    list_filter   = ("category","range_type")
    search_fields = ("name","damage")

    def damage_types_list(self, obj):
        # display friendly labels
        mapping = dict(Weapon.DAMAGE_CHOICES)
        return ", ".join(mapping.get(v, v) for v in (obj.damage_types or [])) or "—"
    damage_types_list.short_description = "Damage types"

    class Media:
        js = ("characters/js/weapon_admin.js",)
