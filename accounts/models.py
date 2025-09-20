from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
import uuid

User = get_user_model()


class UserEmail(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="email_meta")
    is_verified = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.user.username}: verified={self.is_verified}"

class EmailVerification(models.Model):
    PURPOSE_SIGNUP = "signup"
    PURPOSE_CHANGE = "change"
    PURPOSE_CHOICES = [(PURPOSE_SIGNUP, "Signup verification"), (PURPOSE_CHANGE, "Change-email verification")]
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_verifications")
    email     = models.EmailField()
    purpose   = models.CharField(max_length=10, choices=PURPOSE_CHOICES)
    token     = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at    = models.DateTimeField(null=True, blank=True)
    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])
    def __str__(self):
        return f"{self.user} {self.purpose} → {self.email}"