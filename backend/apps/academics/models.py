import uuid
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import TimeStampedModel, SoftDeleteModel


class Institution(TimeStampedModel):
    """Multi-institution support (national platform)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    acronym = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, default='Abidjan')
    country = models.CharField(max_length=100, default="Côte d'Ivoire")
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to='institutions/logos/', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Department(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='departments')
    code = models.CharField(max_length=20, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    head = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='headed_departments'
    )

    class Meta:
        ordering = ['name']
        unique_together = [['institution', 'code']]

    def __str__(self):
        return f'{self.code} - {self.name}'


class Specialization(TimeStampedModel):
    """Spécialité STAPS : EM, ES, MS, APA ou tronc commun (TC)."""

    TRACKS = [
        ('PL', 'Professeur de Lycée'),
        ('PC', 'Professeur de Collège'),
        ('BOTH', 'Lycée et Collège'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    track = models.CharField(max_length=5, choices=TRACKS, default='BOTH')
    is_tronc_commun = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f'{self.code} — {self.name}'


class Program(TimeStampedModel, SoftDeleteModel):
    """Filière LMD: Licence, Master, Doctorat."""
    DEGREE_TYPES = [
        ('L', 'Licence'),
        ('M', 'Master'),
        ('D', 'Doctorat'),
        ('DU', 'Diplôme Universitaire'),
    ]
    TRACKS = [
        ('PL', 'Professeur de Lycée'),
        ('PC', 'Professeur de Collège'),
        ('', 'Général'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='programs')
    code = models.CharField(max_length=20, db_index=True)
    name = models.CharField(max_length=255)
    degree_type = models.CharField(max_length=2, choices=DEGREE_TYPES)
    track = models.CharField(max_length=5, choices=TRACKS, blank=True, default='')
    duration_semesters = models.PositiveSmallIntegerField(default=6)
    total_credits = models.PositiveSmallIntegerField(default=180)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    coordinator = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='coordinated_programs'
    )

    class Meta:
        ordering = ['degree_type', 'name']
        unique_together = [['department', 'code']]

    def __str__(self):
        return f'{self.get_degree_type_display()} {self.name}'


class Promotion(TimeStampedModel):
    """Cohorte d'étudiants."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='promotions')
    name = models.CharField(max_length=50)
    entry_year = models.PositiveSmallIntegerField()
    current_semester = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-entry_year', 'name']
        unique_together = [['program', 'name']]

    def __str__(self):
        return f'{self.program.code} - {self.name}'


class AcademicYear(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='academic_years')
    label = models.CharField(max_length=20, help_text='Ex: 2025-2026')
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False, db_index=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_date']
        unique_together = [['institution', 'label']]

    def __str__(self):
        return self.label


class Semester(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='semesters')
    number = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ['academic_year', 'number']
        unique_together = [['academic_year', 'number']]

    def __str__(self):
        return f'{self.academic_year.label} - S{self.number}'


class FormationPeriod(TimeStampedModel):
    """Fenêtre calendaire sur laquelle un emploi du temps est généré puis publié."""

    RHYTHMS = [
        ('full', 'Toutes les semaines'),
        ('w1', '1re semaine du mois'),
        ('w1_2', '2 premières semaines du mois'),
        ('w1_3', '3 premières semaines du mois'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, related_name='formation_periods'
    )
    program = models.ForeignKey(
        Program, on_delete=models.CASCADE, null=True, blank=True, related_name='formation_periods',
        help_text='Vide = période commune à toutes les filières.',
    )
    semester = models.ForeignKey(
        Semester, on_delete=models.SET_NULL, null=True, blank=True, related_name='formation_periods'
    )
    label = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    order = models.PositiveSmallIntegerField(default=0)
    weekly_rhythm = models.CharField(max_length=10, choices=RHYTHMS, default='full')
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['academic_year', 'order', 'start_date']
        unique_together = [['academic_year', 'program', 'label']]
        verbose_name = 'Période de formation'
        verbose_name_plural = 'Périodes de formation'

    def __str__(self):
        return f'{self.label} ({self.start_date:%d/%m/%Y} → {self.end_date:%d/%m/%Y})'

    def clean(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({
                'end_date': 'La date de fin doit être postérieure ou égale à la date de début.',
            })

    def covers(self, day):
        return self.start_date <= day <= self.end_date


class Holiday(TimeStampedModel):
    """Jour férié ou journée banalisée, exclu de la génération d'emploi du temps."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='holidays')
    date = models.DateField(db_index=True)
    label = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['-date']
        unique_together = [['institution', 'date']]
        verbose_name = 'Jour férié'
        verbose_name_plural = 'Jours fériés'

    def __str__(self):
        return f'{self.date:%d/%m/%Y} — {self.label}'


class TeachingUnit(TimeStampedModel, SoftDeleteModel):
    """Unité d'Enseignement (UE) LMD."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    credits_ects = models.PositiveSmallIntegerField(default=3)
    coefficient = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    semester_number = models.PositiveSmallIntegerField()
    description = models.TextField(blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='teaching_units')
    passing_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('10.00'),
        verbose_name='Note de validation',
        help_text='Seuil de validation ECUE/UE (/20)',
    )

    class Meta:
        ordering = ['semester_number', 'code']
        verbose_name = "Unité d'enseignement"

    def __str__(self):
        return f'{self.code} - {self.name} ({self.credits_ects} ECTS)'


class Course(TimeStampedModel, SoftDeleteModel):
    """Cours / ECUE au sein d'une UE."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teaching_unit = models.ForeignKey(TeachingUnit, on_delete=models.CASCADE, related_name='courses')
    code = models.CharField(max_length=20, db_index=True)
    name = models.CharField(max_length=255)
    hours_cm = models.PositiveSmallIntegerField(default=0, verbose_name='CM')
    hours_td = models.PositiveSmallIntegerField(default=0, verbose_name='TD')
    hours_tp = models.PositiveSmallIntegerField(default=0, verbose_name='TP')
    coefficient = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    passing_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('10.00'),
        verbose_name='Note de validation',
        help_text='Seuil de validation de l\'ECUE (/20)',
    )

    class Meta:
        ordering = ['teaching_unit', 'code']
        unique_together = [['teaching_unit', 'code']]

    def __str__(self):
        return f'{self.code} - {self.name}'


class ProgramCourse(TimeStampedModel):
    """Liaison filière ↔ UE avec crédits spécifiques."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='program_courses')
    teaching_unit = models.ForeignKey(TeachingUnit, on_delete=models.CASCADE, related_name='program_links')
    specialization = models.ForeignKey(
        Specialization, on_delete=models.SET_NULL, null=True, blank=True, related_name='program_courses'
    )
    semester_number = models.PositiveSmallIntegerField()
    is_mandatory = models.BooleanField(default=True)
    credits_override = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        unique_together = [['program', 'teaching_unit', 'specialization']]
        ordering = ['program', 'semester_number']

    @property
    def credits(self):
        return self.credits_override or self.teaching_unit.credits_ects


class StapsJobNomenclature(TimeStampedModel):
    """Nomenclature officielle des emplois STAPS (grades A3/A4, CAPS/CAPEPS)."""

    GRADES = [
        ('A3', 'Grade A3 — Professeur de Collège'),
        ('A4', 'Grade A4 — Professeur de Lycée'),
    ]
    TRACKS = [
        ('PC', 'Professeur de Collège'),
        ('PL', 'Professeur de Lycée'),
    ]
    DIPLOMA_CODES = [
        ('CAPS', 'CAPS'),
        ('CAPEPS', 'CAPEPS'),
        ('CAPCS', 'CAPCS'),
        ('CAPCEPS', 'CAPCEPS'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    degree_type = models.CharField(max_length=2, choices=Program.DEGREE_TYPES)
    specialization = models.ForeignKey(
        Specialization, on_delete=models.PROTECT, related_name='job_nomenclatures'
    )
    civil_service_grade = models.CharField(max_length=2, choices=GRADES, db_index=True)
    track = models.CharField(max_length=2, choices=TRACKS, db_index=True)
    job_title = models.CharField(max_length=255)
    duration_years = models.PositiveSmallIntegerField(default=3)
    competencies = models.TextField(blank=True)
    career_outcomes = models.TextField(blank=True)
    diploma_code = models.CharField(max_length=10, choices=DIPLOMA_CODES, db_index=True)
    diploma_label = models.CharField(max_length=255)
    employers = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['degree_type', 'specialization__code']
        unique_together = [['degree_type', 'specialization']]
        verbose_name = 'Nomenclature emploi STAPS'
        verbose_name_plural = 'Nomenclature emplois STAPS'

    def __str__(self):
        return (
            f'{self.get_degree_type_display()} {self.specialization.code} — '
            f'{self.civil_service_grade} ({self.diploma_code})'
        )
