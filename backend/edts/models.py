"""Modèles du module Emploi du temps (lot L8 — app edts).

Principes :
- les créneaux sont des unités horaires de base ;
- un emploi du temps est paramétrable par année académique et par
  population cible (formation, groupe, enseignant, salle) ;
- les affectations expriment ce qui est placé dans un créneau ;
- les conflits sont détectés côté service et peuvent être journalisés.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from scolarite.models import AnneeAcademique, Groupe

JOUR_CHOICES = [
    ('LUNDI', 'Lundi'),
    ('MARDI', 'Mardi'),
    ('MERCREDI', 'Mercredi'),
    ('JEUDI', 'Jeudi'),
    ('VENDREDI', 'Vendredi'),
    ('SAMEDI', 'Samedi'),
    ('DIMANCHE', 'Dimanche'),
]

NATURE_CHOICES = [
    ('COURS', 'Cours'),
    ('TD', 'Travaux dirigés'),
    ('TP', 'Travaux pratiques'),
    ('EVALUATION', 'Évaluation'),
    ('REMPLACEMENT', 'Remplacement'),
    ('AUTRE', 'Autre'),
]

POPULATION_TYPE_CHOICES = [
    ('FORMATION', 'Formation'),
    ('GROUPE', 'Groupe'),
    ('ENSEIGNANT', 'Enseignant'),
    ('SALLE', 'Salle'),
]

EDT_STATUT_CHOICES = [
    ('BROUILLON', 'Brouillon'),
    ('EN_VALIDATION', 'En validation'),
    ('VALIDE', 'Validé'),
    ('PUBLIE', 'Publié'),
    ('ARCHIVE', 'Archivé'),
]

CONFLIT_TYPE_CHOICES = [
    ('HORAIRE_ENSEIGNANT', 'Chevauchement enseignant'),
    ('HORAIRE_GROUPETUDIANT', 'Chevauchement groupe/étudiant'),
    ('HORAIRE_SALLE', 'Chevauchement salle'),
    ('HORAIRE_MODULE', 'Chevauchement module'),
    ('MANUEL', 'Signalé manuellement'),
]


class CreneauTemplate(models.Model):
    """Référentiel de créneaux types (jour + horaire)."""

    jour = models.CharField(max_length=10, choices=JOUR_CHOICES, db_index=True)
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    duree_prevue_minutes = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        help_text='Durée calculée (laisser None pour auto-calcul).',
    )

    class Meta:
        ordering = ['jour', 'heure_debut']
        verbose_name = 'LMD – Créneau type'
        verbose_name_plural = 'LMD – Créneaux types'
        indexes = [
            models.Index(fields=['jour', 'heure_debut', 'heure_fin']),
        ]

    def clean(self):
        if self.heure_debut and self.heure_fin and self.heure_debut >= self.heure_fin:
            raise ValidationError({
                'heure_fin': "L'heure de fin doit être strictement après l'heure de début.",
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.duree_prevue_minutes and self.heure_debut and self.heure_fin:
            self.duree_prevue_minutes = self._calculer_duree_minutes()
        super().save(*args, **kwargs)

    def _calculer_duree_minutes(self):
        from datetime import datetime, timedelta

        base = datetime(2000, 1, 1, self.heure_debut.hour, self.heure_debut.minute)
        fin = datetime(2000, 1, 1, self.heure_fin.hour, self.heure_fin.minute)
        delta = fin - base
        if delta.total_seconds() <= 0:
            delta += timedelta(days=1)
        return int(delta.total_seconds() // 60)

    @property
    def duree_heures(self):
        if not self.duree_prevue_minutes:
            return None
        return round(self.duree_prevue_minutes / 60, 2)

    def __str__(self):
        return f"{self.get_jour_display()} {self.heure_debut}→{self.heure_fin}"


class EmploiDuTemps(models.Model):
    """Périmètre d'un emploi du temps éditable/publié.

    Un EDT est attaché à une année académique et à une population cible.
    """
    annee_academique = models.ForeignKey(
        AnneeAcademique,
        on_delete=models.PROTECT,
        related_name='emplois_du_temps',
    )
    population_type = models.CharField(
        max_length=15,
        choices=POPULATION_TYPE_CHOICES,
        db_index=True,
    )
    population_id = models.PositiveIntegerField(
        db_index=True,
        help_text='ID de la formation/groupe/enseignant/salle cible.',
    )
    population_denominateur = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Libellé humain pour affichage et recherche.',
    )
    titre = models.CharField(max_length=255, blank=True, default='')
    statut = models.CharField(
        max_length=15,
        choices=EDT_STATUT_CHOICES,
        default='BROUILLON',
        db_index=True,
    )
    semaine_debut = models.PositiveSmallIntegerField(
        default=1,
        help_text='Numéro de semaine académique de début (1-based).',
    )
    semaine_fin = models.PositiveSmallIntegerField(
        default=36,
        help_text='Numéro de semaine académique de fin (bornes de planification).',
    )
    rentree = models.DateField(
        null=True,
        blank=True,
        help_text='Date de rentrée pédagogique de cet EDT.',
    )
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edt_crees',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'LMD – Emploi du temps'
        verbose_name_plural = 'LMD – Emplois du temps'
        indexes = [
            models.Index(fields=['annee_academique', 'population_type', 'population_id']),
            models.Index(fields=['statut']),
        ]
        unique_together = ['annee_academique', 'population_type', 'population_id']

    def clean(self):
        super().clean()
        erreurs = {}
        if self.semaine_debut and self.semaine_fin and self.semaine_fin < self.semaine_debut:
            erreurs['semaine_fin'] = 'La semaine de fin doit être ≥ à la semaine de début.'
        if self.statut and self.statut not in dict(EDT_STATUT_CHOICES):
            erreurs['statut'] = 'Statut inconnu.'
        if erreurs:
            raise ValidationError(erreurs)

    @property
    def population_label(self):
        """Libellé lisible de la population cible (jamais un champ fantôme)."""
        return (self.population_denominateur or '').strip() or f'{self.get_population_type_display()} #{self.population_id}'

    def __str__(self):
        return f"{self.titre or self.population_denominateur} — {self.get_statut_display()}"


class AffectationCreneau(models.Model):
    """Placement d'un créneau type dans un emploi du temps précis.

    C'est la donnée opérationnelle de l'EDT : qui enseigne quoi, où,
    à quelle période, avec quels étudiants.
    """

    emploi_du_temps = models.ForeignKey(
        EmploiDuTemps,
        on_delete=models.CASCADE,
        related_name='affectations',
    )
    creneau_template = models.ForeignKey(
        CreneauTemplate,
        on_delete=models.PROTECT,
        related_name='affectations',
    )
    semaine_debut = models.PositiveSmallIntegerField(
        db_index=True,
        help_text='Numéro de semaine académique de début (1-based).',
    )
    semaine_fin = models.PositiveSmallIntegerField(
        db_index=True,
        help_text='Numéro de semaine académique de fin.',
    )
    salle_nom = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Salle attendue (chaîne éditable).',
    )
    formation = models.ForeignKey(
        'formations.RefFormation',
        on_delete=models.PROTECT,
        related_name='edt_affectations',
        null=True,
        blank=True,
    )
    groupe = models.ForeignKey(
        Groupe,
        on_delete=models.PROTECT,
        related_name='edt_affectations',
        null=True,
        blank=True,
    )
    enseignant_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text='ID utilisateur enseignant/encadrant.',
    )
    formateur = models.ForeignKey(
        'formations.Formateur',
        on_delete=models.PROTECT,
        related_name='edt_affectations',
        null=True,
        blank=True,
        help_text='Formateur de référence (socle INJS-LMD) pour la détection de surcharges.',
    )
    enseignant_nom = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Nom complet enseignant (dénormalisé pour recherche/planification).',
    )
    nature = models.CharField(
        max_length=15,
        choices=NATURE_CHOICES,
        default='COURS',
    )
    intitule = models.CharField(max_length=255, blank=True, default='')
    commentaire = models.TextField(blank=True, default='')
    actif = models.BooleanField(default=True, db_index=True)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edt_affectations_crees',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [
            'emploi_du_temps',
            'creneau_template__jour',
            'creneau_template__heure_debut',
            'semaine_debut',
        ]
        verbose_name = 'LMD – Affectation créneau'
        verbose_name_plural = 'LMD – Affectations créneaux'
        indexes = [
            models.Index(
                fields=['emploi_du_temps', 'creneau_template', 'semaine_debut', 'semaine_fin'],
                name='edts__edt_creneau_semaine_idx',
            ),
        ]

    def clean(self):
        super().clean()
        erreurs = {}
        if self.semaine_debut is None:
            erreurs['semaine_debut'] = 'La semaine de début est obligatoire.'
        if self.semaine_fin is None:
            erreurs['semaine_fin'] = 'La semaine de fin est obligatoire.'
        if (self.semaine_debut is not None and self.semaine_fin is not None
                and self.semaine_fin < self.semaine_debut):
            erreurs['semaine_fin'] = 'La semaine de fin doit être ≥ à la semaine de début.'
        if self.nature and self.nature not in dict(NATURE_CHOICES):
            erreurs['nature'] = 'Nature inconnue.'
        if erreurs:
            raise ValidationError(erreurs)

    @property
    def horaire(self):
        """Résumé lisible du créneau (jour + plage horaire) ou chaîne vide."""
        ct = self.creneau_template
        if not ct:
            return ''
        jours = dict(JOUR_CHOICES)
        return (f"{jours.get(ct.jour, ct.jour)} "
                f"{ct.heure_debut:%H:%M}–{ct.heure_fin:%H:%M}")

    def __str__(self):
        return (
            f"{self.creneau_template} | {self.get_nature_display()} "
            f"| s.{self.semaine_debut}-s.{self.semaine_fin} "
            f"| {self.enseignant_nom or self.formation or self.groupe}"
        )


class ConflitCreneau(models.Model):
    """Détection de conflit stockée pour audit et revue humaine.

    Les conflits peuvent être générés automatiquement ou signalés manuellement.
    """

    emploi_du_temps = models.ForeignKey(
        EmploiDuTemps,
        on_delete=models.CASCADE,
        related_name='conflits',
    )
    type_conflit = models.CharField(
        max_length=30,
        choices=CONFLIT_TYPE_CHOICES,
        db_index=True,
    )
    description = models.TextField()
    lignes_creneaux = models.JSONField(
        default=list,
        help_text='Liste des identifiants ou représentations brutes des affectations en conflit.',
    )
    recalcule_le = models.DateTimeField(auto_now=True)
    actif = models.BooleanField(default=True, db_index=True)
    signale_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edt_conflits_signales',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recalcule_le']
        verbose_name = 'LMD – Conflit créneau'
        verbose_name_plural = 'LMD – Conflits créneaux'
        indexes = [
            models.Index(fields=['emploi_du_temps', 'type_conflit']),
            models.Index(fields=['actif', 'recalcule_le']),
        ]

    def __str__(self):
        return f"{self.get_type_conflit_display()} — {self.emploi_du_temps}"

