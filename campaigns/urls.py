from django.urls import path
from . import views

app_name = "campaigns"

urlpatterns = [
    path("", views.campaign_list, name="campaign_list"),
    path("create/", views.create_campaign, name="create_campaign"),
    path("<int:campaign_id>/", views.campaign_detail, name="campaign_detail"),
    path("<int:campaign_id>/join/", views.join_campaign, name="join_campaign"),
    path("<int:campaign_id>/attach/", views.attach_character, name="attach_character"),
    path("<int:campaign_id>/detach/<int:character_id>/", views.detach_character, name="detach_character"),
    path("<int:campaign_id>/leave/", views.leave_campaign, name="leave_campaign"),
    path("<int:campaign_id>/inventory/add/", views.add_party_item, name="add_party_item"),
    # NEW
    path("<int:campaign_id>/enemy-types/<int:et_id>/edit/", views.edit_enemy_type, name="edit_enemy_type"),  # ✅
    path("<int:campaign_id>/encounters/<int:encounter_id>/delete/", views.delete_encounter, name="delete_encounter"),
        path("<int:campaign_id>/bg/<int:pb_id>/approve/", views.approve_pending_bg, name="approve_pending_bg"),
    path("<int:campaign_id>/bg/<int:pb_id>/reject/",  views.reject_pending_bg,  name="reject_pending_bg"),
    path("<int:campaign_id>/notes/add/", views.add_campaign_note, name="add_campaign_note"),
    path("<int:campaign_id>/messages/send/", views.send_campaign_message, name="send_campaign_message"),
        path("<int:campaign_id>/assign-skill-feats/", views.assign_skill_feats, name="assign_skill_feats"),
    path("<int:campaign_id>/encounters/create/", views.create_encounter, name="create_encounter"),
    path("<int:campaign_id>/enemies/create/", views.create_enemy_type, name="create_enemy_type"),
    path("<int:campaign_id>/enemies/add-ability/", views.add_enemy_ability, name="add_enemy_ability"),
    path("<int:campaign_id>/encounters/<int:encounter_id>/add-enemy/", views.add_enemy_to_encounter, name="add_enemy_to_encounter"),
    path("<int:campaign_id>/encounters/set-hp/", views.set_encounter_enemy_hp, name="set_encounter_enemy_hp"),
    path("<int:campaign_id>/encounters/adjust-hp/", views.adjust_encounter_enemy_hp, name="adjust_encounter_enemy_hp"),
    path("<int:campaign_id>/encounters/<int:encounter_id>/remove/<int:ee_id>/", views.remove_encounter_enemy, name="remove_encounter_enemy"),
path("<int:campaign_id>/encounters/quick-add-enemy/", views.quick_add_enemy, name="quick_add_enemy"),
    path("<int:campaign_id>/encounters/<int:encounter_id>/", views.encounter_detail, name="encounter_detail"),
    path("<int:campaign_id>/encounters/create/", views.create_encounter, name="create_encounter"),
path("<int:campaign_id>/enemies/<int:et_id>/delete/", views.delete_enemy_type, name="delete_enemy_type"),
    path("<int:campaign_id>/enemy-types/<int:et_id>/edit/", views.edit_enemy_type, name="edit_enemy_type"),
    # NEW dedicated page
    path("<int:campaign_id>/enemies/new/", views.new_enemy_type, name="new_enemy_type"),
        path("<int:campaign_id>/encounters/<int:encounter_id>/delete/", views.delete_encounter, name="delete_encounter"),
]
