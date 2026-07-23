import uuid
from django.db import models
from apps.core.models import TimeStampedModel


class Conversation(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.CharField(max_length=255)
    participants = models.ManyToManyField('accounts.User', related_name='conversations')

    class Meta:
        ordering = ['-updated_at']


class Message(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='sent_messages')
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    attachment = models.FileField(upload_to='messages/', null=True, blank=True)

    class Meta:
        ordering = ['created_at']
