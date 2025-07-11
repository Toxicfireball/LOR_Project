# characters/urls.py

from django.urls import path
from . import views
from .views import character_detail, create_character, character_list, spell_list, feat_list,    RulebookListView, RulebookDetailView, RulebookPageDetailView

app_name = 'characters'

urlpatterns = [
    path('', views.character_list, name='character_list'),
    path('create/stage1/', views.create_character, name='create_character'),
    path('<int:character_id>/link/<int:campaign_id>/', views.link_character_to_campaign, name='link_character'),
path('<int:pk>/', character_detail, name='character_detail'),

 path('<int:char_id>/level-up/', views.level_up, name='level_up'),
path('codex/', views.codex_index, name='codex_index'),
path('codex/spells/', views.spell_list, name='codex_spells'),
path('codex/feats/', views.feat_list, name='codex_feats'),
path('codex/classes/', views.class_list, name='codex_classes'),
path('codex/classes/<int:pk>/', views.class_detail, name='class_detail'),
    path("codex/races",  views.race_list,  name="codex_races"),
    path("codex/races/<int:pk>/", views.race_detail, name="race_detail"),
        path("rules/", RulebookListView.as_view(), name="rulebook_list"),
    path("rules/<int:pk>/", RulebookDetailView.as_view(), name="rulebook_detail"),
    path(
        "rules/<int:rulebook_pk>/page/<int:pk>/",
        RulebookPageDetailView.as_view(),
        name="rulebook_page_detail",
    ),
    path('loremaster/',                             views.LoremasterListView.as_view(),   name='loremaster_list'),
    path('loremaster/<slug:slug>/',                 views.LoremasterDetailView.as_view(), name='loremaster_detail'),


]
