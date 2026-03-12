from django.contrib import admin
from .models import (
    EnemyCategory,
    EnemyTag,
    EnemyType,
    EnemyAbility,
    EnemyDamageResistance,
    Encounter,
    EncounterEnemy,
)


@admin.register(EnemyCategory)
class EnemyCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "description")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(EnemyTag)
class EnemyTagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


class EnemyAbilityInline(admin.StackedInline):
    model = EnemyAbility
    extra = 0
    fields = ("ability_type", "action_cost", "title", "description")


class EnemyDamageResistanceInline(admin.TabularInline):
    model = EnemyDamageResistance
    extra = 0
    fields = ("mode", "damage_type", "amount")


@admin.register(EnemyType)
class EnemyTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "kind",
        "category",
        "scope_display",
        "level",
        "hp",
        "armor",
        "dodge",
        "initiative",
        "created_at",
    )
    list_filter = (
        "kind",
        "category",
        "campaign",
        "can_cast_spells",
        "tags",
    )
    search_fields = ("name", "description", "resistances")
    filter_horizontal = ("tags", "spells", "martial_masteries")
    raw_id_fields = ("campaign",)
    readonly_fields = ("created_at",)
    inlines = [EnemyAbilityInline, EnemyDamageResistanceInline]

    fieldsets = (
        ("Identity", {
            "fields": ("campaign", "kind", "category", "name", "tags", "created_at")
        }),
        ("Core stats", {
            "fields": ("level", "hp", "speed", "armor", "dodge", "initiative", "crit_threshold")
        }),
        ("Ability scores", {
            "fields": ("str_score", "dex_score", "con_score", "int_score", "wis_score", "cha_score")
        }),
        ("Saves and skills", {
            "fields": (
                "will_save", "reflex_save", "fortitude_save",
                "perception", "stealth", "athletics", "acrobatics", "insight",
            )
        }),
        ("Basic attack", {
            "fields": (
                "basic_attack_name",
                "basic_attack_action",
                "basic_attack_to_hit",
                "basic_attack_ap",
                "basic_attack_damage",
                "basic_attack_note",
            )
        }),
        ("Magic and mastery", {
            "fields": ("can_cast_spells", "spells", "martial_masteries")
        }),
        ("Notes", {
            "fields": ("description", "resistances")
        }),
    )

    def scope_display(self, obj):
        return obj.campaign.name if obj.campaign_id else "Global"
    scope_display.short_description = "Scope"


@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    list_display = ("name", "campaign", "created_at")
    list_filter = ("campaign",)
    search_fields = ("name", "description")


@admin.register(EncounterEnemy)
class EncounterEnemyAdmin(admin.ModelAdmin):
    list_display = (
        "display_name", "encounter", "enemy_type", "side",
        "current_hp", "max_hp", "initiative", "created_at"
    )
    list_filter = ("encounter", "enemy_type", "side")
    search_fields = ("name_override", "enemy_type__name", "encounter__name")