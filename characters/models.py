from django.db import models

# Create your models here.
# characters/models.py

from django.db import models
from django.contrib.auth.models import User
from campaigns.models import Campaign  # Make sure the campaigns app is created and in INSTALLED_APPS

class Character(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='characters')
    name = models.CharField(max_length=255)
    # Stage 1 fields
    race = models.CharField(max_length=50)
    background = models.CharField(max_length=50)
    backstory = models.TextField(blank=True)
    strength = models.IntegerField(default=0)
    dexterity = models.IntegerField(default=0)
    constitution = models.IntegerField(default=0)
    intelligence = models.IntegerField(default=0)
    wisdom = models.IntegerField(default=0)
    charisma = models.IntegerField(default=0)
    # Later progression fields
    level = models.IntegerField(default=0)  # Level 0 after Stage 1
    character_class = models.CharField(max_length=50, blank=True)
    # You can also add fields for class features, feats, etc.
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name="characters")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or f"Character {self.id}"
