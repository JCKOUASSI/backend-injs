"""Modèles EPT-INJS.

Correspondance avec l'application source « eptcpafefinal » :

===========================  ==========================================
eptcpafefinal                eptinjs / INJS-LMD
===========================  ==========================================
Formation + FormationPeriode PeriodeFormation (rattachée à AcademicYear)
FormationModule              ProgrammePeriode (ECUE × promotion × période)
referentiels.Module          academics.Course (ECUE)
Groupe                       academics.Promotion + GroupePedagogique
Auditeur                     students.Student
Formateur                    faculty.Teacher
Salle / Batiment / Site      faculty.Room (code, building, capacity)
Seance                       Seance (datée, sert aussi de séance de badgeage)
ParametreGeneral/Formation   ParametresPlanification
JourFerie                    JourFerie
PlanningRun / AuditLog       PlanningRun / PlanningAuditLog
(absent de la source)        SeanceQRToken / Pointage
===========================  ==========================================
"""
from __future__ import annotations

import uuid
from datetime import date as date_cls, datetime, time as time_cls, timedelta

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel

SESSION_KINDS = [
    ('cm', 'Cours magistral'),
    ('td', 'Travaux dirigés'),
    ('tp', 'Travaux pratiques'),
]

CRENEAU_MODES = [
    ('matin', 'Matin uniquement'),
    ('soir', 'Après-midi uniquement'),
    ('matin_et_soir', 'Matin et après-midi'),
]

WEEKDAYS = [
    (0, 'Lundi'), (1, 'Mardi'), (2, 'Mercredi'),
    (3, 'Jeudi'), (4, 'Vendredi'), (5, 'Samedi'), (6, 'Dimanche'),
]


def default_jours_actifs():
    return [0, 1, 2, 3, 4]


def default_matin_debut():
    return time_cls(8, 0)


def default_matin_fin():
    return time_cls(12, 0)


def default_soir_debut():
    return time_cls(14, 0)


def default_soir_fin():
    return time_cls(18, 0)


def minutes_between(start, end) -> int:
    """Durée en minutes entre deux ``time`` sur une même journée."""
    pivot = date_cls(2000, 1, 1)
    delta = datetime.combine(pivot, end) - datetime.combine(pivot, start)
    return max(int(delta.total_seconds() // 60), 0)


class PeriodeFormation(TimeStampedModel):
    """Fenêtre calendaire de planification (« période de formation »).

    Un ECUE peut être programmé sur plusieurs périodes : c'est ce qui permet au
    module Cours (ECUE) d'agréger les emplois du temps de toutes les périodes.
    """

    STATUTS = [
        ('brouillon', 'Brouillon'),
        ('ouverte', 'Ouverte'),
        ('planifiee', 'Planifiée'),
        ('cloturee', 'Clôturée'),
    ]
    RYTHMES = [
        ('1', '1 semaine par mois'),
        ('2', '2 semaines par mois'),
        ('3', '3 semaines par mois'),
        ('4', 'Toutes les semaines'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    academic_year = models.ForeignKey(
        'academics.AcademicYear', on_delete=models.CASCADE, related_name='periodes_formation',
    )
    semester = models.ForeignKey(
        'academics.Semester', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='periodes_formation',
    )
    code = models.CharField(max_length=30, db_index=True)
    libelle = models.CharField(max_length=150)
    date_debut = models.DateField()
    date_fin = models.DateField()
    ordre = models.PositiveSmallIntegerField(default=1)
    rythme_mensuel = models.CharField(max_length=1, choices=RYTHMES, default='4')
    statut = models.CharField(max_length=20, choices=STATUTS, default='ouverte', db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['-academic_year__start_date', 'ordre', 'date_debut']
        unique_together = [['academic_year', 'code']]
        verbose_name = 'Période de formation'
        verbose_name_plural = 'Périodes de formation'

    def __str__(self):
        return f'{self.code} — {self.libelle}'

    def clean(self):
        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError({'date_fin': 'La date de fin précède la date de début.'})

    def semaine_autorisee(self, jour: date_cls) -> bool:
        """Applique le rythme mensuel : n premières semaines du mois."""
        limite = int(self.rythme_mensuel or '4')
        if limite >= 4:
            return True
        return ((jour.day - 1) // 7) + 1 <= limite


class ParametresPlanification(TimeStampedModel):
    """Réglages du moteur de génération.

    La ligne dont ``periode`` est nul porte les valeurs par défaut de
    l'établissement ; chaque période peut la surcharger.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    periode = models.OneToOneField(
        PeriodeFormation, on_delete=models.CASCADE, null=True, blank=True,
        related_name='parametres',
    )
    jours_actifs = models.JSONField(default=default_jours_actifs, help_text='0 = lundi … 6 = dimanche')
    matin_actif = models.BooleanField(default=True)
    matin_debut = models.TimeField(default=default_matin_debut)
    matin_fin = models.TimeField(default=default_matin_fin)
    soir_actif = models.BooleanField(default=True)
    soir_debut = models.TimeField(default=default_soir_debut)
    soir_fin = models.TimeField(default=default_soir_fin)
    duree_seance_minutes = models.PositiveSmallIntegerField(default=120, validators=[MinValueValidator(30)])
    max_seances_par_jour = models.PositiveSmallIntegerField(default=2, validators=[MinValueValidator(1)])
    tolerance_capacite_pct = models.PositiveSmallIntegerField(
        default=10, help_text='Dépassement toléré de la capacité de salle, en %.',
    )
    verrouiller_salle_par_groupe = models.BooleanField(
        default=False, help_text='Conserver la même salle pour toutes les séances d’un groupe.',
    )
    poids_ecart_capacite = models.PositiveSmallIntegerField(default=5)
    poids_rotation_salle = models.PositiveSmallIntegerField(default=2)
    poids_equilibrage_salles = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name = 'Paramètres de planification'
        verbose_name_plural = 'Paramètres de planification'

    def __str__(self):
        return f'Paramètres — {self.periode or "valeurs par défaut"}'

    @classmethod
    def resolve(cls, periode: PeriodeFormation | None) -> 'ParametresPlanification':
        """Paramètres applicables : surcharge de période sinon valeurs par défaut."""
        if periode is not None:
            specifiques = cls.objects.filter(periode=periode).first()
            if specifiques is not None:
                return specifiques
        globaux = cls.objects.filter(periode__isnull=True).first()
        return globaux or cls.objects.create(periode=None)

    def creneaux(self) -> list[tuple[str, object, object]]:
        plages = []
        if self.matin_actif:
            plages.append(('matin', self.matin_debut, self.matin_fin))
        if self.soir_actif:
            plages.append(('soir', self.soir_debut, self.soir_fin))
        return plages


class JourFerie(TimeStampedModel):
    """Jour exclu de la planification."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(
        'academics.Institution', on_delete=models.CASCADE, related_name='jours_feries',
    )
    date = models.DateField(db_index=True)
    libelle = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['date']
        unique_together = [['institution', 'date']]
        verbose_name = 'Jour férié'
        verbose_name_plural = 'Jours fériés'

    def __str__(self):
        return f'{self.date} — {self.libelle}'


class GroupePedagogique(TimeStampedModel):
    """Sous-groupe d'une promotion pour les TD/TP (équivalent ``groupes.Groupe``)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promotion = models.ForeignKey(
        'academics.Promotion', on_delete=models.CASCADE, related_name='groupes_pedagogiques',
    )
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    effectif_max = models.PositiveSmallIntegerField(default=30, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['promotion', 'code']
        unique_together = [['promotion', 'code']]
        verbose_name = 'Groupe pédagogique'
        verbose_name_plural = 'Groupes pédagogiques'

    def __str__(self):
        return f'{self.promotion} · {self.code}'

    @property
    def effectif(self) -> int:
        return self.membres.count()


class GroupeMembre(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    groupe = models.ForeignKey(GroupePedagogique, on_delete=models.CASCADE, related_name='membres')
    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE, related_name='groupes_pedagogiques',
    )

    class Meta:
        unique_together = [['groupe', 'student']]
        verbose_name = 'Membre de groupe'
        verbose_name_plural = 'Membres de groupe'


class ProgrammePeriode(TimeStampedModel):
    """Volume d'un ECUE à planifier pour une promotion sur une période.

    Équivalent de ``formations.FormationModule`` : c'est l'entrée du moteur de
    génération et le pivot entre le catalogue LMD et l'emploi du temps.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    periode = models.ForeignKey(PeriodeFormation, on_delete=models.CASCADE, related_name='programmes')
    course = models.ForeignKey(
        'academics.Course', on_delete=models.CASCADE, related_name='programmes_periode',
    )
    promotion = models.ForeignKey(
        'academics.Promotion', on_delete=models.CASCADE, related_name='programmes_periode',
    )
    session_kind = models.CharField(max_length=5, choices=SESSION_KINDS, default='cm', db_index=True)
    teacher = models.ForeignKey(
        'faculty.Teacher', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='programmes_periode', verbose_name='Enseignant titulaire',
    )
    supervisor = models.ForeignKey(
        'faculty.Teacher', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='programmes_periode_encadres', verbose_name='Encadrant',
    )
    volume_horaire_minutes = models.PositiveIntegerField(
        default=0, help_text='Volume à planifier sur la période, en minutes.',
    )
    creneau_mode = models.CharField(max_length=15, choices=CRENEAU_MODES, default='matin_et_soir')
    salle_preferee = models.ForeignKey(
        'faculty.Room', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='programmes_preferes',
    )
    groupes = models.ManyToManyField(
        GroupePedagogique, blank=True, related_name='programmes',
        help_text='Vide = promotion entière (un seul flux de séances).',
    )
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['periode', 'promotion', 'course']
        unique_together = [['periode', 'course', 'promotion', 'session_kind']]
        verbose_name = 'Programme de période'
        verbose_name_plural = 'Programmes de période'

    def __str__(self):
        return f'{self.course} · {self.promotion} · {self.periode.code} ({self.session_kind})'

    def clean(self):
        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError({'date_fin': 'La date de fin précède la date de début.'})

    @property
    def volume_horaire_heures(self) -> float:
        return round((self.volume_horaire_minutes or 0) / 60, 2)

    @property
    def fenetre(self) -> tuple[date_cls, date_cls]:
        return (
            self.date_debut or self.periode.date_debut,
            self.date_fin or self.periode.date_fin,
        )

    def volume_maquette_minutes(self) -> int:
        """Volume théorique issu de la maquette LMD pour ce type de séance."""
        mapping = {
            'cm': self.course.hours_cm,
            'td': self.course.hours_td,
            'tp': self.course.hours_tp,
        }
        return int(mapping.get(self.session_kind, 0) or 0) * 60

    def minutes_planifiees(self) -> int:
        agg = self.seances.exclude(statut='annulee').aggregate(total=models.Sum('duree_minutes'))
        return int(agg['total'] or 0)


class Seance(TimeStampedModel):
    """Séance datée : unité d'emploi du temps **et** séance de badgeage.

    Remplace ``faculty.Schedule`` (créneau hebdomadaire récurrent) : comme la
    séance porte déjà une date, elle tient aussi le rôle d'``AttendanceSession``.
    """

    STATUTS = [
        ('planifiee', 'Planifiée'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    ]
    ORIGINES = [
        ('auto', 'Génération automatique'),
        ('manuelle', 'Saisie manuelle'),
        ('import', 'Import'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    programme = models.ForeignKey(
        ProgrammePeriode, on_delete=models.CASCADE, related_name='seances',
    )
    periode = models.ForeignKey(
        PeriodeFormation, on_delete=models.CASCADE, related_name='seances',
    )
    course = models.ForeignKey(
        'academics.Course', on_delete=models.CASCADE, related_name='seances',
    )
    promotion = models.ForeignKey(
        'academics.Promotion', on_delete=models.CASCADE, related_name='seances',
    )
    groupe = models.ForeignKey(
        GroupePedagogique, on_delete=models.SET_NULL, null=True, blank=True, related_name='seances',
    )
    teacher = models.ForeignKey(
        'faculty.Teacher', on_delete=models.SET_NULL, null=True, blank=True, related_name='seances',
    )
    supervisor = models.ForeignKey(
        'faculty.Teacher', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='seances_encadrees',
    )
    room = models.ForeignKey(
        'faculty.Room', on_delete=models.SET_NULL, null=True, blank=True, related_name='seances',
    )
    session_kind = models.CharField(max_length=5, choices=SESSION_KINDS, default='cm', db_index=True)
    numero = models.PositiveSmallIntegerField(default=1)
    intitule = models.CharField(max_length=200, blank=True)
    date = models.DateField(db_index=True)
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    duree_minutes = models.PositiveSmallIntegerField(default=0)
    statut = models.CharField(max_length=15, choices=STATUTS, default='planifiee', db_index=True)
    origine = models.CharField(max_length=10, choices=ORIGINES, default='auto')
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    started_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='seances_demarrees',
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['date', 'heure_debut']
        verbose_name = 'Séance'
        verbose_name_plural = 'Séances'
        indexes = [
            models.Index(fields=['periode', 'date']),
            models.Index(fields=['course', 'promotion', 'date']),
            models.Index(fields=['room', 'date']),
            models.Index(fields=['teacher', 'date']),
        ]

    def __str__(self):
        return f'{self.course.code} · {self.date} {self.heure_debut:%H:%M}'

    def clean(self):
        if self.heure_debut and self.heure_fin and self.heure_fin <= self.heure_debut:
            raise ValidationError({'heure_fin': 'L’heure de fin doit suivre l’heure de début.'})

    def save(self, *args, **kwargs):
        if self.heure_debut and self.heure_fin:
            self.duree_minutes = minutes_between(self.heure_debut, self.heure_fin)
        if self.programme_id:
            self.periode_id = self.programme.periode_id
            self.course_id = self.programme.course_id
            self.promotion_id = self.programme.promotion_id
            if not self.session_kind:
                self.session_kind = self.programme.session_kind
        super().save(*args, **kwargs)

    @property
    def duree_heures(self) -> float:
        return round((self.duree_minutes or 0) / 60, 2)

    @property
    def day_of_week(self) -> int:
        return self.date.weekday()

    @property
    def is_open(self) -> bool:
        return self.statut == 'en_cours'

    def chevauche(self, autre: 'Seance') -> bool:
        return (
            self.date == autre.date
            and self.heure_debut < autre.heure_fin
            and autre.heure_debut < self.heure_fin
        )

    def token_actif(self) -> 'SeanceQRToken | None':
        return self.qr_tokens.filter(is_active=True, expires_at__gt=timezone.now()).first()


class SeanceQRToken(TimeStampedModel):
    """Jeton QR d'une séance, scanné par les étudiants et les enseignants."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seance = models.ForeignKey(Seance, on_delete=models.CASCADE, related_name='qr_tokens')
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    expires_at = models.DateTimeField()
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='qr_tokens_eptinjs',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Jeton QR de séance'
        verbose_name_plural = 'Jetons QR de séance'

    def __str__(self):
        return f'QR {self.token} — {self.seance_id}'

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=12)
        super().save(*args, **kwargs)

    @property
    def est_valide(self) -> bool:
        return self.is_active and self.expires_at > timezone.now()


class Pointage(TimeStampedModel):
    """Badgeage entrée/sortie d'une personne sur une séance.

    Un même modèle couvre étudiants, formateurs et encadrants (là où INJS
    séparait ``Attendance`` et ``StaffAttendance``).
    """

    ROLES = [
        ('etudiant', 'Étudiant'),
        ('formateur', 'Formateur'),
        ('encadrant', 'Encadrant'),
    ]
    STATUTS = [
        ('attendu', 'Attendu'),
        ('present', 'Présent'),
        ('retard', 'Retard'),
        ('absent', 'Absent'),
        ('excuse', 'Excusé'),
        ('force', 'Forcé'),
    ]
    SOURCES = [
        ('qr', 'Scan QR'),
        ('manuel', 'Saisie manuelle'),
        ('force', 'Forçage administratif'),
        ('auto', 'Clôture automatique'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seance = models.ForeignKey(Seance, on_delete=models.CASCADE, related_name='pointages')
    role = models.CharField(max_length=12, choices=ROLES, default='etudiant', db_index=True)
    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE, null=True, blank=True, related_name='pointages',
    )
    teacher = models.ForeignKey(
        'faculty.Teacher', on_delete=models.CASCADE, null=True, blank=True, related_name='pointages',
    )
    statut = models.CharField(max_length=10, choices=STATUTS, default='attendu', db_index=True)
    source = models.CharField(max_length=10, choices=SOURCES, default='qr')
    entree_at = models.DateTimeField(null=True, blank=True)
    sortie_at = models.DateTimeField(null=True, blank=True)
    duree_minutes = models.PositiveSmallIntegerField(default=0)
    device_id = models.CharField(max_length=80, blank=True, db_index=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    accuracy_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    outside_geofence_count = models.PositiveSmallIntegerField(default=0)
    recorded_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='pointages_saisis',
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['seance', 'role', 'id']
        unique_together = [['seance', 'student'], ['seance', 'teacher', 'role']]
        verbose_name = 'Pointage'
        verbose_name_plural = 'Pointages'
        indexes = [models.Index(fields=['seance', 'statut'])]

    def __str__(self):
        return f'{self.personne_nom} — {self.seance_id} ({self.statut})'

    def clean(self):
        if self.role == 'etudiant' and not self.student_id:
            raise ValidationError({'student': 'Un pointage étudiant requiert un étudiant.'})
        if self.role != 'etudiant' and not self.teacher_id:
            raise ValidationError({'teacher': 'Un pointage personnel requiert un enseignant.'})

    @property
    def personne_nom(self) -> str:
        if self.student_id:
            return self.student.user.get_full_name()
        if self.teacher_id:
            return self.teacher.user.get_full_name()
        return '—'

    @property
    def est_present(self) -> bool:
        return self.statut in {'present', 'retard', 'force'}

    def recalculer_duree(self) -> int:
        if self.entree_at and self.sortie_at and self.sortie_at > self.entree_at:
            self.duree_minutes = min(
                int((self.sortie_at - self.entree_at).total_seconds() // 60),
                self.seance.duree_minutes or 24 * 60,
            )
        else:
            self.duree_minutes = 0
        return self.duree_minutes


class PlanningRun(TimeStampedModel):
    """Trace d'une exécution du moteur de génération."""

    MODES = [('strict', 'Strict'), ('best_effort', 'Au mieux')]
    STATUTS = [('running', 'En cours'), ('done', 'Terminée'), ('error', 'En erreur')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    periode = models.ForeignKey(PeriodeFormation, on_delete=models.CASCADE, related_name='runs')
    mode = models.CharField(max_length=15, choices=MODES, default='best_effort')
    statut = models.CharField(max_length=10, choices=STATUTS, default='running', db_index=True)
    scope = models.JSONField(default=dict, blank=True)
    synthese = models.JSONField(default=dict, blank=True)
    started_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='planning_runs',
    )
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Exécution de planification'
        verbose_name_plural = 'Exécutions de planification'

    def __str__(self):
        return f'{self.periode.code} — {self.statut}'


class PlanningAuditLog(TimeStampedModel):
    """Journal des actions sensibles (génération, édition, badgeage, exports)."""

    ACTIONS = [
        ('generate', 'Génération'),
        ('create', 'Création'),
        ('update', 'Modification'),
        ('delete', 'Suppression'),
        ('start', 'Démarrage de séance'),
        ('stop', 'Clôture de séance'),
        ('badge', 'Badgeage'),
        ('force', 'Forçage'),
        ('export', 'Export'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=15, choices=ACTIONS, db_index=True)
    periode = models.ForeignKey(
        PeriodeFormation, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs',
    )
    seance = models.ForeignKey(
        Seance, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs',
    )
    actor = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='eptinjs_audit_logs',
    )
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Journal de planification'
        verbose_name_plural = 'Journaux de planification'

    def __str__(self):
        return f'{self.action} — {self.created_at:%Y-%m-%d %H:%M}'

    @classmethod
    def log(cls, action, *, actor=None, periode=None, seance=None, **details):
        return cls.objects.create(
            action=action, actor=actor, periode=periode, seance=seance, details=details,
        )
