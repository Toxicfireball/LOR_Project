# characters/urls.py

from django.urls import path
from . import views
from .views import character_detail, create_character, character_list

app_name = 'characters'

urlpatterns = [
    path('', views.character_list, name='character_list'),
    path('create/stage1/', views.create_character, name='create_character'),
    path('<int:character_id>/link/<int:campaign_id>/', views.link_character_to_campaign, name='link_character'),
path('<int:pk>/', character_detail, name='character_detail'),
path('', views.character_list, name='character_list'),
 path('<int:char_id>/level-up/', views.level_up, name='level_up'),
]
