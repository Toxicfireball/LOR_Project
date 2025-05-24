# characters/urls.py

from django.urls import path
from . import views
from .views import character_detail, create_character, character_list, spell_list, feat_list

app_name = 'characters'

urlpatterns = [
    path('', views.character_list, name='character_list'),
    path('create/stage1/', views.create_character, name='create_character'),
    path('<int:character_id>/link/<int:campaign_id>/', views.link_character_to_campaign, name='link_character'),
path('<int:pk>/', character_detail, name='character_detail'),

 path('<int:char_id>/level-up/', views.level_up, name='level_up'),
     path('spells/', views.spell_list, name='spell_list'),
path('codex/', views.codex_index, name='codex_index'),
path('codex/spells/', views.spell_list, name='codex_spells'),
path('codex/feats/', views.feat_list, name='codex_feats'),
path('codex/classes/', views.class_list, name='codex_classes'),
path('codex/features/', views.class_feature_list, name='codex_features'),
path('codex/subclasses/', views.class_subclass_list, name='codex_subclasses'),
path('codex/groups/', views.subclass_group_list, name='codex_subgroups'),
path('codex/classes/<int:pk>/', views.class_detail, name='codex_class_detail'),


]
