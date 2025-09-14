# campaigns/models.py  (additions marked 'NEW')
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType   # NEW
from django.contrib.contenttypes.fields import GenericForeignKey  # NEW

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


# ========== NEW: Party inventory (campaign-level items) ==========
class PartyItem(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="party_items")
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    item_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    item_object_id    = models.PositiveIntegerField()
    item              = GenericForeignKey("item_content_type", "item_object_id")
    quantity          = models.PositiveIntegerField(default=1)
    note              = models.CharField(max_length=255, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.campaign.name} – {self.item} ×{self.quantity}"


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
