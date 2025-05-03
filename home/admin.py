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
    ResourceType, ClassResource, CharacterResource
)

from django.contrib.admin.widgets import FilteredSelectMultiple
from characters.widgets import FormulaBuilderWidget, CharacterClassSelect
from characters.models import ResourceType, ClassResource, CharacterResource

from django.shortcuts import get_object_or_404

class SubclassGroupForm(forms.ModelForm):
    """
    Form for editing SubclassGroup in the admin.
    """
    subclasses = forms.ModelMultipleChoiceField(
        queryset=ClassSubclass.objects.none(),
        required=False,
        widget=FilteredSelectMultiple("subclasses", is_stacked=True),
        help_text="Move → to adopt subclasses into this umbrella."
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
                self.fields["subclasses"].initial = self.instance.subclasses.all()

        # apply sizing to the widget so it’s not postage-stamp
        w = self.fields["subclasses"].widget
        w.attrs["style"] = "width:30em; height:15em;"
        w.attrs["size"] = 10

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


class ClassLevelFeatureInline(admin.TabularInline):
    model  = ClassLevelFeature
    extra  = 1
    fields = ('feature', 'chosen_option')


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


@admin.register(ClassLevel)
class ClassLevelAdmin(admin.ModelAdmin):
    list_display   = ('character_class', 'level')
    list_filter    = ('character_class',)
    inlines        = (ClassLevelFeatureInline,)


# ─── ClassFeature ────────────────────────────────────────────────────────────────

DICE = ["d4","d6","d8","d10","d12","d20"]
VARS = [
    "level", "class_level", "proficiency_modifier",
    "hp", "temp_hp",
] + [f"{cls.name.lower()}_level" for cls in CharacterClass.objects.all()] + [
    "reflex_save","fortitude_save","will_save",
    "initiative","weapon_attack","spell_attack","spell_dc",
    "perception","dodge",
]
class ClassResourceForm(forms.ModelForm):
    class Meta:
        model = ClassResource
        fields = ("resource_type", "formula")
        widgets = {
            "formula": FormulaBuilderWidget(
                variables=VARS + [f"{rt.code}_points" for rt in ResourceType.objects.all()],
                dice=DICE,
                attrs={"rows":2, "cols":40},
            )
        }

class ClassFeatureForm(forms.ModelForm):
    class Meta:
        model  = ClassFeature
        fields = "__all__"
        labels = {
            "character_class": "Applies To Class",
            "feature_type":    "Feature Category",
            "activity_type":  "Active / Passive",
            "subclass_group":  "Umbrella (if subclass-related)",
            "subclasses":      "Which Subclasses",
            "code":            "Unique Code",
            "name":            "Feature Name",
            "description":     "Description / Fluff",
            "has_options":     "Has Options?",
            "formula":         "Dice Formula",
            "uses":            "Usage Frequency",
            "formula_target":  "Roll Type",
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
            "subclass_group":  (
                "If this is a subclass_choice or subclass_feat, pick the umbrella here."
            ),
            "subclasses":      (
                "For subclass_feat only: which subclasses receive it?"
            ),
            "code":            "Short identifier used in formulas and JSON.",
            "name":            "Human-readable name shown to players.",
            "has_options":     "Check to add FeatureOption inlines below.",
            "formula":         "Dice+attribute expression, e.g. '1d10+level'.",
            "uses":            "How many times? e.g. 'level/3 round down +1'.",
            "formula_target":  "What kind of roll this formula applies to.",
        }
        widgets = {
            "character_class": CharacterClassSelect(),
            "formula":         FormulaBuilderWidget(variables=VARS, dice=DICE, attrs={"rows":4,"cols":40}),
            "uses":            FormulaBuilderWidget(variables=VARS, dice=DICE, attrs={"rows":4,"cols":40}),
            "cantrips_formula":    FormulaBuilderWidget(variables=VARS, dice=DICE, attrs={"rows":2,"cols":40}),
            "spells_known_formula": FormulaBuilderWidget(variables=VARS, dice=DICE, attrs={"rows":2,"cols":40}),
            "subclasses": FilteredSelectMultiple("Subclasses", is_stacked=True),

        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 1) build the “static” variable list you already have:
        from characters.models import CharacterClass
        DICE = ["d4","d6","d8","d10","d12","d20"]
        base_vars = [
            "level", "class_level", "proficiency_modifier",
            "hp", "temp_hp",
        ] + [f"{cls.name.lower()}_level"
            for cls in CharacterClass.objects.all()
        ] + [
            "reflex_save","fortitude_save","will_save",
            "initiative","weapon_attack","spell_attack","spell_dc",
            "perception","dodge",
        ]

        # 2) only the resources defined on *this* class:
        from characters.models import ClassResource
        # try POST (new) or existing instance
        cls_id = self.data.get("character_class") or getattr(self.instance, "character_class_id", None)
        if cls_id:
            resource_qs = ClassResource.objects.filter(character_class_id=cls_id)
            resource_vars = [f"{cr.resource_type.code}_points" for cr in resource_qs]
        else:
            resource_vars = []
        
        all_vars = base_vars + resource_vars
        # 3) reassign your FormulaBuilderWidgets:
        self.fields["formula"].widget = FormulaBuilderWidget(
            variables=all_vars,
            dice=DICE,
            attrs={"rows":4, "cols":40}
        )
        self.fields["uses"].widget = FormulaBuilderWidget(
            variables=all_vars,
            dice=DICE,
            attrs={"rows":4, "cols":40}
        )

        # chain subclasses → based on subclass_group, or fallback to class
        if "subclasses" in self.fields:
            group_id = self.data.get("subclass_group") or getattr(
                self.instance, "subclass_group_id", None
            )
            if group_id:
                qs = ClassSubclass.objects.filter(group_id=group_id)
            else:
                cls_id = self.data.get("character_class") or getattr(
                    self.instance, "character_class_id", None
                )
                qs = ClassSubclass.objects.filter(base_class_id=cls_id) if cls_id else ClassSubclass.objects.none()
            self.fields["subclasses"].queryset = qs
            w = self.fields["subclasses"].widget
            w.attrs.update({"style": "width:30em; height:15em;", "size": 10})


    def clean(self):
        cleaned = super().clean()
        ft = self.data.get("feature_type") or getattr(self.instance, "feature_type", None)        
        grp = cleaned.get("subclass_group")

        # enforce modular_mastery rules entirely from JSON
        if ft == "subclass_feat" and grp and grp.system_type == SubclassGroup.SYSTEM_MODULAR_MASTERY:
            rules       = grp.modular_rules or {}
            per_mastery = rules.get("modules_per_mastery", 2)
            max_m3      = rules.get("max_mastery_3", 1)

            total_modules = ClassFeature.objects.filter(
                feature_type="subclass_choice",
                subclass_group=grp
            ).count()

            # extract level from code suffix: master_<n>
            try:
                my_level = int(cleaned["code"].rsplit("_",1)[1])
            except Exception:
                raise forms.ValidationError(
                    "Mastery codes must end in “_1”, “_2” or “_3”."
                )

            # must have enough modules to unlock this mastery
            if my_level > (total_modules // per_mastery):
                raise forms.ValidationError(
                    f"{per_mastery*my_level} modules required for Mastery {my_level}."
                )

            # limit number of Mastery-3 features
            if my_level == 3:
                existing_m3 = ClassFeature.objects.filter(
                    feature_type="subclass_feat",
                    subclass_group=grp,
                    code__endswith="_3"
                ).count()
                if existing_m3 >= max_m3:
                    raise forms.ValidationError(
                        f"Only {max_m3} Mastery 3 features allowed here."
                    )

        # ensure only subclass-feat may set subclass_group
        if ft == 'subclass_feat' and not grp:
            self.add_error('subclass_group',
                           "Pick an umbrella for subclass_feat features.")
        if ft != 'subclass_feat' and grp:
            self.add_error('subclass_group',
                           "Only subclass_feat may set a subclass-umbrella.")

        return cleaned


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
    form         = ClassFeatureForm
    inlines      = [FeatureOptionInline, SpellSlotRowInline]
    list_display = (
        'character_class','feature_type','subclass_group',
        'code','name','formula_target','has_options',
        'formula','uses',
    )
    list_filter  = ('character_class','feature_type','subclass_group',)
    autocomplete_fields = ('subclasses',)
    # 1) our core fields (must include subclasses!)

    base_fields = [
        "character_class",
        "feature_type",
        "activity_type",
        "subclass_group",
        "subclasses",
        "code",
        "name",
        "description",
        "has_options",
        "formula_target",
        "formula",
        "uses",
        "cantrips_formula",
        "spells_known_formula",
         "modify_proficiency_target", "modify_proficiency_amount",
    ]
    def get_fieldsets(self, request, obj=None):
        # determine the feature_type (None on initial GET)
        if request.method == "POST":
            ft = request.POST.get("feature_type")
        elif obj:
            ft = obj.feature_type
        else:
            ft = None

        # start with all core fields (including "subclasses")
        fields = self.base_fields[:]

        # if it's actually a subclass_feat, move subclasses next to code
        if ft == "subclass_feat":
            # ensure it's present, then reposition
            if "subclasses" in fields:
                fields.remove("subclasses")
            fields.insert(fields.index("code"), "subclasses")

        # only show these formulas if it's a spell table
        if ft == "spell_table":
            fields += ["cantrips_formula", "spells_known_formula"]

        return [(None, {"fields": fields})]
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        Whenever Django renders the 'subclasses' m2m widget,
        filter its queryset to the selected subclass_group.
        """
        if db_field.name == "subclasses":
            # Try POST (on auto-submit) or GET (on reload)
            group_id = request.POST.get("subclass_group") or request.GET.get("subclass_group")
            if group_id:
                kwargs["queryset"] = ClassSubclass.objects.filter(group_id=group_id)
            else:
                kwargs["queryset"] = ClassSubclass.objects.none()
        return super().formfield_for_manytomany(db_field, request, **kwargs)
    def get_inline_instances(self, request, obj=None):
        """
        Only filter out the FeatureOptionInline on POST.
        On GET we always include it so the JS can hide/show it.
        """
        inline_instances = super().get_inline_instances(request, obj)

        if request.method == "POST":
            # checkbox values can come through as "on", "true", "1"
            has_opt = request.POST.get("has_options") in ("true", "on", "1")
            if not has_opt:
                inline_instances = [
                    inst for inst in inline_instances
                    if not isinstance(inst, FeatureOptionInline)
                ]

        return inline_instances


    class Media:
        js = (
            'characters/js/formula_builder.js',
            'characters/js/classfeature_admin.js',
        )
        css = {
            'all': ('characters/css/formula_builder.css',)
        }


    
class ClassResourceInline(admin.TabularInline):
    model = ClassResource
    form  = ClassResourceForm
    extra = 1
    fields = ("resource_type","formula")
    # no more max_points here!
@admin.register(CharacterClass)
class CharacterClassAdmin(admin.ModelAdmin):
    list_display      = ('name', 'hit_die', 'class_ID')
    search_fields     = ('name', 'tags__name')
    list_filter       = ('tags',)
    inlines = [
        ClassProficiencyProgressInline,
        SubclassGroupInline,
        ClassResourceInline,     # ← add this
    ]

    filter_horizontal = ('tags',)   
@admin.register(SubclassGroup)
class SubclassGroupAdmin(admin.ModelAdmin):
    form         = SubclassGroupForm
    list_display = ("character_class", "name", "code", "system_type")
    list_filter  = ("character_class",)
    inlines      = ()                       # none; widget handles membership

    def save_related(self, request, form, formsets, change):
        """
        Runs *after* the SubclassGroup has definitely been written,
        so `form.instance.pk` is always valid here.
        """
        super().save_related(request, form, formsets, change)

        grp         = form.instance
        chosen      = form.cleaned_data.get("subclasses") or []
        chosen_ids  = [s.pk for s in chosen]

        # link the selected subclasses …
        (ClassSubclass.objects
            .filter(pk__in=chosen_ids)
            .update(group=grp))

        # … and unlink every other subclass that *used* to belong
        (ClassSubclass.objects
            .filter(group=grp)
            .exclude(pk__in=chosen_ids)
            .update(group=None))