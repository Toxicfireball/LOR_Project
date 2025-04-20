from django.contrib import admin
from django import forms

from characters.models import (
    Character,
    CharacterClass,
    ProficiencyTier,
    ClassProficiencyProgress,
    CharacterClassProgress,
    ClassFeature,
    FeatureOption,
    ClassLevel,
    ClassLevelFeature,
)

# define dice (and maybe your vars) at module level
DICE = ["d4","d6","d8","d10","d12","d20"]
VARS  = [
    "level", "class_level", "proficiency_modifier",
    "hp", "temp_hp",
] + [f"{cls.name.lower()}_level" for cls in CharacterClass.objects.all()] \
  + [
    "reflex_save","fortitude_save","will_save",
    "initiative","weapon_attack","spell_attack","spell_dc",
    "perception","dodge",
]
# ─── Inlines ────────────────────────────────────────────────────────────────────

class ClassProficiencyProgressInline(admin.TabularInline):
    model = ClassProficiencyProgress
    extra = 1
    fields = ('proficiency_type', 'at_level', 'tier')


class CharacterClassProgressInline(admin.TabularInline):
    model  = CharacterClassProgress
    extra  = 1
    fields = ('character_class', 'levels')





class ClassLevelFeatureInline(admin.TabularInline):
    model  = ClassLevelFeature
    extra  = 1
    fields = ('feature', 'chosen_option')


# ─── ModelAdmin registrations ─────────────────────────────────────────────────

@admin.register(CharacterClass)
class CharacterClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'hit_die', "class_ID")
    inlines      = (ClassProficiencyProgressInline,)


@admin.register(ProficiencyTier)
class ProficiencyTierAdmin(admin.ModelAdmin):
    list_display = ('name', 'bonus')


@admin.register(ClassLevel)
class ClassLevelAdmin(admin.ModelAdmin):
    list_display = ('character_class', 'level')
    list_filter  = ('character_class',)
    inlines      = (ClassLevelFeatureInline,)


# characters/admin.py
from django.contrib import admin
from characters.models import ClassFeature, FeatureOption, CharacterClass
from characters.widgets import FormulaBuilderWidget, CharacterClassSelect
from django import forms




class FeatureOptionInline(admin.TabularInline):
    model   = FeatureOption
    fk_name = "feature"      # ← point at the field on FeatureOption that links to ClassFeature
    extra   = 1
    verbose_name = "Feature option"
    verbose_name_plural = "Feature options"
class ClassFeatureForm(forms.ModelForm):
    class Meta:
        model  = ClassFeature
        fields = "__all__"   # ← render every field on the model
        widgets = {
            # just override the bits you want:
            "character_class": CharacterClassSelect(),
            "description":     forms.Textarea(attrs={"rows":4, "cols":40}),
            "formula":         FormulaBuilderWidget(variables=VARS, dice=DICE, attrs={"cols":40,"rows":4}),
            "uses":            FormulaBuilderWidget(variables=VARS, dice=DICE, attrs={"cols":40,"rows":4}),
        }

    def clean(self):
        cleaned = super().clean()
        ft   = cleaned.get("feat_type")
        code = cleaned.get("code")

        # use the literal key 'class', not a missing constant
        if ft == 'class' and not code:
            self.add_error("code", "Class‑granted features must have a code.")
        return cleaned



    
@admin.register(ClassFeature)
class ClassFeatureAdmin(admin.ModelAdmin):
    form    = ClassFeatureForm
    
    inlines = [FeatureOptionInline]
    list_display = (
      "character_class",
      "code",
      "name",
              'feat_type',
      "formula_target",
      "has_options",
      "formula",
      "uses",
    )

    class Media:
        js  = [
          "characters/js/formula_builder.js",
          "characters/js/classfeature_admin.js",
        ]
        css = {"all": ("characters/css/formula_builder.css",)}