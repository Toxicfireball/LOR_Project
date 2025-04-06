# campaigns/models.py

from django.db import models
from django.contrib.auth.models import User

class Campaign(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ManyToManyField to link users via a through model:
    members = models.ManyToManyField(
        User,
        through='CampaignMembership',
        related_name='campaigns'
    )

    def __str__(self):
        return self.name

class CampaignMembership(models.Model):
    ROLE_CHOICES = (
        ('gm', 'Game Master'),
        ('pc', 'Player Character'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    role = models.CharField(max_length=2, choices=ROLE_CHOICES)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'campaign')  # Ensures one membership per user per campaign

    def __str__(self):
        return f"{self.user.username} as {self.get_role_display()} in {self.campaign.name}"
