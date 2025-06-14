# characters/admin.py

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
    SpellSlotRow , 
    ResourceType, ClassResource, CharacterResource, Spell
)

from django.urls import resolve
from django.contrib.admin.widgets import FilteredSelectMultiple
from characters.widgets import FormulaBuilderWidget, CharacterClassSelect
from characters.models import RulebookPage, Rulebook, RacialFeature, Rulebook, RulebookPage,AbilityScore,Background, ResourceType,Weapon, SubSkill, UniversalLevelFeature, Skill,SkillCategory, WeaponTraitValue,WeaponTrait, ClassResource, CharacterResource, SubclassGroup, SubclassTierLevel
from characters.forms import CharacterClassForm
from django.utils.html import format_html
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError

# characters/admin.py



# characters/admin.py

from django.contrib import admin

# admin.py



# ─── Inline for Pages ─────────────────────────────────────────────────────────


@admin.register(Rulebook)
class RulebookAdmin(admin.ModelAdmin):
    list_display  = ("name",)
    search_fields = ("name",)


@admin.register(RulebookPage)
class RulebookPageAdmin(admin.ModelAdmin):
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
@admin.register(WeaponTrait)
class WeaponTraitAdmin(admin.ModelAdmin):
    list_display = ("name", "requires_value")
    search_fields = ("name",)

class WeaponTraitValueInline(admin.TabularInline):
    model = WeaponTraitValue
    extra = 1
    autocomplete_fields = ("trait",)
    fields = ("trait", "value")
                
@admin.register(Weapon)
class WeaponAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "damage", "is_melee")
    list_filter = ("category", "is_melee")
    search_fields = ("name", "damage")
    inlines = [WeaponTraitValueInline]

class SubSkillInline(admin.TabularInline):
    model = SubSkill
    extra = 1
    fields = ("name",)


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display   = ("name", "ability")
    search_fields  = ("name",)
    inlines        = [SubSkillInline]

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "ability", "is_advanced")
    search_fields = ("name",)
    list_filter = ("ability", "is_advanced")

@admin.register(SubSkill)
class SubSkillAdmin(admin.ModelAdmin):
    list_display       = ("name", "category")
    search_fields      = ("name",)
    list_filter        = ("category",)
    autocomplete_fields= ("category",)


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

class ClassProficiencyProgressInline(admin.TabularInline):
    model  = ClassProficiencyProgress
    extra  = 1
    fields = ('proficiency_type', 'at_level', 'tier')





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


class RacialFeatureInline(admin.TabularInline):
    model = RacialFeature
    extra = 1

class FeatureOptionInline(admin.TabularInline):
    model   = FeatureOption
    fk_name = "feature"
    extra   = 1
    verbose_name = "Feature option"
    verbose_name_plural = "Feature options"


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
            "feature_type":    (
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
            "gain_subskills": FilteredSelectMultiple("Sub-skills", is_stacked=True),
            "subclasses": FilteredSelectMultiple("Subclasses", is_stacked=True),
        }

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




from characters.models import ClassLevelFeature

class ClassLevelFeatureInline(admin.TabularInline):
    model = ClassLevelFeature
    extra = 1
    
    verbose_name = "Feature granted at this level"
    verbose_name_plural = "Features granted at this level"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "feature":
            # Remove the filter; show everything:
            # kwargs["queryset"] = ClassFeature.objects.filter(scope="subclass_choice")
            # instead use:
            kwargs["queryset"] = ClassFeature.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(SubclassGroup)
class SubclassGroupAdmin(admin.ModelAdmin):
    list_display = ("character_class", "name", "code", "system_type")
    list_filter  = ("character_class", "system_type")
    inlines      = (SubclassTierLevelInline,)
    form         = SubclassGroupForm
    fields       = ("character_class", "name", "code", "system_type", "modular_rules")
    readonly_fields = ()  # leave modular_rules visible if you use it for other purposes

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        grp = form.instance
        chosen = form.cleaned_data.get("subclasses", [])
        chosen_ids = [s.pk for s in chosen]
        # Link selected subclasses to this group
        ClassSubclass.objects.filter(pk__in=chosen_ids).update(group=grp)
        # Unlink any other that used to be in this group
        ClassSubclass.objects.filter(group=grp).exclude(pk__in=chosen_ids).update(group=None)

# characters/admin.py
class SpellSlotRowForm(forms.ModelForm):
    level = forms.IntegerField(disabled=True)

    class Meta:
        model  = SpellSlotRow
        fields = "__all__"
        labels = {f"slot{i}": f"Level {i}" for i in range(1, 11)}

class SpellSlotRowInline(admin.TabularInline):
    form            = SpellSlotRowForm
    model           = SpellSlotRow
    fields          = ["level"] + [f"slot{i}" for i in range(1, 11)]
    can_delete      = False
    min_num         = 20
    max_num         = 20
    extra           = 0
    # absolutely no deletions, ever
    def has_delete_permission(self, request, obj=None):
        return False
    max_num         = 20
    extra           = 0
    classes         = ["spell-slot-inline"]
    verbose_name    = "Spell Slots for Level"
    verbose_name_plural = "Spell Slots Table"

    def get_extra(self, request, obj=None, **kwargs):
        if obj is None or getattr(obj, "feature_type", None) == "spell_table":
            return 20
        return 0

    def get_formset(self, request, obj=None, **kwargs):
        FormSet = super().get_formset(request, obj, **kwargs)
        class Prefilled(FormSet):
            def __init__(self, *args, **fkwargs):
                fkwargs.setdefault(
                    "initial",
                    [{"level": lvl} for lvl in range(1, 21)]
                )
                super().__init__(*args, **fkwargs)
        return Prefilled



@admin.register(ResourceType)
class ResourceTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")



@admin.register(ClassFeature)
class ClassFeatureAdmin(admin.ModelAdmin):
    search_fields = ("name", "code")
    form         = ClassFeatureForm
    inlines = [FeatureOptionInline, SpellSlotRowInline, SpellInline]    
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
        """
        We put all fields in one big fieldset, but because our custom form hides/shows
        tier/mastery_rank/min_level dynamically, this is enough.
        """
        return [
            (
                None,
                {
                    "fields": [
                        "character_class",
                        "scope",
                        "kind",
                        "gain_subskills",
                        "activity_type",
                        "action_type",
                        "subclass_group",
                        "subclasses",
                        "code",
                        "name",
                        "description",
                        "has_options",
                        "tier",           # ← add this
                        "mastery_rank",   # ← and this
                        "formula_target",
                        "formula",
                        "uses",
                        "tier",
                        "spell_list",           # ← our new dropdown
                        "modify_proficiency_target",
                        "modify_proficiency_amount",             
                        "cantrips_formula",
                        "spells_known_formula",
                        "spells_prepared_formula",

                    ]
                },
            )
        ]

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
        """
        Wrap the normal form (ClassFeatureForm) so that
        <select id="id_subclass_group"> always has 
        data-system-type="…" set correctly.
        """
        BaseForm = super().get_form(request, obj, **kwargs)

        class WrappedForm(BaseForm):
            def __init__(self, *args, **inner_kwargs):
                super().__init__(*args, **inner_kwargs)

                # 1) Figure out the “pre-selected” umbrella ID:
                raw_data = self.data or {}
                initial  = self.initial or {}
                grp_id = (
                    raw_data.get("subclass_group")
                    or initial.get("subclass_group")
                    or getattr(self.instance, "subclass_group_id", None)
                )

                # 2) Look up that SubclassGroup’s system_type (linear/modular_linear/modular_mastery)
                system_t = ""
                if grp_id:
                    try:
                        system_t = SubclassGroup.objects.get(pk=grp_id).system_type
                    except SubclassGroup.DoesNotExist:
                        system_t = ""

                # 3) ***Crucial:*** set the exact ASCII hyphen key "data-system-type"
                self.fields["subclass_group"].widget.attrs["data-system-type"] = system_t

        return WrappedForm
    
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



@admin.register(Background)
class BackgroundAdmin(admin.ModelAdmin):
    list_display = (
        "code", "name",
        "primary_ability", "primary_bonus", "primary_skill",
        "secondary_ability", "secondary_bonus", "secondary_skill",
    )
    search_fields = ("code", "name")
    list_filter  = ("primary_ability", "secondary_ability")
    autocomplete_fields = ("primary_skill", "secondary_skill")

    fields = [
        "code", "name",
        ("primary_ability", "primary_bonus", "primary_skill"),
        ("secondary_ability", "secondary_bonus", "secondary_skill"),
    ]

@admin.register(AbilityScore)
class AbilityScoreAdmin(admin.ModelAdmin):
    search_fields = ("name",)

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


@admin.register(RaceTag)
class RaceTagAdmin(admin.ModelAdmin):
    list_display         = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields        = ("name",)

class RaceFeatureInline(admin.TabularInline):
    model  = RacialFeature
    extra  = 1
    fields = (
        "code","name","description",
        "saving_throw_required","saving_throw_type","saving_throw_granularity",
        "saving_throw_basic_success","saving_throw_basic_failure",
        "saving_throw_critical_success","saving_throw_success",
        "saving_throw_failure","saving_throw_critical_failure",
        "damage_type","formula","uses",
    )


class RaceFeatureOptionInline(admin.TabularInline):
    model = RaceFeatureOption
    fk_name = "feature"
    extra = 1
    autocomplete_fields = ("grants_feature",)
    verbose_name = "Feature option"
    verbose_name_plural = "Feature options"




class RacialFeatureForm(ClassFeatureForm):
    class Meta(ClassFeatureForm.Meta):
        model = RacialFeature

@admin.register(RacialFeature)
class RaceFeatureAdmin(ClassFeatureAdmin):
    form = RacialFeatureForm
    inlines = [RaceFeatureOptionInline]

    list_display = (
                "race", "subrace", "scope", "kind",
       "code", "name", "has_options", "formula", "uses",
    )
    list_filter = ("race", "scope", "kind")
    autocomplete_fields = ("subrace",)
    search_fields = ("code", "name", "description")
    fieldsets = [
        (None, {
            "fields": [
                "race", "subrace",
                "scope", "kind", "gain_subskills",
                "activity_type", "action_type",
                "subclasses",
                "code", "name", "description",
                "has_options",                "tier", "mastery_rank", "level_required",
               "formula_target",
                "spell_list",
                "cantrips_formula", "spells_known_formula", "spells_prepared_formula",
                "modify_proficiency_target", "modify_proficiency_amount",
            ]
        }),
        ("Saving Throw", {
            "classes": ["collapse"],
            "fields": [
                "saving_throw_required", "saving_throw_type", "saving_throw_granularity",
                "saving_throw_basic_success", "saving_throw_basic_failure",
                "saving_throw_critical_success", "saving_throw_success",
                "saving_throw_failure", "saving_throw_critical_failure",
            ]
        }),
        ("Effect / Damage", {
            "classes": ["collapse"],
            "fields": ["damage_type", "formula", "uses"],
        }),
    ]

    class Media:
        js = (
            "characters/js/formula_builder.js",
            "characters/js/classfeature_admin.js",
        )
        css = {"all": ("characters/css/formula_builder.css",)}

@admin.register(Race)
class RaceAdmin(admin.ModelAdmin):
    inlines = [RacialFeatureInline,]
    list_display = (
        "name","code","size","speed",
        "secondary_thumbnail","tertiary_thumbnail",
    )
    search_fields    = ("name","code")
    list_filter      = ("size",)
    filter_horizontal = ("tags",)

    readonly_fields = (
        "primary_preview","secondary_preview","tertiary_preview",
    )
    fieldsets = [
        (None, {
            "fields": [
                "code","name","description",
                "size","speed",
                ("strength_bonus","dexterity_bonus","constitution_bonus"),
                ("intelligence_bonus","wisdom_bonus","charisma_bonus"),
                "tags",
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
class SubraceAdmin(admin.ModelAdmin):
    list_display      = ("name","race","code")
    filter_horizontal = ("tags",)
    search_fields     = ("name","code")
    inlines           = [RacialFeatureInline ]



@admin.register(UniversalLevelFeature)
class UniversalLevelFeatureAdmin(admin.ModelAdmin):
    list_display  = ("level", "grants_general_feat", "grants_asi")
    list_editable = ("grants_general_feat", "grants_asi")
    list_per_page = 25

    search_fields = ("level",)
    ordering      = ("level",)

    fields = ("level", "grants_general_feat", "grants_asi")


