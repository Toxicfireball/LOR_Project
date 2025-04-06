# characters/urls.py

from django.urls import path
from . import views

app_name = 'characters'

urlpatterns = [
    path('', views.character_list, name='character_list'),
    path('create/stage1/', views.create_character_stage1, name='create_character_stage1'),
    path('<int:character_id>/link/<int:campaign_id>/', views.link_character_to_campaign, name='link_character'),
]
