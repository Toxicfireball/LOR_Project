from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.apps import apps

User = get_user_model()

@receiver(post_save, sender=User)
def ensure_user_email_meta(sender, instance, created, **kwargs):
    if not created:
        return
    UserEmail = apps.get_model('accounts', 'UserEmail')  # lazy resolve
    UserEmail.objects.get_or_create(user=instance)
