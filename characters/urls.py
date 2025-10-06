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
    path("<int:pk>/delete/", views.delete_character, name="delete_character"),
    path("bulk-delete/", views.bulk_delete_characters, name="bulk_delete_characters"),

    # AJAX / mutations
    path("ajax/race-features/", views.race_features_data, name="race_features_data"),
    path("<int:pk>/set-weapon/", views.set_weapon_choice, name="set_weapon_choice"),
    path("<int:pk>/set-armor/", views.set_armor_choice, name="set_armor_choice"),
    path("<int:pk>/set-activation/", views.set_activation, name="set_activation"),
    path("<int:pk>/add-known-spell/", views.add_known_spell, name="add_known_spell"),
    path("<int:pk>/set-prepared-spell/", views.set_prepared_spell, name="set_prepared_spell"),
    path("<int:pk>/pick-martial-mastery/", views.pick_martial_mastery, name="pick_martial_mastery"),
    path("<int:pk>/override/", views.set_field_override, name="set_field_override"),
    path("<int:pk>/set-shield/", views.set_shield_choice, name="set_shield_choice"),

    # Search / share
    path("search/", views.global_search, name="global_search"),
    path("<int:pk>/share/", views.character_share_create, name="character_share_create"),
    path("<uuid:token>/share/accept/", views.character_share_accept, name="character_share_accept"),
    path("<int:pk>/share/revoke/<int:invite_id>/", views.character_share_revoke, name="character_share_revoke"),
    path("<int:pk>/share/remove/<int:user_id>/", views.character_share_remove_viewer, name="character_share_remove"),

    # Codex / Loremaster / Rulebooks (keep as you had, trimmed here for brevity)
    path("codex/", views.codex_index, name="codex_index"),
    path("codex/spells/", views.spell_list, name="codex_spells"),
    path("codex/feats/", views.feat_list, name="codex_feats"),
    path("codex/feats/data/", views.feat_data, name="feat_data"),
    path("codex/classes/", views.class_list, name="codex_classes"),
    path("codex/classes/<int:pk>/", views.class_detail, name="class_detail"),
    path("codex/subclasses/", views.class_subclass_list, name="codex_subclasses"),
    path("codex/groups/", views.subclass_group_list, name="codex_groups"),
    path("codex/races/", views.race_list, name="codex_races"),
    path("codex/races/<int:pk>/", views.race_detail, name="race_detail"),
    path("codex/weapons/", views.weapon_list, name="codex_weapons"),
    path("codex/armor/", views.armor_list, name="codex_armor"),
    path("codex/masteries/", views.mastery_list, name="codex_masteries"),
    path("codex/masteries/data/", views.mastery_data, name="mastery_data"),
    path("codex/masteries/<int:pk>/", views.mastery_detail, name="mastery_detail"),

    path("loremaster/", views.LoremasterListView.as_view(), name="loremaster_list"),
    path("loremaster/<slug:slug>/", views.LoremasterDetailView.as_view(), name="loremaster_detail"),
    path("loremaster/id/<int:pk>/", views.LoremasterDetailView.as_view(), name="loremaster_detail_by_pk"),

    # Rulebook pages (both styles)
    path("rulebooks/", views.RulebookListView.as_view(), name="rulebook_list"),
    path("rulebooks/<int:pk>/", views.RulebookDetailView.as_view(), name="rulebook_detail"),
    path("rulebooks/<int:rulebook_pk>/page/<int:pk>/", views.RulebookPageDetailView.as_view(), name="rulebook_page_detail"),
    path("rulebooks/page/<int:pk>/", views.RulebookPageDetailView.as_view(), name="rulebook_page_detail_by_pk"),
]
