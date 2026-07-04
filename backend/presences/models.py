from django.conf import settings
from django.db import models
from django.utils import timezone
from formations.models import Participant, Formateur, SessionModule


class Pointage(models.Model):
    class Statut(models.TextChoices):
        EN_COURS = 'EN_COURS', 'En cours (en salle)'
        TERMINE = 'TERMINE', 'Terminé'
        FORCE_DFRC = 'FORCE_DFRC', 'Forcé par DFRC'
        ABSENT_NON_BADGE = 'ABSENT_NON_BADGE', 'Absent (non badgé à la sortie)'
        HORS_LIGNE_SUSPECT = 'HORS_LIGNE_SUSPECT', 'Hors ligne suspect'
        SORTIE_AUTO = 'SORTIE_AUTO', 'Sortie automatique (anti-fraude)'

    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='pointages',
        null=True,
        blank=True,
    )
    formateur = models.ForeignKey(
        Formateur,
        on_delete=models.CASCADE,
        related_name='pointages',
        null=True,
        blank=True,
    )
    encadrant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pointages_encadrant',
        null=True,
        blank=True,
        limit_choices_to={'role': 'ENCADRANT'},
    )
    session = models.ForeignKey(
        SessionModule,
        on_delete=models.CASCADE,
        related_name='pointages',
        help_text="Séance liée à ce pointage",
    )
    date_journee = models.DateField(default=timezone.localdate)
    device_id = models.CharField(max_length=255, blank=True, default='')
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    last_latitude = models.FloatField(null=True, blank=True)
    last_longitude = models.FloatField(null=True, blank=True)
    last_accuracy_m = models.FloatField(null=True, blank=True)
    last_battery_level = models.PositiveSmallIntegerField(null=True, blank=True)
    last_is_charging = models.BooleanField(null=True, blank=True)
    outside_geofence_count = models.PositiveSmallIntegerField(default=0)
    timestamp_entree = models.DateTimeField()
    timestamp_sortie = models.DateTimeField(null=True, blank=True)
    duree_presence_minutes = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.EN_COURS,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_journee', '-timestamp_entree']
        verbose_name = 'Pointage'
        verbose_name_plural = 'Pointages'
        indexes = [
            models.Index(fields=['date_journee', 'session'], name='pointage_date_session_idx'),
            models.Index(fields=['session', 'participant'], name='pointage_session_part_idx'),
        ]

    @property
    def personne(self):
        """Retourne la personne liée (participant, formateur ou encadrant)."""
        return self.participant or self.formateur or self.encadrant

    @property
    def type_personne(self):
        if self.formateur_id:
            return 'formateur'
        if self.encadrant_id:
            return 'encadrant'
        return 'participant'

    @property
    def formation(self):
        return self.session.module.formation

    def __str__(self):
        personne = self.personne
        return f"{personne} — {self.session.module.formation.formation} ({self.get_statut_display()})"

    def calculer_duree(self):
        """Calcule la durée de présence côté serveur (R5).

        Règle SYGEP unique : durée clampée au créneau planifié de la séance
        (voir ``presences.duree``), jamais négative.
        """
        from .duree import pointage_minutes_clampees

        if self.timestamp_entree and self.timestamp_sortie:
            self.duree_presence_minutes = pointage_minutes_clampees(self)
        return self.duree_presence_minutes


class AuditLog(models.Model):
    """Trace toutes les actions critiques du système (badgeage, force, fermeture session)."""

    class Action(models.TextChoices):
        # ── Badgeage ──
        SCAN_ENTREE = 'SCAN_ENTREE', 'Scan entrée (QR public)'
        SCAN_SORTIE = 'SCAN_SORTIE', 'Scan sortie (QR public)'
        SCAN_SECURE_ENTREE = 'SCAN_SECURE_ENTREE', 'Scan sécurisé entrée (mobile)'
        SCAN_SECURE_SORTIE = 'SCAN_SECURE_SORTIE', 'Scan sécurisé sortie (mobile)'
        FORCE_ENTREE = 'FORCE_ENTREE', 'Entrée forcée (encadrant/DFRC)'
        FORCE_SORTIE = 'FORCE_SORTIE', 'Sortie forcée (encadrant/DFRC)'
        CLOSE_SESSION = 'CLOSE_SESSION', 'Fermeture de session (encadrant/DFRC)'
        AUTO_ABSENT = 'AUTO_ABSENT', 'Absent automatique (délai badge sortie dépassé)'
        SCAN_HEARTBEAT = 'SCAN_HEARTBEAT', 'Heartbeat mobile géolocalisé'
        NO_HEARTBEAT = 'NO_HEARTBEAT', 'Alerte absence heartbeat mobile'
        OUT_OF_GEOFENCE = 'OUT_OF_GEOFENCE', 'Sortie du périmètre géographique'
        AUTO_EXIT = 'AUTO_EXIT', 'Sortie automatique (heartbeat/geofence)'
        DEVICE_UNBIND = 'DEVICE_UNBIND', 'Déliaison appareil'
        # ── Formations ──
        FORMATION_CREATE = 'FORMATION_CREATE', 'Création de formation'
        FORMATION_UPDATE = 'FORMATION_UPDATE', 'Modification de formation'
        FORMATION_DELETE = 'FORMATION_DELETE', 'Suppression de formation'
        FORMATION_STATUT = 'FORMATION_STATUT', 'Changement de statut de formation'
        FORMATION_ASSIGN_SUPERVISEUR = 'FORMATION_ASSIGN_SUPERVISEUR', 'Assignation superviseur'
        MODULE_ASSIGN_SUPERVISEUR = 'MODULE_ASSIGN_SUPERVISEUR', 'Assignation encadrant à un module'
        MODULE_CREATE = 'MODULE_CREATE', 'Création de module'
        MODULE_UPDATE = 'MODULE_UPDATE', 'Modification de module'
        MODULE_DELETE = 'MODULE_DELETE', 'Suppression de module'
        MODULE_ARCHIVE = 'MODULE_ARCHIVE', 'Archivage de module'
        FORMATION_QR_GENERATE = 'FORMATION_QR_GENERATE', 'Génération QR code'
        # ── Séances ──
        SEANCE_CREATE = 'SEANCE_CREATE', 'Création de séance'
        SEANCE_START = 'SEANCE_START', 'Démarrage de séance'
        SEANCE_STOP = 'SEANCE_STOP', 'Arrêt de séance'
        SEANCE_UPDATE = 'SEANCE_UPDATE', 'Modification de séance'
        SEANCE_DELETE = 'SEANCE_DELETE', 'Suppression de séance'
        SEANCE_IMPORT = 'SEANCE_IMPORT', 'Import séances (Excel)'
        # ── Auditeurs ──
        PARTICIPANT_CREATE = 'PARTICIPANT_CREATE', 'Création d\'auditeur'
        PARTICIPANT_UPDATE = 'PARTICIPANT_UPDATE', 'Modification d\'auditeur'
        PARTICIPANT_DELETE = 'PARTICIPANT_DELETE', 'Suppression d\'auditeur'
        PARTICIPANT_ADD_FORMATION = 'PARTICIPANT_ADD_FORMATION', 'Inscription auditeur à formation'
        PARTICIPANT_REMOVE_FORMATION = 'PARTICIPANT_REMOVE_FORMATION', 'Désinscription auditeur de formation'
        PARTICIPANT_IMPORT = 'PARTICIPANT_IMPORT', 'Import auditeurs (Excel)'
        # ── Formateurs ──
        FORMATEUR_CREATE = 'FORMATEUR_CREATE', 'Création de formateur'
        FORMATEUR_UPDATE = 'FORMATEUR_UPDATE', 'Modification de formateur'
        FORMATEUR_DELETE = 'FORMATEUR_DELETE', 'Suppression de formateur'
        FORMATEUR_ADD_FORMATION = 'FORMATEUR_ADD_FORMATION', 'Assignation formateur à formation'
        FORMATEUR_REMOVE_FORMATION = 'FORMATEUR_REMOVE_FORMATION', 'Retrait formateur de formation'
        FORMATEUR_IMPORT = 'FORMATEUR_IMPORT', 'Import formateurs (Excel)'
        # ── Utilisateurs ──
        USER_CREATE = 'USER_CREATE', 'Création d\'utilisateur'
        USER_UPDATE = 'USER_UPDATE', 'Modification d\'utilisateur'
        USER_DELETE = 'USER_DELETE', 'Suppression d\'utilisateur'
        USER_LOGIN = 'USER_LOGIN', 'Connexion utilisateur'
        USER_LOGOUT = 'USER_LOGOUT', 'Déconnexion utilisateur'
        USER_PASSWORD_CHANGE = 'USER_PASSWORD_CHANGE', 'Changement de mot de passe'
        # ── Secrétariats ──
        SECRETARIAT_CREATE = 'SECRETARIAT_CREATE', 'Création de secrétariat'
        SECRETARIAT_UPDATE = 'SECRETARIAT_UPDATE', 'Modification de secrétariat'
        SECRETARIAT_DELETE = 'SECRETARIAT_DELETE', 'Suppression de secrétariat'
        # ── Référentiels ──
        REFERENTIEL_CREATE = 'REFERENTIEL_CREATE', 'Création référentiel'
        REFERENTIEL_UPDATE = 'REFERENTIEL_UPDATE', 'Modification référentiel'
        REFERENTIEL_DELETE = 'REFERENTIEL_DELETE', 'Suppression référentiel'
        # ── Imports globaux ──
        IMPORT_EXCEL = 'IMPORT_EXCEL', 'Import Excel global'
        # ── Finance ──
        FINANCE_AJUSTEMENT_PROPOSE = 'FINANCE_AJUSTEMENT_PROPOSE', 'Proposition ajustement horaire finance'
        FINANCE_AJUSTEMENT_VALIDE = 'FINANCE_AJUSTEMENT_VALIDE', 'Validation ajustement horaire finance'
        FINANCE_AJUSTEMENT_REJETE = 'FINANCE_AJUSTEMENT_REJETE', 'Rejet ajustement horaire finance'
        FINANCE_SETTINGS_UPDATE = 'FINANCE_SETTINGS_UPDATE', 'Modification paramètres finance'

    action = models.CharField(max_length=40, choices=Action.choices)

    # Qui a déclenché l'action (null = scan public anonyme)
    acteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text="Utilisateur connecté ayant réalisé l'action (null si scan public)",
    )
    acteur_label = models.CharField(
        max_length=255, blank=True, default='',
        help_text="Nom de l'acteur au moment de l'action (dénormalisé)",
    )

    # Sur qui porte l'action
    cible_type = models.CharField(
        max_length=20, blank=True, default='',
        help_text="'participant', 'formateur' ou 'encadrant'",
    )
    cible_numero = models.CharField(max_length=50, blank=True, default='')
    cible_nom = models.CharField(max_length=255, blank=True, default='')

    # Contexte
    formation = models.ForeignKey(
        'formations.Formation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    formation_titre = models.CharField(max_length=255, blank=True, default='')
    pointage = models.ForeignKey(
        'Pointage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )

    # Métadonnées
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_id = models.CharField(max_length=255, blank=True, default='')
    extra = models.JSONField(default=dict, blank=True, help_text="Données supplémentaires libres")

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Journal d\'audit'
        verbose_name_plural = 'Journal d\'audit'
        indexes = [
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['acteur', 'timestamp']),
            models.Index(fields=['cible_numero', 'timestamp']),
        ]

    def __str__(self):
        acteur = self.acteur_label or 'Anonyme'
        return f"[{self.get_action_display()}] {acteur} → {self.cible_nom} ({self.timestamp:%Y-%m-%d %H:%M})"


def _get_client_ip(request):
    """Extrait l'IP réelle du client (derrière proxy)."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _log_audit(
    action, request, cible_type='', cible_numero='', cible_nom='',
    formation=None, pointage=None, device_id='', extra=None,
):
    """Raccourci pour créer un AuditLog depuis une vue."""
    acteur = None
    acteur_label = ''
    if request and request.user and request.user.is_authenticated:
        acteur = request.user
        acteur_label = request.user.get_full_name() or request.user.username

    AuditLog.objects.create(
        action=action,
        acteur=acteur,
        acteur_label=acteur_label,
        cible_type=cible_type,
        cible_numero=cible_numero,
        cible_nom=cible_nom,
        formation=formation,
        formation_titre=formation.formation if formation else '',
        pointage=pointage,
        ip_address=_get_client_ip(request) if request else None,
        device_id=device_id or '',
        extra=extra or {},
    )


def log_audit_system(action, *, formation=None, extra=None):
    """Journalise une action automatique (sans utilisateur connecté)."""
    AuditLog.objects.create(
        action=action,
        acteur=None,
        acteur_label='Système',
        formation=formation,
        formation_titre=formation.formation if formation else '',
        extra=extra or {},
    )


class DeviceBinding(models.Model):
    """Lie un appareil mobile à un utilisateur.
    Empêche qu'un participant se déconnecte et se reconnecte
    avec le compte d'un autre depuis le même téléphone."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='device_bindings',
    )
    device_id = models.CharField(max_length=255, unique=True, db_index=True)
    device_info = models.CharField(max_length=500, blank=True, default='')
    bound_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Liaison appareil'
        verbose_name_plural = 'Liaisons appareils'

    def __str__(self):
        return f"{self.user} ↔ {self.device_id[:20]}..."
