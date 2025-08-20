from django.db import models
from django.contrib.auth.models import User
from campaigns.models import Campaign  # Make sure the campaigns app is created and in INSTALLED_APPS
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
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


ABILITY_CHOICES = [
    ("strength",     "Strength"),
    ("dexterity",    "Dexterity"),
    ("constitution", "Constitution"),
    ("intelligence", "Intelligence"),
    ("wisdom",       "Wisdom"),
    ("charisma",     "Charisma"),
]


HIT_DIE_CHOICES = [
    (4,  "d4"),
    (6,  "d6"),
    (8,  "d8"),
    (10, "d10"),
    (12, "d12"),
]


ABILITY_CHOICES = [
    ("strength",     "Strength"),
    ("dexterity",    "Dexterity"),
    ("constitution", "Constitution"),
    ("intelligence", "Intelligence"),
    ("wisdom",       "Wisdom"),
    ("charisma",     "Charisma"),
]

class Skill(models.Model):
    name               = models.CharField(max_length=100, unique=True)
    ability            = models.CharField(
        max_length=12,
        choices=ABILITY_CHOICES,
        default="strength",
        help_text="Primary governing ability"
    )
    secondary_ability  = models.CharField(
        max_length=12,
        choices=ABILITY_CHOICES,
        blank=True,
        null=True,
        help_text="Optional secondary governing ability"
    )
    description        = models.TextField(blank=True)
    is_advanced        = models.BooleanField(default=False)

    def __str__(self):
        if self.secondary_ability:
            return f"{self.name} ({self.ability.title()} / {self.secondary_ability.title()})"
        return self.name


class Language(models.Model):
    code = models.SlugField(max_length=20, unique=True,
                            help_text="Identifier, e.g. ‘common’, ‘elvish’")
    name = models.CharField(max_length=100,
                            help_text="Human-readable name, e.g. ‘Common’")
    description = models.TextField(
        blank=True,
        help_text="A brief description of this language (dialects, notes, etc.)"
    )

    def __str__(self):
        return self.name


class DamageResistance(models.Model):
    """
    A resistance entry that can apply to any feature (class or racial).
    """
    # link to the granting feature (ClassFeature or RacialFeature)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id    = models.PositiveIntegerField()
    owner        = GenericForeignKey('content_type', 'object_id')

    # mirror your existing damage‐type choices, plus grouping options:
    DAMAGE_TYPE_CHOICES = [
        ('all',                       "All Damage Types"),
        ('physical_all',              "All Physical Damage"),
        ('physical_non_magical',      "Non-magical Physical Damage"),
        # your four core physical types:
        ('physical_bludgeoning',      "Physical Bludgeoning"),
        ('physical_slashing',         "Physical Slashing"),
        ('physical_piercing',         "Physical Piercing"),
        # and all the rest from ClassFeature.DAMAGE_TYPE_CHOICES :contentReference[oaicite:1]{index=1}
        ('explosive',                 "Explosive"),
        ('magical_bludgeoning',       "Magical Bludgeoning"),
        ('magical_slashing',          "Magical Slashing"),
        ('magical_piercing',          "Magical Piercing"),
        ('acid',                      "Acid"),
        ('cold',                      "Cold"),
        ('fire',                      "Fire"),
        ('force',                     "Force"),
        ('lightning',                 "Lightning"),
        ('necrotic',                  "Necrotic"),
        ('poison',                    "Poison"),
        ('psychic',                   "Psychic"),
        ('radiant',                   "Radiant"),
        ('thunder',                   "Thunder"),
        ('true',                      "True"),
    ]

    damage_type = models.CharField(
        max_length=25,
        choices=DAMAGE_TYPE_CHOICES,
        help_text="Which damage type (or grouping) this resistance applies to."
    )
    amount = models.PositiveSmallIntegerField(
        default=0,
        help_text="How much to subtract from incoming damage of that type."
    )

    class Meta:
        unique_together = ('content_type','object_id','damage_type')

    def __str__(self):
        return f"{self.owner} DR {self.damage_type} –{self.amount}"

    def applies_to(self, incoming_type: str) -> bool:
        """
        Decide whether this resistance applies to a given raw damage_type.
        """
        if self.damage_type == 'all':
            return True
        if self.damage_type == 'physical_all':
            return incoming_type.startswith('physical_') or incoming_type.startswith('magical_')
        if self.damage_type == 'physical_non_magical':
            return incoming_type.startswith('physical_')
        return self.damage_type == incoming_type

class BaseRace(models.Model):
    code        = models.SlugField(max_length=20, unique=True)
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    starting_hp = models.IntegerField(
        null=True,
        blank=True,
        help_text="Starting HP for this race (to be filled in)"
    )

    SIZE_CHOICES = [
    ("small", "Small"),
    ("medium","Medium"),
    ("large","Large"),
    ]
    size = models.CharField(
        max_length=6,
        choices=SIZE_CHOICES,
        default="medium",            # ← sensible default for existing rows
        help_text="Small / Medium / Large"
    )
    primary_image = models.ImageField(
        upload_to="race_images/primary/",
        blank=True,
        null=True,
        help_text="Upload the main portrait or icon for this race."
    )
    secondary_image = models.ImageField(
        upload_to="race_images/secondary/",
        blank=True,
        null=True,
        help_text="Upload a second image (e.g. a banner or alternate art) for this race."
    )
     
    tertiary_image = models.ImageField(
       upload_to="race_images/tertiary/",
        blank=True,
        null=True,
        help_text="Upload a thumbnail or list‐page image for this race."
    )
    languages = models.ManyToManyField(
        Language,
        blank=True,
        help_text="Select which languages this race knows inherently"
    )    
    def __str__(self):
        return self.name

    @property
    def primary_image_url(self):
        return self.primary_image.url if self.primary_image else ""

    @property
    def secondary_image_url(self):
        return self.secondary_image.url if self.secondary_image else ""
    @property
    def tertiary_image_url(self):
        return self.tertiary_image.url if self.tertiary_image else ""
    
    tags = models.ManyToManyField("RaceTag", blank=True)
    speed = models.PositiveIntegerField(default=30)


    # six fixed bonuses instead of a JSON blob:
    strength_bonus     = models.IntegerField(default=0, help_text="Strength increase")
    dexterity_bonus    = models.IntegerField(default=0, help_text="Dexterity increase")
    constitution_bonus = models.IntegerField(default=0, help_text="Constitution increase")
    intelligence_bonus = models.IntegerField(default=0, help_text="Intelligence increase")
    wisdom_bonus       = models.IntegerField(default=0, help_text="Wisdom increase")
    charisma_bonus     = models.IntegerField(default=0, help_text="Charisma increase")
    bonus_budget = models.PositiveSmallIntegerField(
        default=4,
        help_text="Total points (fixed + free) this race may grant to ability scores."
    )
    free_points = models.PositiveSmallIntegerField(
        default=0,
        help_text="Of the bonus_budget, how many are unassigned and left for the player to allocate."
    )
    max_bonus_per_ability = models.PositiveSmallIntegerField(
        default=3,
        help_text="Maximum total bonus (fixed + free) any one ability may receive."
    )

    def clean(self):
        super().clean()
        fixed = (
            self.strength_bonus     +
            self.dexterity_bonus    +
            self.constitution_bonus +
            self.intelligence_bonus +
            self.wisdom_bonus       +
            self.charisma_bonus
        )
        if fixed + self.free_points != self.bonus_budget:
            raise ValidationError(
                f"Fixed bonuses ({fixed}) + free_points ({self.free_points}) "
                f"must equal bonus_budget ({self.bonus_budget})."
            )
        for field in (
            "strength_bonus","dexterity_bonus","constitution_bonus",
            "intelligence_bonus","wisdom_bonus","charisma_bonus"
        ):
            val = getattr(self, field)
            if val > self.max_bonus_per_ability:
                raise ValidationError(
                    {field: f"{field} ({val}) cannot exceed max_bonus_per_ability ({self.max_bonus_per_ability})."}
                )
    class Meta:
         abstract = True

# characters/models.py

from django.db import models
from django_summernote.fields import SummernoteTextField

# in characters/models.py


# models.py

class Rulebook(models.Model):
    name        = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    image       = models.ImageField(
                     upload_to="rulebook_images/",
                     blank=True, null=True
                  )
    class Meta:
        ordering = ["name"]
    def __str__(self):
        return self.name


from django.urls import reverse


class LoremasterArticle(models.Model):
    title       = models.CharField(max_length=255)
    slug        = models.SlugField(unique=True)
    excerpt     = models.TextField(blank=True, help_text="Short summary for list page")
    content     = SummernoteTextField()  # rich-text body
    cover_image = models.ImageField(upload_to="loremaster/covers/", blank=True, null=True)
    main_image  = models.ImageField(upload_to="loremaster/main/",   blank=True, null=True)
    # A simple gallery: single FK per‐image; could also use a separate GalleryImage model
    gallery     = models.ManyToManyField(
        "LoremasterImage",
        blank=True,
        related_name="articles",
    )
    published   = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Loremaster Article"
        verbose_name_plural = "Loremaster Articles"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("characters:loremaster_detail", kwargs={"slug": self.slug})


class LoremasterImage(models.Model):
    image      = models.ImageField(upload_to="loremaster/gallery/")
    caption    = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.caption or f"Image #{self.pk}"



class RulebookPage(models.Model):
    rulebook = models.ForeignKey(
        Rulebook,
        on_delete=models.CASCADE,
        related_name="pages",
    )
    
    title   = models.CharField(max_length=255)
    content = SummernoteTextField()
    order   = models.PositiveIntegerField(default=0)
    image   = models.ImageField(
        upload_to="rulebook_page_images/",
        blank=True, null=True
    )

    class Meta:
        ordering        = ["rulebook__name", "order"]
        unique_together = ("rulebook", "order")

    def __str__(self):
        return f"{self.rulebook.name} → {self.title}"


class Background(models.Model):
    code        = models.SlugField(max_length=50, unique=True)
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True, help_text="Background Summary:")

    ABILITY_CHOICES = [
        ("strength",     "Strength"),
        ("dexterity",    "Dexterity"),
        ("constitution", "Constitution"),
        ("intelligence", "Intelligence"),
        ("wisdom",       "Wisdom"),
        ("charisma",     "Charisma"),
    ]
    SELECTION_MODES = [
        ("all",     "Grant all SubSkills"),
        ("pick_one","Let user pick exactly one SubSkill"),
        ("pick_two",  "Let user pick exactly two SubSkill"),
        ("pick_three","Let user pick exactly three SubSkill"),
    ]
    # Primary bonus
    primary_ability = models.CharField(
        max_length=12, choices=ABILITY_CHOICES, default="strength",
        help_text="Which ability gets the primary bonus"
    )
    primary_bonus = models.PositiveSmallIntegerField()
    primary_selection_mode = models.CharField(
        max_length=10,
        choices=SELECTION_MODES,
        default="all",
        help_text="If primary_selection is a Skill with sub-skills, do you grant all of them or let the player choose one?"
    )
    secondary_selection_mode = models.CharField(
        max_length=10,
        choices=SELECTION_MODES,
        default="all",
        help_text="Same, but for the secondary selection."
    )

    # Primary skill (either Skill or SubSkill)
    primary_skill_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=Q(app_label="characters", model__in=["skill","subskill"]),
        related_name="+",
                null=True,
        blank=True,
    )
    primary_skill_id = models.PositiveIntegerField(
        verbose_name="Primary Skill/SubSkill ID",
        null=True, blank=True,
    )
    primary_skill    = GenericForeignKey("primary_skill_type", "primary_skill_id")
    # Secondary bonus
    secondary_ability = models.CharField(
        max_length=12, choices=ABILITY_CHOICES, default="dexterity",
        help_text="Which ability gets the secondary bonus"
    )
    secondary_bonus = models.PositiveSmallIntegerField()

    # Secondary skill (either Skill or SubSkill)

    secondary_skill_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=Q(app_label="characters", model__in=["skill","subskill"]),
        related_name="+",
        null=True,
        blank=True,
    )
    secondary_skill_id = models.PositiveIntegerField(
        verbose_name="Secondary Skill/SubSkill ID",
        null=True, blank=True,
    )
    secondary_skill    = GenericForeignKey("secondary_skill_type", "secondary_skill_id")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# register in admin.py
class Race(BaseRace):
   pass

class Subrace(BaseRace):
    race = models.ForeignKey(Race, on_delete=models.CASCADE, related_name="subraces")

    class Meta:
        unique_together = ("race","name")


# ------------------------------------------------------------------------------
# Core Character
# ------------------------------------------------------------------------------
class Character(models.Model):
    user               = models.ForeignKey(User, on_delete=models.CASCADE, related_name='characters')
    name               = models.CharField(max_length=255)
    # Stage 1 fields
    race    = models.ForeignKey(Race,    on_delete=models.SET_NULL,
                                null=True, blank=True, related_name="characters")
    subrace = models.ForeignKey(Subrace, on_delete=models.SET_NULL,
                                null=True, blank=True, related_name="characters")

    half_elf_origin    = models.CharField(max_length=20, blank=True, null = True,)
    bg_combo           = models.CharField(max_length=10, blank=True)
    main_background    = models.CharField(max_length=50, blank=True)
    side_background_1  = models.CharField(max_length=50, blank=True, null = True,)
    side_background_2  = models.CharField(max_length=50, blank=True, null = True,)
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
class RaceTag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    def __str__(self):
        return self.name


# ------------------------------------------------------------------------------
# Skills & Proficiencies
# ------------------------------------------------------------------------------

class SubSkill(models.Model):
    skill = models.ForeignKey(
        'Skill',
        on_delete=models.CASCADE,
        related_name='subskills',
        help_text="Which Skill this SubSkill falls under",
    )
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    def __str__(self):
        # show “<Skill name> – <SubSkill name>”
        return f"{self.skill.name} – {self.name}"


class ProficiencyLevel(models.Model):
    name  = models.CharField(max_length=20)  # Trained, Expert, Master
    tier  = models.IntegerField()            # 0=Trained,1=Expert,2=Master
    bonus = models.IntegerField()            # e.g. +0, +1, +2

    def __str__(self):
        return self.name


from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class CharacterSkillProficiency(models.Model):
    character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name='skill_proficiencies'
    )

    # Now required—points at either Skill or SubSkill
    selected_skill_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=models.Q(
            app_label="characters",
            model__in=["skill", "subskill"],
        ),
        verbose_name="Skill or SubSkill type",
                null=True,
        blank=True,

    )
    selected_skill_id = models.PositiveIntegerField(
        verbose_name="Skill or SubSkill ID",
        null=True,
        blank=True,
    )
    selected_skill = GenericForeignKey(
        "selected_skill_type",
        "selected_skill_id",
    )

    proficiency = models.ForeignKey(
        ProficiencyLevel,
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = (
            ("character", "selected_skill_type", "selected_skill_id"),
        )
        verbose_name = "Character Skill Proficiency"
        verbose_name_plural = "Character Skill Proficiencies"

    def __str__(self):
        return f"{self.character.name} – {self.selected_skill} ({self.proficiency})"



# ------------------------------------------------------------------------------
# Classes, Levels, Features
# ------------------------------------------------------------------------------
class ClassTag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
class AbilityScore(models.Model):
    """
    Lookup table for ability scores (e.g. Strength, Dexterity, ...)
    """
    name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class CharacterClass(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    class_ID = models.TextField(blank=True)
    hit_die     = models.PositiveSmallIntegerField(
                      choices=HIT_DIE_CHOICES,
                      default=8,
                      help_text="Your class’s Hit Die"
                  )
    
    key_abilities = models.ManyToManyField(
        AbilityScore,
        blank=False,
        help_text="Select exactly one or two key ability scores for this class."
    )    
    primary_image = models.ImageField(
        upload_to="class_images/primary/",
        blank=True,
        null=True,
        help_text="Upload the main portrait or icon for this class."
    )
    secondary_image = models.ImageField(
        upload_to="class_images/secondary/",
        blank=True,
        null=True,
        help_text="Upload a second image (e.g. a symbol or alternate art) for this class."
    )
    tertiary_image  = models.ImageField(
        upload_to="class_images/tertiary/",
        blank=True, null=True,
        help_text="Upload a thumbnail or list‐page image for this class."
    )
    tags = models.ManyToManyField(
        'ClassTag',
        blank=True,
        related_name='classes',
        help_text="High‑level archetype tags (e.g. Martial, Spellcaster…)"
    )
    def __str__(self):
        return self.name
    @property
    def primary_image_url(self):
        return self.primary_image.url if self.primary_image else ""
    @property
    def tertiary_image_url(self):
        return self.tertiary_image.url if self.tertiary_image else ""
    @property
    def secondary_image_url(self):
        return self.secondary_image.url if self.secondary_image else ""    


class SubclassGroup(models.Model):
    character_class = models.ForeignKey(
        "CharacterClass",
        on_delete=models.CASCADE,
        related_name="subclass_groups"
    )
    SYSTEM_LINEAR         = "linear"
    SYSTEM_MODULAR_LINEAR = "modular_linear"
    SYSTEM_MODULAR_MASTERY= "modular_mastery"
    SYSTEM_CHOICES = [
        (SYSTEM_LINEAR,          "Linear (fixed level)"),
        (SYSTEM_MODULAR_LINEAR,  "Modular Linear (tiered)"),
        (SYSTEM_MODULAR_MASTERY, "Modular Mastery (pick & master)"),
    ]
    system_type   = models.CharField(max_length=20, choices=SYSTEM_CHOICES, default=SYSTEM_LINEAR)
    name          = models.CharField(max_length=100, help_text="Umbrella/Order name (e.g. 'Moon Circle')")
    code          = models.CharField(max_length=20, blank=True, help_text="Optional shorthand code")
    modular_rules = models.JSONField(blank=True, null=True)  # you can still use this, but not required for modular-linear

    class Meta:
        unique_together = ("character_class", "name")
        ordering        = ["character_class", "name"]

    def __str__(self):
        return f"{self.character_class.name} – {self.name}"



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
    description = models.CharField(max_length=1000, blank=True, null=True)
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

class WeaponTrait(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    requires_value = models.BooleanField(default=False, help_text="e.g., Brutal D8/D10 etc.")

    def __str__(self):
        return self.name

class Weapon(models.Model):
    CATEGORY_CHOICES = [
        ('simple', 'Simple'),
        ('martial', 'Martial'),
        ('special', 'Special'),
    ]

    MELEE = "melee"
    RANGED = "ranged"
    RANGE_CHOICES = [(MELEE, "Melee"), (RANGED, "Ranged")]

    name           = models.CharField(max_length=100, unique=True)
    damage         = models.CharField(max_length=50)
    category       = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    is_melee       = models.BooleanField(default=True)  # keep for backwards-compat
    range_type     = models.CharField(max_length=6, choices=RANGE_CHOICES, default=MELEE)
    range_normal   = models.PositiveIntegerField(null=True, blank=True, help_text="Normal range for ranged weapons")
    range_max      = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum range")

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

class WeaponTraitValue(models.Model):
    weapon = models.ForeignKey('Weapon', on_delete=models.CASCADE)
    trait = models.ForeignKey('WeaponTrait', on_delete=models.CASCADE)
    value = models.CharField(max_length=50, blank=True, null=True, help_text="Only used if trait.requires_value=True")

    class Meta:
        unique_together = ('weapon', 'trait')

    def __str__(self):
        return f"{self.weapon.name} – {self.trait.name} {self.value or ''}".strip()


class EquipmentSlot(models.Model):
    name = models.CharField(max_length=50)
    def __str__(self): return self.name



class ArmorTrait(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField()

    def __str__(self):
        return self.name    
class Armor(models.Model):
    TYPE_CLOTHING = "clothing"
    TYPE_LIGHT    = "light"
    TYPE_MEDIUM   = "medium"
    TYPE_HEAVY    = "heavy"
    TYPE_SHIELD   = "shield"
    TYPE_CHOICES  = [
        (TYPE_CLOTHING, "Clothing"),
        (TYPE_LIGHT,    "Light"),
        (TYPE_MEDIUM,   "Medium"),
        (TYPE_HEAVY,    "Heavy"),
        (TYPE_SHIELD,   "Shield"),
    ]

    name          = models.CharField(max_length=100, unique=True)
    armor_value   = models.PositiveSmallIntegerField()
    type          = models.CharField(max_length=10, choices=TYPE_CHOICES)
    traits        = models.ManyToManyField(ArmorTrait, blank=True, help_text="Select any special traits")
    speed_penalty = models.IntegerField(help_text="Flat penalty to speed (ft)")
    hinderance    = models.IntegerField(help_text="Penalty to Str/Dex checks")

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class WearableSlot(models.Model):

    code = models.SlugField(max_length=20, unique=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class SpecialItem(models.Model):
    ITEM_TYPE_CHOICES = [
        ("weapon",     "Weapon"),
        ("armor",      "Armor"),
        ("wearable",   "Wearable"),
        ("artifact",   "Artifact"),
        ("consumable", "Consumable"),
    ]
    RARITY_CHOICES = [
        ("common",   "Common"),
        ("uncommon", "Uncommon"),
        ("rare",     "Rare"),
        ("very_rare","Very Rare"),
        ("legendary","Legendary"),
    ]


    attunement        = models.BooleanField("Attunement required", default=False)
    name              = models.CharField(max_length=100)
    slot              = models.ForeignKey(EquipmentSlot, on_delete=models.CASCADE)
    item_type         = models.CharField(max_length=12, null=True, choices=ITEM_TYPE_CHOICES)

    weapon            = models.ForeignKey(Weapon,       null=True, blank=True, on_delete=models.SET_NULL)
    armor             = models.ForeignKey(Armor,        null=True, blank=True, on_delete=models.SET_NULL)
    wearable_slot     = models.ForeignKey(WearableSlot, null=True, blank=True, on_delete=models.SET_NULL)

    enhancement_bonus = models.IntegerField(null=True, blank=True)
    rarity            = models.CharField(max_length=12, choices=RARITY_CHOICES)
    description       = models.TextField(blank=True)

    def clean(self):
        super().clean()
        # require exactly the right FK per type
        if self.item_type == "weapon"   and not self.weapon:
            raise ValidationError("Pick a Weapon when item_type=Weapon.")
        if self.item_type == "armor"    and not self.armor:
            raise ValidationError("Pick an Armor when item_type=Armor.")
        if self.item_type == "wearable" and not self.wearable_slot:
            raise ValidationError("Pick a Wearable Slot when item_type=Wearable.")
        # clear the others
        if self.item_type != "weapon":        self.weapon = None
        if self.item_type != "armor":         self.armor = None
        if self.item_type != "wearable":      self.wearable_slot = None




class SpecialItemTraitValue(models.Model):
    special_item = models.ForeignKey(SpecialItem, null= True, on_delete=models.CASCADE)
    name         = models.CharField("Trait name", null=True, max_length=100)
    active       = models.BooleanField("Active", default=False)

    # Active‐only config
    formula_target           = models.CharField(max_length=50, blank=True)
    formula                  = models.CharField(max_length=100, blank=True)
    uses                     = models.CharField(max_length=100, blank=True)
    action_type              = models.CharField(max_length=50, blank=True)
    damage_type              = models.CharField(max_length=50, blank=True)
    saving_throw_required    = models.BooleanField(default=False)
    saving_throw_type        = models.CharField(max_length=50, blank=True)
    saving_throw_granularity = models.CharField(max_length=20, blank=True)
    saving_throw_basic_success    = models.CharField(max_length=100, blank=True)
    saving_throw_basic_failure    = models.CharField(max_length=100, blank=True)
    saving_throw_critical_success = models.CharField(max_length=100, blank=True)
    saving_throw_success         = models.CharField(max_length=100, blank=True)
    saving_throw_failure         = models.CharField(max_length=100, blank=True)
    saving_throw_critical_failure= models.CharField(max_length=100, blank=True)

    # Passive‐only config
    modify_proficiency_target = models.CharField(max_length=50, blank=True)
    modify_proficiency_amount = models.CharField(max_length=50, blank=True)

    SAVING_THROW_TYPE_CHOICES = [
        ("reflex",    "Reflex"),
        ("fortitude", "Fortitude"),
        ("will",      "Will"),
    ]
    saving_throw_type = models.CharField(
        max_length=50,
        choices=SAVING_THROW_TYPE_CHOICES,
        blank=True,
        help_text="Which saving throw?",
    )

    SAVING_THROW_GRAN_CHOICES = [
        ("basic",  "Basic (Success / Failure)"),
        ("normal", "Normal (Crit / Success / Failure / Crit Failure)"),
    ]
    saving_throw_granularity = models.CharField(
        max_length=20,
        choices=SAVING_THROW_GRAN_CHOICES,
        blank=True,
        help_text="Simple or full save table?",
    )

    GAIN_RES_MODE_CHOICES = [
        ("resistance", "Resistance (half damage)"),
        ("reduction",  "Damage Reduction (flat)"),
    ]
    gain_resistance_mode = models.CharField(
        max_length=20,
        choices=GAIN_RES_MODE_CHOICES,
        blank=True,
        help_text="Resistance vs. Damage Reduction?",
    )
    description = models.TextField("Trait description", blank=True)

    class Meta:
        verbose_name = "Item Trait"
        verbose_name_plural = "Item Traits"
class CharacterSkillRating(models.Model):
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='skill_ratings')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    bonus_points = models.IntegerField(default=0, help_text="Allocated from ability score increases, NOT proficiency.")

    class Meta:
        unique_together = ('character', 'skill')

class CharacterSubSkillProficiency(models.Model):
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='subskill_proficiencies')
    selected_skill_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=models.Q(
            app_label="characters",
            model__in=["skill","subskill"],
        ),
        verbose_name="Skill or SubSkill type",
        blank = True,
        null = True
    )
    selected_skill_id = models.PositiveIntegerField(
        verbose_name="Skill or SubSkill ID",
        null=True,
        blank=True,
        help_text="(temporarily nullable so migrations can run; you can remove null=True once it’s back-filled)"
    )    
    selected_skill = GenericForeignKey("selected_skill_type", "selected_skill_id")    
    proficiency = models.ForeignKey(ProficiencyLevel, on_delete=models.CASCADE)

    class Meta:
        unique_together = (
            'character',
            'selected_skill_type',
            'selected_skill_id',
        )

class ClassFeature(models.Model):
   # ← new!
    saving_throw_required = models.BooleanField(
        default=False,
        help_text="Does this ability allow a saving throw?"
    )

    # 2) If so, which save?
    SAVING_THROW_TYPE_CHOICES = [
        ("reflex",    "Reflex"),
        ("fortitude", "Fortitude"),
        ("will",      "Will"),
    ]
    saving_throw_type = models.CharField(
        max_length=10,
        choices=SAVING_THROW_TYPE_CHOICES,
        blank=True, null=True,
        help_text="Which saving throw?"
    )
    min_level = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="(Optional) extra minimum class-level required to pick this feature, beyond tier mapping.",
    )
    SPELL_LIST_CHOICES = [
        ("arcane", "Arcane"),
        ("primal", "Primal"),
        ("occult", "Occult"),
        ("divine", "Divine"),
    ]
    spell_list = models.CharField(
        max_length=10,
        choices=SPELL_LIST_CHOICES,
        blank=True, null=True,
        help_text="Which tradition’s slots these are (Arcane/Primal/Occult/Divine)."
    )
    # (2) If this feature belongs to a modular_linear SubclassGroup, we store the "tier":  
    tier = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="(Only for modular_linear subclass_feat) Tier index (1, 2, 3, …).",
    )
    level_required = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="(Only for subclass_feats) The minimum class‐level at which this feature is actually gained."
    )
    
    # (3) If this feature belongs to a modular_mastery SubclassGroup, we store a mastery rank (0…4):
    MASTER_RANK_CHOICES = [(i, f"Rank {i}") for i in range(0, 5)]
    mastery_rank = models.PositiveIntegerField(
        choices=MASTER_RANK_CHOICES,
        blank=True,
        null=True,
        help_text="(Only for modular_mastery subclass_feat) Mastery Rank (0…4).",
    )
    # 3) Basic vs Normal
    SAVING_THROW_GRAN_CHOICES = [
        ("basic",  "Basic (Success / Failure)"),
        ("normal", "Normal (Crit Success / Success / Failure / Crit Failure)"),
    ]
    saving_throw_granularity = models.CharField(
        max_length=10,
        choices=SAVING_THROW_GRAN_CHOICES,
        blank=True, null=True,
        help_text="Simple or full save table?"
    )

    # 4a) Outcomes for basic
    SAVING_THROW_BASIC_OUTCOME_CHOICES = [
        ("success", "Success"),
        ("failure", "Failure"),
    ]
    # ─── Basic‐save outcomes ────────────────────────────────────────────────────
    saving_throw_basic_success = models.CharField(
        max_length=255, blank=True,
        help_text="What happens on a basic save: Success"
    )
    saving_throw_basic_failure = models.CharField(
        max_length=255, blank=True,
        help_text="What happens on a basic save: Failure"
    )

    # ─── Full‐save outcomes ─────────────────────────────────────────────────────
    saving_throw_critical_success = models.CharField(
        max_length=255, blank=True,
        help_text="What happens on a full save: Critical Success"
    )
    saving_throw_success = models.CharField(
        max_length=255, blank=True,
        help_text="What happens on a full save: Success"
    )
    saving_throw_failure = models.CharField(
        max_length=255, blank=True,
        help_text="What happens on a full save: Failure"
    )
    saving_throw_critical_failure = models.CharField(
        max_length=255, blank=True,
        help_text="What happens on a full save: Critical Failure"
    )


    DAMAGE_TYPE_PHYSICAL_BLUDGEONING = "physical_bludgeoning"
    DAMAGE_TYPE_PHYSICAL_SLASHING     = "physical_slashing"
    DAMAGE_TYPE_PHYSICAL_PIERCING     = "physical_piercing"
    DAMAGE_TYPE_EXPLOSIVE             = "explosive"
    DAMAGE_TYPE_MAGICAL_BLUDGEONING  = "magical_bludgeoning"
    DAMAGE_TYPE_MAGICAL_SLASHING      = "magical_slashing"
    DAMAGE_TYPE_MAGICAL_PIERCING      = "magical_piercing"
    DAMAGE_TYPE_ACID                  = "acid"
    DAMAGE_TYPE_COLD                  = "cold"
    DAMAGE_TYPE_FIRE                  = "fire"
    DAMAGE_TYPE_FORCE                 = "force"
    DAMAGE_TYPE_LIGHTNING             = "lightning"
    DAMAGE_TYPE_NECROTIC              = "necrotic"
    DAMAGE_TYPE_POISON                = "poison"
    DAMAGE_TYPE_PSYCHIC               = "psychic"
    DAMAGE_TYPE_RADIANT               = "radiant"
    DAMAGE_TYPE_THUNDER               = "thunder"
    DAMAGE_TYPE_TRUE                  = "true"

    DAMAGE_TYPE_CHOICES = [
        (DAMAGE_TYPE_PHYSICAL_BLUDGEONING,  "Physical Bludgeoning"),
        (DAMAGE_TYPE_PHYSICAL_SLASHING,      "Physical Slashing"),
        (DAMAGE_TYPE_PHYSICAL_PIERCING,      "Physical Piercing"),
        (DAMAGE_TYPE_EXPLOSIVE,              "Explosive"),
        (DAMAGE_TYPE_MAGICAL_BLUDGEONING,   "Magical Bludgeoning"),
        (DAMAGE_TYPE_MAGICAL_SLASHING,       "Magical Slashing"),
        (DAMAGE_TYPE_MAGICAL_PIERCING,       "Magical Piercing"),
        (DAMAGE_TYPE_ACID,                   "Acid"),
        (DAMAGE_TYPE_COLD,                   "Cold"),
        (DAMAGE_TYPE_FIRE,                   "Fire"),
        (DAMAGE_TYPE_FORCE,                  "Force"),
        (DAMAGE_TYPE_LIGHTNING,              "Lightning"),
        (DAMAGE_TYPE_NECROTIC,               "Necrotic"),
        (DAMAGE_TYPE_POISON,                 "Poison"),
        (DAMAGE_TYPE_PSYCHIC,                "Psychic"),
        (DAMAGE_TYPE_RADIANT,                "Radiant"),
        (DAMAGE_TYPE_THUNDER,                "Thunder"),
        (DAMAGE_TYPE_TRUE,                   "True"),
    ]

    # ← NEW FIELD
    damage_type = models.CharField(
        max_length=25,
        choices=DAMAGE_TYPE_CHOICES,
        blank=True,
        null=True,
        help_text="If this feature deals damage, pick its damage type (optional)."
    )    
    character_class = models.ForeignKey(
        CharacterClass,
        on_delete=models.CASCADE,
        related_name="features",
        help_text="Which class grants this feature?",
        null=True,    # ← allow existing rows to be empty
        blank=True,
    )

    SCOPE_CHOICES = [
        ("class_feat",        "Class Feature"),
        ("subclass_feat",     "Subclass Feature"),
        ("subclass_choice",   "Subclass Choice"),
        ("gain_subclass_feat","Gain Subclass Feature"),   # ← NEW
    ]
    scope = models.CharField(
        max_length=20,
        choices=SCOPE_CHOICES,
        default="class_feat",
        help_text="Does this belong to the base class, a subclass, or is it a subclass-choice?"
    )

    KIND_CHOICES = [
        ("class_feat",         "Class Feat"),
        ("class_trait",         "Class Trait"),
        ("skill_feat",         "Skill Feat"),
        ("martial_mastery",    "Martial Mastery"),
        ("modify_proficiency", "Modify Proficiency"),
        ("spell_table",        "Spell Slot Table"),
        ("inherent_spell",     "Inherent Spell"),
        ("gain_proficiency",   "Gain Proficiency"),
        ("gain_resistance",    "Gain Resistance"),
    ]
    gain_subskills = models.ManyToManyField(
        "SubSkill",
        blank=True,
        related_name="gained_by_features",
        help_text="Select which sub-skills this feature grants proficiency in"
    )
    
    kind = models.CharField(
        max_length=20,
        choices=KIND_CHOICES,
        default="class_feat",
        help_text="What *type* of feature this is."
    )
    modify_proficiency_target = models.CharField(
       max_length=50,        # leave room for "skill_123"
       blank=True,
       help_text="Which proficiency to modify"
   )
    modify_proficiency_amount = models.ForeignKey(
        ProficiencyTier,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        help_text="Pick the exact proficiency tier to grant (overrides current tier)"
    )
    cantrips_formula    = models.CharField(
        max_length=100, blank=True,
        help_text="Formula for number of cantrips known per class level, e.g. '1 + level//4'"
    )
    spells_known_formula = models.CharField(
        max_length=100, blank=True,
        help_text="Formula for number of spells known per class level, e.g. '2 + level//2'"
    )
    spells_prepared_formula = models.CharField(
        max_length=100, blank=True,
        help_text="Formula for number of spells you can prepare per class level, e.g. 'intelligence//2 + level//3'"
    )
    ACTIVITY_CHOICES = [
        ("active",  "Active"),
        ("passive", "Passive"),
    ]

    ACTION_TYPES = (
    ('action_1', "One Action"),
    ('action_2', "Two Actions"),
    ('action_3', "Three Actions"),
    ('reaction', "Reaction"),
    ('free',     "Free Action"),
    )    
    action_type = models.CharField(
        'Action Required',
        max_length=10,
        choices=ACTION_TYPES,
        blank=True,
        null=True,
        help_text="What kind of action this ability consumes."
    )
    GAIN_RES_MODE_CHOICES = [
        ("resistance", "Resistance (half damage)"),
        ("reduction",  "Damage Reduction (flat)"),
    ]
    gain_resistance_mode = models.CharField(
        max_length=12,
        choices=GAIN_RES_MODE_CHOICES,
        blank=True, null=True,
        help_text="Resistance vs. Damage Reduction?"
    )

    gain_resistance_types = models.JSONField(
     default=list,    # ← ensures [] instead of NULL
     blank=True,      # still allow empty
     help_text="List of damage types to which this feature applies."
)

    gain_resistance_amount = models.PositiveSmallIntegerField(
        blank=True, null=True,
        help_text="Flat reduction amount (only for ‘reduction’ mode)."
    )    
    activity_type = models.CharField(
        max_length=7,
        choices=ACTIVITY_CHOICES,
        default="active",
        help_text="For class_trait & subclass_choice: active consumes uses; passive is static."
    )
    code        = models.CharField(max_length=10, unique=True)
    name        = models.CharField(max_length=100)
    description = SummernoteTextField(blank=True)

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
        ("strength",     "Strength"),
        ("dexterity",     "Dexterity"),
        ("intelligence",     "Intelligence"),
        ("wisdom",     "Wisdom"),
        ("constitution",     "Constitution"),
        ("charisma",     "Charisma"),
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
        blank=True,         # allow it to be left blank in forms
        null=True,          # allow NULL in the database
        default=None,       # default to NULL instead of a fixed choice
        help_text="What kind of roll this formula is used for (optional)"
    )
    # … all your fields …

    def clean(self):
        """Enforce only the minimal rules outside the form. 
        “scope == 'subclass_feat' ⇒ level_required must be ≥1. 
         Otherwise we ignore it.”"""
        errors = {}
        grp     = self.subclass_group
        scope   = self.scope
        lvl_req = self.level_required
        tier    = self.tier
        master  = self.mastery_rank

        # 1) If scope is “subclass_feat,” enforce that level_required ≥ 1.
        if scope == "subclass_feat":


            # Then enforce the correct tier/mastery logic exactly as before (if you still want it here)
            if grp:
                if grp.system_type == SubclassGroup.SYSTEM_LINEAR:
                    if tier is not None:
                        errors["tier"] = "Only modular_linear features may have a Tier."
                    if master is not None:
                        errors["mastery_rank"] = "Only modular_mastery features may have a Mastery Rank."
                elif grp.system_type == SubclassGroup.SYSTEM_MODULAR_LINEAR:
                    if tier is None:
                        errors["tier"] = "This modular_linear feature must have a Tier (1,2,3…)."
                    if master is not None:
                        errors["mastery_rank"] = "Modular_linear features may not have a Mastery Rank."
                elif grp.system_type == SubclassGroup.SYSTEM_MODULAR_MASTERY:
                    if master is None:
                        errors["mastery_rank"] = "This modular_mastery feature must have a Mastery Rank (0…4)."
                    if tier is not None:
                        errors["tier"] = "Modular_mastery features may not have a Tier."

        # 2) If scope != “subclass_feat,” we simply do not care what level_required is.
        #    We do *not* add any error if level_required is non‐null or null—let the form handle it.
        #    That means we remove any “else: if lvl_req is not None: errors[…]=…” block.

        if errors:
            raise ValidationError(errors)
        return super().clean()
    def __str__(self):
        # render “<code> – <name>”, e.g. “DRUID_1 – Wild Shape”
        return f"{self.code} – {self.name}"

class ResourceType(models.Model):
    """
    A kind of pool: bloodline points, nature points, rage points, etc.
    """
    code = models.SlugField(
        max_length=50,
        unique=True,
        help_text="Identifier for formulas, e.g. 'bloodline_points'"
    )
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    
# characters/models.py

class MartialMastery(models.Model):
    name               = models.CharField(max_length=100, unique=True)
    level_required     = models.PositiveSmallIntegerField()
    description        = models.TextField(blank=True)
    points_cost        = models.PositiveIntegerField()
    classes            = models.ManyToManyField(CharacterClass, blank=True)
    all_classes        = models.BooleanField(default=False,
        help_text="If true, any class may take this mastery.")

    def __str__(self):
        return f"{self.name} (L{self.level_required}, cost {self.points_cost})"


class CharacterFeat(models.Model):
    character = models.ForeignKey(
        Character, on_delete=models.CASCADE, related_name="feats"
    )
    feat      = models.ForeignKey(
        "characters.ClassFeat", on_delete=models.CASCADE
    )
    level     = models.PositiveIntegerField()

    class Meta:
        unique_together = ("character","feat")
        verbose_name_plural = "Character Feats"




# characters/models.py (continuing after SubclassGroup)

class SubclassTierLevel(models.Model):
    """
    For each SubclassGroup and each Tier index, record the class-level at which that tier becomes unlocked.
    (You already had this.)
    """
    subclass_group = models.ForeignKey(
        "SubclassGroup",
        on_delete=models.CASCADE,
        related_name="tier_levels",
        help_text="Which group this mapping belongs to"
    )
    tier = models.PositiveIntegerField(
        help_text="Tier index (e.g. 1, 2, 3, …). Must match the integer suffix on feature.code."
    )
    unlock_level = models.PositiveIntegerField(
        help_text="Class-level at which this tier becomes available.",
        null=True,
    )

    class Meta:
        unique_together = (
            ("subclass_group", "tier"),
            ("subclass_group", "unlock_level"),
        )
        ordering = ["subclass_group", "tier"]

    def __str__(self):
        return f"{self.subclass_group.name} Tier {self.tier} → L{self.unlock_level}"




class RacialFeature(ClassFeature):
    race    = models.ForeignKey(Race,   on_delete=models.CASCADE, related_name="features")
    subrace = models.ForeignKey(Subrace, on_delete=models.CASCADE, related_name="features", blank=True, null=True)

    class Meta:
        verbose_name = "Racial Feature"
        verbose_name_plural = "Racial Features"
# in models.py
class RaceFeatureOption(models.Model):
    feature        = models.ForeignKey(
        "characters.RacialFeature",
        on_delete=models.CASCADE,
        related_name="race_options",
    )
    label          = models.CharField(max_length=100)
    grants_feature = models.ForeignKey(
        "characters.RacialFeature",
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name="race_granted_by_options",
    )

    def __str__(self):
        return self.label

class CharacterFeature(models.Model):
    character      = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name="features",
    )
    feature        = models.ForeignKey(
        "characters.ClassFeature",
        on_delete=models.CASCADE,
        related_name="character_features",
        null=True, blank=True,
    )
    racial_feature = models.ForeignKey(
        "characters.RacialFeature",
        on_delete=models.CASCADE,
        related_name="racial_character_features",
        null=True, blank=True,
    )
    option         = models.ForeignKey("characters.FeatureOption",   on_delete=models.SET_NULL, null=True, blank=True)
    subclass       = models.ForeignKey("characters.ClassSubclass",  on_delete=models.SET_NULL, null=True, blank=True)
    level          = models.PositiveIntegerField(help_text="Character level when gained")

    class Meta:
        unique_together = [("character","feature","option","subclass","level")]



class ClassResource(models.Model):
    """
    “Wizard gets Arcane Points,” “Druid gets Nature Points,” etc.
    Default points per class level, and optional cap.
    """
    character_class   = models.ForeignKey(
        CharacterClass,
        on_delete=models.CASCADE,
        related_name="resources"
    )
    resource_type     = models.ForeignKey(ResourceType, on_delete=models.CASCADE)
    formula = models.CharField(
        max_length=100,
       blank=True,
        help_text=(
          "Formula for how many points this class grants at a given level, "
          "e.g. 'ceil(level/2) + strength_modifier', "
          "or 'floor(level/3)+1', etc."
        )
    )
    max_points        = models.IntegerField(
        default=0,
        help_text="Maximum pool size (0 = no cap)"
    )

    class Meta:
        unique_together = ("character_class", "resource_type")

    def __str__(self):
        return f"{self.character_class.name} → {self.resource_type.code}"

class CharacterManualGrant(models.Model):
    character     = models.ForeignKey('Character', on_delete=models.CASCADE, related_name='manual_grants')
    content_type  = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=Q(app_label="characters", model__in=["classfeat","classfeature","racialfeature"])
    )
    object_id     = models.PositiveIntegerField()
    item          = GenericForeignKey('content_type', 'object_id')
    reason        = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class CharacterFieldOverride(models.Model):
    character = models.ForeignKey('Character', on_delete=models.CASCADE, related_name='field_overrides')
    key       = models.CharField(max_length=100)   # e.g., "HP", "temp_HP", "level", "strength"
    value     = models.CharField(max_length=50)    # store as text; cast in view if needed
    class Meta:
        unique_together = ('character','key')

class CharacterFieldNote(models.Model):
    character = models.ForeignKey('Character', on_delete=models.CASCADE, related_name='field_notes')
    key       = models.CharField(max_length=100)
    note      = models.TextField(blank=True)
    class Meta:
        unique_together = ('character','key')



class CharacterResource(models.Model):
    """
    Tracks each character’s current and max points of a given ResourceType.
    """
    character     = models.ForeignKey(Character, on_delete=models.CASCADE, related_name="pools")
    resource_type = models.ForeignKey(ResourceType, on_delete=models.CASCADE)
    current       = models.IntegerField(default=0)

    class Meta:
        unique_together = ("character", "resource_type")

    def __str__(self):
        return f"{self.character.name}: {self.resource_type.code} {self.current}/{self.maximum}"

class SpellSlotRow(models.Model):
    """
    One row per (spell_table feature × character level),
    with up to 10 slot columns.
    """
    feature = models.ForeignKey(
        ClassFeature,
        on_delete=models.CASCADE,
        related_name="spell_slot_rows"
    )
    level = models.PositiveSmallIntegerField(
        choices=[(i, f"Level {i}") for i in range(1,21)],
        help_text="Character level"
    )
    # up to 10 ranks of slots
    slot1 = models.PositiveSmallIntegerField(default=0, help_text="1st-rank slots")
    slot2 = models.PositiveSmallIntegerField(default=0, help_text="2nd-rank slots")
    slot3 = models.PositiveSmallIntegerField(default=0, help_text="3rd-rank slots")
    slot4 = models.PositiveSmallIntegerField(default=0, help_text="4th-rank slots")
    slot5 = models.PositiveSmallIntegerField(default=0, help_text="5th-rank slots")
    slot6 = models.PositiveSmallIntegerField(default=0, help_text="6th-rank slots")
    slot7 = models.PositiveSmallIntegerField(default=0, help_text="7th-rank slots")
    slot8 = models.PositiveSmallIntegerField(default=0, help_text="8th-rank slots")
    slot9 = models.PositiveSmallIntegerField(default=0, help_text="9th-rank slots")
    slot10 = models.PositiveSmallIntegerField(default=0, help_text="10th-rank slots")

    class Meta:
        unique_together = ("feature", "level")
        ordering        = ["level"]

    def __str__(self):
        return f"{self.feature.code} @ L{self.level}"

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


class UniversalLevelFeature(models.Model):
    """
    Declares, for each numeric level, whether ALL classes get
    a General Feat and/or an Ability Score Increase at that level.
    """
    level = models.PositiveIntegerField(
        unique=True,
        help_text="Character level (e.g. 1, 2, 3 …)."
    )
    grants_general_feat = models.BooleanField(
        default=False,
        help_text="If True, then at this level every class gains a General Feat."
    )
    grants_asi = models.BooleanField(
        default=False,
        help_text="If True, then at this level every class gains an ASI."
    )

    class Meta:
        ordering = ["level"]
        verbose_name = "Universal Level Feature"
        verbose_name_plural = "Universal Level Features"

    def __str__(self):
        flags = []
        if self.grants_general_feat:
            flags.append("Feat")
        if self.grants_asi:
            flags.append("ASI")
        label = ",".join(flags) or "None"
        return f"L{self.level} → {label}"

# after you determine cls & new_level:


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


    class Meta:
        unique_together = ("class_level", "feature")


    def __str__(self):
        return f"{self.class_level} → {self.feature.code}"



#GOOGLE TRANSFER STUFFF 
#MODELS FOR THEM 

from django.db import models

class Spell(models.Model):
    name = models.CharField(max_length=501)
    level = models.IntegerField()  # 0 = Cantrip
    classification = models.CharField(max_length=512, blank=True)
    description = models.TextField()
    effect = models.TextField(blank=True)
    upcast_effect = models.TextField(blank=True)
    saving_throw = models.CharField(max_length=512, blank=True)
    casting_time = models.CharField(max_length=512)
    duration = models.CharField(max_length=512)
    components = models.CharField(max_length=512)
    range = models.CharField(max_length=512)
    target = models.CharField(max_length=512)
    origin = models.CharField(max_length=512)
    sub_origin = models.CharField(max_length=512, blank=True)
    mastery_req = models.CharField(max_length=512, blank=True)
    tags = models.TextField(blank=True)
    last_synced = models.DateTimeField(auto_now=True)
    class_feature = models.OneToOneField(
        "characters.ClassFeature",
        on_delete=models.CASCADE,
        related_name="inherent_spell_data",
        blank=True,
        null=True,
        help_text="If this is an inherent‐spell feature, store its full Spell here."
    )
class ClassFeat(models.Model):
    name = models.CharField(max_length=512)
    description = models.TextField()
    level_prerequisite = models.CharField(max_length=512, blank=True)
    feat_type = models.CharField(max_length=512)
    class_name = models.CharField(max_length=512, blank=True)
    race = models.CharField(max_length=512, blank=True)
    tags = models.TextField(blank=True)
    prerequisites = models.TextField(blank=True)
    last_synced = models.DateTimeField(auto_now=True)

    def __str__(self):
        # show just the name (you can append level_prerequisite if you like)
        return self.name