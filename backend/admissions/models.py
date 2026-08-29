"""Candidatures, pièces justificatives et admissions.

Couche additive : aucun modèle existant n'est modifié. Le rattachement à
l'étudiant opérationnel (``formations.Participant``) est facultatif et n'est
renseigné qu'au moment de la conversion en inscription.
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def piece_upload_path(instance, filename):
    """Range les pièces par candidature. Le dossier media n'est pas servi publiquement."""
    return f'candidatures/{instance.candidature.numero}/{filename}'


class TypeCandidature(models.Model):
    """Type de recrutement (concours externe, interne, sur titre…)."""

    code = models.CharField(max_length=30, unique=True)
    libelle = models.CharField(max_length=150)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ['libelle']
        verbose_name = 'Admission – Type de candidature'
        verbose_name_plural = 'Admission – Types de candidature'

    def __str__(self):
        return self.libelle


class VoieAcces(models.Model):
    """Voie d'accès à la formation (concours, validation des acquis, transfert…)."""

    code = models.CharField(max_length=30, unique=True)
    libelle = models.CharField(max_length=150)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ['libelle']
        verbose_name = "Admission – Voie d'accès"
        verbose_name_plural = "Admission – Voies d'accès"

    def __str__(self):
        return self.libelle


class TypePiece(models.Model):
    """Type de pièce justificative attendue dans un dossier de candidature."""

    code = models.CharField(max_length=30, unique=True)
    libelle = models.CharField(max_length=150)
    obligatoire_par_defaut = models.BooleanField(default=True)
    avec_date_expiration = models.BooleanField(
        default=False,
        help_text="La pièce a une date de validité (ex: certificat médical).",
    )
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ['libelle']
        verbose_name = 'Admission – Type de pièce'
        verbose_name_plural = 'Admission – Types de pièce'

    def __str__(self):
        return self.libelle


class ReglePiece(models.Model):
    """Rend une pièce obligatoire ou facultative pour une formation ou un type de formation."""

    type_piece = models.ForeignKey(TypePiece, on_delete=models.CASCADE, related_name='regles')
    type_formation = models.ForeignKey(
        'scolarite.TypeFormation', on_delete=models.CASCADE, related_name='regles_pieces',
        null=True, blank=True,
    )
    ref_formation = models.ForeignKey(
        'formations.RefFormation', on_delete=models.CASCADE, related_name='regles_pieces',
        null=True, blank=True, verbose_name='Formation (cycle)',
    )
    obligatoire = models.BooleanField(default=True)

    class Meta:
        ordering = ['type_piece__libelle']
        verbose_name = 'Admission – Règle de pièce'
        verbose_name_plural = 'Admission – Règles de pièces'
        unique_together = ('type_piece', 'type_formation', 'ref_formation')

    def clean(self):
        if not self.type_formation_id and not self.ref_formation_id:
            raise ValidationError(
                'Renseignez au moins un type de formation ou un cycle de formation.'
            )

    def __str__(self):
        cible = self.ref_formation or self.type_formation
        return f'{self.type_piece} → {cible}'


class Candidat(models.Model):
    """Personne candidatant à une formation. Indépendant du dossier étudiant."""

    class Sexe(models.TextChoices):
        MASCULIN = 'M', 'Masculin'
        FEMININ = 'F', 'Féminin'

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    nom = models.CharField(max_length=150)
    prenom = models.CharField(max_length=150)
    sexe = models.CharField(max_length=1, choices=Sexe.choices, blank=True)
    date_naissance = models.DateField(null=True, blank=True)
    lieu_naissance = models.CharField(max_length=150, blank=True)
    nationalite = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    telephone = models.CharField(max_length=30, blank=True)
    telephone2 = models.CharField(max_length=30, blank=True)
    adresse = models.TextField(blank=True)
    participant = models.OneToOneField(
        'formations.Participant', on_delete=models.SET_NULL,
        related_name='candidat', null=True, blank=True,
        help_text="Renseigné lors de la conversion en étudiant inscrit.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nom', 'prenom']
        verbose_name = 'Admission – Candidat'
        verbose_name_plural = 'Admission – Candidats'
        indexes = [
            models.Index(fields=['nom', 'prenom']),
        ]

    def __str__(self):
        return f'{self.nom} {self.prenom}'

    @property
    def nom_complet(self):
        return f'{self.nom} {self.prenom}'.strip()


class Candidature(models.Model):
    """Dossier de candidature à une formation pour une année académique."""

    class Statut(models.TextChoices):
        BROUILLON = 'BROUILLON', 'Brouillon'
        SOUMISE = 'SOUMISE', 'Soumise'
        EN_ATTENTE_DE_VERIFICATION = 'EN_ATTENTE_DE_VERIFICATION', 'En attente de vérification'
        PIECES_INCOMPLETES = 'PIECES_INCOMPLETES', 'Pièces incomplètes'
        PIECES_VALIDEES = 'PIECES_VALIDEES', 'Pièces validées'
        EN_ETUDE = 'EN_ETUDE', 'En étude'
        ADMISSIBLE = 'ADMISSIBLE', 'Admissible'
        ADMIS = 'ADMIS', 'Admis'
        ADMIS_SOUS_RESERVE = 'ADMIS_SOUS_RESERVE', 'Admis sous réserve'
        LISTE_ATTENTE = 'LISTE_ATTENTE', "Liste d'attente"
        REFUSE = 'REFUSE', 'Refusé'
        ANNULE = 'ANNULE', 'Annulé'

    numero = models.CharField(max_length=30, unique=True, editable=False)
    candidat = models.ForeignKey(Candidat, on_delete=models.CASCADE, related_name='candidatures')
    annee_academique = models.ForeignKey(
        'scolarite.AnneeAcademique', on_delete=models.PROTECT, related_name='candidatures',
    )
    ref_formation = models.ForeignKey(
        'formations.RefFormation', on_delete=models.PROTECT, related_name='candidatures',
        verbose_name='Formation (cycle) demandée',
    )
    parcours = models.ForeignKey(
        'scolarite.Parcours', on_delete=models.PROTECT, related_name='candidatures',
        null=True, blank=True,
    )
    niveau = models.ForeignKey(
        'scolarite.Niveau', on_delete=models.PROTECT, related_name='candidatures',
        verbose_name='Niveau demandé',
    )
    type_candidature = models.ForeignKey(
        TypeCandidature, on_delete=models.PROTECT, related_name='candidatures',
        null=True, blank=True,
    )
    voie_acces = models.ForeignKey(
        VoieAcces, on_delete=models.PROTECT, related_name='candidatures', null=True, blank=True,
    )
    regime = models.ForeignKey(
        'scolarite.RegimeEtudes', on_delete=models.PROTECT, related_name='candidatures',
        null=True, blank=True,
    )
    vague = models.ForeignKey(
        'formations.RefVague', on_delete=models.SET_NULL, related_name='candidatures',
        null=True, blank=True,
    )
    date_candidature = models.DateField(default=timezone.localdate)
    statut = models.CharField(max_length=30, choices=Statut.choices, default=Statut.BROUILLON)
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    observations = models.TextField(blank=True)
    date_decision = models.DateTimeField(null=True, blank=True)
    decide_par = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, related_name='candidatures_decidees',
        null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_candidature', '-id']
        verbose_name = 'Admission – Candidature'
        verbose_name_plural = 'Admission – Candidatures'
        constraints = [
            models.UniqueConstraint(
                fields=['candidat', 'annee_academique', 'ref_formation', 'niveau'],
                condition=~models.Q(statut='ANNULE'),
                name='uniq_candidature_active_par_candidat_formation_niveau',
            ),
        ]
        indexes = [
            models.Index(fields=['statut', 'annee_academique']),
        ]

    def __str__(self):
        return f'{self.numero} – {self.candidat}'

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self._generer_numero()
        super().save(*args, **kwargs)

    def _generer_numero(self):
        """Numéro séquentiel par année académique : CAND-2026-2027-0001."""
        prefixe = f'CAND-{self.annee_academique.libelle}-'
        dernier = (
            Candidature.objects.filter(numero__startswith=prefixe)
            .order_by('-numero')
            .values_list('numero', flat=True)
            .first()
        )
        sequence = int(dernier.rsplit('-', 1)[1]) + 1 if dernier else 1
        return f'{prefixe}{sequence:04d}'

    def clean(self):
        if self.parcours_id and self.ref_formation_id and self.parcours.ref_formation_id != self.ref_formation_id:
            raise ValidationError({'parcours': "Le parcours n'appartient pas à cette formation."})

    # ── Complétude du dossier ───────────────────────────────────────────────

    @property
    def pieces_obligatoires(self):
        return self.pieces.filter(obligatoire=True)

    @property
    def completude(self):
        """Retourne (nb_pièces_validées, nb_pièces_obligatoires)."""
        obligatoires = list(self.pieces_obligatoires)
        validees = [p for p in obligatoires if p.statut == PieceCandidature.Statut.VALIDEE]
        return len(validees), len(obligatoires)

    @property
    def dossier_complet(self):
        validees, total = self.completude
        return total > 0 and validees == total

    @property
    def taux_completude(self):
        validees, total = self.completude
        return round(validees * 100 / total) if total else 0


class PieceCandidature(models.Model):
    """Pièce justificative déposée dans un dossier de candidature."""

    class Statut(models.TextChoices):
        MANQUANTE = 'MANQUANTE', 'Manquante'
        FOURNIE = 'FOURNIE', 'Fournie'
        EN_VERIFICATION = 'EN_VERIFICATION', 'En vérification'
        VALIDEE = 'VALIDEE', 'Validée'
        REFUSEE = 'REFUSEE', 'Refusée'
        EXPIREE = 'EXPIREE', 'Expirée'

    candidature = models.ForeignKey(Candidature, on_delete=models.CASCADE, related_name='pieces')
    type_piece = models.ForeignKey(TypePiece, on_delete=models.PROTECT, related_name='pieces')
    obligatoire = models.BooleanField(default=True)
    fichier = models.FileField(upload_to=piece_upload_path, null=True, blank=True)
    numero_document = models.CharField(max_length=100, blank=True)
    date_delivrance = models.DateField(null=True, blank=True)
    date_expiration = models.DateField(null=True, blank=True)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.MANQUANTE)
    commentaire = models.TextField(blank=True)
    verifie_par = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, related_name='pieces_verifiees',
        null=True, blank=True,
    )
    verifie_le = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['type_piece__libelle']
        verbose_name = 'Admission – Pièce de candidature'
        verbose_name_plural = 'Admission – Pièces de candidature'
        constraints = [
            models.UniqueConstraint(
                'candidature', 'type_piece', name='uniq_piece_par_candidature_et_type',
            ),
        ]

    def __str__(self):
        return f'{self.type_piece} – {self.candidature.numero}'

    @property
    def est_expiree(self):
        return bool(self.date_expiration and self.date_expiration < timezone.localdate())


class Admission(models.Model):
    """Décision d'admission issue d'une candidature. Entité distincte de la candidature."""

    class Decision(models.TextChoices):
        ADMIS = 'ADMIS', 'Admis'
        ADMIS_SOUS_RESERVE = 'ADMIS_SOUS_RESERVE', 'Admis sous réserve'
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        REFUSEE = 'REFUSEE', 'Refusée'
        ANNULEE = 'ANNULEE', 'Annulée'

    candidature = models.OneToOneField(
        Candidature, on_delete=models.CASCADE, related_name='admission',
    )
    candidat = models.ForeignKey(Candidat, on_delete=models.CASCADE, related_name='admissions')
    annee_academique = models.ForeignKey(
        'scolarite.AnneeAcademique', on_delete=models.PROTECT, related_name='admissions',
    )
    ref_formation = models.ForeignKey(
        'formations.RefFormation', on_delete=models.PROTECT, related_name='admissions',
        verbose_name='Formation (cycle)',
    )
    parcours = models.ForeignKey(
        'scolarite.Parcours', on_delete=models.PROTECT, related_name='admissions',
        null=True, blank=True,
    )
    niveau = models.ForeignKey(
        'scolarite.Niveau', on_delete=models.PROTECT, related_name='admissions',
        verbose_name="Niveau d'entrée",
    )
    vague = models.ForeignKey(
        'formations.RefVague', on_delete=models.SET_NULL, related_name='admissions',
        null=True, blank=True,
    )
    categorie = models.ForeignKey(
        'formations.RefCategorie', on_delete=models.SET_NULL, related_name='admissions',
        null=True, blank=True,
    )
    grade = models.ForeignKey(
        'formations.RefGrade', on_delete=models.SET_NULL, related_name='admissions',
        null=True, blank=True,
    )
    voie_acces = models.ForeignKey(
        VoieAcces, on_delete=models.PROTECT, related_name='admissions', null=True, blank=True,
    )
    decision = models.CharField(max_length=30, choices=Decision.choices, default=Decision.EN_ATTENTE)
    date_decision = models.DateTimeField(null=True, blank=True)
    reference_decision = models.CharField(max_length=100, blank=True)
    date_limite_inscription = models.DateField(
        null=True, blank=True,
        help_text="Au-delà de cette date, l'admission ne permet plus de créer une inscription.",
    )
    observations = models.TextField(blank=True)
    decide_par = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, related_name='admissions_decidees',
        null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Admission – Admission'
        verbose_name_plural = 'Admission – Admissions'
        indexes = [
            models.Index(fields=['decision', 'annee_academique']),
        ]

    def __str__(self):
        return f'{self.candidat} – {self.get_decision_display()}'

    def clean(self):
        if self.grade_id and self.categorie_id and self.grade.categorie_id != self.categorie_id:
            raise ValidationError({'grade': "Le grade n'appartient pas à cette catégorie."})

    @property
    def est_expiree(self):
        return bool(
            self.date_limite_inscription
            and self.date_limite_inscription < timezone.localdate()
        )

    @property
    def permet_inscription(self):
        return (
            self.decision in (self.Decision.ADMIS, self.Decision.ADMIS_SOUS_RESERVE)
            and not self.est_expiree
        )
