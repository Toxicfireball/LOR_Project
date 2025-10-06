from django.contrib import admin
from .models import EnemyType, EnemyAbility, Encounter, EncounterEnemy, EnemyTag

@admin.register(EnemyTag)
class EnemyTagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}

from .models import EnemyType, EnemyAbility, Encounter, EncounterEnemy, EnemyTag

class EnemyAbilityInline(admin.TabularInline):
    model = EnemyAbility
    extra = 1
    fields = ("ability_type", "action_cost", "title", "description")
    show_change_link = True

@admin.register(EnemyType)
class EnemyTypeAdmin(admin.ModelAdmin):
    def scope(self, obj):
        return obj.campaign.name if obj.campaign_id else "Global"
    scope.short_description = "Scope"

    list_display = ("name", "level", "hp", "armor", "dodge", "initiative", scope, "created_at")
    list_filter  = ("campaign", "tags")
    search_fields = ("name",)
    filter_horizontal = ("tags",)
    inlines = [EnemyAbilityInline]

@admin.register(EncounterEnemy)
class EncounterEnemyAdmin(admin.ModelAdmin):
    list_display = ("display_name", "encounter", "enemy_type", "current_hp", "max_hp", "initiative", "notes", "created_at")
    list_filter  = ("encounter", "enemy_type")
    search_fields = ("name_override", "enemy_type__name", "encounter__name")



