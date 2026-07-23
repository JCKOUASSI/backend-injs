import uuid
from django.db import models
from apps.core.models import TimeStampedModel


class Notification(TimeStampedModel):
    TYPES = [
        ('grade', 'Résultats'),
        ('absence', 'Absence'),
        ('payment', 'Paiement'),
        ('general', 'Général'),
        ('admission', 'Admission'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=15, choices=TYPES, default='general')
    is_read = models.BooleanField(default=False, db_index=True)
    data = models.JSONField(default=dict, blank=True)
    sent_email = models.BooleanField(default=False)
    sent_push = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['recipient', 'is_read', '-created_at'])]
