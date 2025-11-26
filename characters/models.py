from django.db import models
from django.contrib.auth.models import User
from campaigns.models import Campaign  # Make sure the campaigns app is created and in INSTALLED_APPS
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.db.models import Max, Sum, Q
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
# ── add near your other constants ──────────────────────────────────────────────
ARMOR_GROUPS = [
    ("unarmored", "Unarmored"),   # maps to Clothing / no armor
    ("light",     "Light"),
    ("medium",    "Medium"),
    ("heavy",     "Heavy"),
    ("shield",    "Shield"),
]

WEAPON_GROUPS = [
    ("unarmed", "Unarmed"),
    ("simple",  "Simple"),
    ("martial", "Martial"),
    ("special", "Special"),
    ('black_powder', "Black Powder")
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

from django.conf import settings
from django.db import models
from django.utils import timezone
import uuid
from math import floor
from django.contrib.contenttypes.models import ContentType
class CharacterViewer(models.Model):
    character  = models.ForeignKey("characters.Character", on_delete=models.CASCADE, related_name="viewers")
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="character_views")
    added_by   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="granted_character_views")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("character", "user"),)

    def __str__(self):
        return f"{self.user} → {self.character}"

class CharacterShareInvite(models.Model):
    character     = models.ForeignKey("characters.Character", on_delete=models.CASCADE, related_name="share_invites")
    invited_email = models.EmailField(db_index=True)
    invited_user  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    token         = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_by    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_character_invites")
    created_at    = models.DateTimeField(auto_now_add=True)
    expires_at    = models.DateTimeField()
    accepted_at   = models.DateTimeField(null=True, blank=True)
    revoked_at    = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=7)
        # best-effort link to an existing account
        if self.invited_email and not self.invited_user:
            from django.contrib.auth import get_user_model
            U = get_user_model()
            self.invited_user = U.objects.filter(email__iexact=self.invited_email.strip()).first()
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return self.revoked_at is None and self.accepted_at is None and timezone.now() < self.expires_at

    def __str__(self):
        return f"{self.invited_email} → {self.character}"

class NoteCategory(models.Model):
    character = models.ForeignKey('Character', on_delete=models.CASCADE, related_name='note_categories')
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('character', 'name')
        ordering = ['name']

    def __str__(self):
        return self.name


class CharacterNote(models.Model):
    character = models.ForeignKey('Character', on_delete=models.CASCADE, related_name='notes')
    category = models.ForeignKey(NoteCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='notes')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='character_notes/%Y/%m/%d/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

# ──────────────────────────────────────────────────────────────────────────────
# Prestige Classes (additive, does not change existing models)
# ──────────────────────────────────────────────────────────────────────────────
from django.db import models
from django.core.exceptions import ValidationError

# Reuse existing types you already have:
# CharacterClass, Skill, ProficiencyTier, Race, Subrace, ClassTag, RaceTag, ClassFeature


class Character(models.Model):

    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("active", "Active"),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
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
    details_image = models.ImageField(upload_to='character_details/%Y/%m/%d/', blank=True, null=True)
    strength           = models.IntegerField(default=8)
    dexterity          = models.IntegerField(default=8)
    constitution       = models.IntegerField(default=8)
    intelligence       = models.IntegerField(default=8)
    wisdom             = models.IntegerField(default=8)
    charisma           = models.IntegerField(default=8)
    # progression
    level              = models.PositiveIntegerField(default=0)
    backstory          = SummernoteTextField(blank=True)
    campaign           = models.ForeignKey(
                            Campaign,
                            on_delete=models.SET_NULL,
                            null=True, blank=True,
                            related_name="characters"
                        )
    created_at         = models.DateTimeField(auto_now_add=True)
    worshipped_gods      = SummernoteTextField(blank=True)
    believers_and_ideals = SummernoteTextField(blank=True)   # “Believers and ideals”
    iconic_strengths     = SummernoteTextField(blank=True)   # “Iconic (Strength)”
    iconic_flaws         = SummernoteTextField(blank=True)   # “Iconic (Flaws)”
    bonds_relationships  = SummernoteTextField(blank=True)
    ties_connections     = SummernoteTextField(blank=True)
    outlook              = SummernoteTextField(blank=True)
    appearance              = SummernoteTextField(blank=True)
    # characters/models.py (inside Character)
    gold   = models.IntegerField(default=0)
    silver = models.IntegerField(default=0)
    copper = models.IntegerField(default=0)
    speed = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Leave blank to use your race's default."
    )
    attunement_max = models.PositiveSmallIntegerField(
        default=5,
        help_text="Maximum number of magic items this character can be attuned to at once."
    )
    # characters/models.py (inside class Character)


    def ability_mod(self, key: str) -> int:
        val = int(getattr(self, key, 10) or 10)
        return floor((val - 10) / 2)

    @property
    def dex_mod(self): return self.ability_mod("dexterity")
    @property
    def con_mod(self): return self.ability_mod("constitution")
    @property
    def wis_mod(self): return self.ability_mod("wisdom")

    def _base_prof_bonus(self, code: str) -> int:
        """
        Read the highest proficiency tier (bonus) this character reaches for `code`
        from class progression rows. We look across ALL classes the character has,
        using their current level in each class.
        """
        from .models import ClassProficiencyProgress, ProficiencyTier, CharacterClassProgress
        best = 0
        for cp in CharacterClassProgress.objects.filter(character=self).select_related("character_class"):
            if cp.levels <= 0:
                continue
            # generic (non-weapon/non-armor group) rows for this progression
            rows = (ClassProficiencyProgress.objects
                    .filter(character_class=cp.character_class,
                            proficiency_type=code,
                            at_level__lte=cp.levels,
                            armor_group__isnull=True,
                            weapon_group__isnull=True)
                    .select_related("tier"))
            if rows.exists():
                best = max(best, max(r.tier.bonus for r in rows if r.tier and isinstance(r.tier.bonus, int)))
        return int(best)

    def _feature_or_item_prof_override(self, code: str) -> int:
        """
        If any ClassFeature (kind=modify_proficiency) or active item trait sets a tier,
        use the highest bonus among them. (Treat as override, not a stack.)
        """
        from .models import SpecialItemTraitValue, SpecialItem, CharacterFeature
        best = 0

        # from features
        feats = (self.features
                .filter(feature__kind="modify_proficiency",
                        feature__modify_proficiency_target=code,
                        feature__modify_proficiency_amount__isnull=False)
                .select_related("feature__modify_proficiency_amount"))
        for cf in feats:
            t = cf.feature.modify_proficiency_amount
            if t and isinstance(t.bonus, int):
                best = max(best, t.bonus)

        # from active special items (if you toggle them with CharacterActivation)
        si_ct = ContentType.objects.get_for_model(SpecialItem)
        active_item_ids = list(self.activations.filter(content_type=si_ct, is_active=True)
                            .values_list("object_id", flat=True))
        if active_item_ids:
            for tv in SpecialItemTraitValue.objects.filter(
                special_item_id__in=active_item_ids,
                modify_proficiency_target=code
            ):
                try:
                    best = max(best, int(tv.modify_proficiency_amount))
                except (TypeError, ValueError):
                    pass
        return int(best)

    def _prof_bonus(self, code: str) -> int:
        """
        Final proficiency bonus for `code`: max(class progression, feature/item override).
        """
        return max(self._base_prof_bonus(code), self._feature_or_item_prof_override(code))

    def skill_total(self, skill_name: str) -> int:
        """
        If you treat Perception as a Skill, this gives ability mod + proficiency + any extra points.
        """
        from .models import Skill, CharacterSkillProficiency, CharacterSkillRating
        try:
            sk = Skill.objects.get(name__iexact=skill_name.strip())
        except Skill.DoesNotExist:
            return 0
        total = self.ability_mod(sk.ability)

        skill_ct = ContentType.objects.get_for_model(Skill)
        prof = (self.skill_proficiencies
                .filter(selected_skill_type=skill_ct, selected_skill_id=sk.id)
                .select_related("proficiency")
                .first())
        if prof and prof.proficiency and isinstance(prof.proficiency.bonus, int):
            total += prof.proficiency.bonus

        rating = self.skill_ratings.filter(skill=sk).first()
        if rating:
            total += int(rating.bonus_points or 0)
        return total

        # ceil(level/2)
        return (int(self.level or 0) + 1) // 2

    def _is_trained(self, code: str) -> bool:
        # Treat any positive tier bonus as trained
        try:
            return int(self._prof_bonus(code) or 0) > 0
        except Exception:
            return False

    @property
    def passive_perception(self) -> int:
        """
        10 + proficiency (Perception) + ceil(level/2) + WIS mod.
        Uses the higher of class-based 'perception' proficiency or the Perception Skill proficiency.
        """
        wis = self.wis_mod
        half_level = self._half_level_up()

        class_prof = int(self._prof_bonus("perception") or 0)
        skill_prof = 0
        try:
            from django.contrib.contenttypes.models import ContentType
            from .models import Skill
            sk = Skill.objects.get(name__iexact="Perception")
            skill_ct = ContentType.objects.get_for_model(Skill)
            sp = (self.skill_proficiencies
                    .filter(selected_skill_type=skill_ct, selected_skill_id=sk.id)
                    .select_related("proficiency")
                    .first())
            if sp and sp.proficiency and isinstance(sp.proficiency.bonus, int):
                skill_prof = int(sp.proficiency.bonus)
        except Exception:
            pass

        prof = max(class_prof, skill_prof)
        return 10 + prof + half_level + wis

    @property
    def dodge_total(self) -> int:
        # Base (the view may add shield & dex-cap logic)
        prof = int(self._prof_bonus("dodge") or 0)
        return 10 + self.dex_mod + prof + (self._half_level_up() if prof > 0 else 0)

    @property
    def reflex_save(self) -> int:
        prof = int(self._prof_bonus("reflex") or 0)
        return self.dex_mod + prof + (self._half_level_up() if prof > 0 else 0)

    @property
    def fortitude_save(self) -> int:
        prof = int(self._prof_bonus("fortitude") or 0)
        return self.con_mod + prof + (self._half_level_up() if prof > 0 else 0)

    @property
    def will_save(self) -> int:
        prof = int(self._prof_bonus("will") or 0)
        return self.wis_mod + prof + (self._half_level_up() if prof > 0 else 0)

    def _equipped_armor_item(self):
        """
        Super simple: take the active SpecialItem with the highest armor_value.
        If you track equip differently, replace this with your real 'equipped' lookup.
        """
        from .models import SpecialItem
        si_ct = ContentType.objects.get_for_model(SpecialItem)
        best = None
        for act in self.activations.filter(content_type=si_ct, is_active=True):
            si = act.target  # SpecialItem
            if getattr(si, "armor", None) and getattr(si.armor, "armor_value", None) is not None:
                if best is None or si.armor.armor_value > best.armor.armor_value:
                    best = si
        return best

    @property
    def armor_total(self) -> int:
        eq = self._equipped_armor_item()
        return int(eq.armor.armor_value) if eq and eq.armor else 0


    def owner_name(self) -> str:
        return getattr(self.user, "username", "—")

    @property
    def effective_speed(self) -> int:
        # prefer explicit character override
        if self.speed is not None:
            return int(self.speed)
        # then subrace (if your Subrace has .speed), else race
        if self.subrace and hasattr(self.subrace, "speed") and self.subrace.speed:
            return int(self.subrace.speed)
        if self.race and hasattr(self.race, "speed") and self.race.speed:
            return int(self.race.speed)
        return 30  # final fallback
    # characters/models.py  (INSIDE class Character)
    def class_level_for(self, base_class: "CharacterClass") -> int:
        """
        Return HOW MANY levels this character has in a specific base class.
        Uses CharacterClassProgress (you already have it).
        """
        return (
            self.class_progress
            .filter(character_class=base_class)
            .values_list("levels", flat=True)
            .first()
        ) or 0

    def __str__(self):
        # What shows in dropdowns, admin, etc.
        return self.name or f"Character #{self.pk}"
    def mastery_for(self, subclass: "ClassSubclass") -> int:
        """
        Current tier = floor(modules_taken / modules_required).
        No unlock-level gates are used for modular mastery.
        """
        grp = getattr(subclass, "group", None)
        if not grp or grp.system_type != SubclassGroup.SYSTEM_MODULAR_MASTERY:
            return 0

        taken = CharacterFeature.objects.filter(
            character=self, subclass=subclass, feature__scope="subclass_feat",
        ).count()
        per = max(1, int(getattr(grp, "modules_per_mastery", 2)))
        # 1-based tiers: at 0 modules you are Tier 1; tier increases every `per` modules.
        return 1 + (taken // per)


    def _cap_from_gainers(self, base_class: "CharacterClass", group: "SubclassGroup", lvl: int) -> int:
        """
        Look at the ClassLevelFeatures for THIS exact class level that point to
        features with scope='gain_subclass_feat' in the same modular_mastery group,
        and use the highest mastery_rank among them as the cap for this level.
        """
        from .models import ClassLevelFeature, ClassFeature
        return (
            ClassLevelFeature.objects
            .filter(
                class_level__character_class=base_class,
                class_level__level=lvl,
                feature__scope="gain_subclass_feat",
                feature__subclass_group=group,
            )
            .aggregate(models.Max("feature__mastery_rank"))["feature__mastery_rank__max"]
            or 0
        )

    def _cap_from_rank_gates(self, group: "SubclassGroup", base_class: "CharacterClass") -> int:
        """
        Respect SubclassMasteryUnlock level gates (if you use them).
        """
        cls_lvl = self.class_level_for(base_class)
        from .models import SubclassMasteryUnlock
        return (
            SubclassMasteryUnlock.objects
            .filter(subclass_group=group, unlock_level__lte=cls_lvl)
            .aggregate(models.Max("rank"))["rank__max"]
            or 0
        )


    def mastery_pick_options(self, subclass, preview_level=None, gainer_cap=None):
        """
        Return (allowed_cap, queryset) for modular mastery picks.
        - Tier is 1-based: 0 modules ⇒ Tier 1.
        - 'gainer_cap' is the Mastery Rank on the *gain_subclass_feat* trigger (max tier allowed).
        - We do *not* apply level gating for mastery; only tier + 'modules required'.
        """
        grp = getattr(subclass, "subclass_group", None) or getattr(subclass, "group", None)
        if not grp:
            return 0, ClassFeature.objects.none()

        # modules needed to increase tier (a.k.a. "Modules Required")
        per = getattr(grp, "modules_per_mastery", None)
        if not per or int(per) <= 0:
            per = getattr(grp, "modules_required", 2)
        per = max(1, int(per))

        # how many modules already taken in THIS subclass
        taken = (CharacterFeature.objects
                 .filter(character=self,
                         subclass=subclass,
                         feature__scope='subclass_feat')
                 .count())

        current_tier = 1 + (taken // per)   # 1-based
        # cap from the gainer (if None, don't reduce below current_tier)
        cap = int(gainer_cap) if gainer_cap is not None else current_tier
        allowed_cap = max(1, min(current_tier, cap))

        # feature ids already owned in this subclass (exclude)
        owned_ids = list(CharacterFeature.objects
                         .filter(character=self,
                                 subclass=subclass,
                                 feature__scope='subclass_feat')
                         .values_list("feature_id", flat=True))

        # eligible modules for this subclass at tier ≤ allowed_cap
        # accept either .tier or .mastery_rank as the module's tier field
        qs = (ClassFeature.objects
              .filter(scope='subclass_feat',
                      subclass_group=grp,
                      subclasses=subclass)
              .filter(
                  Q(tier__isnull=True) | Q(tier__lte=allowed_cap) |
                  Q(mastery_rank__isnull=True) | Q(mastery_rank__lte=allowed_cap)
              )
              .exclude(pk__in=owned_ids)
              .order_by('tier', 'mastery_rank', 'name'))

        return allowed_cap, qs
    


# characters/models.py
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class CharacterItem(models.Model):
    character = models.ForeignKey('Character', on_delete=models.CASCADE, related_name='inventory_items')

    # what the item actually is (Weapon, Armor, etc.) — ✅ make optional
    item_content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, blank=True, null=True)  # was on_delete=CASCADE, required
    item_object_id    = models.PositiveIntegerField(blank=True, null=True)  # was required
    item              = GenericForeignKey('item_content_type', 'item_object_id')

    # ✅ new: native free-text support (no catalog object)
    is_custom   = models.BooleanField(default=False)
    name        = models.CharField(max_length=120, blank=True, default="")
    is_equipped = models.BooleanField(default=False)
    quantity    = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True, null=True)

    from_party_item = models.ForeignKey(
        'campaigns.PartyItem',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='claimed_by_characters'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

class WearableSlot(models.Model):

    code = models.SlugField(max_length=20, unique=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class CharacterWearable(models.Model):
    """
    For each character and WearableSlot, remember which inventory item is equipped.
    Slots themselves come from WearableSlot rows.
    """
    character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name="wearables",
    )
    slot = models.ForeignKey(
        WearableSlot,
        on_delete=models.CASCADE,
        related_name="equipped_by",
    )
    item = models.ForeignKey(
        CharacterItem,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="equipped_in_wearable_slots",
    )

    class Meta:
        unique_together = (("character", "slot"),)

    def __str__(self):
        base = f"{self.character} – {self.slot.name}"
        if self.item:
            base += f": {self.item.name or getattr(self.item.item, 'name', '')}"
        return base
class PendingBackground(models.Model):
    """Player-proposed background awaiting GM approval. Mirrors Background fields 1:1."""
    # link it to a campaign optionally; GM of that campaign can approve
    campaign = models.ForeignKey(
        'campaigns.Campaign', null=True, blank=True, on_delete=models.CASCADE, related_name='pending_backgrounds'
    )

    requested_by = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='pending_backgrounds')

    # same shape as Background (use your actual field names)
    code = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)

    primary_ability = models.CharField(max_length=32, choices=Background._meta.get_field('primary_ability').choices)
    primary_bonus   = models.IntegerField(default=2)
    secondary_ability = models.CharField(max_length=32, choices=Background._meta.get_field('secondary_ability').choices, blank=True)
    secondary_bonus   = models.IntegerField(default=1)

    # skill selections (ContentType + id), same approach as Background
    primary_skill_type   = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    primary_skill_id     = models.PositiveIntegerField(null=True, blank=True)
    secondary_skill_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    secondary_skill_id   = models.PositiveIntegerField(null=True, blank=True)

    # mirror your selection_mode strings if present
    primary_selection_mode   = models.CharField(max_length=16, default=getattr(Background, 'DEFAULT_MODE', 'fixed'))
    secondary_selection_mode = models.CharField(max_length=16, blank=True, default=getattr(Background, 'DEFAULT_MODE', 'fixed'))

    # workflow
    STATUS = (("pending","Pending"),("approved","Approved"),("rejected","Rejected"))
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    gm_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):  # pragma: no cover
        base = f"{self.name} ({self.code})"
        if self.campaign_id:
            base += f" @ {self.campaign.name}"
        return base

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


# ──────────────────────────────────────────────────────────────────────────────
# Skill System (global): upgrade costs and level gates
# ──────────────────────────────────────────────────────────────────────────────
SKILL_RANKS = [
    ("untrained", "Untrained"),
    ("trained",   "Trained"),
    ("expert",    "Expert"),
    ("master",    "Master"),
    ("legendary", "Legendary"),
]

class SkillProficiencyUpgrade(models.Model):
    """
    Global rule rows that the client can read to know:
      - how many points it costs to upgrade from A → B
      - the minimum *character level* required for that upgrade
    Example rows you will seed:
      untrained→trained:  points=1, min_level=0
      trained  →expert :  points=2, min_level=3
      expert   →master :  points=3, min_level=7
      master   →legend.:  points=5, min_level=14
    """
    from_rank   = models.CharField(max_length=12, choices=SKILL_RANKS)
    to_rank     = models.CharField(max_length=12, choices=SKILL_RANKS)
    points      = models.PositiveSmallIntegerField()
    min_level   = models.PositiveIntegerField(default=0,
                    help_text="Minimum CHARACTER level to perform this upgrade")

    class Meta:
        unique_together = (("from_rank", "to_rank"),)
        ordering = ["points", "min_level", "from_rank", "to_rank"]

    def __str__(self):
        return f"{self.from_rank.title()} → {self.to_rank.title()} (cost {self.points}, L{self.min_level}+)"

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
    starting_skills_formula = models.CharField(
        max_length=200,
        blank=True,
        help_text=(
            "Formula for the number of skills you start trained in at level 1. "
            "Examples: '2', '2 + int_mod', '1 + floor((intelligence-10)/2)'."
        ),
    )
    skill_points_per_level = models.PositiveSmallIntegerField(
        default=1,
        help_text="How many skill points this class grants each time you gain a level in it.",
    )   
    key_abilities = models.ManyToManyField(
        AbilityScore,
        blank=True,
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
    system_type   = models.CharField(max_length=32, choices=SYSTEM_CHOICES, default=SYSTEM_LINEAR)
    name          = models.CharField(max_length=100, help_text="Umbrella/Order name (e.g. 'Moon Circle')")
    code          = models.CharField(max_length=20, blank=True, help_text="Optional shorthand code")
    modular_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text='Example: {"modules_per_mastery":2, "picks_per_trigger":1, "max_mastery_rank":3}'
    )
    modules_per_mastery = models.PositiveSmallIntegerField(
        default=2,
        help_text="Default modules needed to earn +1 mastery rank (used by modular_mastery groups)."
    )
    class Meta:
        unique_together = ("character_class", "name")
        ordering        = ["character_class", "name"]

    def __str__(self):
        return f"{self.character_class.name} – {self.name}"

# models.py
class CharacterSkillPointTx(models.Model):
    SOURCE_CHOICES = [
        ("level_award", "Level Award"),
        ("spend",       "Spend on Skill"),
        ("refund",      "Refund (Retrain)"),
        ("admin",       "Admin/Adjustment"),
    ]
    character     = models.ForeignKey("Character", related_name="skill_point_txs", on_delete=models.CASCADE)
    amount        = models.IntegerField(help_text="Positive=grant/refund, negative=spend")
    source        = models.CharField(max_length=16, choices=SOURCE_CHOICES)
    reason        = models.CharField(max_length=255, blank=True)
    at_level      = models.IntegerField(default=0)
    awarded_class = models.ForeignKey("CharacterClass", null=True, blank=True, on_delete=models.SET_NULL)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    @staticmethod
    def balance_for(character):
        from django.db.models import Sum
        return (character.skill_point_txs.aggregate(t=Sum("amount"))["t"] or 0)


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
    character_class  = models.ForeignKey('CharacterClass', on_delete=models.CASCADE, related_name="prof_progress")
    proficiency_type = models.CharField(max_length=20, choices=PROFICIENCY_TYPES)
    armor_group  = models.CharField(max_length=10, choices=ARMOR_GROUPS, blank=True, null=True)
    weapon_group = models.CharField(max_length=20, choices=WEAPON_GROUPS, blank=True, null=True)
    at_level     = models.PositiveIntegerField()
    tier         = models.ForeignKey('ProficiencyTier', on_delete=models.PROTECT)
    armor_item   = models.ForeignKey('Armor',  on_delete=models.PROTECT, blank=True, null=True)
    weapon_item  = models.ForeignKey('Weapon', on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        ordering = ["character_class", "proficiency_type", "at_level"]


    def clean(self):
        # keep this no-op, that’s fine
        super().clean()

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

# at top
from django.contrib.postgres.fields import ArrayField

class Weapon(models.Model):
    CATEGORY_CHOICES = [
        ('simple', 'Simple'),
        ('martial', 'Martial'),
        ('special', 'Special'),
        ('black powder', "Black Powder")
    ]
    MELEE, RANGED = "melee", "ranged"
    RANGE_CHOICES = [(MELEE, "Melee"), (RANGED, "Ranged")]

    DAMAGE_CHOICES = [
        ('bludgeoning', 'Bludgeoning'),
        ('piercing',    'Piercing'),
        ('slashing',    'Slashing'),
        ('explosive',    'Explosives'),
        
    ]

    name         = models.CharField(max_length=100, unique=True)
    damage       = models.CharField(max_length=50)
    category     = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    is_melee     = models.BooleanField(default=True)
    range_type   = models.CharField(max_length=6, choices=RANGE_CHOICES, default=MELEE)
    range_normal = models.PositiveIntegerField(null=True, blank=True)
    range_max    = models.PositiveIntegerField(null=True, blank=True)

    # ⬇️ replace the old CharField with ArrayField
    damage_types = ArrayField(
        base_field=models.CharField(max_length=30, choices=DAMAGE_CHOICES),
        default=list,
        blank=True,
        help_text="Select one or more damage types."
    )

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
    strength_requirement = models.PositiveSmallIntegerField(
        blank=True, null=True,
        help_text="Minimum Strength to wear effectively (optional)."
    )
    name          = models.CharField(max_length=100, unique=True)
    armor_value   = models.PositiveSmallIntegerField()
    type          = models.CharField(max_length=10, choices=TYPE_CHOICES)
    traits        = models.ManyToManyField(ArmorTrait, blank=True, help_text="Select any special traits")
    speed_penalty = models.IntegerField(help_text="Flat penalty to speed (ft)")
    hinderance    = models.IntegerField(help_text="Penalty to Str/Dex checks")
    dex_cap = models.IntegerField(help_text="10 + dex cap for dodge", blank=True, null=True)
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"
    def group_code(self) -> str:
            return "unarmored" if self.type == self.TYPE_CLOTHING else self.type


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
    slot = models.ForeignKey(
        EquipmentSlot,
        null=True, blank=True,             
        on_delete=models.SET_NULL          
    )    
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
    def __str__(self):
        bits = [self.name]
        if self.enhancement_bonus:
            bits.append(f"+{self.enhancement_bonus}")
        if self.rarity:
            bits.append(self.get_rarity_display())
        return " ".join(bits)


class SpecialItemTraitValue(models.Model):
    special_item = models.ForeignKey(SpecialItem, null= True, on_delete=models.CASCADE)
    name         = models.CharField("Trait name", null=True, max_length=100)
    active       = models.BooleanField("Active", default=False)

    # Active‐only config
    formula_target           = models.CharField(max_length=50,null=True, blank=True)
    formula                  = models.CharField(max_length=100,null=True, blank=True)
    uses                     = models.CharField(max_length=100, null=True,blank=True)
    action_type              = models.CharField(max_length=50,null=True, blank=True)
    damage_type              = models.CharField(max_length=50, null=True,blank=True)
    saving_throw_required    = models.BooleanField(null=True,default=False)
    saving_throw_type        = models.CharField(max_length=50, null=True,blank=True)
    saving_throw_granularity = models.CharField(max_length=20,null=True, blank=True)
    saving_throw_basic_success    = models.CharField(max_length=100,null=True, blank=True)
    saving_throw_basic_failure    = models.CharField(max_length=100,null=True, blank=True)
    saving_throw_critical_success = models.CharField(max_length=100,null=True, blank=True)
    saving_throw_success         = models.CharField(max_length=100,null=True, blank=True)
    saving_throw_failure         = models.CharField(max_length=100,null=True, blank=True)
    saving_throw_critical_failure= models.CharField(max_length=100,null=True, blank=True)

    # Passive‐only config
    modify_proficiency_target = models.CharField(max_length=50,null=True, blank=True)
    modify_proficiency_amount = models.CharField(max_length=50,null=True, blank=True)

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
    gain_resistance_types = models.JSONField(
        default=list, blank=True,
        help_text="List of damage types this trait applies to.",
    )
    gain_resistance_amount = models.PositiveSmallIntegerField(
        blank=True, null=True,
        help_text="Flat reduction (only when mode = reduction).",
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
    # characters/models.py (inside ClassFeature)
    martial_points_formula = models.CharField(
        max_length=100, blank=True, null=True, default=None,
        help_text="(Only for kind='martial_mastery') Formula for the Martial Mastery points this class grants."
    )
    available_masteries_formula = models.CharField(
        max_length=100, blank=True, null=True, default=None,
        help_text="(Only for kind='martial_mastery') Formula for how many masteries are available at this class level."
    )
    mastery_rank = models.PositiveIntegerField(null=True, blank=True)
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
        help_text=(
            "(modular_mastery) For scope='subclass_feat': the module's rank (0–4). "
            "For scope='gain_subclass_feat': the MAX rank this level allows you to pick up to."
        ),
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
        ("core_proficiency",   "Add Core Proficiency (Armor/Weapon)"),
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
    def __str__(self):
        # keep it compact but informative
        left = []
        if self.character_class_id:
            left.append(self.character_class.name)
        if self.subclass_group_id:
            left.append(self.subclass_group.name)

        right = self.name or self.code or f"Feature #{self.pk}"
        # optional helpful bits:
        if self.tier:
            right += f" (Tier {self.tier})"
        if self.mastery_rank is not None:
            right += f" (Rank {self.mastery_rank})"
        if self.level_required:
            right += f" @L{self.level_required}"
        if self.code:
            right += f" [{self.code}]"

        return " – ".join(left + [right]) if left else right
    def clean(self):
        super().clean()

        grp   = self.subclass_group
        scope = self.scope

        # Only subclass features must name an umbrella
        if scope in ("subclass_feat", "gain_subclass_feat") and not grp:
            from django.core.exceptions import ValidationError
            raise ValidationError({"subclass_group": "Pick an umbrella (SubclassGroup) for subclass features."})

        # If no group, nothing else to normalize
        if not grp:
            self.tier = None
            self.mastery_rank = None
            return

        # Normalize by system, avoiding hard failures
        if grp.system_type == SubclassGroup.SYSTEM_MODULAR_MASTERY:
            # REQUIRED: rank on subclass modules & gainers (it's your core structure)
            if scope in ("subclass_feat", "gain_subclass_feat") and self.mastery_rank is None:
                from django.core.exceptions import ValidationError
                raise ValidationError({"mastery_rank": "Set a mastery rank (0–4)."})
            # Not used here
            self.tier = None

        elif grp.system_type == SubclassGroup.SYSTEM_MODULAR_LINEAR:
            # Minimal requirement: tier on subclass modules; no level_required enforcement
            if scope == "subclass_feat" and self.tier is None:
                from django.core.exceptions import ValidationError
                raise ValidationError({"tier": "Set a Tier (1,2,3…)."})
            # Not used here
            self.mastery_rank = None

        else:  # linear
            self.tier = None
            self.mastery_rank = None


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

# characters/models.py

class MartialMastery(models.Model):
    name           = models.CharField(max_length=100, unique=True)
    level_required = models.PositiveSmallIntegerField()
    description    = SummernoteTextField(blank=True)
    points_cost    = models.PositiveIntegerField()
    restrict_by_ability     = models.BooleanField(
        default=False,
        help_text="If checked, a character must meet the minimum score below."
    )
    required_ability        = models.CharField(
        max_length=12,
        choices=ABILITY_CHOICES,
        blank=True, null=True,
        help_text="Which ability this requirement targets."
    )
    required_ability_score  = models.PositiveSmallIntegerField(
        blank=True, null=True,
        help_text="Minimum ability score needed (e.g., 13)."
    )
    # characters/models.py  (inside class MartialMastery)
    TRAIT_MATCH_CHOICES = [
        ("any", "Match ANY of the selected traits"),
        ("all", "Match ALL of the selected traits"),
    ]
    restrict_to_range    = models.BooleanField(
        default=False,
        help_text="When on, limit to the selected weapon range types (melee/ranged)."
    )
    allowed_range_types  = models.JSONField(
        default=list, blank=True,
        help_text="Values: 'melee' and/or 'ranged'. Leave empty if not restricting."
    )
    trait_match_mode = models.CharField(
        max_length=3,
        choices=TRAIT_MATCH_CHOICES,
        default="any",
        help_text="When restricting to traits, require the weapon to match ANY vs ALL selected traits."
    )

    ACTION_TYPES = (
        ('action_1', "One Action"),
        ('action_2', "Two Actions"),
        ('action_3', "Three Actions"),
        ('reaction', "Reaction"),
        ('free',     "Free Action"),
    )
    is_rare = models.BooleanField(
        default=False,
        help_text="If checked, this mastery is rare/unusual."
    )
    action_cost = models.CharField(
        max_length=10,
        choices=ACTION_TYPES,
        blank=True,
        null=True,
        help_text="How many actions this mastery takes to use (if applicable)."
    )
    classes        = models.ManyToManyField(CharacterClass, blank=True)
    all_classes    = models.BooleanField(
        default=False,
        help_text="If true, any class may take this mastery."
    )

    # NEW: restriction toggles
    restrict_to_weapons = models.BooleanField(
        default=False,
        help_text="If checked, this mastery only applies to selected weapons."
    )
    restrict_to_traits = models.BooleanField(
        default=False,
        help_text="If checked, this mastery only applies to weapons having any of the selected traits."
    )
    # Toggle: restrict by damage types?
    restrict_to_damage = models.BooleanField(
        default=False,
        help_text="If checked, this mastery only applies to weapons that deal any of the selected damage types."
    )

    # Store the allowed damage types (same codes as Weapon.DAMAGE_CHOICES).
    # Use JSONField to stay DB-agnostic (your project already uses JSONField elsewhere).
    allowed_damage_types = models.JSONField(
        default=list,
        blank=True,
        help_text="List of allowed damage types. Uses Weapon.DAMAGE_CHOICES values (e.g. 'bludgeoning')."
    )
    # Restrict by weapon groups (values from WEAPON_GROUPS: 'unarmed','simple','martial','special','black_powder')
    restrict_to_weapon_groups = models.BooleanField(
        default=False,
        help_text="If checked, this mastery only applies to selected weapon groups."
    )
    allowed_weapon_groups = models.JSONField(
        default=list,
        blank=True,
        help_text="List of allowed weapon groups (e.g. ['simple','martial']). Uses WEAPON_GROUPS values."
    )

    # NEW: picklists (only used when the toggles above are true)
    allowed_weapons = models.ManyToManyField(
        'Weapon',
        blank=True,
        related_name='masteries',
        help_text="Check the weapons this mastery is usable with (shown when ‘Weapon restriction’ is enabled)."
    )
    allowed_traits = models.ManyToManyField(
        'WeaponTrait',
        blank=True,
        related_name='masteries',
        help_text="Check the weapon traits this mastery targets (shown when ‘Weapon trait restriction’ is enabled)."
    )


    def __str__(self):
        return f"{self.name} (L{self.level_required}, cost {self.points_cost})"

    def applies_to_weapon(self, weapon) -> bool:
        """
        Returns True if this mastery can be used with the given Weapon.
        Enforces all enabled restriction toggles consistently.
        """
        # Specific weapons
        if self.restrict_to_weapons and not self.allowed_weapons.filter(pk=weapon.pk).exists():
            return False

        # Weapon traits (ANY/ALL support optional; current behavior = ANY)
        if self.restrict_to_traits:
            wanted = list(self.allowed_traits.values_list('pk', flat=True))
            if not wanted:
                return False
            # If you later want to honor self.trait_match_mode == 'all', add an ALL check here.
            has_any = WeaponTraitValue.objects.filter(weapon=weapon, trait_id__in=wanted).exists()
            if not has_any:
                return False

        # Damage types (ANY overlap)
        if self.restrict_to_damage:
            allowed = set(self.allowed_damage_types or [])
            weap_types = set(weapon.damage_types or [])
            if not (allowed and weap_types and (allowed & weap_types)):
                return False

        # Weapon group restriction
        if self.restrict_to_weapon_groups:
            groups = set(self.allowed_weapon_groups or [])
            # assumes Weapon.category stores values like 'simple','martial','special','black_powder','unarmed'
            if not groups or weapon.category not in groups:
                return False

        # Range restriction (since the model has these fields)
        if self.restrict_to_range:
            ranges = set(self.allowed_range_types or [])
            if not ranges or weapon.range_type not in ranges:
                return False

        return True



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

# characters/models.py (place near SubclassTierLevel)
class SubclassMasteryUnlock(models.Model):
    """
    For SYSTEM_MODULAR_MASTERY groups: when a class can *reach* a given mastery rank.
    Rank 0 is always allowed; only ranks >0 are gated here.
    """
    subclass_group = models.ForeignKey(
        "SubclassGroup",
        on_delete=models.CASCADE,
        related_name="mastery_unlocks",
        help_text="Which umbrella this rule belongs to"
    )
    rank = models.PositiveSmallIntegerField(help_text="Mastery rank > 0 (e.g., 1, 2, 3)")
    unlock_level = models.PositiveIntegerField(help_text="Class level at which this rank becomes reachable")
    modules_required = models.PositiveIntegerField(
        default=2,
        help_text="CUMULATIVE modules from the SAME subclass required to claim this rank."
    )

    class Meta:
        unique_together = (("subclass_group", "rank"),)
        ordering = ["subclass_group", "rank"]

    def __str__(self):
        return f"{self.subclass_group.name} Rank {self.rank} @ L{self.unlock_level} (needs {self.modules_required} modules)"



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
    def clean(self):
        super().clean()
        # Only enforce for modular_mastery subclass modules
        if self.feature and self.subclass:
            grp = getattr(self.subclass, "group", None)
            if grp and grp.system_type == SubclassGroup.SYSTEM_MODULAR_MASTERY and self.feature.scope == "subclass_feat":
                # cap = min(current_tier_at_that_time, gainer cap at that time)
                base_class = self.subclass.base_class
                lvl        = int(self.level)

                cap_gainer = (ClassLevelFeature.objects
                    .filter(class_level__character_class=base_class,
                            class_level__level=lvl,
                            feature__scope="gain_subclass_feat",
                            feature__subclass_group=grp)
                    .aggregate(models.Max("feature__mastery_rank"))["feature__mastery_rank__max"] or 0)

                per = max(1, int(getattr(grp, "modules_per_mastery", 2)))

                # modules already taken in this subclass BEFORE this pick
                taken_before = (CharacterFeature.objects
                    .filter(character=self.character, subclass=self.subclass,
                            feature__scope="subclass_feat", level__lt=lvl)
                    .count())

                current_tier = 1 + (taken_before // per)  # 1-based
                allowed_cap  = min(current_tier, cap_gainer)

                feat_rank = int(self.feature.mastery_rank or 0)
                if feat_rank > allowed_cap:
                    raise ValidationError({"feature": f"This pick requires rank ≤ {allowed_cap}, but feature is rank {feat_rank}."})


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
    value     = models.CharField(max_length=999)    # store as text; cast in view if needed
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

    num_picks = models.PositiveSmallIntegerField(
        default=1,
        help_text="Only for subclass_choice: how many features the player may pick at this level."
    )
    class Meta:
        unique_together = ("class_level", "feature")


    def __str__(self):
        return f"{self.class_level} → {self.feature.code}"

# ──────────────────────────────────────────────────────────────────────────────
# Class-level tables for Skill Points and Skill Feat grants
# ──────────────────────────────────────────────────────────────────────────────
class ClassSkillPointGrant(models.Model):
    """
    How many SKILL POINTS this class grants *when you reach this class level*.
    The client can sum these across the character's class splits.
    """
    character_class = models.ForeignKey('CharacterClass', on_delete=models.CASCADE, related_name='skill_point_grants')
    at_level        = models.PositiveIntegerField()
    points_awarded  = models.PositiveSmallIntegerField(help_text="Skill points granted at this class level")

    class Meta:
        unique_together = (("character_class", "at_level"),)
        ordering = ["character_class", "at_level"]

    def __str__(self):
        return f"{self.character_class.name} L{self.at_level} → +{self.points_awarded} skill point(s)"


class ClassSkillFeatGrant(models.Model):
    """
    Whether this class grants SKILL FEAT pick(s) at a given class level.
    """
    character_class = models.ForeignKey('CharacterClass', on_delete=models.CASCADE, related_name='skill_feat_grants')
    at_level        = models.PositiveIntegerField()
    num_picks       = models.PositiveSmallIntegerField(default=1, help_text="How many skill feat picks at this level")

    class Meta:
        unique_together = (("character_class", "at_level"),)
        ordering = ["character_class", "at_level"]

    def __str__(self):
        return f"{self.character_class.name} L{self.at_level} → Skill Feat ×{self.num_picks}"


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
    
# --- New: which weapons a character has equipped (2 simple slots) ---
class CharacterWeaponEquip(models.Model):
    SLOT_CHOICES = [(1, "Primary"), (2, "Secondary"), (3, "Tertiary")]
    character   = models.ForeignKey(Character, on_delete=models.CASCADE, related_name="equipped_weapons")
    weapon      = models.ForeignKey(Weapon, on_delete=models.CASCADE)
    slot_index  = models.PositiveSmallIntegerField(choices=SLOT_CHOICES)

    class Meta:
        unique_together = ("character", "slot_index")

    def __str__(self):
        return f"{self.character.name} – {dict(self.SLOT_CHOICES).get(self.slot_index, self.slot_index)}: {self.weapon.name}"

# --- New: character spell picks (split known vs prepared for clarity) ---
class CharacterKnownSpell(models.Model):
    ORIGIN_CHOICES = [
        ("arcane", "Arcane"),
        ("divine", "Divine"),
        ("primal", "Primal"),
        ("occult", "Occult"),
    ]
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name="known_spells")
    spell     = models.ForeignKey(Spell, on_delete=models.CASCADE)
    origin    = models.CharField(max_length=10, choices=ORIGIN_CHOICES)  # tradition
    rank      = models.PositiveSmallIntegerField(default=1)
    from_class = models.ForeignKey(
        CharacterClass, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Optional: which class granted/learned this"
    )

    class Meta:
        unique_together = ("character", "spell")

    def __str__(self):
        return f"{self.character.name} knows {self.spell.name} (R{self.rank}, {self.origin})"


class CharacterPreparedSpell(models.Model):
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name="prepared_spells")
    spell     = models.ForeignKey(Spell, on_delete=models.CASCADE)
    origin    = models.CharField(max_length=10, choices=CharacterKnownSpell.ORIGIN_CHOICES)
    rank      = models.PositiveSmallIntegerField(default=1)
    # Optional: track which table granted the slot for audit/display
    source_feature = models.ForeignKey(
        ClassFeature, on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={"kind": "spell_table"}
    )

    class Meta:
        unique_together = ("character", "spell", "rank", "origin")

    def __str__(self):
        return f"{self.character.name} prepared {self.spell.name} (R{self.rank}, {self.origin})"


# --- New: martial mastery picks saved per character ---
class CharacterMartialMastery(models.Model):
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name="martial_masteries")
    mastery   = models.ForeignKey(MartialMastery, on_delete=models.CASCADE)
    level_picked = models.PositiveSmallIntegerField(help_text="Character level when selected")

    class Meta:
        unique_together = ("character", "mastery")

    def __str__(self):
        return f"{self.character.name} – {self.mastery.name} @L{self.level_picked}"


# --- New: generic Active/Passive toggle + note for any owned thing (feat/feature/spell/item) ---
class CharacterActivation(models.Model):
    character    = models.ForeignKey(Character, on_delete=models.CASCADE, related_name="activations")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id    = models.PositiveIntegerField()
    target       = GenericForeignKey("content_type", "object_id")

    is_active = models.BooleanField(default=False)
    note      = models.TextField(blank=True)

    class Meta:
        unique_together = ("character", "content_type", "object_id")

    def __str__(self):
        k = self.content_type.model
        return f"{self.character.name} – {k}:{self.object_id} {'ACTIVE' if self.is_active else 'passive'}"

# ──────────────────────────────────────────────────────────────────────────────
# Prestige Classes (no self-imports; use string FKs to avoid circular imports)
# ──────────────────────────────────────────────────────────────────────────────
from django.core.exceptions import ValidationError
# characters/models.py
# NEW: stores the player's choice for each prestige level when mode is "choose"
class CharacterPrestigeLevelChoice(models.Model):
    """
    Stores, for each character, which base class a prestige level
    "counts as" for a given PrestigeClass and prestige_level.
    """
    character = models.ForeignKey(
        "characters.Character",
        on_delete=models.CASCADE,
        related_name="prestige_choices",
        null=True,
    )
    prestige_class = models.ForeignKey(
        "characters.PrestigeClass",
        on_delete=models.CASCADE,
        related_name="prestige_choices",
        null=True,
    )
    prestige_level = models.PositiveSmallIntegerField()

    # NEW: record which *character level* this prestige level was taken at
    char_level_at_gain = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Character level at which this prestige level was taken.",
    )

    counts_as = models.ForeignKey(
        "characters.CharacterClass",
        on_delete=models.PROTECT,
        related_name="prestige_counts_as",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["character", "prestige_class", "prestige_level"]
        unique_together = (("character", "prestige_class", "prestige_level"),)

    def __str__(self):
        return f"{self.character} – {self.prestige_class} L{self.prestige_level}"


class CharacterManualFeat(models.Model):
    character = models.ForeignKey("characters.Character",
                                  on_delete=models.CASCADE,
                                  related_name="manual_feats")
    feat = models.ForeignKey("characters.ClassFeat",
                             on_delete=models.PROTECT)
    note = models.CharField(max_length=200, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("character", "feat"),)
        ordering = ["feat__name", "id"]

    def __str__(self) -> str:
        return f"{self.character} ↦ {self.feat}"

# characters/models.py

class RollModifier(models.Model):
    """
    Per-character saved modifiers for the dice roller.

    roll_code: identifies which roll this belongs to, e.g.
      "attack", "save_fort", "skill_athletics"
    kind:
      - "standard"   -> always-on for that roll
      - "toggle"     -> toggleable per roll
      - "ap_standard" -> always-on for AP for attack rolls
      - "ap_toggle"   -> toggleable for AP for attack rolls
    """
    character = models.ForeignKey("characters.Character", on_delete=models.CASCADE)
    roll_code = models.CharField(max_length=64)
    name      = models.CharField(max_length=100)
    value     = models.IntegerField()
    kind      = models.CharField(
        max_length=20,
        choices=[
            ("standard", "Standard"),
            ("toggle", "Toggle"),
            ("ap_standard", "AP Standard"),
            ("ap_toggle", "AP Toggle"),
        ],
    )

    class Meta:
        ordering = ["roll_code", "id"]

    def __str__(self):
        sign = "+" if self.value >= 0 else ""
        return f"{self.character} [{self.roll_code}] {self.name} {sign}{self.value}"

class PrestigeClass(models.Model):
    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    min_entry_level = models.PositiveSmallIntegerField(default=7, editable=False)
    requires_gm_approval = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.min_entry_level != 7:
            raise ValidationError({"min_entry_level": "Minimum entry level is fixed at 7."})


class PrestigePrerequisite(models.Model):
    OP_AND = "AND"
    OP_OR  = "OR"
    OP_CHOICES = ((OP_AND, "AND (all in this group)"),
                  (OP_OR,  "OR (any in this group)"))

    KIND_CLASS_LEVEL = "class_level"
    KIND_SKILL_TIER  = "skill_tier"
    KIND_RACE        = "race"
    KIND_SUBRACE     = "subrace"
    KIND_CLASS_TAG   = "class_tag"
    KIND_RACE_TAG    = "race_tag"
    KIND_FEAT_CODE   = "feat_code"

    KIND_CHOICES = (
        (KIND_CLASS_LEVEL, "Class level (e.g., Fighter 5+)"),
        (KIND_SKILL_TIER,  "Skill proficiency (min tier)"),
        (KIND_RACE,        "Race"),
        (KIND_SUBRACE,     "Subrace"),
        (KIND_CLASS_TAG,   "Class Tag"),
        (KIND_RACE_TAG,    "Race Tag"),
        (KIND_FEAT_CODE,   "Feat / other tag (free text code)"),
    )

    prestige_class = models.ForeignKey("characters.PrestigeClass", on_delete=models.CASCADE, related_name="prereqs")
    group_index = models.PositiveSmallIntegerField(default=1, help_text="All groups are ANDed together. Inside a group, use the operator below.")
    intragroup_operator = models.CharField(max_length=3, choices=OP_CHOICES, default=OP_AND)

    # class-level requirement
    target_class = models.ForeignKey("characters.CharacterClass", null=True, blank=True, on_delete=models.SET_NULL)
    min_class_level = models.PositiveSmallIntegerField(null=True, blank=True)

    # skill tier requirement
    skill = models.ForeignKey("characters.Skill", null=True, blank=True, on_delete=models.SET_NULL)
    min_tier = models.ForeignKey("characters.ProficiencyTier", null=True, blank=True, on_delete=models.SET_NULL)

    # race / subrace
    race = models.ForeignKey("characters.Race", null=True, blank=True, on_delete=models.SET_NULL)
    subrace = models.ForeignKey("characters.Subrace", null=True, blank=True, on_delete=models.SET_NULL)

    # tags / feats
    class_tag = models.ForeignKey("characters.ClassTag", null=True, blank=True, on_delete=models.SET_NULL)
    race_tag = models.ForeignKey("characters.RaceTag", null=True, blank=True, on_delete=models.SET_NULL)
    feat_code = models.CharField(max_length=80, blank=True, help_text="Optional free text code for feat/other tag (e.g. 'feat_toughness').")

    class Meta:
        ordering = ["prestige_class", "group_index", "id"]

    def __str__(self):
        return f"{self.prestige_class} – {self.get_kind_display()}"

    def clean(self):
        super().clean()
        k = self.kind

        def need(fields, msg):
            for f in fields:
                v = getattr(self, f, None)
                if v is None or v == "":
                    raise ValidationError({fields[0]: msg})

        if k == self.KIND_CLASS_LEVEL:
            need(("target_class", "min_class_level"), "Pick a class and minimum level (e.g., Fighter and 5).")
        elif k == self.KIND_SKILL_TIER:
            need(("skill", "min_tier"), "Pick the skill and the minimum proficiency tier.")
        elif k == self.KIND_RACE:
            need(("race",), "Pick a Race.")
        elif k == self.KIND_SUBRACE:
            need(("subrace",), "Pick a Subrace.")
        elif k == self.KIND_CLASS_TAG:
            need(("class_tag",), "Pick a Class Tag.")
        elif k == self.KIND_RACE_TAG:
            need(("race_tag",), "Pick a Race Tag.")
        elif k == self.KIND_FEAT_CODE:
            if not (self.feat_code or "").strip():
                raise ValidationError({"feat_code": "Enter a code for the feat/tag."})

    kind = models.CharField(max_length=20, choices=KIND_CHOICES)


class PrestigeLevel(models.Model):
    MODE_FIXED  = "fixed"
    MODE_CHOOSE = "choose"
    MODE_CHOICES = ((MODE_FIXED, "Fixed — this level always counts as the class below"),
                    (MODE_CHOOSE, "Choose at level-up — pick one of the allowed classes"))

    prestige_class = models.ForeignKey("characters.PrestigeClass", on_delete=models.CASCADE, related_name="levels")
    level = models.PositiveSmallIntegerField(help_text="Prestige level (1 = entry; 1 is a dead level by rule).")
    counts_as_mode = models.CharField(max_length=8, choices=MODE_CHOICES, default=MODE_FIXED)
    fixed_counts_as = models.ForeignKey(
        "characters.CharacterClass", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        help_text="Used only when mode = Fixed."
    )
    allowed_counts_as = models.ManyToManyField("characters.CharacterClass", blank=True, help_text="Used only when mode = Choose.")

    class Meta:
        unique_together = (("prestige_class", "level"),)
        ordering = ["prestige_class", "level"]

    def __str__(self):
        return f"{self.prestige_class} L{self.level}"

    def clean(self):
        super().clean()
        if self.counts_as_mode == self.MODE_FIXED and self.fixed_counts_as is None:
            raise ValidationError({"fixed_counts_as": "Pick the counted class (mode is Fixed)."})


class PrestigeFeature(models.Model):
    prestige_class = models.ForeignKey("characters.PrestigeClass", on_delete=models.CASCADE, related_name="features")
    at_prestige_level = models.PositiveSmallIntegerField()
    code = models.SlugField(max_length=60, help_text="Unique within this prestige class.")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    grants_class_feature = models.ForeignKey(
        "characters.ClassFeature", null=True, blank=True, on_delete=models.SET_NULL,
        help_text="Optional: link to an existing ClassFeature row to drive mechanics."
    )

    class Meta:
        unique_together = (("prestige_class", "code"),)
        ordering = ["prestige_class", "at_prestige_level", "name"]

    def __str__(self):
        return f"{self.prestige_class} L{self.at_prestige_level} – {self.name}"

    def clean(self):
        super().clean()
        if self.at_prestige_level == 1:
            raise ValidationError({"at_prestige_level": "Prestige 1 is a dead level; do not add features here."})


