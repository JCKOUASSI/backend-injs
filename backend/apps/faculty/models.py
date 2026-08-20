import uuid
from django.db import models
from apps.core.models import TimeStampedModel


class Teacher(TimeStampedModel):
    GRADES = [
        ('assistant', 'Assistant'),
        ('maitre_assistant', 'Maître-Assistant'),
        ('maitre_conferences', 'Maître de Conférences'),
        ('professeur', 'Professeur'),
        ('vacataire', 'Vacataire'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='teacher_profile')
    employee_id = models.CharField(max_length=20, unique=True, db_index=True)
    department = models.ForeignKey('academics.Department', on_delete=models.PROTECT, related_name='teachers')
    grade = models.CharField(max_length=30, choices=GRADES)
    specialization = models.CharField(max_length=255, blank=True)
    gender = models.CharField(
        max_length=1,
        choices=[('M', 'Masculin'), ('F', 'Féminin')],
        blank=True,
        db_index=True,
    )
    hire_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['user__last_name']

    def __str__(self):
        return f'{self.employee_id} - {self.user.get_full_name()}'


class Room(TimeStampedModel):
    """Espace pédagogique / infrastructure campus INJS (salles, labs, gymnases, terrains…)."""

    ROOM_TYPES = [
        ('amphitheater', 'Amphithéâtre'),       # AMP
        ('classroom', 'Salle de cours'),        # SC
        ('td', 'Salle de TD'),                  # TD
        ('tp', 'Salle de TP'),                  # TP
        ('lab', 'Laboratoire'),                 # LAB
        ('computer', 'Salle informatique'),     # INF
        ('gym', 'Gymnase'),                     # GYM
        ('medical', 'Médecine du sport'),       # MED
        ('sport', 'Installation sportive'),     # SPORT
        ('conference', 'Salle de conférence'),  # CONF
        ('seminar', 'Salle de séminaire'),      # SEM
        ('library', 'Bibliothèque'),
        ('research', 'Espace recherche'),
        ('admin', 'Espace administratif'),
        ('residence', 'Résidence'),
        ('outdoor', 'Espace extérieur'),
        ('specialized', 'Salle spécialisée'),
    ]

    BUILDINGS = [
        ('ENSEPS', 'Bloc ENSEPS'),
        ('ENSEP', 'Bloc ENSEP'),
        ('LMD', 'Bâtiment LMD'),
        ('CNMS', 'Centre National de Médecine du Sport'),
        ('CNSHN', 'Centre National du Sport de Haut Niveau'),
        ('GYM', 'Gymnases'),
        ('EXT', 'Installations sportives extérieures'),
        ('LAB', 'Laboratoires pédagogiques'),
        ('NUM', 'Espaces numériques'),
        ('RECH', 'Espaces de recherche'),
        ('BIB', 'Bibliothèque'),
        ('SPEC', 'Salles spécialisées'),
        ('ADM', 'Espaces administratifs'),
        ('POLY', 'Espaces polyvalents'),
        ('RES', 'Résidences pédagogiques'),
        ('CAMPUS', 'Espaces extérieurs campus'),
    ]

    STATUSES = [
        ('available', 'Disponible'),
        ('maintenance', 'En maintenance'),
        ('reserved', 'Réservée'),
        ('inactive', 'Inactive'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('academics.Institution', on_delete=models.CASCADE, related_name='rooms')
    code = models.CharField(max_length=20, db_index=True)
    name = models.CharField(max_length=150)
    capacity = models.PositiveSmallIntegerField(default=30)
    building = models.CharField(max_length=20, choices=BUILDINGS, blank=True, db_index=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='classroom', db_index=True)
    floor = models.CharField(max_length=20, blank=True)
    equipment = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default='available', db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [['institution', 'code']]
        ordering = ['building', 'code']

    def __str__(self):
        return f'{self.code} — {self.name}'


class CourseAssignment(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='assignments')
    supervisor = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='supervised_assignments',
        verbose_name='Encadrant',
        help_text='Encadrant pédagogique (TP, stages, séances pratiques).',
    )
    course = models.ForeignKey('academics.Course', on_delete=models.CASCADE, related_name='assignments')
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE)
    promotion = models.ForeignKey('academics.Promotion', on_delete=models.CASCADE, related_name='assignments')
    is_primary = models.BooleanField(default=True)

    class Meta:
        unique_together = [['teacher', 'course', 'academic_year', 'promotion']]


class Schedule(TimeStampedModel):
    DAYS = [(i, d) for i, d in enumerate(['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'])]
    SESSION_KINDS = [
        ('cm', 'Cours magistral'),
        ('td', 'Travaux dirigés'),
        ('tp', 'Travaux pratiques'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(CourseAssignment, on_delete=models.CASCADE, related_name='schedules')
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, related_name='schedules')
    supervisor = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='supervised_schedules',
        verbose_name='Encadrant de séance',
    )
    session_kind = models.CharField(max_length=5, choices=SESSION_KINDS, default='cm', db_index=True)
    day_of_week = models.PositiveSmallIntegerField(choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['day_of_week', 'start_time']

    def resolved_supervisor(self):
        """Encadrant de la séance, sinon celui de l'affectation."""
        return self.supervisor or getattr(self.assignment, 'supervisor', None)


class Attendance(TimeStampedModel):
    STATUSES = [('present', 'Présent'), ('absent', 'Absent'), ('late', 'Retard'), ('excused', 'Excusé')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='attendances')
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=10, choices=STATUSES, default='present')
    recorded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    notes = models.CharField(max_length=255, blank=True)
    device_id = models.CharField(max_length=80, blank=True, db_index=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    accuracy_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    outside_geofence_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = [['student', 'schedule', 'date']]


class AttendanceSession(TimeStampedModel):
    """Séance de badgeage ouverte par l'administration (schedule + date)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='attendance_sessions')
    session_date = models.DateField(db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, related_name='opened_attendance_sessions',
    )
    teacher_checked_in = models.BooleanField(default=False)
    teacher_checked_in_at = models.DateTimeField(null=True, blank=True)
    teacher_checked_in_by = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='checked_in_sessions',
    )
    supervisor_checked_in = models.BooleanField(default=False)
    supervisor_checked_in_at = models.DateTimeField(null=True, blank=True)
    supervisor_checked_in_by = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='checked_in_supervised_sessions',
    )

    class Meta:
        unique_together = [['schedule', 'session_date']]
        ordering = ['-session_date', 'schedule__start_time']

    def __str__(self):
        return f'{self.schedule} — {self.session_date}'


class StaffAttendance(TimeStampedModel):
    """Présence formateur / encadrant pour une séance planifiée."""

    ROLES = [
        ('formateur', 'Formateur'),
        ('encadrant', 'Encadrant'),
    ]
    STATUSES = Attendance.STATUSES

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='staff_attendances')
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='staff_attendances')
    date = models.DateField(db_index=True)
    role = models.CharField(max_length=15, choices=ROLES, db_index=True)
    status = models.CharField(max_length=10, choices=STATUSES, default='present')
    recorded_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='recorded_staff_attendances',
    )
    notes = models.CharField(max_length=255, blank=True)
    device_id = models.CharField(max_length=80, blank=True, db_index=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    accuracy_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    outside_geofence_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = [['teacher', 'schedule', 'date', 'role']]
        ordering = ['-date', 'role']
        verbose_name = 'Présence personnel pédagogique'
        verbose_name_plural = 'Présences personnel pédagogique'

    def __str__(self):
        return f'{self.get_role_display()} {self.teacher} — {self.date}'


class RoomReservation(TimeStampedModel):
    """Réservation d'infrastructure hors EDT récurrent (événements, examens, etc.)."""

    STATUSES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvée'),
        ('rejected', 'Refusée'),
        ('cancelled', 'Annulée'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='reservations')
    requested_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, related_name='room_reservations',
    )
    title = models.CharField(max_length=200)
    purpose = models.TextField(blank=True)
    start_datetime = models.DateTimeField(db_index=True)
    end_datetime = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUSES, default='pending', db_index=True)
    attendees_count = models.PositiveSmallIntegerField(default=0)
    required_equipment = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-start_datetime']

    def __str__(self):
        return f'{self.title} — {self.room.code}'


class MaintenanceTicket(TimeStampedModel):
    """Ticket de maintenance bâtiment / salle."""

    PRIORITIES = [
        ('low', 'Basse'),
        ('medium', 'Moyenne'),
        ('high', 'Haute'),
        ('critical', 'Critique'),
    ]
    STATUSES = [
        ('open', 'Ouvert'),
        ('in_progress', 'En cours'),
        ('resolved', 'Résolu'),
        ('closed', 'Fermé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='maintenance_tickets')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITIES, default='medium')
    status = models.CharField(max_length=20, choices=STATUSES, default='open', db_index=True)
    reported_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, related_name='reported_tickets',
    )
    assigned_to = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets',
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} ({self.room.code})'


class EquipmentAsset(TimeStampedModel):
    """Inventaire d'équipements campus (évolutif via metadata JSON)."""

    STATUSES = [
        ('available', 'Disponible'),
        ('in_use', 'En service'),
        ('maintenance', 'En maintenance'),
        ('retired', 'Réformé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('academics.Institution', on_delete=models.CASCADE, related_name='equipment_assets')
    code = models.CharField(max_length=40, db_index=True)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=80, blank=True, db_index=True)
    serial_number = models.CharField(max_length=80, blank=True)
    quantity = models.PositiveSmallIntegerField(default=1)
    room = models.ForeignKey(
        Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='assets',
    )
    status = models.CharField(max_length=20, choices=STATUSES, default='available', db_index=True)
    purchase_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    capability_tags = models.JSONField(
        default=list, blank=True,
        help_text='Tags alignés sur Room.equipment pour l’auto-affectation',
    )
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [['institution', 'code']]
        ordering = ['category', 'code']

    def __str__(self):
        return f'{self.code} — {self.name}'


class BadgeDevice(TimeStampedModel):
    """Appareil autorisé pour le badgeage QR (un actif par utilisateur)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='badge_devices',
    )
    device_id = models.CharField(max_length=80, db_index=True)
    device_label = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [['user', 'device_id']]
        ordering = ['-last_seen_at', '-created_at']

    def __str__(self):
        return f'{self.user} — {self.device_id}'
