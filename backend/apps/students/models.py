import uuid
import io
import qrcode
from django.db import models
from django.core.files.base import ContentFile
from apps.core.models import TimeStampedModel


class Student(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='student_profile')
    matricule = models.CharField(max_length=20, unique=True, db_index=True)
    program = models.ForeignKey('academics.Program', on_delete=models.PROTECT, related_name='students')
    promotion = models.ForeignKey('academics.Promotion', on_delete=models.PROTECT, related_name='students')
    specialization = models.ForeignKey(
        'academics.Specialization', on_delete=models.SET_NULL, null=True, blank=True, related_name='students'
    )
    date_of_birth = models.DateField(null=True, blank=True)
    place_of_birth = models.CharField(max_length=100, blank=True)
    nationality = models.CharField(max_length=50, default="Ivoirienne")
    gender = models.CharField(max_length=1, choices=[('M', 'Masculin'), ('F', 'Féminin')], blank=True)
    address = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    qr_code = models.ImageField(upload_to='students/qr/', null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Actif'),
            ('suspended', 'Suspendu'),
            ('graduated', 'Diplômé'),
            ('withdrawn', 'Retiré'),
        ],
        default='active',
        db_index=True,
    )
    enrollment_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['matricule']
        indexes = [models.Index(fields=['program', 'promotion', 'status'])]

    def __str__(self):
        return f'{self.matricule} - {self.user.get_full_name()}'

    def save(self, *args, skip_qr=False, **kwargs):
        super().save(*args, **kwargs)
        if not skip_qr and not self.qr_code:
            self._generate_qr_code()

    def _generate_qr_code(self):
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(f'INJS:{self.matricule}:{self.id}')
        qr.make(fit=True)
        img = qr.make_image(fill_color='#0D47A1', back_color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        self.qr_code.save(f'qr_{self.matricule}.png', ContentFile(buffer.getvalue()), save=False)
        Student.objects.filter(pk=self.pk).update(qr_code=self.qr_code.name)


class Enrollment(TimeStampedModel):
    TYPES = [
        ('administrative', 'Inscription administrative'),
        ('pedagogical', 'Inscription pédagogique'),
        ('pre_registration', 'Préinscription'),
    ]
    STATUSES = [
        ('pending', 'En attente'),
        ('approved', 'Validée'),
        ('rejected', 'Rejetée'),
        ('cancelled', 'Annulée'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE, related_name='enrollments')
    enrollment_type = models.CharField(max_length=20, choices=TYPES, db_index=True)
    status = models.CharField(max_length=20, choices=STATUSES, default='pending', db_index=True)
    semester = models.ForeignKey('academics.Semester', on_delete=models.SET_NULL, null=True, blank=True)
    validated_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='validated_enrollments'
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [['student', 'academic_year', 'enrollment_type']]
        ordering = ['-created_at']


class AcademicRecord(models.Model):
    """Immutable academic history snapshot."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='academic_records')
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.PROTECT)
    semester = models.ForeignKey('academics.Semester', on_delete=models.PROTECT)
    semester_average = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    credits_acquired = models.PositiveSmallIntegerField(default=0)
    credits_total = models.PositiveSmallIntegerField(default=0)
    is_validated = models.BooleanField(default=False)
    decision = models.CharField(max_length=50, blank=True)
    snapshot_data = models.JSONField(default=dict)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
        indexes = [models.Index(fields=['student', 'academic_year'])]
