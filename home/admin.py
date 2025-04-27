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
)

from django.contrib.admin.widgets import FilteredSelectMultiple
from characters.widgets import FormulaBuilderWidget, CharacterClassSelect

# characters/admin.py  – only the SubclassGroupForm bits

# characters/admin.py
# characters/admin.py  (only SubclassGroupForm changes)
class SubclassGroupForm(forms.ModelForm):
    subclasses = forms.ModelMultipleChoiceField(
        queryset = ClassSubclass.objects.none(),
        required = False,
        widget   = FilteredSelectMultiple("subclasses", is_stacked=False),
        help_text = "Move → to adopt subclasses into this umbrella.",
    )

    class Meta:
        model  = SubclassGroup
        fields = ("character_class", "name", "code", "system_type")

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        # which class drives the queryset?
        cls = (self.instance.character_class if self.instance.pk
               else CharacterClass.objects.filter(
                        pk=self.data.get("character_class") or
                           self.initial.get("character_class")
                    ).first())

        if cls:
            qs = ClassSubclass.objects.filter(base_class=cls)
            self.fields["subclasses"].queryset = qs
            if self.instance.pk:
                self.fields["subclasses"].initial = self.instance.subclasses.all()


class ClassProficiencyProgressInline(admin.TabularInline):
    model  = ClassProficiencyProgress
    extra  = 1
    fields = ('proficiency_type', 'at_level', 'tier')







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


@admin.register(ClassSubclass)
class ClassSubclassAdmin(admin.ModelAdmin):
    list_display  = ("base_class", "name", "group", "system_type", "code")
    list_filter   = ("base_class", "group", "group__system_type")
    search_fields = ("name", "code")
    list_editable = ("group",)
    def get_system_type(self, obj):
        return getattr(obj.group, "system_type", "—")
    
    # ── filters ───────────────────────────────────────────
    list_filter  = (
        "base_class",
        ("group__system_type", admin.ChoicesFieldListFilter),  # filter by umbrella’s type
        "group",
    )

    search_fields = ("name", "code")
    list_editable = ("group",)   
class SubclassGroupInline(admin.TabularInline):
    model  = SubclassGroup
    extra  = 1
    fields = ("name", "code", "system_type")   # ← added
# ─── CharacterClass, Tiers & Levels ─────────────────────────────────────────────

@admin.register(CharacterClass)
class CharacterClassAdmin(admin.ModelAdmin):
    list_display      = ('name', 'hit_die', 'class_ID')
    search_fields     = ('name', 'tags__name')
    list_filter       = ('tags',)
    inlines = (
        ClassProficiencyProgressInline,
        SubclassGroupInline,     # <- newly added
    )

    filter_horizontal = ('tags',)


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

class ClassFeatureForm(forms.ModelForm):
    class Meta:
        model  = ClassFeature
        fields = "__all__"
        
        widgets = {
            "character_class": CharacterClassSelect(),
            "formula":         FormulaBuilderWidget(variables=VARS, dice=DICE, attrs={"rows":4,"cols":40}),
            "uses":            FormulaBuilderWidget(variables=VARS, dice=DICE, attrs={"rows":4,"cols":40}),
        }


    def clean(self):
        cleaned = super().clean()
        ft  = cleaned.get('feature_type')
        grp = cleaned.get('subclass_group')

        # when this feature is “subclass_feat”, require exactly one umbrella
        if ft == 'subclass_feat':
            if not grp:
                self.add_error(
                    'subclass_group',
                    "Pick one subclass-umbrella for Subclass-type features."
                )
        else:
            if grp:
                self.add_error(
                    'subclass_group',
                    "Only Subclass-type features may set a subclass-umbrella."
                )

        return cleaned
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        # dynamic queryset: when you pick a class, limit umbrellas + subclasses
        cc = self.initial.get("character_class") or getattr(self.instance, "character_class_id", None)
        if cc:
            self.fields["subclass_group"].queryset = SubclassGroup.objects.filter(character_class_id=cc)
            self.fields["subclasses"].queryset     = ClassSubclass.objects.filter(group__character_class_id=cc)
        else:
            self.fields["subclass_group"].queryset = SubclassGroup.objects.none()
            self.fields["subclasses"].queryset     = ClassSubclass.objects.none()

@admin.register(ClassFeature)
class ClassFeatureAdmin(admin.ModelAdmin):
    form         = ClassFeatureForm
    inlines      = [FeatureOptionInline]
    list_display = (
        'character_class',
        'feature_type',
        'subclass_group',
        'code',
        'name',
        'formula_target',
        'has_options',
        'formula',
        'uses',
    )
    list_filter = (
        'character_class',
        'feature_type',
        'subclass_group',
    )
  
    class Media:
        js  = (
            "characters/js/formula_builder.js",
            "characters/js/classfeature_admin.js",
        )
        css = {"all": ("characters/css/formula_builder.css",)}


    def subclass_list(self, obj):
        return ", ".join(
            obj.subclasses
               .order_by('name')
               .values_list('name', flat=True)
        )
    subclass_list.short_description = "Subclasses"




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