from django.db import models
from django.contrib.auth.models import User
from campaigns.models import Campaign  # Make sure the campaigns app is created and in INSTALLED_APPS

# ------------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------------
PROFICIENCY_TYPES = [
    ("armor",       "Armor"),
    ("dodge",       "Dodge"),
    ("perception",  "Perception"),
    ("initiative",  "Initiative"),
    ("dc",          "Spell/DC"),
    ("reflex",      "Reflex Save"),
    ("fortitude",   "Fortitude Save"),
    ("will",        "Will Save"),
    ("weapon",      "Weapon"),
]

HIT_DIE_CHOICES = [
    (4,  "d4"),
    (6,  "d6"),
    (8,  "d8"),
    (10, "d10"),
    (12, "d12"),
]


# ------------------------------------------------------------------------------
# Core Character
# ------------------------------------------------------------------------------
class Character(models.Model):
    user               = models.ForeignKey(User, on_delete=models.CASCADE, related_name='characters')
    name               = models.CharField(max_length=255)
    # Stage 1 fields
    race               = models.CharField(max_length=50)
    subrace            = models.CharField(max_length=50, blank=True)
    half_elf_origin    = models.CharField(max_length=20, blank=True)
    bg_combo           = models.CharField(max_length=10, blank=True)
    main_background    = models.CharField(max_length=50, blank=True)
    side_background_1  = models.CharField(max_length=50, blank=True)
    side_background_2  = models.CharField(max_length=50, blank=True)
    HP = models.IntegerField(blank=True, null = True)
    temp_HP = models.IntegerField( blank=True,  null = True)
    # ability scores
    strength           = models.IntegerField(default=8)
    dexterity          = models.IntegerField(default=8)
    constitution       = models.IntegerField(default=8)
    intelligence       = models.IntegerField(default=8)
    wisdom             = models.IntegerField(default=8)
    charisma           = models.IntegerField(default=8)
    # progression
    level              = models.PositiveIntegerField(default=0)
    backstory          = models.TextField(blank=True)
    campaign           = models.ForeignKey(
                            Campaign,
                            on_delete=models.SET_NULL,
                            null=True, blank=True,
                            related_name="characters"
                        )
    created_at         = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or f"Character {self.id}"


# ------------------------------------------------------------------------------
# Skills & Proficiencies
# ------------------------------------------------------------------------------
class SkillCategory(models.Model):
    name    = models.CharField(max_length=100, unique=True)
    ability = models.CharField(max_length=3)  # e.g. DEX, INT

    def __str__(self):
        return self.name

class SubSkill(models.Model):
    category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE, related_name='subskills')
    name     = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.category.name} – {self.name}"


class ProficiencyLevel(models.Model):
    name  = models.CharField(max_length=20)  # Trained, Expert, Master
    tier  = models.IntegerField()            # 0=Trained,1=Expert,2=Master
    bonus = models.IntegerField()            # e.g. +0, +1, +2

    def __str__(self):
        return self.name


class CharacterSkillProficiency(models.Model):
    character   = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='skill_proficiencies')
    subskill    = models.ForeignKey(SubSkill, on_delete=models.CASCADE)
    proficiency = models.ForeignKey(ProficiencyLevel, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('character', 'subskill')


# ------------------------------------------------------------------------------
# Classes, Levels, Features
# ------------------------------------------------------------------------------
class ClassTag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class CharacterClass(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    class_ID = models.TextField(blank=True)
    hit_die     = models.PositiveSmallIntegerField(
                      choices=HIT_DIE_CHOICES,
                      default=8,
                      help_text="Your class’s Hit Die"
                  )
    tags = models.ManyToManyField(
        'ClassTag',
        blank=True,
        related_name='classes',
        help_text="High‑level archetype tags (e.g. Martial, Spellcaster…)"
    )
    def __str__(self):
        return self.name
    
class SubclassGroup(models.Model):
    character_class = models.ForeignKey(
        CharacterClass,
        on_delete=models.CASCADE,
        related_name="subclass_groups",
    )

    SYSTEM_LINEAR         = "linear"
    SYSTEM_MODULAR_LINEAR = "modular_linear"
    SYSTEM_MODULAR_MASTERY= "modular_mastery"

    SYSTEM_CHOICES = [
        (SYSTEM_LINEAR,          "Linear (fixed level)"),
        (SYSTEM_MODULAR_LINEAR,  "Modular Linear (tiered)"),
        (SYSTEM_MODULAR_MASTERY, "Modular Mastery (pick & master)"),
    ]

    system_type = models.CharField(
        max_length=20,
        choices=SYSTEM_CHOICES,
        default=SYSTEM_LINEAR,
    )    
    name  = models.CharField(max_length=100, help_text="Umbrella / Order name (e.g. Moon Circle)")
    code        = models.CharField(max_length=20, blank=True)
    class Meta:
        unique_together = ("character_class", "name")
        ordering        = ["character_class", "name"]
    def __str__(self):
        return f"{self.character_class.name} – {self.name}"



class ClassSubclass(models.Model):
    """Optional ‘archetype’ or specialization of a base CharacterClass."""

    group       = models.ForeignKey(
        SubclassGroup,
        on_delete=models.CASCADE,
        related_name="subclasses",
        blank=True, null=True,
        help_text="Which umbrella / order this belongs to"
    )

    base_class  = models.ForeignKey(
        CharacterClass,
        on_delete=models.CASCADE,
        related_name='subclasses',
    )
    name        = models.CharField(max_length=100)
    description = models.CharField(max_length=100, blank=True, null=True)
    code        = models.CharField(
        max_length=20,
        blank=True,
        help_text="Optional shorthand code for this subclass"
    )

    # ← NEW

    modular_rules = models.JSONField(
        blank=True, null=True,
        help_text=(
            "Extra numbers for modular systems.  "
            "eg. {\"modules_per_mastery\":2, \"ability_req\":{\"0\":13,\"1\":15}}"
        )
    )
    @property
    def system_type(self):
        return self.group.system_type if self.group else None
    class Meta:
        unique_together = ('base_class', 'name')

    def __str__(self):
        return f"{self.base_class.name} – {self.name}"

class ProficiencyTier(models.Model):
    """
    e.g. Trained / Expert / Master / Legendary
    """
    name  = models.CharField(max_length=20, unique=True)
    bonus = models.IntegerField(help_text="e.g. +2 for Expert")

    def __str__(self):
        return self.name


class ClassProficiencyProgress(models.Model):
    """
    For each (class, proficiency_type), at what level you bump up to a given tier.
    """
    character_class  = models.ForeignKey(CharacterClass, on_delete=models.CASCADE, related_name="prof_progress")
    proficiency_type = models.CharField(max_length=20, choices=PROFICIENCY_TYPES)
    at_level         = models.PositiveIntegerField(help_text="Level at which this tier becomes active")
    tier             = models.ForeignKey(ProficiencyTier, on_delete=models.PROTECT)

    class Meta:
        unique_together = ("character_class", "proficiency_type", "at_level")
        ordering        = ["character_class", "proficiency_type", "at_level"]

    def __str__(self):
        return f"{self.character_class.name} {self.proficiency_type}@L{self.at_level} → {self.tier.name}"


class CharacterClassProgress(models.Model):
    """
    Tracks how many levels of each class a character has taken.
    """
    character       = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='class_progress')
    character_class = models.ForeignKey(CharacterClass, on_delete=models.CASCADE)
    levels          = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('character', 'character_class')

    def __str__(self):
        return f"{self.character.name} – {self.character_class.name} L{self.levels}"

# models.py



class ClassFeature(models.Model):
    # ← new!
    character_class = models.ForeignKey(
        CharacterClass,
        on_delete=models.CASCADE,
        related_name="features",
        help_text="Which class grants this feature?",
        null=True,    # ← allow existing rows to be empty
        blank=True,
    )
    FEATURE_TYPE_CHOICES = [
        ("class_trait",   "Class Trait"),
        ("class_feat",    "Class Feat"),
        ("skill_feat",    "Skill Feat"),
        ("martial_mastery","Martial Mastery"),
        ("subclass_choice","Subclass Choice"),   # new
        ("subclass_feat", "Subclass Feature"),   # renamed for clarity
    ]
    feature_type       = models.CharField(
        max_length=100,
        choices=FEATURE_TYPE_CHOICES,
        default='class_feat',
        help_text="Type of trait"
    )
    code        = models.CharField(max_length=10, unique=True)
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    has_options = models.BooleanField(
        default=False,
        help_text="If checked, you must add at least one Option below."
    )

    formula = models.CharField(
        max_length=100,
        blank=True,
        help_text="Any dice+attribute expression, e.g. '1d10+level'"
    )

    uses = models.CharField(
        max_length=100,
        blank=True,
        help_text="How many times? e.g. 'level', '1', 'level/3 round down +1'"
    )
    subclass_group = models.ForeignKey(
        SubclassGroup,
        on_delete=models.CASCADE,
        blank=True, null=True,
        related_name="choice_features",
        help_text="For a subclass_choice, pick the umbrella shown to the player."
    )
    subclasses = models.ManyToManyField(
        ClassSubclass,
        blank=True,
        related_name="features",
        help_text="For subclass_feat, which subclasses receive this?",
    )
    
    FORMULA_TARGETS =  [
        ("acrobatics",     "Acrobatics (DEX)"),
        ("animal_handling","Animal Handling (WIS)"),
        ("arcana",         "Arcana (INT)"),
        ("arts",           "Arts (CHA)"),
        ("athletics",      "Athletics (STR)"),
        ("charm",          "Charm (CHA)"),
        ("deception",      "Deception (CHA)"),
        ("insight",        "Insight (WIS/CHA)"),
        ("investigation",  "Investigation (INT)"),
        ("linguistic",     "Linguistic (INT)"),
        ("local_instinct", "Local Instinct (WIS)"),
        ("general_knowledge","General Knowledge (INT)"),
        ("lore",           "Lore (INT)"),
        ("memory",         "Memory (INT)"),
        ("sleight_of_hand","Sleight of Hand (DEX)"),
        ("stealth",        "Stealth (DEX)"),
        ("survival",       "Survival (WIS)"),
        ("technology",     "Technology (INT)"),
        # now your “roll types”:
        ("attack_roll",    "Attack Roll"),
        ("damage",         "Damage"),
        ("save_dc",        "Save DC"),
        ("reflex_save",    "Reflex Save"),
        ("fortitude_save", "Fortitude Save"),
        ("will_save",      "Will Save"),
        ("initiative",     "Initiative"),
        ("skill_check",    "Skill Check"),
        ("temp_HP",    "Temporary Hitpoints"),
        ("HP",    "Hitpoints"),
        # weapon‐specific if you like:
        ("attack",  "Attack Roll"),
        ("weapon_attack",  "Weapon Attack"),
        ("melee_attack",   "Melee Attack"),
        ("ranged_attack",  "Ranged Attack"),
        ("melee_weapon_attack",   "Melee Weapon Attack"),
        ("ranged_weapon_attack",  "Ranged Weapon Attack"),
        ("unarmed_attack", "Unarmed Attack"),
        ("spell_attack", "Spell Attack"),
        ("spell_damage", "Spell Damage"),
        ("weapon_damage",  "Weapon Damage"),
        ("melee_weapon_damage",   "Melee Weapon Damage"),
        ("melee_damage",   "Melee Damage"),
        ("ranged_damage",  "Ranged Weapon Damage"),
        ("ranged_attack",  "Ranged Attack"),
        ("unarmed_damage", "Unarmed Damage"),
      # … add whatever else you need …
    ]
    formula_target = models.CharField(
       max_length=20,
       choices=FORMULA_TARGETS,
       default='attack_roll',
       help_text="What kind of roll this formula is used for"
    )


    def __str__(self):
        return f"{self.character_class.name}: {self.code} – {self.name}"



class FeatureOption(models.Model):
    feature        = models.ForeignKey(
                         ClassFeature,
                         on_delete=models.CASCADE,
                         related_name="options"
                     )
    label          = models.CharField(max_length=100)
    grants_feature = models.ForeignKey(
                         ClassFeature,
                         on_delete=models.SET_NULL,
                         blank=True, null=True,
                         related_name="granted_by_options",
                         help_text="Which other feature does this choice grant?"
                     )

    def __str__(self):
        return self.label




class ClassLevel(models.Model):
    """
    One record per (class, level) grouping all features you gain at that level.
    """
    character_class = models.ForeignKey(CharacterClass, on_delete=models.CASCADE, related_name="levels")
    level           = models.PositiveIntegerField()
    features        = models.ManyToManyField(
                          ClassFeature,
                          through="ClassLevelFeature",
                          help_text="All ClassFeatures (and option‑selections) you get at this level"
                      )

    class Meta:
        unique_together = ("character_class", "level")
        ordering        = ["character_class", "level"]

    def __str__(self):
        return f"{self.character_class.name} L{self.level}"


class ClassLevelFeature(models.Model):
    """
    The through‐table linking a ClassLevel → ClassFeature,
    optionally capturing which FeatureOption was chosen.
    """
    class_level   = models.ForeignKey(ClassLevel, on_delete=models.CASCADE)
    feature       = models.ForeignKey(ClassFeature, on_delete=models.CASCADE)
    chosen_option = models.CharField(
                        max_length=100, blank=True,
                        help_text="One of the parent feature’s option labels"
                    )

    class Meta:
        unique_together = ("class_level", "feature")

    def clean(self):
        super().clean()
        if self.feature.has_options:
            valid_labels = {opt.label for opt in self.feature.options.all()}
            if self.chosen_option not in valid_labels:
                from django.core.exceptions import ValidationError
                raise ValidationError("chosen_option must match one of the feature’s option labels")

    def __str__(self):
        if self.feature.has_options:
            return f"{self.class_level} → {self.feature.code} [picked {self.chosen_option}]"
        return f"{self.class_level} → {self.feature.code}"
