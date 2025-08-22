# characters/urls.py
from django.urls import path
from . import views

app_name = "characters"

urlpatterns = [
    # Characters
    path("", views.character_list, name="character_list"),
    path("create/", views.create_character, name="create_character"),
    path("<int:pk>/", views.character_detail, name="character_detail"),
    path("<int:pk>/level-down/", views.level_down, name="level_down"),

    # Character mutations / AJAX (POST)
    path("<int:pk>/set-weapon/", views.set_weapon_choice, name="set_weapon_choice"),
    path("<int:pk>/set-armor/", views.set_armor_choice, name="set_armor_choice"),
    path("<int:pk>/set-activation/", views.set_activation, name="set_activation"),
    path("<int:pk>/add-known-spell/", views.add_known_spell, name="add_known_spell"),
    path("<int:pk>/set-prepared-spell/", views.set_prepared_spell, name="set_prepared_spell"),
    path("<int:pk>/pick-martial-mastery/", views.pick_martial_mastery, name="pick_martial_mastery"),
    path("<int:pk>/override/", views.set_field_override, name="set_field_override"),

    # Link character ↔ campaign
    path(
        "campaigns/<int:campaign_id>/link/<int:character_id>/",
        views.link_character_to_campaign,
        name="link_character_to_campaign",
    ),

    # Codex
    path("codex/", views.codex_index, name="codex_index"),
    path("codex/spells/", views.spell_list, name="codex_spells"),
    path("codex/feats/", views.feat_list, name="codex_feats"),
    path("codex/classes/", views.class_list, name="codex_classes"),
    path("codex/classes/<int:pk>/", views.class_detail, name="codex_class_detail"),
    path("codex/subclasses/", views.class_subclass_list, name="codex_subclasses"),
    path("codex/groups/", views.subclass_group_list, name="codex_groups"),
    path("codex/races/", views.race_list, name="codex_races"),
    path("codex/races/<int:pk>/", views.race_detail, name="codex_race_detail"),

    # Loremaster
    path("loremaster/", views.LoremasterListView.as_view(), name="loremaster_list"),
    path("loremaster/<slug:slug>/", views.LoremasterDetailView.as_view(), name="loremaster_detail"),
    path("loremaster/id/<int:pk>/", views.LoremasterDetailView.as_view(), name="loremaster_detail_by_pk"),

    # Rulebooks (PK-based)
    path("rulebooks/", views.RulebookListView.as_view(), name="rulebook_list"),
    path("rulebooks/<int:pk>/", views.RulebookDetailView.as_view(), name="rulebook_detail"),
    path("rulebooks/page/<int:pk>/", views.RulebookPageDetailView.as_view(), name="rulebook_page_detail"),

    # Select2 autocomplete
    path("autocomplete/classfeats/", views.ClassFeatAutocomplete.as_view(), name="classfeat_autocomplete"),
]