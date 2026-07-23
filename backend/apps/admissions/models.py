import uuid
from django.db import models
from apps.core.models import TimeStampedModel


class AdmissionCampaign(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE)
    program = models.ForeignKey('academics.Program', on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    max_places = models.PositiveIntegerField(default=100)
    is_open = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_date']


class PreRegistration(TimeStampedModel):
    STATUSES = [('pending', 'En attente'), ('accepted', 'Acceptée'), ('rejected', 'Rejetée')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(AdmissionCampaign, on_delete=models.CASCADE, related_name='pre_registrations')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    date_of_birth = models.DateField(null=True, blank=True)
    documents = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=15, choices=STATUSES, default='pending')
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
