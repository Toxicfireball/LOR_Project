from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Home Page
    path('character-creator/', views.character_creator, name='character_creator'),  # Character Creator Page
]
