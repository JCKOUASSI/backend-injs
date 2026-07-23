import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel


class ExamSession(TimeStampedModel):
    TYPES = [('normal', 'Session normale'), ('retake', 'Session de rattrapage')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE, related_name='exam_sessions')
    semester = models.ForeignKey('academics.Semester', on_delete=models.CASCADE, related_name='exam_sessions')
    session_type = models.CharField(max_length=10, choices=TYPES, default='normal')
    start_date = models.DateField()
    end_date = models.DateField()
    is_open = models.BooleanField(default=False)
    results_published = models.BooleanField(default=False)

    class Meta:
        unique_together = [['academic_year', 'semester', 'session_type']]


class Evaluation(TimeStampedModel):
    TYPES = [
        ('cc', 'Contrôle Continu'),
        ('exam', 'Examen'),
        ('tp', 'Travaux Pratiques'),
        ('project', 'Projet'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teaching_unit = models.ForeignKey('academics.TeachingUnit', on_delete=models.CASCADE, related_name='evaluations')
    course = models.ForeignKey('academics.Course', on_delete=models.SET_NULL, null=True, blank=True)
    exam_session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name='evaluations')
    name = models.CharField(max_length=100)
    evaluation_type = models.CharField(max_length=10, choices=TYPES)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('1.0'))
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('20'))
    date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['teaching_unit', 'evaluation_type']


class Grade(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='grades')
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name='grades')
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_absent = models.BooleanField(default=False)
    is_anonymized = models.BooleanField(default=False)
    entered_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    comments = models.TextField(blank=True)

    class Meta:
        unique_together = [['student', 'evaluation']]
        indexes = [models.Index(fields=['student', 'evaluation'])]


class Deliberation(TimeStampedModel):
    STATUSES = [('draft', 'Brouillon'), ('validated', 'Validée'), ('published', 'Publiée')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam_session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name='deliberations')
    program = models.ForeignKey('academics.Program', on_delete=models.CASCADE, related_name='deliberations')
    promotion = models.ForeignKey('academics.Promotion', on_delete=models.CASCADE, related_name='deliberations')
    status = models.CharField(max_length=15, choices=STATUSES, default='draft')
    deliberation_date = models.DateTimeField(null=True, blank=True)
    validated_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    results_summary = models.JSONField(default=dict)

    class Meta:
        unique_together = [['exam_session', 'program', 'promotion']]


class Jury(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deliberation = models.ForeignKey(Deliberation, on_delete=models.CASCADE, related_name='jury_members')
    member = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='jury_memberships')
    role = models.CharField(max_length=50, default='membre')

    class Meta:
        unique_together = [['deliberation', 'member']]


class Defense(TimeStampedModel):
    """Soutenance (Master/Doctorat)."""
    STATUSES = [('scheduled', 'Programmée'), ('completed', 'Terminée'), ('cancelled', 'Annulée')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='defenses')
    title = models.CharField(max_length=500)
    scheduled_date = models.DateTimeField()
    room = models.ForeignKey('faculty.Room', on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=15, choices=STATUSES, default='scheduled')
    grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    mention = models.CharField(max_length=50, blank=True)
    report_file = models.FileField(upload_to='defenses/reports/', null=True, blank=True)

    class Meta:
        ordering = ['-scheduled_date']
