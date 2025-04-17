

from django.db import models
from django.contrib.auth.models import User
from campaigns.models import Campaign  # Make sure the campaigns app is created and in INSTALLED_APPS



# If you're using Django 3.1+ you can use models.JSONField directly.
# Otherwise, if you need PostgreSQL support in earlier versions, import from django.contrib.postgres.fields

class Character(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='characters')
    name = models.CharField(max_length=255)
    
    # Stage 1: Basic Character Creation Fields
    race = models.CharField(max_length=50)
    subrace = models.CharField(max_length=50, blank=True)  
    half_elf_origin = models.CharField(max_length=20, blank=True)  # For fully half-blooded half-elves
    bg_combo = models.CharField(max_length=10, blank=True)  # e.g., "0", "1", or "2" to indicate the background combo chosen
    main_background = models.CharField(max_length=50, blank=True)
    side_background_1 = models.CharField(max_length=50, blank=True)
    side_background_2 = models.CharField(max_length=50, blank=True)
    
    backstory = models.TextField(blank=True)
    
    # Ability scores (set by the point-buy system)
    strength = models.IntegerField(default=8)
    dexterity = models.IntegerField(default=8)
    constitution = models.IntegerField(default=8)
    intelligence = models.IntegerField(default=8)
    wisdom = models.IntegerField(default=8)
    charisma = models.IntegerField(default=8)
    
    # Skill proficiencies: a mapping of each skill to its proficiency tier
    # (e.g., "Acrobatics": "Trained", "Arcana": "Trained", etc.)    
    # Later progression fields
    level = models.IntegerField(default=0)  # Level 0 after Stage 1
    character_class = models.CharField(max_length=50, blank=True)
    
    # Campaign-related field (if the character is part of a campaign)
    campaign = models.ForeignKey("campaigns.Campaign", on_delete=models.SET_NULL, null=True, blank=True, related_name="characters")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or f"Character {self.id}"
class SkillCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    ability = models.CharField(max_length=3)  # e.g. DEX, INT

    def __str__(self):
        return self.name

class SubSkill(models.Model):
    category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE, related_name='subskills')
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.category.name} - {self.name}"

class ProficiencyLevel(models.Model):
    name = models.CharField(max_length=20)  # Trained, Expert, Master
    tier = models.IntegerField()  # 0: Trained, 1: Expert, 2: Master
    bonus = models.IntegerField()  # 0, 1, 2

    def __str__(self):
        return self.name

class CharacterSkillProficiency(models.Model):
    character = models.ForeignKey('characters.Character', on_delete=models.CASCADE, related_name='skill_proficiencies')
    subskill = models.ForeignKey(SubSkill, on_delete=models.CASCADE)
    proficiency = models.ForeignKey(ProficiencyLevel, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('character', 'subskill')