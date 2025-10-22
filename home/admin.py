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
    ResourceType, ClassResource, CharacterResource, Spell, SubclassMasteryUnlock, ARMOR_GROUPS, WEAPON_GROUPS
)
from characters.models import CharacterPrestigeEnrollment, CharacterPrestigeLevelChoice

from characters.models import (
    PrestigeClass, PrestigeLevel, PrestigePrerequisite, PrestigeFeature
)
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.urls import resolve
from django.contrib.admin.widgets import FilteredSelectMultiple
from characters.widgets import FormulaBuilderWidget, CharacterClassSelect
from characters.models import EquipmentSlot, WearableSlot ,SpecialItem, SpecialItemTraitValue,Language,Armor, ArmorTrait, CharacterSkillProficiency, LoremasterArticle, LoremasterImage, RulebookPage, Rulebook, RacialFeature, Rulebook, RulebookPage,AbilityScore,Background, ResourceType,Weapon, SubSkill, UniversalLevelFeature, Skill, WeaponTraitValue,WeaponTrait, ClassResource, CharacterResource, SubclassGroup, SubclassTierLevel
from characters.forms import BackgroundForm,CharacterClassForm, CombinedSkillField
from django.utils.html import format_html
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError
from characters.models import PROFICIENCY_TYPES, Skill ,    SkillProficiencyUpgrade,  ClassSkillPointGrant, ClassSkillFeatGrant
import json
# admin.py
from django.contrib.admin import SimpleListFilter
from django.db.models import Q
DICE = ["d4","d6","d8","d10","d12","d20"]

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
    classes = ["featureoption-inline"]
    verbose_name = "Feature option"
    verbose_name_plural = "Feature options"
    autocomplete_fields = ("grants_feature",) 
# ─── Inline for Pages ─────────────────────────────────────────────────────────
from django_summernote.widgets import SummernoteWidget
from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin
from django.apps import apps
from django.db import models, connection
from django.db.models import IntegerField

class SpecialItemForm(forms.ModelForm):
    class Meta:
        model  = SpecialItem
        fields = "__all__"   # or list exactly the fields you show in your fieldsets
ABILITY_NAMES = ("strength","dexterity","constitution","intelligence","wisdom","charisma")
Character = apps.get_model("characters", "Character")

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

# home/admin.py (near other small helpers)
ABILITY_MOD_VARS = [f"{name}_mod" for name in ABILITY_NAMES]
VARS = ABILITY_FIELDS + get_other_vars() + ALL_INT_FIELDS

class CSVMultipleChoiceField(forms.MultipleChoiceField):
    """
    Treat a stored comma-separated string as a list for initial/redisplay.
    """
    def prepare_value(self, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [v for v in value.split(",") if v.strip()]
        return list(value)

# in home/admin.py
from django.forms.forms import DeclarativeFieldsMetaclass
class ProficiencyTargetUIMixin(metaclass=DeclarativeFieldsMetaclass):
    PROF_TARGET_KIND = (
        ("armor_group",  "Armor group"),
        ("weapon_group", "Weapon group"),
        ("armor_item",   "Specific armor"),
        ("weapon_item",  "Specific weapon"),
    )
    prof_target_kind     = forms.ChoiceField(choices=PROF_TARGET_KIND, required=False, label="Proficiency target type")
    armor_group_choice   = forms.ChoiceField(choices=ARMOR_GROUPS,  required=False, label="Armor group")
    weapon_group_choice  = forms.ChoiceField(choices=WEAPON_GROUPS, required=False, label="Weapon group")
    armor_item_choice    = forms.ModelMultipleChoiceField(queryset=Armor.objects.all(),  required=False, widget=forms.CheckboxSelectMultiple, label="Armor items")
    weapon_item_choice   = forms.ModelMultipleChoiceField(queryset=Weapon.objects.all(), required=False, widget=forms.CheckboxSelectMultiple, label="Weapon items")
    PROF_CHANGE_MODE     = (("progress","Add to class progression"), ("set","Set / override on the character"))
    prof_change_mode     = forms.ChoiceField(choices=PROF_CHANGE_MODE, required=False, widget=forms.RadioSelect, label="How to apply")

    def _normalize_prof_targets(self):
        """
        Returns a list of normalized target tokens:
          • ["armor:<group>"]            e.g. ["armor:light"]
          • ["weapon:<group>"]           e.g. ["weapon:martial"]
          • ["armor#<id>", ...]          e.g. ["armor#12", "armor#27"]
          • ["weapon#<id>", ...]         e.g. ["weapon#3",  "weapon#8"]
        """
        out = []
        kind = self.cleaned_data.get("prof_target_kind")

        if kind == "armor_group":
            grp = self.cleaned_data.get("armor_group_choice")
            if not grp:
                self.add_error("armor_group_choice", "Pick an armor group.")
                return []
            return [f"armor:{grp}"]

        if kind == "weapon_group":
            grp = self.cleaned_data.get("weapon_group_choice")
            if not grp:
                self.add_error("weapon_group_choice", "Pick a weapon group.")
                return []
            return [f"weapon:{grp}"]

        if kind == "armor_item":
            items = list(self.cleaned_data.get("armor_item_choice") or [])
            if not items:
                self.add_error("armor_item_choice", "Pick at least one armor item.")
                return []
            return [f"armor#{itm.pk}" for itm in items]

        if kind == "weapon_item":
            items = list(self.cleaned_data.get("weapon_item_choice") or [])
            if not items:
                self.add_error("weapon_item_choice", "Pick at least one weapon item.")
                return []
            return [f"weapon#{itm.pk}" for itm in items]

        # Nothing chosen
        return []




def build_proficiency_target_choices():
    from characters.models import Skill, PROFICIENCY_TYPES
    base = list(PROFICIENCY_TYPES)
    try:
        skills = [(f"skill_{s.pk}", s.name) for s in Skill.objects.all()]
    except Exception:
        skills = []
    return [("", "---------")] + base + skills

# home/admin.py
def build_proficiency_target_choices():
    """
    Returns optgrouped choices for:
      • Core proficiencies (from PROFICIENCY_TYPES)
      • Skills (skill_<id>)
      • Sub-skills (subskill_<id>) labeled “<Skill> – <Sub-skill>”
    """
    from characters.models import Skill, SubSkill, PROFICIENCY_TYPES
    core      = list(PROFICIENCY_TYPES)
    try:
        skills    = [(f"skill_{s.pk}", s.name) for s in Skill.objects.all()]
        subskills = [(f"subskill_{ss.pk}", f"{ss.skill.name} – {ss.name}")
                     for ss in SubSkill.objects.select_related("skill")]
    except Exception:
        skills, subskills = [], []

    # Django supports optgroups as ("Group label", [(value,label),...])
    return [
        ("Core",       core),
        ("Skills",     skills),
        ("Sub-skills", subskills),
    ]

# home/admin.py
class ClassProficiencyProgressForm(forms.ModelForm):
    class Meta:
        model  = ClassProficiencyProgress
        fields = "__all__"

    def clean(self):
        cd = super().clean()
        # hard-clear sub-targets; progress rows don’t deal with them
        cd["armor_group"] = None
        cd["weapon_group"] = None
        cd["armor_item"]  = None
        cd["weapon_item"] = None
        return cd

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
                tier = getattr(feature, "tier", None)
                if tier is None:
                    raise ValidationError(
                        f"{feature} is modular-linear but has no Tier set. "
                        "Open the feature and set its integer Tier."
                    )            
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



class SubclassMasteryUnlockInline(admin.TabularInline):
    model = SubclassMasteryUnlock
    extra = 1
    fields = ("rank", "unlock_level", "modules_required")
    ordering = ("unlock_level", "id")
    verbose_name = "Mastery Rank Gate"
    verbose_name_plural = "Mastery Rank Gates"

# home/admin.py
@admin.register(SubclassGroup)
class SubclassGroupAdmin(admin.ModelAdmin):
    form = SubclassGroupForm
    list_display = ("character_class", "name", "code", "system_type")
    list_filter  = ("character_class", "system_type")
    fields = ("character_class", "name", "code", "system_type")

    # ✅ Only attach inlines that make sense for SubclassGroup
    def get_inline_instances(self, request, obj=None):
        inlines = []
        if obj:
            if obj.system_type == SubclassGroup.SYSTEM_MODULAR_LINEAR:
                inlines.append(SubclassTierLevelInline(self.model, self.admin_site))
            elif obj.system_type == SubclassGroup.SYSTEM_MODULAR_MASTERY:
                inlines.append(SubclassMasteryUnlockInline(self.model, self.admin_site))
        return inlines

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        grp = form.instance
        if grp.system_type == SubclassGroup.SYSTEM_MODULAR_MASTERY:
            gates = list(SubclassMasteryUnlock.objects.filter(subclass_group=grp))
            if any(g.rank is None for g in gates):
                for idx, gate in enumerate(sorted(
                        gates, key=lambda g: (g.rank is None, g.rank, g.unlock_level, g.pk))):
                    if gate.rank is None:
                        gate.rank = idx
                SubclassMasteryUnlock.objects.bulk_update(gates, ["rank"])


class CPPFormSet(BaseInlineFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)
        # If this is a bound POST, include the posted pk in the id field's queryset
        if form.is_bound and "id" in form.fields:
            posted_pk = form.data.get(f"{form.prefix}-id")
            if posted_pk:
                field = form.fields["id"]
                # default queryset = rows for THIS parent; add the posted row just in case
                field.queryset = field.queryset | ClassProficiencyProgress.objects.filter(pk=posted_pk)

    def clean(self):
        super().clean()
        for form in self.forms:
            if self.can_delete and form.cleaned_data.get("DELETE"):
                continue
            pt   = form.cleaned_data.get("proficiency_type")
            lvl  = form.cleaned_data.get("at_level")
            tier = form.cleaned_data.get("tier")
            if not pt and not lvl and not tier:
                form.cleaned_data["DELETE"] = True
            elif pt and (not lvl or not tier):
                if not lvl:  form.add_error("at_level", "Enter the class level.")
                if not tier: form.add_error("tier", "Pick a proficiency tier.")

class ClassProficiencyProgressInline(admin.TabularInline):
    model   = ClassProficiencyProgress
    fk_name = "character_class"   # ← make Django’s relation explicit
    formset = CPPFormSet
    extra   = 0
    fields  = ('proficiency_type','at_level','tier')


class ClassSkillPointGrantInline(admin.TabularInline):
    model = ClassSkillPointGrant
    fk_name = "character_class"
    extra = 0
    fields = ("at_level", "points_awarded")
    ordering = ("at_level",)


class ClassSkillFeatGrantInline(admin.TabularInline):
    model = ClassSkillFeatGrant
    fk_name = "character_class"
    extra = 0
    fields = ("at_level", "num_picks")
    ordering = ("at_level",)


class CharacterClassBaseProfForm(CharacterClassForm):
    armor_proficiencies = forms.MultipleChoiceField(
        choices=ARMOR_GROUPS,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Armor proficiencies (baseline)",
        help_text="Armor groups this class starts proficient with at level 1."
    )

    starting_skills_formula = forms.CharField(
        required=False,
        label="Starting skills (formula)",
        widget=FormulaBuilderWidget(
            # Suggest the usual numeric vars PLUS ability modifiers
            variables=VARS + ABILITY_MOD_VARS,
            dice=DICE,
            attrs={"rows": 2, "cols": 40},
        ),
        help_text=(
            "How many trained skills the class grants at level 1. "
            "Examples: '2', '2 + int_mod'."
        ),
    )    
    weapon_proficiencies = forms.MultipleChoiceField(
        choices=WEAPON_GROUPS,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Weapon proficiencies (baseline)",
        help_text="Weapon groups this class starts proficient with at level 1."
    )
    armor_items_baseline = forms.ModelMultipleChoiceField(
       queryset=Armor.objects.all(), required=False, widget=forms.CheckboxSelectMultiple,
       label="Specific armor (baseline)", help_text="Optional: list specific armor items at level 1."
   )
    weapon_items_baseline = forms.ModelMultipleChoiceField(
       queryset=Weapon.objects.all(), required=False, widget=forms.CheckboxSelectMultiple,
       label="Specific weapons (baseline)", help_text="Optional: list specific weapons at level 1."
   )

    class Meta(CharacterClassForm.Meta):
        model  = CharacterClass
        fields = getattr(CharacterClassForm.Meta, "fields", "__all__")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cls = getattr(self, "instance", None)
        if cls and cls.pk:
            self.initial["armor_proficiencies"] = list(
                ClassProficiencyProgress.objects
                .filter(character_class=cls, proficiency_type="armor", at_level=1)
                .values_list("armor_group", flat=True)
            )
            self.initial["weapon_proficiencies"] = list(
                ClassProficiencyProgress.objects
                .filter(character_class=cls, proficiency_type="weapon", at_level=1)
                .values_list("weapon_group", flat=True)
            )


            self.initial["armor_items_baseline"] = list(
                ClassProficiencyProgress.objects
                .filter(character_class=cls, proficiency_type="armor", at_level=1, armor_item__isnull=False)
                .values_list("armor_item", flat=True)
            )
            self.initial["weapon_items_baseline"] = list(
                ClassProficiencyProgress.objects
                .filter(character_class=cls, proficiency_type="weapon", at_level=1, weapon_item__isnull=False)
                .values_list("weapon_item", flat=True)
            )
    def sync_baseline_prof_progress(self, inst, skip_tokens=frozenset()):
        # ⬇️ this is the exact body you currently have in save() that
        #     deletes/creates CPP rows. Move it here unchanged.
        armor_sel   = set(self.cleaned_data.get("armor_proficiencies") or [])
        weapon_sel  = set(self.cleaned_data.get("weapon_proficiencies") or [])
        armor_items = set(self.cleaned_data.get("armor_items_baseline") or [])
        weapon_items= set(self.cleaned_data.get("weapon_items_baseline") or [])

        default_tier = (
            ProficiencyTier.objects.order_by("bonus").first()
            or ProficiencyTier.objects.order_by("pk").first()
        )
        if not default_tier:
            return inst

        with transaction.atomic():
            # ---- keep your exact delete/get_or_create code here ----
            # Armor groups @ L1
            # Armor groups @ L1
            ClassProficiencyProgress.objects.filter(
                character_class=inst, proficiency_type="armor", at_level=1
            ).exclude(armor_group__in=armor_sel).delete()

            for grp in armor_sel:
                if ("armor_group", grp) in skip_tokens:   # ⬅️ NEW
                    continue
                ClassProficiencyProgress.objects.get_or_create(
                    character_class=inst, proficiency_type="armor", at_level=1,
                    armor_group=grp, weapon_group=None,
                    defaults={"tier": default_tier},
                )

            # Weapon groups @ L1
            ClassProficiencyProgress.objects.filter(
                character_class=inst, proficiency_type="weapon", at_level=1
            ).exclude(weapon_group__in=weapon_sel).delete()

            for grp in weapon_sel:
                if ("weapon_group", grp) in skip_tokens:
                    continue
                ClassProficiencyProgress.objects.get_or_create(
                    character_class=inst, proficiency_type="weapon", at_level=1,
                    armor_group=None, weapon_group=grp,
                    defaults={"tier": default_tier},
                )


            # Specific items @ L1
            # Specific items @ L1
            ClassProficiencyProgress.objects.filter(
                character_class=inst, proficiency_type="armor", at_level=1, armor_item__isnull=False
            ).exclude(armor_item__in=armor_items).delete()
            for a in armor_items:
                tok = ("armor_item", a.pk if hasattr(a, "pk") else a)   # ⬅️ NEW
                if tok in skip_tokens:                                  # ⬅️ NEW
                    continue
                ClassProficiencyProgress.objects.get_or_create(
                    character_class=inst, proficiency_type="armor", at_level=1,
                    armor_group=None, weapon_group=None, armor_item=a, weapon_item=None,
                    defaults={"tier": default_tier},
                )


            ClassProficiencyProgress.objects.filter(
                character_class=inst, proficiency_type="weapon", at_level=1, weapon_item__isnull=False
            ).exclude(weapon_item__in=weapon_items).delete()
            for w in weapon_items:
                tok = ("weapon_item", w.pk if hasattr(w, "pk") else w)  # ⬅️ NEW
                if tok in skip_tokens:                                  # ⬅️ NEW
                    continue
                ClassProficiencyProgress.objects.get_or_create(
                    character_class=inst, proficiency_type="weapon", at_level=1,
                    armor_group=None, weapon_group=None, armor_item=None, weapon_item=w,
                    defaults={"tier": default_tier},
                )

        return inst

    def save(self, commit=True):
        inst = forms.ModelForm.save(self, commit=commit)
        self._needs_baseline_sync = True
        return inst
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

    _RANGE_CHOICES = getattr(Weapon, "RANGE_CHOICES", None) or \
                     Weapon._meta.get_field("range_type").choices
    restrict_to_range = forms.BooleanField(
        required=False,
        label="Range restriction",
        help_text="When checked, limit to selected range types below."
    )
    allowed_range_types = forms.MultipleChoiceField(
        label="Allowed range types",
        choices=_RANGE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Shown only if ‘Range restriction’ is enabled."
    )   

    # ---- NEW: Weapon group restriction (simple / martial / special / black powder)
    restrict_to_weapon_groups = forms.BooleanField(
        required=False,
        label="Weapon group restriction",
        help_text="When checked, limit to selected weapon groups below."
    )
    allowed_weapon_groups = forms.MultipleChoiceField(
        label="Allowed weapon groups",
        choices=WEAPON_GROUPS,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Shown only if ‘Weapon group restriction’ is enabled."
    )

    trait_match_mode = forms.ChoiceField(
        choices=[("any", "ANY of the selected traits (OR)"),
                 ("all", "ALL selected traits (AND)")],
        required=False,
        label="Trait match mode",
        help_text="Only used when ‘Restrict to Traits’ is on."
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
        if cleaned.get("restrict_to_range") and not cleaned.get("allowed_range_types"):
            self.add_error("allowed_range_types", "Select at least one range type or uncheck ‘Range restriction’.")
        if cleaned.get("restrict_to_weapon_groups") and not cleaned.get("allowed_weapon_groups"):
            self.add_error("allowed_weapon_groups",
                           "Select at least one weapon group or uncheck ‘Weapon group restriction’.")

        if cleaned.get("restrict_by_ability"):
            if not cleaned.get("required_ability"):
                self.add_error("required_ability", "Pick an ability or uncheck ‘Ability restriction’.")
            if not cleaned.get("required_ability_score"):
                self.add_error("required_ability_score", "Enter a minimum score or uncheck ‘Ability restriction’.")
# home/admin.py – inside MartialMasteryForm.clean()

        if cleaned.get("restrict_to_traits") and not cleaned.get("allowed_traits"):
            self.add_error("allowed_traits",
                        "Select at least one trait or uncheck ‘Trait restriction’.")

        # If they turned it on but left match mode blank, default to 'any'
        if cleaned.get("restrict_to_traits") and not cleaned.get("trait_match_mode"):
            cleaned["trait_match_mode"] = "any"

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
        'all_classes',
        'restrict_to_weapons', 'restrict_to_damage', 'restrict_to_range', 'restrict_to_traits', 'restrict_by_ability',
        'restriction_summary',
    )
    list_filter  = (
        'is_rare',
        'all_classes',
        'restrict_to_weapons', 'restrict_to_damage', 'restrict_to_range', 'restrict_to_traits', 'restrict_by_ability'
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

                # NEW — weapon group restriction
                "restrict_to_weapon_groups", "allowed_weapon_groups",

                "restrict_to_range",   "allowed_range_types",
                "restrict_to_traits",  "allowed_traits", "trait_match_mode",
                "restrict_by_ability", "required_ability", "required_ability_score",
                "all_classes",
            ),
        }),


    ]

    def restriction_summary(self, obj):
        parts = []
        if obj.restrict_to_weapons:
            parts.append(f"Weapons({obj.allowed_weapons.count()})")
        if getattr(obj, "restrict_to_damage", False):
            parts.append(f"Damage({len(obj.allowed_damage_types or [])})")
        # NEW — range summary


        if getattr(obj, "restrict_to_weapon_groups", False):
            chosen = ", ".join(dict(WEAPON_GROUPS).get(v, v) for v in (obj.allowed_weapon_groups or [])) or "—"
            parts.append(f"Groups({chosen})")
  
        if getattr(obj, "restrict_to_range", False):
            labels = dict(getattr(Weapon, "RANGE_CHOICES", []) or Weapon._meta.get_field("range_type").choices)
            chosen = ", ".join(labels.get(v, v) for v in (obj.allowed_range_types or [])) or "—"
            parts.append(f"Range({chosen})")
        if obj.restrict_to_traits:
            mode = getattr(obj, "trait_match_mode", "any")
            mode_lbl = "ANY" if mode == "any" else "ALL"
            parts.append(f"Traits({obj.allowed_traits.count()} {mode_lbl})")
        if getattr(obj, "restrict_by_ability", False):
            parts.append(f"{getattr(obj, 'get_required_ability_display', lambda: 'Ability')()}≥{obj.required_ability_score or '?'}")
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

 




class SubclassGroupInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen = set()
        for form in self.forms:
            if self.can_delete and form.cleaned_data.get("DELETE"):
                continue
            name = form.cleaned_data.get("name")
            if not name:
                continue
            # duplicate in the posted forms
            if name in seen:
                form.add_error("name", "Name already used under this class.")
            seen.add(name)
            # duplicate vs DB
            exists = (SubclassGroup.objects
                      .filter(character_class=self.instance, name=name)
                      .exclude(pk=form.instance.pk)
                      .exists())
            if exists:
                form.add_error("name", "This umbrella name already exists for this class.")

class SubclassGroupInline(admin.TabularInline):
    model  = SubclassGroup
    extra  = 1
    fields = ("name", "code", "system_type")
    def get_formset(self, request, obj=None, **kwargs):
        FS = super().get_formset(request, obj, **kwargs)
        class Wrapped(FS, SubclassGroupInlineFormSet):
            pass
        return Wrapped




@admin.register(ProficiencyTier)
class ProficiencyTierAdmin(admin.ModelAdmin):
    list_display   = ('name', 'bonus')
    search_fields  = ('name',)


@admin.register(SkillProficiencyUpgrade)
class SkillProficiencyUpgradeAdmin(admin.ModelAdmin):
    list_display  = ("from_rank", "to_rank", "points", "min_level")
    list_filter   = ("from_rank", "to_rank")
    ordering      = ("points", "min_level", "from_rank", "to_rank")
    search_fields = ("from_rank", "to_rank")

    def get_readonly_fields(self, request, obj=None):
        # Disallow nonsense sequences in UI by making from/to readonly on edit
        ro = list(super().get_readonly_fields(request, obj))
        if obj:
            ro += ["from_rank", "to_rank"]
        return ro




# ─── ClassFeature ────────────────────────────────────────────────────────────────
from django.apps import apps
from django.db import models
from django.db.models import IntegerField

# the rest of your VARS (levels, saves, class_level, plus any “_level” fields)
from django.db import connection




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


class ClassFeatureForm( ProficiencyTargetUIMixin,forms.ModelForm):

    gain_resistance_types = forms.MultipleChoiceField(
        choices=ClassFeature.DAMAGE_TYPE_CHOICES,     # same tuple of (value, label)
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select which damage types you resist/reduce."
    )
    # in ClassFeatureForm (top-level under other field defs)
    # in ClassFeatureForm
    GMP_MODE = (("uptier", "Increase tier by one"), ("set", "Gain amount to override"))
    gmp_mode = forms.ChoiceField(
        choices=GMP_MODE,
        required=False,
        widget=forms.RadioSelect,
        label="Gain/Modify mode",
        help_text="Pick one: Increase tier by one (+1 tier), or Gain amount to override (set to a fixed tier)."
    )
    TARGET_GRANT_MODE = (
        ("grant_all",      "Grant all selected now"),
        ("present_choices","Let the player choose (pick N)"),
    )
    target_grant_mode   = forms.ChoiceField(
        choices=TARGET_GRANT_MODE, required=False, widget=forms.RadioSelect,
        label="When multiple targets are selected…",
        help_text="Grant all immediately, or present them as choices to the player."
    )
    target_choice_count = forms.IntegerField(
        required=False, min_value=1, label="Choices to pick (N)",
        help_text="Only used if ‘Let the player choose’ is selected."
    )

    gain_proficiency_target = forms.ChoiceField(
        choices=build_proficiency_target_choices(),
        required=False,
        label="Gain Proficiency Target",
        help_text="Pick a specific armor/weapon group or any base type, or a Skill."
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


        # Keep the target hidden (it’s driven by the core picker UI), but DO NOT hide the amount,
        # because authors need to choose the tier for 'progress' mode.
        if "gain_proficiency_target" in self.fields:
            self.fields["gain_proficiency_target"].widget = forms.HiddenInput()
        # leave 'gain_proficiency_amount' visible


         
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
        import json as _json
        self.fields["subclass_group"].widget.attrs["data-system-type"] = system_t
        widget = self.fields["subclass_group"].widget
        # 1) keep current system on the element
        widget.attrs["data-system-type"] = system_t or ""

        # 2) attach a full id->system_type map so JS can switch instantly on change
        #    (do it here as well so it's *always* present, even if ModelAdmin.get_form
        #     wasn’t the thing that set it)
        mapping = {str(g.pk): g.system_type for g in SubclassGroup.objects.all()}
        widget.attrs["data-group-types"] = _json.dumps(mapping)
    def _resolve_prof_target(self, target_field):
        """
        If the target is 'armor' or 'weapon', require the matching group and
        rewrite the value to 'armor:<group>' or 'weapon:<group>'.
        Otherwise pass-through (skill_*, dc, perception, etc., or already armor:*)
        """
        val = (self.cleaned_data.get(target_field) or "").strip()
        if not val:
            return val
        if ":" in val or val.startswith("skill_"):
            return val  # already specific (e.g., armor:light, weapon:martial) or a skill
        if val == "armor":
            grp = self.cleaned_data.get("armor_group_choice")
            if not grp:
                self.add_error("armor_group_choice", "Pick an armor type.")
            return f"armor:{grp}" if grp else val
        if val == "weapon":
            grp = self.cleaned_data.get("weapon_group_choice")
            if not grp:
                self.add_error("weapon_group_choice", "Pick a weapon type.")
            return f"weapon:{grp}" if grp else val
        return val
    def clean(self):
        cleaned = super().clean()
        scope_val  = cleaned.get("scope")
        grp        = cleaned.get("subclass_group")
        tier_val   = cleaned.get("tier")
        master_val = cleaned.get("mastery_rank")
        if scope_val in ("subclass_feat", "subclass_choice", "gain_subclass_feat"):
            cleaned["level_required"] = None


        
        # 1) If scope is some subclass‐flow, force them to pick a group
        # 1) require group for subclass flows
        if scope_val in ("subclass_choice", "subclass_feat", "gain_subclass_feat") and grp is None:
            if "subclass_group" in self.fields:
                self.add_error("subclass_group", "Pick an umbrella …")
        if cleaned.get("kind") != "martial_mastery":
            cleaned["martial_points_formula"] = ""
            cleaned["available_masteries_formula"] = ""
        if grp and scope_val not in ("subclass_choice", "subclass_feat", "gain_subclass_feat"):
            if "subclass_group" in self.fields:
                self.add_error("subclass_group", "Only subclass_feats (or subclass_choices) may set a subclass_group.")
        # 2) If they are in subclass_feat/gain_subclass_feat, enforce tier/mastery rules:

        if scope_val in ("subclass_feat", "gain_subclass_feat") and grp:
            if grp.system_type == SubclassGroup.SYSTEM_LINEAR:
                # linear subclass-feats shouldn't use tier/mast rank either
                if tier_val is not None:
                    self.add_error("tier", "Only modular_linear features may have a Tier.")
                if master_val is not None:
                    self.add_error("mastery_rank", "Only modular_mastery features may have a Mastery Rank.")
            elif grp.system_type == SubclassGroup.SYSTEM_MODULAR_LINEAR:
                if tier_val is None:
                    self.add_error("tier", "This modular_linear feature must have a Tier (1,2,3…).")
                if master_val is not None:
                    self.add_error("mastery_rank", "Modular_linear features may not have a Mastery Rank.")
            elif grp.system_type == SubclassGroup.SYSTEM_MODULAR_MASTERY:
                if master_val is None:
                    self.add_error("mastery_rank", "This modular_mastery feature must have a Mastery Rank (0…4).")
                if tier_val is not None:
                    self.add_error("tier", "Modular_mastery features may not have a Tier.")



        
        target_tokens = self._normalize_prof_targets()  # LIST, may be empty
        mode_core     = (self.cleaned_data.get("prof_change_mode") or "").strip()
        gmp_mode      = (self.cleaned_data.get("gmp_mode") or "").strip()

        # Clear programmatic “gain” every pass; we only set it for core/progress
        self.cleaned_data["gain_proficiency_target"] = ""
        self.cleaned_data["gain_proficiency_amount"] = None

        # Keep/seed modify_* (generic and core 'set' funnel through here)
        self.cleaned_data["modify_proficiency_target"] = (self.cleaned_data.get("modify_proficiency_target") or "")
        # modify_proficiency_amount already present

        used_generic = bool(gmp_mode)
        used_core    = bool(mode_core)

        if used_generic and used_core:
            self.add_error(None, "Choose either ‘Gain/Modify (generic)’ OR ‘Add Core Proficiency’, not both.")

        kind = cleaned.get("kind")
        # ── guardrails so stray radios don't trip validation or clobber data ──
        if kind != "modify_proficiency":
            cleaned["gmp_mode"] = ""                 # ignore generic section entirely
            cleaned["target_grant_mode"] = ""
            cleaned["target_choice_count"] = None
        
        if kind != "core_proficiency":
            cleaned["prof_change_mode"] = ""         # ignore core section entirely
            # also ignore the core pickers
            for fld in ("prof_target_kind","armor_group_choice","weapon_group_choice",
                        "armor_item_choice","weapon_item_choice"):
                if fld in self.cleaned_data:
                    self.cleaned_data[fld] = None
                # ── A) Gain/Modify (generic) ────────────────────────────────────
        if used_generic:
            if kind != "modify_proficiency":
                self.add_error("kind", "Use ‘Gain/Modify Proficiency’ when using the generic section.")
            tgt = self.cleaned_data.get("modify_proficiency_target")
            if isinstance(tgt, (list, tuple)):
                self.cleaned_data["modify_proficiency_target"] = ",".join(filter(None, tgt))

            if not tgt:
                self.add_error("modify_proficiency_target", "Pick a target to change.")

            if gmp_mode == "set":
                tgt = self.cleaned_data.get("modify_proficiency_target")
                if not tgt:
                    # no target → ignore generic section
                    cleaned["gmp_mode"] = ""
            elif gmp_mode == "uptier":
                # uptier ⇒ clear amount (runtime = +1 tier)
                self.cleaned_data["modify_proficiency_amount"] = None

        # ── B) Add Core Proficiency (armor/weapons only) ────────────────
        if used_core:
            if kind != "core_proficiency":
                self.add_error("kind", "Use ‘Add Core Proficiency (Armor/Weapon)’ when using the core section.")
            if not target_tokens:
                self.add_error("prof_target_kind", "Select what this affects (group or specific items).")

            if mode_core == "progress":
               self.cleaned_data["gain_proficiency_amount"] = None
               self.cleaned_data["gain_proficiency_target"] = ",".join(target_tokens)

            elif mode_core == "set":
                if target_tokens:
                    self.cleaned_data["modify_proficiency_target"] = ",".join(target_tokens)
                    if not self.cleaned_data.get("modify_proficiency_amount"):
                        self.add_error("modify_proficiency_amount", "Pick the proficiency tier to override to.")
                else:
                    self.cleaned_data["modify_proficiency_target"] = ""


        target_tokens = self._normalize_prof_targets()
        mode_core     = (self.cleaned_data.get("prof_change_mode") or "").strip()
        gmp_mode      = (self.cleaned_data.get("gmp_mode") or "").strip()
        # If author used the armor/weapon pickers while in the generic section, merge them
        if used_generic and target_tokens:
            existing = self.cleaned_data.get("modify_proficiency_target") or ""
            if isinstance(existing, str):
                existing_list = [t for t in existing.split(",") if t]
            else:
                existing_list = list(existing or [])
            merged = ",".join(sorted(set(existing_list + target_tokens)))
            self.cleaned_data["modify_proficiency_target"] = merged
        # important: we only meddle with the *generic* Gain/Modify section
        used_generic = bool(gmp_mode)          # your existing flag
        # used_core    = bool(mode_core)       # as you already compute

        # normalize modify_* to a flat list of tokens if necessary
        sel = self.cleaned_data.get("modify_proficiency_target") or ""
        if isinstance(sel, str):
            selected = [t for t in sel.split(",") if t]
        else:
            selected = list(sel or [])

        # ── NEW: apply the grant/choices mode when using generic section ──
        if used_generic and selected:
            grant_mode = (self.cleaned_data.get("target_grant_mode") or "grant_all").strip()

            if grant_mode == "present_choices":
                n = self.cleaned_data.get("target_choice_count") or 0
                if n < 1:
                    self.add_error("target_choice_count", "Enter how many the player may pick (≥ 1).")
                if n > len(selected):
                    self.add_error("modify_proficiency_target",
                                   f"You selected only {len(selected)} target(s) but set pick {n}.")
                # Encode as: choose:<N>:<comma-separated tokens>
                encoded = f"choose:{n}:{','.join(selected)}"
                self.cleaned_data["modify_proficiency_target"] = encoded
            else:
                # grant_all → store as simple comma-joined list (your current format)
                self.cleaned_data["modify_proficiency_target"] = ",".join(selected)

        # if NOT using the generic section, keep whatever you already set earlier
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
                feat.subclass_group
                and feat.subclass_group.system_type == SubclassGroup.SYSTEM_MODULAR_MASTERY
                and feat.scope == "gain_subclass_feat"       # ← only gainers
            ):
                picks = form.cleaned_data.get("num_picks") or 0
                if picks < 1:
                    raise ValidationError(
                        f"‘{feat.name}’ is a modular-mastery gainer; set ‘Choices granted at this level’ ≥ 1."
                    )


from characters.models import ClassLevelFeature
from django.core.exceptions import ValidationError
from django.db.models import Q

# keep your existing MasteryChoiceFormSet as-is

class CombinedCLFFormSet(MasteryChoiceFormSet):
    """
    Runs MasteryChoiceFormSet.clean() AND the modular-linear tier gate check.
    """
    def clean(self):
        # 1) MasteryChoiceFormSet validation
        super().clean()

        # 2) Modular-linear: prevent picking Tier N without lower tier earlier
        this_level = self.instance.level
        cls = self.instance.character_class

        picks = []
        seen = set()
        dupes = []

        for form in self.forms:
            if self.can_delete and form.cleaned_data.get("DELETE"):
                continue
            feature = form.cleaned_data.get("feature")
            if not feature:
                continue
            grp = getattr(feature, "subclass_group", None)
            if not grp or grp.system_type != SubclassGroup.SYSTEM_MODULAR_LINEAR:
                continue

            # derive tier from code suffix "_<int>"
            try:
                tier = getattr(feature, "tier", None)
                if tier is None:
                    raise ValidationError(
                        f"{feature} is modular-linear but has no Tier set."
                    )            
            except (ValueError, IndexError):
                raise ValidationError(
                    f"Feature code {feature.code!r} does not end in _<tier> "
                    f"(required for modular_linear)."
                )

            if feature in seen:
                dupes.append(feature)
            seen.add(feature)
            picks.append((feature, grp, tier))

        if dupes:
            names = ", ".join(str(f) for f in dupes)
            raise ValidationError(f"Duplicate feature selected at this level: {names}")

        
class CLFForm(forms.ModelForm):
    class Meta:
        model  = ClassLevelFeature
        fields = ("feature", "num_picks")
        labels = {"num_picks": "Choices granted at this level"}

    # CLFForm.__init__  (remove the HiddenInput swap)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Always render the input; we’ll hide/show with JS.
        self.fields["num_picks"].required = False
        self.fields["num_picks"].widget.attrs.setdefault("min", 0)


class ClassLevelFeatureInline(admin.TabularInline):
    model  = ClassLevelFeature
    extra  = 1
    form   = CLFForm
    fields = ("feature", "num_picks")
    formset = CombinedCLFFormSet

    # stash the parent ClassLevel so we can see its class/level
    def get_formset(self, request, obj=None, **kwargs):
        self._parent_level = obj
        return super().get_formset(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "feature":
            qs = ClassFeature.objects.filter(racialfeature__isnull=True)

            parent = getattr(self, "_parent_level", None)
            if parent:
                cls = parent.character_class
                L   = parent.level
                qs = qs.filter(character_class=cls)

                # modular_mastery unlocked (group, rank) pairs
                allowed_mm = set(
                    SubclassMasteryUnlock.objects
                    .filter(subclass_group__character_class=cls, unlock_level__lte=L)
                    .values_list("subclass_group_id", "rank")
                )
                mm_q = Q()
                for g_id, r in allowed_mm:
                    mm_q |= Q(subclass_group_id=g_id, mastery_rank=r)

                # modular_linear unlocked (group, tier) pairs
                allowed_ml = set(
                    SubclassTierLevel.objects
                    .filter(subclass_group__character_class=cls, unlock_level__lte=L)
                    .values_list("subclass_group_id", "tier")
                )
                ml_q = Q()
                for g_id, t in allowed_ml:
                    ml_q |= Q(subclass_group_id=g_id, tier=t)

                qs = qs.filter(
                    ~Q(scope="subclass_feat")
                    |
                    ~Q(subclass_group__system_type__in=[
                        SubclassGroup.SYSTEM_MODULAR_MASTERY,
                        SubclassGroup.SYSTEM_MODULAR_LINEAR,
                    ])
                    |
                    (Q(subclass_group__system_type=SubclassGroup.SYSTEM_MODULAR_MASTERY) & mm_q)
                    |
                    (Q(subclass_group__system_type=SubclassGroup.SYSTEM_MODULAR_LINEAR) & ml_q)
                ).distinct()

            kwargs["queryset"] = qs

        # build the field once
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)

        if db_field.name == "feature":
            # use the module-level imports; do NOT re-import SubclassGroup here
            mm_gainer_map = {
                str(f.pk): bool(
                    f.scope == "gain_subclass_feat"
                    and f.subclass_group
                    and f.subclass_group.system_type == SubclassGroup.SYSTEM_MODULAR_MASTERY
                )
                for f in field.queryset
            }
            field.widget.attrs["data-mm-gainer-map"] = json.dumps(mm_gainer_map)

        return field

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
    exclude = ("traits",)
    inlines      = [ArmorTraitInline]
    

class SpellSlotRowForm(forms.ModelForm):
    class Meta:
        model  = SpellSlotRow
        fields = "__all__"
        labels = {f"slot{i}": f"Level {i}" for i in range(1, 11)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Submit the value but make it visually read-only
        self.fields["level"].widget.attrs["readonly"] = True   # not 'disabled'
class SpellSlotRowInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen_levels = set()
        for form in self.forms:
            if self.can_delete and form.cleaned_data.get("DELETE"):
                continue
            if not form.cleaned_data:
                continue
            level = form.cleaned_data.get("level")
            # ignore completely empty extra forms
            if level is None:
                continue
            if level in seen_levels:
                form.add_error("level", "You already added a row for this level.")
            seen_levels.add(level)

# admin.py (SpellSlotRowInline)
class SpellSlotRowInline(admin.TabularInline):
    form       = SpellSlotRowForm
    model      = SpellSlotRow
    fields     = ["level"] + [f"slot{i}" for i in range(1, 11)]
    can_delete = False
    max_num    = 20
    extra      = 0
    classes    = ["spell-slot-inline"]
    verbose_name = "Spell Slots for Level"
    verbose_name_plural = "Spell Slots Table"

    def has_delete_permission(self, request, obj=None):
        return False

    def get_extra(self, request, obj=None, **kwargs):
        # On the Add page (no obj yet), show rows if kind=spell_table
        if obj is None:
            kind = (request.POST.get("kind") or request.GET.get("kind") or "").strip()
            return 20 if kind == "spell_table" else 0
        return 0

    def get_formset(self, request, obj=None, **kwargs):
        FormSet = super().get_formset(request, obj, **kwargs)
        # Prefill 1..20 in the Add case so "level" isn't blank
        class Prefilled(FormSet):
            def __init__(self, *a, **kw):
                if obj is None:
                    kind = (request.POST.get("kind") or request.GET.get("kind") or "").strip()
                    if kind == "spell_table":
                        kw.setdefault("initial", [{"level": i} for i in range(1, 21)])
                super().__init__(*a, **kw)
        return Prefilled


@admin.register(ResourceType)
class ResourceTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")



@admin.register(ClassFeature)
class ClassFeatureAdmin(admin.ModelAdmin):
    prepopulated_fields = {"code": ("name",)}
    search_fields = ("name", "code")
    form         = ClassFeatureForm
    inlines = [FeatureOptionInline,SpellSlotRowInline]    
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
    # in home/admin.py  (inside ClassFeatureAdmin)
    def get_fieldsets(self, request, obj=None):
        base = [
            (None, {"fields": [
                "character_class","scope","kind","gain_subskills","activity_type",
                "action_type","subclass_group","subclasses",
                "code","name","description","has_options",
                "tier","mastery_rank","level_required",
                "spell_list",
                "cantrips_formula","spells_known_formula","spells_prepared_formula",
            ]}),
            ("Saving Throw (optional)", { "fields": [
                "saving_throw_required","saving_throw_type","saving_throw_granularity",
                "saving_throw_basic_success","saving_throw_basic_failure",
                "saving_throw_critical_success","saving_throw_success",
                "saving_throw_failure","saving_throw_critical_failure",
            ]}),
            ("Damage / Formula (optional)", { "fields": ["formula_target","damage_type","formula","uses"]}),            ("Resistance (optional)", { "fields": [
                "gain_resistance_mode","gain_resistance_types","gain_resistance_amount",
            ]}),

            # ── Section A: Gain/Modify (generic) ─────────────────────────
("Gain/Modify Proficiency (generic)", { "fields": [
    "gmp_mode",                       # (uptier | set)
    "modify_proficiency_target",      # multi-select (core + skills + sub-skills)
    "modify_proficiency_amount",      # used when gmp_mode = set

    # ↓↓↓ NEW ↓↓↓
    "target_grant_mode",              # Grant all vs. Present choices
    "target_choice_count",            # N, when presenting choices
]}),

            # ── Section B: Add Core Proficiency (armor & weapons only) ───
            ("Add Core Proficiency (armor/weapons only)", { "fields": [
                "prof_target_kind",
                "armor_group_choice", "weapon_group_choice",
                "armor_item_choice",  "weapon_item_choice",
                "prof_change_mode",                 # (progress | set)
                "gain_proficiency_amount",          # used when progress
             
            ]}),


            ("Martial Mastery (optional)", {
                "fields": ["martial_points_formula","available_masteries_formula"]
            }),
        ]
        return base


        # NEW — show the proficiency UI and the tier to grant when in “progress” mode
    all_inlines = (FeatureOptionInline, SpellInline, SpellSlotRowInline)
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(racialfeature__isnull=True)


    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # Force a <select> for modify_proficiency_target even though the model is CharField
        if db_field.name == "modify_proficiency_target":
            # nice, opt-grouped choices (Core / Skills / Sub-skills)
            choices = build_proficiency_target_choices()

            field = CSVMultipleChoiceField(
                choices=choices,
                required=False,
                widget=FilteredSelectMultiple("proficiency targets", is_stacked=False),
                label=db_field.verbose_name,
                help_text="Select one or more (core proficiencies, skills, sub-skills).",
            )
            return field

        if db_field.name == "gain_proficiency_target":
            # keep your existing single-select (hidden by the form)
            return forms.ChoiceField(
                choices=[("", "---------")] + build_proficiency_target_choices(),
                required=not db_field.blank,
                widget=forms.Select,
                label=db_field.verbose_name,
                help_text=db_field.help_text,
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if obj.kind == "spell_table" and not SpellSlotRow.objects.filter(feature=obj).exists():
            SpellSlotRow.objects.bulk_create(
                [SpellSlotRow(feature=obj, level=i) for i in range(1, 21)]
            )
            # optional: confirm in UI
            self.message_user(request, "Seeded 20 spell slot rows.")




    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        # If ?scope=​… is in the URL, copy it into initial
        if "scope" in request.GET:
            initial["scope"] = request.GET["scope"]
        # If ?subclass_group=​… is in the URL, copy it into initial
        if "subclass_group" in request.GET:
            initial["subclass_group"] = request.GET["subclass_group"]
        return initial

# in ClassFeatureAdmin

    # inside ClassFeatureAdmin

    def _ensure_spell_rows(self, obj):
        if not obj:
            return
        if obj.kind == "spell_table" and not SpellSlotRow.objects.filter(feature=obj).exists():
            SpellSlotRow.objects.bulk_create(
                [SpellSlotRow(feature=obj, level=i) for i in range(1, 21)]
            )

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        # On GET of the change page, ensure rows exist so the inline actually renders
        if object_id:
            obj = self.get_object(request, object_id)
            self._ensure_spell_rows(obj)
        return super().changeform_view(request, object_id, form_url, extra_context)

    def get_inline_instances(self, request, obj=None):
        # Use the saved obj (not POST) to decide visibility.
        instances = [inline(self.model, self.admin_site) for inline in self.all_inlines]
        # If you want to remove some, do it based on obj.kind only:
        if obj:
            if obj.kind != "inherent_spell":
                instances = [i for i in instances if not isinstance(i, SpellInline)]
            if obj.kind != "spell_table":
                instances = [i for i in instances if not isinstance(i, SpellSlotRowInline)]
        # IMPORTANT: on add view (obj is None) don’t remove any; or redirect after save.
        return instances


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
    # in ClassFeatureAdmin
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)

        if db_field.name == "subclass_group":
            # figure out the selected id (POST → GET → existing obj)
            selected_id = None
            if request.method == "POST" and "subclass_group" in request.POST:
                selected_id = request.POST.get("subclass_group")
            if not selected_id:
                selected_id = request.GET.get("subclass_group")
            if not selected_id:
                try:
                    match = resolve(request.path_info)
                    obj_id = match.kwargs.get("object_id")
                    if obj_id:
                        cf = ClassFeature.objects.get(pk=obj_id)
                        selected_id = cf.subclass_group_id
                except Exception:
                    selected_id = None

            # always attach the full id → system_type map
            mapping = {str(g.pk): g.system_type for g in SubclassGroup.objects.all()}
            field.widget.attrs["data-group-types"] = json.dumps(mapping)

            # set current system_type (empty ok)
            system_t = ""
            if selected_id:
                try:
                    sg = SubclassGroup.objects.get(pk=selected_id)
                    system_t = sg.system_type or ""
                except SubclassGroup.DoesNotExist:
                    pass
            field.widget.attrs["data-system-type"] = system_t

        return field



    class Media:
        js = (
            'characters/js/formula_builder.js',
            'characters/js/classfeature_admin.js',
        )
        css = {
            'all': ('characters/css/formula_builder.css','characters/css/ClassFeatureAdmin.css')
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
    form = CharacterClassBaseProfForm
    list_display      = (
        "name", "hit_die", "class_ID", "display_key_abilities",
        "secondary_thumbnail", "tertiary_thumbnail"
    )
    search_fields     = ("name", "tags__name")
    list_filter       = ("tags", "key_abilities")
    filter_horizontal = ("tags", "key_abilities")  # use horizontal filter for the M2M

    inlines = [
        ClassProficiencyProgressInline,  # existing prof-progression rows
        ClassSkillPointGrantInline,      # NEW: per-level skill points
        ClassSkillFeatGrantInline,       # NEW: per-level skill feat grants
        SubclassGroupInline, 
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
                "starting_skills_formula",
         "armor_proficiencies", "weapon_proficiencies",
         "armor_items_baseline","weapon_items_baseline",
        # … any other existing CharacterClass fields …
    )
    readonly_fields = ("primary_preview", "secondary_preview", "tertiary_preview")
    def get_form(self, request, obj=None, **kwargs):
        Base = super().get_form(request, obj, **kwargs)

        class DebugForm(Base):
            def is_valid(self):
                ok = super().is_valid()
                if not ok:
                    print(">>> CharacterClass FORM errors:", self.errors.as_data())
                return ok

        return DebugForm
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if getattr(form, "_needs_baseline_sync", False):
            form.sync_baseline_prof_progress(form.instance)


    def get_inline_instances(self, request, obj=None):
        # also wrap each inline formset to log their errors
        inlines = super().get_inline_instances(request, obj)
        for inline in inlines:
            base_get_formset = inline.get_formset

            def _wrap(base):
                def wrapped_get_formset(request_, obj_=None, **kw):
                    FS = base(request_, obj_, **kw)
                    class DebugFS(FS):
                        def is_valid(self):
                            ok = super().is_valid()
                            if not ok:
                                print(f">>> {self.model.__name__} INLINE non-form:",
                                    self.non_form_errors().as_data())
                                for f in self.forms:
                                    if f.errors:
                                        print("   - row errors:", f.errors.as_data())
                            return ok
                    return DebugFS
                return wrapped_get_formset

            inline.get_formset = _wrap(base_get_formset)
        return inlines
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
    def save_model(self, request, obj, form, change):
        if form.errors:
            print(">>> CharacterClass form errors:", form.errors.as_data())
        return super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        if formset.total_error_count():
            print(f">>> {formset.model.__name__} non-form errors:",
                  formset.non_form_errors().as_data())
            for f in formset.forms:
                if f.errors:
                    print("   - row errors:", f.errors.as_data())
        return super().save_formset(request, form, formset, change)
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


    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # record that we need to sync L1 baseline prof rows after m2m/save_related
        if hasattr(form, "_needs_baseline_sync"):
            obj._needs_baseline_sync = True

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        skip = set()
        for fs in formsets:
            if getattr(fs, "model", None) is ClassProficiencyProgress:
                for f in fs.forms:
                    cd = getattr(f, "cleaned_data", None) or {}
                    if not cd.get("DELETE"):
                        continue

                    # Only baseline rows can be resurrected by the sync
                    lvl = cd.get("at_level", getattr(f.instance, "at_level", None))
                    if lvl != 1:
                        continue

                    pt = cd.get("proficiency_type", getattr(f.instance, "proficiency_type", None))

                    if pt == "armor":
                        grp = cd.get("armor_group", getattr(f.instance, "armor_group", None))
                        itm = cd.get("armor_item",  getattr(f.instance, "armor_item",  None))
                        if grp:
                            skip.add(("armor_group", grp))
                        if itm:
                            skip.add(("armor_item", itm.pk if hasattr(itm, "pk") else itm))

                    elif pt == "weapon":
                        grp = cd.get("weapon_group", getattr(f.instance, "weapon_group", None))
                        itm = cd.get("weapon_item",  getattr(f.instance, "weapon_item",  None))
                        if grp:
                            skip.add(("weapon_group", grp))
                        if itm:
                            skip.add(("weapon_item", itm.pk if hasattr(itm, "pk") else itm))

        inst = form.instance
        if getattr(inst, "_needs_baseline_sync", False):
            form.sync_baseline_prof_progress(inst, skip_tokens=frozenset(skip))
            delattr(inst, "_needs_baseline_sync")

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
    # RaceFeatureForm (add fields)
    CORE_MODE = (("uptier", "Increase tier by one"), ("set", "Gain amount to override"))
    core_skill_change_mode = forms.ChoiceField(
        choices=CORE_MODE, required=False, widget=forms.RadioSelect,
        label="Core skill mode",
        help_text="Pick one: Increase tier by one (+1) or set to a fixed tier."
    )
    core_skill_choice = forms.ModelChoiceField(
        queryset=Skill.objects.all(), required=False, label="Core Skill"
    )
    core_skill_amount = forms.ModelChoiceField(
        queryset=ProficiencyTier.objects.all(), required=False,
        label="Amount (if overriding)"
    )

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
        # bypass ClassFeatureForm.__init__
        forms.ModelForm.__init__(self, *args, **kwargs)

        # remove class-only fields (keep your existing pops)
        for f in ("character_class", "subclass_group", "subclasses", "tier", "mastery_rank"):
            self.fields.pop(f, None)

        # ⬅️ NEW: inert placeholder so add_error('subclass_group', ...) never ValueErrors
        self.fields["subclass_group"] = forms.CharField(
            required=False,
            widget=forms.HiddenInput(),
            label="(unused placeholder)",
        )

        # limit subrace to selected race (keep your existing code)
        race_val = (
            self.data.get("race")
            or self.initial.get("race")
            or getattr(self.instance, "race_id", None)
        )
        if "subrace" in self.fields:
            self.fields["subrace"].queryset = (
                Subrace.objects.filter(race_id=race_val) if race_val else Subrace.objects.none()
            )

        if getattr(self.instance, "pk", None):
            self.fields["code"].initial = self.instance.code

    def clean(self):
        cleaned = forms.ModelForm.clean(self)

        if cleaned.get("scope") == "subclass_feat" and not cleaned.get("subrace"):
            self.add_error("subrace", "Please select a Subrace for a Subrace Feature.")

        # ---- silent parse of proficiency target (no add_error calls) ----
        kind = (self.cleaned_data.get("prof_target_kind") or "").strip()
        targets = []

        if kind == "armor_group":
            grp = self.cleaned_data.get("armor_group_choice")
            if grp:
                targets = [f"armor:{grp}"]
        elif kind == "weapon_group":
            grp = self.cleaned_data.get("weapon_group_choice")
            if grp:
                targets = [f"weapon:{grp}"]
        elif kind == "armor_item":
            items = list(self.cleaned_data.get("armor_item_choice") or [])
            if items:
                targets = [f"armor#{i.pk}" for i in items]
        elif kind == "weapon_item":
            items = list(self.cleaned_data.get("weapon_item_choice") or [])
            if items:
                targets = [f"weapon#{i.pk}" for i in items]

        existing_mod = self.cleaned_data.get("modify_proficiency_target") or ""
        if isinstance(existing_mod, (list, tuple)):
            existing_mod = ",".join(filter(None, existing_mod))

        # If armor/weapon picker was used, append those tokens; otherwise keep whatever was selected
        if targets:
            merged = [t.strip() for t in (existing_mod.split(",") if existing_mod else []) if t.strip()]
            merged.extend(targets)
            self.cleaned_data["modify_proficiency_target"] = ",".join(sorted(set(merged)))
        else:
            self.cleaned_data["modify_proficiency_target"] = existing_mod

        # Clear any 'gain' since races do not advance class progression
        self.cleaned_data["gain_proficiency_target"] = ""
        self.cleaned_data["gain_proficiency_amount"] = None

        # ── Generic Gain/Modify (same two choices as class) ──
        gmp_mode = (self.cleaned_data.get("gmp_mode") or "").strip()
        if gmp_mode:
            # When using generic section, amount only matters for "set"
            if gmp_mode == "uptier":
                self.cleaned_data["modify_proficiency_amount"] = None
            # if "set", keep whatever amount the author selected
            if gmp_mode == "set" and not self.cleaned_data.get("modify_proficiency_amount"):
                self.add_error("modify_proficiency_amount", "Pick the proficiency tier to set.")
        # ── Core Skill helper (same two choices), maps into modify_* as well ──
        core_mode = (self.cleaned_data.get("core_skill_change_mode") or "").strip()
        core_skill = self.cleaned_data.get("core_skill_choice")
        core_amount = self.cleaned_data.get("core_skill_amount")

        if core_mode and core_skill:
            tok = f"skill_{core_skill.pk}"
            merged = [t.strip() for t in (self.cleaned_data.get("modify_proficiency_target") or "").split(",") if t.strip()]
            merged.append(tok)
            self.cleaned_data["modify_proficiency_target"] = ",".join(sorted(set(merged)))
            if core_mode == "uptier":
                self.cleaned_data["modify_proficiency_amount"] = None
            else:
                self.cleaned_data["modify_proficiency_amount"] = core_amount

        return cleaned



    def add_error(self, field, error):
        if field == "subclass_group":
            scope = (self.data.get("scope") or self.cleaned_data.get("scope") or "").strip()
            if scope == "subclass_feat" and "subrace" in self.fields:
                return super().add_error("subrace", "Please select a Subrace for a Subrace Feature.")
            return super().add_error(None, error)
        return super().add_error(field, error)

@admin.register(RacialFeature)
class RacialFeatureAdmin(SummernoteModelAdmin):
    form = RaceFeatureForm
    inlines = [RaceFeatureOptionInline]
    exclude = ("character_class", "subclasses")
    search_fields = ("name", "code", "race__name", "subrace__name", "description")
    fieldsets = [
        (None, {
            "fields": [
                "race","subrace","scope","kind","gain_subskills",
                "code","name","description","has_options",
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

("Gain/Modify Proficiency (generic)", {
    "fields": [
        "gmp_mode",                  # Increase tier by one | Gain amount to override
        "modify_proficiency_target", # now a multi-select incl. all Skills
        "modify_proficiency_amount", # used only when 'Gain amount to override'
    ],
}),
("Core Skill Proficiency", {
    "fields": [
        "core_skill_change_mode",    # Increase tier by one | Gain amount to override
        "core_skill_choice",         # pick a Skill
        "core_skill_amount",         # used only when overriding
    ],
}),
("Armor/Weapon Proficiency (core)", {
    "fields": [
        "prof_change_mode",          # progress | set  (kept for armor/weapon)
        "prof_target_kind",
        "armor_group_choice", "weapon_group_choice",
        "armor_item_choice",  "weapon_item_choice",
        "gain_proficiency_amount",   # used only when progress
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
    
    def get_form(self, request, obj=None, **kwargs):
        BaseForm = super().get_form(request, obj, **kwargs)
        race_pk = (
            request.POST.get("race")
            or request.GET.get("race")
            or (getattr(obj, "race_id", None) if obj else None)
        )

        class WrappedForm(BaseForm):
            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)
                if "subrace" in self.fields:
                    if race_pk:
                        self.fields["subrace"].queryset = Subrace.objects.filter(race_id=race_pk)
                        self.fields["subrace"].widget.attrs.pop("disabled", None)
                    else:
                        self.fields["subrace"].queryset = Subrace.objects.none()
                        self.fields["subrace"].help_text = "Pick a Race; the page will refresh to load subraces."

            # ⬅️ make remap unconditional
            def add_error(self, field, error):
                if field == "subclass_group":
                    scope = (self.data.get("scope") or getattr(self, "cleaned_data", {}).get("scope") or "").strip()
                    if scope == "subclass_feat" and "subrace" in self.fields:
                        return super().add_error("subrace", "Please select a Subrace for a Subrace Feature.")
                    return super().add_error(None, error)
                return super().add_error(field, error)

        return WrappedForm


    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # Force a <select> for modify_proficiency_target even though the model is CharField
        if db_field.name == "modify_proficiency_target":

            # 1) build the combined list: base prof types + all Skill names
            base = list(PROFICIENCY_TYPES)
            skill_choices = [(f"skill_{s.pk}", s.name) for s in Skill.objects.all()]
            all_choices = [("", "---------")] + base + skill_choices

            # 2) return a ChoiceField (renders as <select>) instead of default TextInput
            choices = build_proficiency_target_choices()
            return CSVMultipleChoiceField(
                choices=choices,
                required=False,
                widget=FilteredSelectMultiple("proficiency targets", is_stacked=False),
                label=db_field.verbose_name,
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
            js = ["characters/js/formula_builder.js", "characters/js/racialfeature_admin.js",  ],
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
    gain_resistance_types = forms.MultipleChoiceField(
        choices=ClassFeature.DAMAGE_TYPE_CHOICES,  # reuse the same list
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Resistance applies to",
    )
    gain_resistance_amount = forms.IntegerField(
        required=False,
        min_value=0,
        label="Flat reduction amount",
    )

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
            "gain_resistance_mode", "gain_resistance_types", "gain_resistance_amount",  # ← add
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
        (None, {"fields": [
            "name","active",
            "formula_target","formula","uses","action_type","damage_type",
            "saving_throw_required","saving_throw_type","saving_throw_granularity",
            "saving_throw_basic_success","saving_throw_basic_failure",
            "saving_throw_critical_success","saving_throw_success",
            "saving_throw_failure","saving_throw_critical_failure",
            "modify_proficiency_target","modify_proficiency_amount",
            "gain_resistance_mode","gain_resistance_types","gain_resistance_amount",
            "description",
        ]}),
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



# ──────────────────────────────────────────────────────────────────────────────
# Prestige Admin
# ──────────────────────────────────────────────────────────────────────────────

class PrestigeLevelChoiceInline(admin.TabularInline):
    model = CharacterPrestigeLevelChoice
    extra = 0
    fields = ("prestige_level", "counts_as")
    autocomplete_fields = ("counts_as",)
    ordering = ("prestige_level",)


@admin.register(CharacterPrestigeEnrollment)
class CharacterPrestigeEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("character", "prestige_class", "entered_at_character_level", "gm_approved")
    list_filter = ("gm_approved", "prestige_class")
    search_fields = ("character__name", "prestige_class__name")
    inlines = [PrestigeLevelChoiceInline]


@admin.register(CharacterPrestigeLevelChoice)
class CharacterPrestigeLevelChoiceAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "prestige_level", "counts_as")
    list_filter = ("prestige_level", "counts_as")
    autocomplete_fields = ("enrollment", "counts_as")



class PrestigePrereqInlineForm(forms.ModelForm):
    class Meta:
        model = PrestigePrerequisite
        fields = "__all__"

    def clean(self):
        cd = super().clean()
        # mirror model.clean() errors with friendlier messages if needed
        return cd


class PrestigePrereqInline(admin.TabularInline):
    model = PrestigePrerequisite
    form = PrestigePrereqInlineForm
    extra = 0
    fields = (
        "group_index", "intragroup_operator", "kind",
        "target_class", "min_class_level",
        "skill", "min_tier",
        "race", "subrace",
        "class_tag",
        "race_tag" if hasattr(PrestigePrerequisite, "race_tag") else None,
        "feat_code",
    )
    fields = tuple(f for f in fields if f)  # strip None when RaceTag absent
    ordering = ("group_index", "id")
from django.contrib import admin
from characters.models import (
    PrestigeClass, PrestigePrerequisite, PrestigeLevel, PrestigeFeature,
    CharacterPrestigeEnrollment, CharacterPrestigeLevelChoice
)

class PrestigePrerequisiteInline(admin.StackedInline):
    model = PrestigePrerequisite
    extra = 0
    ordering = ("group_index", "id")
    autocomplete_fields = ("target_class","skill","race","subrace","class_tag","min_tier")
    radio_fields = {"intragroup_operator": admin.HORIZONTAL, "kind": admin.VERTICAL}
    fieldsets = (
        (None, {"fields": ("group_index", "intragroup_operator", "kind")}),
        ("Class level", {"fields": ("target_class", "min_class_level"), "classes": ("collapse",)}),
        ("Skill tier",  {"fields": ("skill", "min_tier"), "classes": ("collapse",)}),
        ("Race / Subrace", {"fields": ("race", "subrace"), "classes": ("collapse",)}),
        ("Tags / Feat code", {"fields": ("class_tag", "feat_code"), "classes": ("collapse",)}),
    )

class PrestigeLevelInline(admin.TabularInline):
    model = PrestigeLevel
    extra = 0
    autocomplete_fields = ("fixed_counts_as",)
    filter_horizontal = ("allowed_counts_as",)
    radio_fields = {"counts_as_mode": admin.HORIZONTAL}
    fields = ("level","counts_as_mode","fixed_counts_as","allowed_counts_as")

class PrestigeFeatureInline(admin.StackedInline):
    model = PrestigeFeature
    extra = 0
    fields = ("at_prestige_level","code","name","description","grants_class_feature")
@admin.action(description="Create prestige levels 1–5 (choose mode)")
def create_default_prestige_levels(modeladmin, request, queryset):
    for pc in queryset:
        for i in range(1, 6):
            PrestigeLevel.objects.get_or_create(
                prestige_class=pc,
                level=i,
                defaults={"counts_as_mode": PrestigeLevel.MODE_CHOOSE},
            )

@admin.register(PrestigeClass)
class PrestigeClassAdmin(admin.ModelAdmin):
    list_display = ("name","min_entry_level","requires_gm_approval")
    list_filter  = ("requires_gm_approval",)
    search_fields = ("name",)
    readonly_fields = ("min_entry_level",)
    actions = [create_default_prestige_levels]

    fieldsets = (
        (None, {"fields": ("name","code","description")}),
        ("Entry & Limits", {"fields": ("min_entry_level","requires_gm_approval")}),
    )
    inlines = [PrestigePrerequisiteInline, PrestigeLevelInline, PrestigeFeatureInline]
    prepopulated_fields = {"code": ("name",)}




