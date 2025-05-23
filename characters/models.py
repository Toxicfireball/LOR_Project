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
    modular_rules = models.JSONField(
    blank=True, null=True,
    help_text="Extra numbers for modular systems (e.g. {modules_per_mastery:2, max_mastery_3:1})"
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
        ("class_feat",      "Class Feature"),
        ("subclass_feat",   "Subclass Feature"),
        ("subclass_choice", "Subclass Choice"),
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
    ]

    
    kind = models.CharField(
        max_length=20,
        choices=KIND_CHOICES,
        default="class_feat",
        help_text="What *type* of feature this is."
    )
    modify_proficiency_target = models.CharField(
        max_length=20,
        choices=PROFICIENCY_TYPES,
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
    activity_type = models.CharField(
        max_length=7,
        choices=ACTIVITY_CHOICES,
        default="active",
        help_text="For class_trait & subclass_choice: active consumes uses; passive is static."
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


    def __str__(self):
        return f"{self.character_class.name}: {self.code} – {self.name}"
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
