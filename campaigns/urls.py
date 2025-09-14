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
    path("<int:campaign_id>/notes/add/", views.add_campaign_note, name="add_campaign_note"),
    path("<int:campaign_id>/messages/send/", views.send_campaign_message, name="send_campaign_message"),
]
