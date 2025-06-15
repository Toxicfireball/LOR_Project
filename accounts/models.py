from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone

class Submission(models.Model):
    STATUS_PENDING  = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES  = [
        (STATUS_PENDING,  'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    submitter    = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.CASCADE,
                                     related_name='submissions')
    content_type = models.ForeignKey(ContentType,
                                     on_delete=models.CASCADE)
    object_id    = models.PositiveIntegerField(null=True, blank=True)
    # If object_id is set, this is an “edit” submission
    data         = models.JSONField()
    status       = models.CharField(max_length=10,
                                    choices=STATUS_CHOICES,
                                    default=STATUS_PENDING)
    created_at   = models.DateTimeField(auto_now_add=True)
    reviewed_at  = models.DateTimeField(null=True, blank=True)
    reviewer     = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     null=True, blank=True,
                                     related_name='reviews',
                                     on_delete=models.SET_NULL)

    # generic FK to the target model
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ['-created_at']

    def approve(self, by_user):
        """Apply this submission: create or update the real object."""
        model = self.content_type.model_class()
        if self.object_id:
            # update existing
            obj = model.objects.get(pk=self.object_id)
            for k, v in self.data.items():
                setattr(obj, k, v)
            obj.save()
        else:
            # new instance
            obj = model.objects.create(**self.data)
        self.status      = self.STATUS_APPROVED
        self.reviewed_at = timezone.now()
        self.reviewer    = by_user
        self.save()

    def reject(self, by_user):
        self.status      = self.STATUS_REJECTED
        self.reviewed_at = timezone.now()
        self.reviewer    = by_user
        self.save()
