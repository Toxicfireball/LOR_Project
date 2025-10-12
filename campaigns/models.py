from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType   # NEW
from django.contrib.contenttypes.fields import GenericForeignKey  # NEW
from django.db.models import Q  
class Campaign(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # NEW: optional password to join
    join_password = models.CharField(
        max_length=128, blank=True,
        help_text="If set, players must enter this to join."
    )

    members = models.ManyToManyField(
        User, through='CampaignMembership', related_name='campaigns'
    )

    def __str__(self):
        return self.name

    @property
    def is_password_protected(self) -> bool:  # NEW
        return bool(self.join_password)


class CampaignMembership(models.Model):
    ROLE_CHOICES = (('gm', 'Game Master'), ('pc', 'Player Character'))
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    role = models.CharField(max_length=2, choices=ROLE_CHOICES)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'campaign')

    def __str__(self):
        return f"{self.user.username} as {self.get_role_display()} in {self.campaign.name}"


# ========== NEW: Notes (GM/private & Party-shared) ==========
class CampaignNote(models.Model):
    VIS_CHOICES = (("gm", "GM only"), ("party", "Party shared"))
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="notes")
    author   = models.ForeignKey(User, on_delete=models.CASCADE, related_name="campaign_notes")
    visibility = models.CharField(max_length=8, choices=VIS_CHOICES, default="party")
    content  = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional: single equipment grant attached to this note
    item_content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.SET_NULL)
    item_object_id    = models.PositiveIntegerField(null=True, blank=True)
    item              = GenericForeignKey("item_content_type", "item_object_id")
    quantity          = models.PositiveIntegerField(default=1)
    class Meta:
        ordering = ["-created_at"]
    def __str__(self):
        return f"{self.campaign.name} note by {self.author} ({self.visibility})"



class PartyItem(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="party_items")
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    item_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    item_object_id    = models.PositiveIntegerField()
    item              = GenericForeignKey("item_content_type", "item_object_id")
    quantity          = models.PositiveIntegerField(default=1)
    note              = models.CharField(max_length=255, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    # NEW (string reference, no import):
    claimed_by = models.ForeignKey(
        "characters.Character",  # <- string avoids circular import
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="claimed_party_items",
    )
    claimed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_claimed(self) -> bool:
        return self.claimed_by_id is not None

    def __str__(self):
        who = f" (claimed by {self.claimed_by.name})" if self.claimed_by_id else ""
        return f"{self.campaign.name} – {self.item} ×{self.quantity}{who}"


# ========== NEW: Simple direct messages between campaign members ==========
class CampaignMessage(models.Model):
    campaign  = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="messages")
    sender    = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_campaign_messages")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_campaign_messages")
    content   = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.campaign.name}: {self.sender} → {self.recipient}"
# campaigns/models.py  (ADD THESE NEW MODELS)
class EnemyTag(models.Model):
    name = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(max_length=64, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
    

class EnemyType(models.Model):
    """Reusable enemy/monster blueprint."""
    # NEW: scope (None => Global; set => Campaign-specific)
    CATEGORY = (("monster", "Monster"), ("npc", "NPC"))
    campaign = models.ForeignKey(
        Campaign, null=True, blank=True, on_delete=models.CASCADE,
        related_name="enemy_types", help_text="Leave blank for Global"
    )
    category = models.CharField(max_length=8, choices=CATEGORY, default="monster", db_index=True)
    # name is no longer globally unique (uniqueness handled via constraints below)
    name = models.CharField(max_length=120)
    level = models.PositiveIntegerField(default=0)
    hp = models.PositiveIntegerField(default=1)
    speed   = models.PositiveIntegerField(default=30)
    armor = models.IntegerField(default=0)
    dodge = models.IntegerField(default=0)
    initiative = models.IntegerField(default=0)  # NEW: base initiative
    # Ability scores
    str_score = models.IntegerField(default=10)
    dex_score = models.IntegerField(default=10)
    con_score = models.IntegerField(default=10)
    int_score = models.IntegerField(default=10)
    wis_score = models.IntegerField(default=10)
    cha_score = models.IntegerField(default=10)

    # Saves
    will_save = models.IntegerField(default=0)
    reflex_save = models.IntegerField(default=0)
    fortitude_save = models.IntegerField(default=0)

    # Skills-ish
    perception = models.IntegerField(default=0)
    stealth = models.IntegerField(default=0)
    athletics = models.IntegerField(default=0)
    # Text
    description = models.TextField(blank=True)
    resistances = models.TextField(blank=True, help_text="Free text for resistances/notes")

    # NEW: tags
    tags = models.ManyToManyField("EnemyTag", blank=True, related_name="enemy_types")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        # Uniqueness: name unique among globals, and unique *within* each campaign.
        constraints = [
            models.UniqueConstraint(
                fields=["name"], condition=Q(campaign__isnull=True),
                name="uniq_enemytype_global_name"
            ),
            models.UniqueConstraint(
                fields=["campaign", "name"],
                name="uniq_enemytype_campaign_name"
            ),
        ]

    def __str__(self):
        scope = self.campaign.name if self.campaign_id else "Global"
        return f"{self.name} ({scope})"


class EnemyAbility(models.Model):
    """Per-enemy-type abilities, passive or active."""
    TYPE_CHOICES = (("passive", "Passive"), ("active", "Active"))
    ACTION_CHOICES = (
        ("free", "Free"),
        ("1", "1 Action"),
        ("2", "2 Actions"),
        ("3", "3 Actions"),
        ("reaction", "Reaction"),
        ("-", "— (Passive/None)"),
    )
    enemy_type   = models.ForeignKey(EnemyType, on_delete=models.CASCADE, related_name="abilities")
    ability_type = models.CharField(max_length=8, choices=TYPE_CHOICES)
    action_cost  = models.CharField(max_length=9, choices=ACTION_CHOICES, default="-")
    title        = models.CharField(max_length=120, blank=True)
    description  = models.TextField()

    class Meta:
        ordering = ["ability_type", "title"]



class Encounter(models.Model):
    """An encounter belongs to a campaign and holds instances of enemies."""
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="encounters")
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "name"]

    def __str__(self):
        return f"{self.campaign.name} – {self.name}"



class EncounterEnemy(models.Model):
    SIDE = (("enemy", "Enemy"), ("neutral", "Neutral"), ("ally", "Ally"))

    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name="enemies")
    enemy_type = models.ForeignKey(EnemyType, on_delete=models.PROTECT, related_name="instances")
    name_override = models.CharField(max_length=160, blank=True)

    # NEW: which side this instance is on in THIS encounter
    side = models.CharField(max_length=7, choices=SIDE, default="enemy", db_index=True)

    max_hp = models.PositiveIntegerField()
    current_hp = models.IntegerField()
    initiative = models.IntegerField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def save(self, *args, **kwargs):
        if not self.max_hp:
            self.max_hp = self.enemy_type.hp
        if self.current_hp is None:
            self.current_hp = self.max_hp
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.name_override or self.enemy_type.name


class EncounterParticipant(models.Model):
    ROLE_CHOICES = (("pc", "Player"), )
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name="participants")
    character = models.ForeignKey("characters.Character", on_delete=models.CASCADE, related_name="encounter_participations")
    role = models.CharField(max_length=3, choices=ROLE_CHOICES, default="pc")
    initiative = models.IntegerField(null=True, blank=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        unique_together = [("encounter", "character")]
        ordering = ["-initiative", "id"]  # high to low like a tracker

    def __str__(self):
        return f"{self.character.name} in {self.encounter.name} ({self.initiative or '—'})"


# NEW: immutable damage log (who hit what, for how much, with notes)
class DamageEvent(models.Model):
    KIND = (("dmg", "Damage"), ("heal", "Heal"))

    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name="damage_events")

    attacker_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="damage_events")
    attacker_character = models.ForeignKey("characters.Character", on_delete=models.SET_NULL, null=True, blank=True, related_name="outgoing_damage_events")
    attacker_enemy = models.ForeignKey(EncounterEnemy, on_delete=models.SET_NULL, null=True, blank=True, related_name="outgoing_events")

    # Target can be a creature OR a player
    # Target can be a creature OR a player
    target_enemy = models.ForeignKey(EncounterEnemy, on_delete=models.SET_NULL, null=True, blank=True, related_name="incoming_events")
    target_character = models.ForeignKey("characters.Character", on_delete=models.SET_NULL, null=True, blank=True, related_name="incoming_damage_events")

    kind = models.CharField(max_length=4, choices=KIND, default="dmg")
    amount = models.PositiveIntegerField()
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def signed_amount(self) -> int:
        return self.amount if self.kind == "dmg" else -self.amount
