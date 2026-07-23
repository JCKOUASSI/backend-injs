import uuid
from django.db import models
from apps.core.models import TimeStampedModel


class LibraryResource(TimeStampedModel):
    RESOURCE_TYPES = [('book', 'Livre'), ('article', 'Article'), ('thesis', 'Mémoire'), ('video', 'Vidéo')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    author = models.CharField(max_length=255, blank=True)
    resource_type = models.CharField(max_length=10, choices=RESOURCE_TYPES, default='book')
    isbn = models.CharField(max_length=20, blank=True)
    file = models.FileField(upload_to='library/', null=True, blank=True)
    cover = models.ImageField(upload_to='library/covers/', null=True, blank=True)
    description = models.TextField(blank=True)
    department = models.ForeignKey(
        'academics.Department', on_delete=models.SET_NULL, null=True, blank=True
    )
    is_public = models.BooleanField(default=True)
    download_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['title']
