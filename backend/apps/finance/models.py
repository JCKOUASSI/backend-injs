import uuid
from django.db import models
from apps.core.models import TimeStampedModel


class FeeType(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    program = models.ForeignKey(
        'academics.Program', on_delete=models.SET_NULL, null=True, blank=True, related_name='fee_types'
    )
    is_mandatory = models.BooleanField(default=True)
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE, related_name='fee_types')

    class Meta:
        ordering = ['name']


class StudentFee(TimeStampedModel):
    STATUSES = [
        ('pending', 'En attente'),
        ('partial', 'Partiellement payé'),
        ('paid', 'Payé'),
        ('overdue', 'En retard'),
        ('waived', 'Exonéré'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='fees')
    fee_type = models.ForeignKey(FeeType, on_delete=models.PROTECT, related_name='student_fees')
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUSES, default='pending', db_index=True)

    class Meta:
        unique_together = [['student', 'fee_type']]

    @property
    def balance(self):
        return self.amount_due - self.amount_paid


class PaymentTransaction(TimeStampedModel):
    PROVIDERS = [
        ('orange_money', 'Orange Money'),
        ('mtn_momo', 'MTN Mobile Money'),
        ('moov_money', 'Moov Money'),
        ('wave', 'Wave'),
        ('visa_card', 'Carte Visa/Mastercard'),
        ('cash', 'Espèces'),
        ('bank_transfer', 'Virement bancaire'),
    ]
    STATUSES = [
        ('initiated', 'Initié'),
        ('pending', 'En cours'),
        ('success', 'Réussi'),
        ('failed', 'Échoué'),
        ('cancelled', 'Annulé'),
        ('refunded', 'Remboursé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=50, unique=True, db_index=True)
    student_fee = models.ForeignKey(StudentFee, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    provider = models.CharField(max_length=20, choices=PROVIDERS)
    provider_reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=15, choices=STATUSES, default='initiated', db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    payment_url = models.URLField(blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']


class PaymentProviderConfig(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=20, choices=PaymentTransaction.PROVIDERS)
    is_enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict)
    institution = models.ForeignKey('academics.Institution', on_delete=models.CASCADE, related_name='payment_configs')

    class Meta:
        unique_together = [['institution', 'provider']]
