import uuid
from datetime import datetime, time

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
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


def default_active_days():
    """Lundi à vendredi."""
    return [0, 1, 2, 3, 4]


class PlanningSettings(TimeStampedModel):
    """Réglages du moteur de planification, par période ou à défaut pour l'établissement."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_global = models.BooleanField(default=False, editable=False, db_index=True)
    period = models.OneToOneField(
        'academics.FormationPeriod', on_delete=models.CASCADE,
        null=True, blank=True, related_name='planning_settings',
        help_text='Vide = réglages par défaut de l’établissement.',
    )
    morning_start = models.TimeField(default=time(8, 0))
    morning_end = models.TimeField(default=time(12, 0))
    afternoon_start = models.TimeField(default=time(14, 0))
    afternoon_end = models.TimeField(default=time(18, 0))
    active_days = models.JSONField(
        default=default_active_days, blank=True,
        help_text='Jours ouvrés, 0 = lundi.',
    )
    session_duration_minutes = models.PositiveSmallIntegerField(
        default=120, validators=[MinValueValidator(30)],
    )
    max_sessions_per_day = models.PositiveSmallIntegerField(
        default=3, validators=[MinValueValidator(1)],
    )
    max_rooms_per_course = models.PositiveSmallIntegerField(
        default=10, validators=[MinValueValidator(1)],
        help_text='Salles mobilisables simultanément pour un même ECUE.',
    )
    capacity_tolerance = models.PositiveSmallIntegerField(
        default=0, help_text='Étudiants tolérés au-delà de la capacité d’une salle.',
    )
    lock_room_per_group = models.BooleanField(
        default=False, help_text='Conserver la même salle pour un groupe sur toute la période.',
    )
    spread_remainder = models.BooleanField(
        default=False, help_text='Étaler le reliquat horaire sur les séances déjà placées.',
    )
    weight_capacity_gap = models.PositiveSmallIntegerField(default=10)
    weight_room_rotation = models.PositiveSmallIntegerField(default=2)
    weight_global_balance = models.PositiveSmallIntegerField(default=1)
    late_after_minutes = models.PositiveSmallIntegerField(
        default=15, help_text='Minutes après le début prévu pour qualifier un retard.',
    )
    partial_under_percent = models.PositiveSmallIntegerField(
        default=75, help_text='Présence partielle sous ce pourcentage de la durée prévue.',
    )
    auto_absent_after_minutes = models.PositiveSmallIntegerField(
        default=60, help_text='Minutes après la fin prévue avant auto-absence.',
    )

    class Meta:
        verbose_name = 'Paramètres de planification'
        verbose_name_plural = 'Paramètres de planification'
        constraints = [
            models.UniqueConstraint(
                fields=['is_global'],
                condition=models.Q(is_global=True),
                name='uniq_global_planning_settings',
            ),
        ]

    def __str__(self):
        return f'Paramètres — {self.period}' if self.period_id else 'Paramètres par défaut'

    def save(self, *args, **kwargs):
        self.is_global = self.period_id is None
        super().save(*args, **kwargs)

    @classmethod
    def resolve(cls, period=None):
        """Réglages applicables : ceux de la période, sinon les globaux, sinon les défauts."""
        if period is not None:
            specific = cls.objects.filter(period=period).first()
            if specific:
                return specific
        return cls.objects.filter(is_global=True).first() or cls()

    @classmethod
    def set_global(cls, **values):
        """Crée ou met à jour l'unique jeu de réglages par défaut."""
        obj, _ = cls.objects.update_or_create(is_global=True, defaults={**values, 'period': None})
        return obj


class StudentGroup(TimeStampedModel):
    """Sous-groupe pédagogique d'une promotion, pour les TD et les TP."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promotion = models.ForeignKey(
        'academics.Promotion', on_delete=models.CASCADE, related_name='student_groups',
    )
    name = models.CharField(max_length=50)
    max_students = models.PositiveSmallIntegerField(default=25)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['promotion', 'name']
        unique_together = [['promotion', 'name']]
        verbose_name = 'Groupe pédagogique'
        verbose_name_plural = 'Groupes pédagogiques'

    def __str__(self):
        return f'{self.promotion.name} — {self.name}'

    @property
    def headcount(self):
        return self.memberships.count()


class StudentGroupMember(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(StudentGroup, on_delete=models.CASCADE, related_name='memberships')
    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE, related_name='group_memberships',
    )

    class Meta:
        unique_together = [['group', 'student']]
        verbose_name = 'Membre de groupe pédagogique'
        verbose_name_plural = 'Membres de groupes pédagogiques'

    def __str__(self):
        return f'{self.student} → {self.group}'


class GroupSchedulingConfig(TimeStampedModel):
    """Disponibilités horaires propres à un groupe pédagogique."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.OneToOneField(
        StudentGroup, on_delete=models.CASCADE, related_name='scheduling_config',
    )
    morning_enabled = models.BooleanField(default=True)
    morning_start = models.TimeField(default=time(8, 0))
    morning_end = models.TimeField(default=time(12, 0))
    afternoon_enabled = models.BooleanField(default=True)
    afternoon_start = models.TimeField(default=time(14, 0))
    afternoon_end = models.TimeField(default=time(18, 0))
    active_days = models.JSONField(default=default_active_days, blank=True)

    class Meta:
        verbose_name = 'Disponibilités du groupe'
        verbose_name_plural = 'Disponibilités des groupes'

    def __str__(self):
        return f'Disponibilités — {self.group}'


class TeachingLoad(TimeStampedModel):
    """Volume horaire d'un ECUE à planifier sur une période, pour une promotion ou un groupe."""

    SLOT_MODES = [
        ('morning', 'Matin uniquement'),
        ('afternoon', 'Après-midi uniquement'),
        ('both', 'Matin et après-midi'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    period = models.ForeignKey(
        'academics.FormationPeriod', on_delete=models.CASCADE, related_name='teaching_loads',
    )
    course = models.ForeignKey(
        'academics.Course', on_delete=models.PROTECT, related_name='teaching_loads',
    )
    promotion = models.ForeignKey(
        'academics.Promotion', on_delete=models.CASCADE, related_name='teaching_loads',
    )
    group = models.ForeignKey(
        StudentGroup, on_delete=models.CASCADE, null=True, blank=True,
        related_name='teaching_loads', help_text='Vide = promotion entière.',
    )
    teacher = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='teaching_loads',
    )
    supervisor = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='supervised_teaching_loads', verbose_name='Encadrant',
    )
    session_kind = models.CharField(
        max_length=5, choices=Schedule.SESSION_KINDS, default='cm', db_index=True,
    )
    hours_total = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        help_text='Volume horaire à répartir sur la période.',
    )
    slot_mode = models.CharField(max_length=10, choices=SLOT_MODES, default='both')
    preferred_room_type = models.CharField(
        max_length=20, choices=Room.ROOM_TYPES, blank=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['period', 'course']
        verbose_name = 'Charge à planifier'
        verbose_name_plural = 'Charges à planifier'
        constraints = [
            # Deux contraintes distinctes : en SQL, NULL n'est jamais égal à NULL,
            # une unicité unique laisserait donc passer les doublons sans groupe.
            models.UniqueConstraint(
                fields=['period', 'course', 'promotion', 'group', 'session_kind'],
                condition=models.Q(group__isnull=False),
                name='uniq_teaching_load_per_group',
            ),
            models.UniqueConstraint(
                fields=['period', 'course', 'promotion', 'session_kind'],
                condition=models.Q(group__isnull=True),
                name='uniq_teaching_load_per_promotion',
            ),
        ]

    def __str__(self):
        cible = self.group.name if self.group_id else self.promotion.name
        return f'{self.course.code} — {cible} ({self.get_session_kind_display()}, {self.hours_total}h)'

    @property
    def audience(self):
        """Public visé : le groupe s'il existe, sinon la promotion entière."""
        return self.group or self.promotion


class Seance(TimeStampedModel):
    """Séance pédagogique datée : l'unité de l'emploi du temps, du cours et du badgeage.

    Contrairement à ``Schedule``, qui décrit un créneau hebdomadaire récurrent servant
    de gabarit, une séance porte une date réelle et peut être déplacée, réaffectée ou
    annulée individuellement. Elle conserve un lien de provenance vers le gabarit et
    vers la charge dont elle est issue, tous deux facultatifs.
    """

    STATUSES = [
        ('draft', 'Brouillon'),
        ('generated', 'Généré'),
        ('validated', 'Validé'),
        ('published', 'Publié'),
        ('in_progress', 'En cours'),
        ('done', 'Terminé'),
        ('cancelled', 'Annulé'),
        ('archived', 'Archivé'),
    ]

    # Statuts pour lesquels la séance est visible des étudiants et ouvrable au badgeage.
    VISIBLE_STATUSES = ('published', 'in_progress', 'done')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Provenance, facultative : une séance peut être créée à la main.
    period = models.ForeignKey(
        'academics.FormationPeriod', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='seances',
    )
    teaching_load = models.ForeignKey(
        TeachingLoad, on_delete=models.SET_NULL, null=True, blank=True, related_name='seances',
    )
    schedule = models.ForeignKey(
        Schedule, on_delete=models.SET_NULL, null=True, blank=True, related_name='seances',
        help_text='Gabarit hebdomadaire dont la séance est issue, le cas échéant.',
    )

    # Contenu de la séance : sa propre vérité, modifiable indépendamment du gabarit.
    course = models.ForeignKey(
        'academics.Course', on_delete=models.PROTECT, related_name='seances',
    )
    promotion = models.ForeignKey(
        'academics.Promotion', on_delete=models.CASCADE, related_name='seances',
    )
    group = models.ForeignKey(
        StudentGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='seances',
        help_text='Vide = promotion entière.',
    )
    teacher = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='seances',
    )
    supervisor = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='supervised_seances', verbose_name='Encadrant',
    )
    room = models.ForeignKey(
        Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='seances',
    )
    session_kind = models.CharField(
        max_length=5, choices=Schedule.SESSION_KINDS, default='cm', db_index=True,
    )
    date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()

    status = models.CharField(max_length=15, choices=STATUSES, default='draft', db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    # Badgeage : repris d'AttendanceSession pour que la séance soit l'unique unité de présence.
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_seances',
    )
    teacher_checked_in = models.BooleanField(default=False)
    teacher_checked_in_at = models.DateTimeField(null=True, blank=True)
    teacher_checked_in_by = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='checked_in_seances',
    )
    supervisor_checked_in = models.BooleanField(default=False)
    supervisor_checked_in_at = models.DateTimeField(null=True, blank=True)
    supervisor_checked_in_by = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='checked_in_supervised_seances',
    )

    class Meta:
        ordering = ['date', 'start_time']
        verbose_name = 'Séance'
        verbose_name_plural = 'Séances'
        indexes = [
            models.Index(fields=['date', 'status']),
            models.Index(fields=['promotion', 'date']),
            models.Index(fields=['teacher', 'date']),
            models.Index(fields=['room', 'date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['schedule', 'date'],
                condition=models.Q(schedule__isnull=False),
                name='uniq_seance_per_schedule_and_date',
            ),
        ]

    def __str__(self):
        return f'{self.course.code} — {self.date:%d/%m/%Y} {self.start_time:%H:%M}'

    def clean(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({
                'end_time': "L'heure de fin doit être postérieure à l'heure de début.",
            })
        if self.period_id and self.date and not self.period.covers(self.date):
            raise ValidationError({
                'date': (
                    f'Le {self.date:%d/%m/%Y} est hors de la période « {self.period.label} ».'
                ),
            })

    @property
    def day_of_week(self):
        return self.date.weekday()

    @property
    def duration_minutes(self):
        start = datetime.combine(self.date, self.start_time)
        end = datetime.combine(self.date, self.end_time)
        return max(int((end - start).total_seconds() // 60), 0)

    @property
    def is_visible(self):
        """Une séance n'est visible des étudiants qu'une fois publiée."""
        return self.status in self.VISIBLE_STATUSES

    def resolved_supervisor(self):
        """Encadrant de la séance, sinon celui de l'affectation d'origine."""
        if self.supervisor_id:
            return self.supervisor
        if self.schedule_id:
            return self.schedule.resolved_supervisor()
        return None

    def staff_ids(self):
        ids = set()
        if self.teacher_id:
            ids.add(self.teacher_id)
        supervisor = self.resolved_supervisor()
        if supervisor:
            ids.add(supervisor.id)
        return ids


class TimetableRun(TimeStampedModel):
    """Trace d'une exécution du moteur de planification."""

    MODES = [
        ('best_effort', 'Meilleur effort'),
        ('strict', 'Strict'),
    ]
    STATUSES = [
        ('running', 'En cours'),
        ('done', 'Terminé'),
        ('error', 'Erreur'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    period = models.ForeignKey(
        'academics.FormationPeriod', on_delete=models.CASCADE, related_name='timetable_runs',
    )
    promotion = models.ForeignKey(
        'academics.Promotion', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='timetable_runs',
    )
    actor = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='timetable_runs',
    )
    mode = models.CharField(max_length=20, choices=MODES, default='best_effort')
    status = models.CharField(max_length=10, choices=STATUSES, default='running', db_index=True)
    summary = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name = 'Exécution de planification'
        verbose_name_plural = 'Exécutions de planification'

    def __str__(self):
        cible = self.promotion.name if self.promotion_id else 'toutes promotions'
        return f'{self.period.label} — {cible} ({self.get_status_display()})'


class Attendance(TimeStampedModel):
    STATUSES = [
        ('present', 'Présent'),
        ('absent', 'Absent'),
        ('late', 'Retard'),
        ('partial', 'Présence partielle'),
        ('excused', 'Excusé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='attendances')
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='attendances')
    seance = models.ForeignKey(
        'faculty.Seance', on_delete=models.CASCADE, null=True, blank=True, related_name='attendances',
    )
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
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    late_minutes = models.PositiveSmallIntegerField(default=0)

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
    seance = models.ForeignKey(
        'faculty.Seance', on_delete=models.CASCADE, null=True, blank=True,
        related_name='staff_attendances',
    )
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
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    late_minutes = models.PositiveSmallIntegerField(default=0)

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


class BadgeEvent(models.Model):
    """Journal immuable d'un badgeage ou d'une correction de présence.

    Distinct de ``Attendance`` (état courant) et de ``AuditLog`` (trace générique).
    """

    KINDS = [
        ('check_in', 'Entrée'),
        ('check_out', 'Sortie'),
        ('correction', 'Correction'),
        ('force', 'Forçage'),
        ('auto_absent', 'Auto-absence'),
    ]
    SOURCES = [
        ('qr', 'QR'),
        ('admin', 'Administration'),
        ('teacher', 'Formateur'),
        ('system', 'Système'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=20, choices=KINDS, db_index=True)
    source = models.CharField(max_length=20, choices=SOURCES, default='qr', db_index=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    actor = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='badge_events',
    )
    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE, null=True, blank=True,
        related_name='badge_events',
    )
    teacher = models.ForeignKey(
        Teacher, on_delete=models.CASCADE, null=True, blank=True,
        related_name='badge_events',
    )
    attendance = models.ForeignKey(
        Attendance, on_delete=models.CASCADE, null=True, blank=True,
        related_name='badge_events',
    )
    staff_attendance = models.ForeignKey(
        StaffAttendance, on_delete=models.CASCADE, null=True, blank=True,
        related_name='badge_events',
    )
    seance = models.ForeignKey(
        'faculty.Seance', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='badge_events',
    )
    schedule = models.ForeignKey(
        Schedule, on_delete=models.CASCADE, null=True, blank=True,
        related_name='badge_events',
    )
    session_date = models.DateField(db_index=True)
    previous_status = models.CharField(max_length=10, blank=True)
    new_status = models.CharField(max_length=10, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    device_id = models.CharField(max_length=80, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    accuracy_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-occurred_at']
        verbose_name = 'Événement de badgeage'
        verbose_name_plural = 'Événements de badgeage'
        indexes = [
            models.Index(fields=['student', '-occurred_at']),
            models.Index(fields=['seance', 'kind']),
            models.Index(fields=['attendance', '-occurred_at']),
        ]

    def __str__(self):
        cible = self.student or self.teacher or '?'
        return f'{self.get_kind_display()} — {cible} ({self.session_date})'
