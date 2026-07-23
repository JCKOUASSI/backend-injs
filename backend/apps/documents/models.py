import uuid
from django.db import models
from apps.core.models import TimeStampedModel


class DocumentCategory(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.name


class Document(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    category = models.ForeignKey(DocumentCategory, on_delete=models.PROTECT, related_name='documents')
    file = models.FileField(upload_to='documents/%Y/%m/')
    owner = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='documents')
    student = models.ForeignKey('students.Student', on_delete=models.SET_NULL, null=True, blank=True)
    is_signed = models.BooleanField(default=False)
    signature_hash = models.CharField(max_length=128, blank=True)
    is_archived = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
