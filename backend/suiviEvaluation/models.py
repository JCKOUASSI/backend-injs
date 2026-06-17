from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

from formations.models import Module, Participant, Formateur, Formation


class Questionnaire(models.Model):
    """Questionnaire d'évaluation créé par un superviseur/encadrant."""

    class Cible(models.TextChoices):
        COURS      = 'COURS',      'Évaluation du cours'
        FORMATEUR  = 'FORMATEUR',  'Évaluation du formateur'
        FORMATEUR_FEEDBACK = 'FORMATEUR_FEEDBACK', 'Questionnaire formateur (feedback didactique/logistique)'

    class Statut(models.TextChoices):
        BROUILLON  = 'BROUILLON',  'Brouillon'
        PUBLIE     = 'PUBLIE',     'Publié'
        FERME      = 'FERME',      'Fermé'

    titres = models.JSONField(
        default=list,
        help_text="Liste des intitulés de modules ciblés (depuis le référentiel).",
    )
    cible = models.CharField(
        max_length=20,
        choices=Cible.choices,
        help_text="Ce questionnaire évalue le cours ou le formateur ?",
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.BROUILLON,
    )
    # Ciblage : module et/ou catégorie de grade
    module = models.ForeignKey(
        'formations.Module',
        on_delete=models.CASCADE,
        related_name='questionnaires',
        null=True,
        blank=True,
        help_text="Module concerné (laisser vide pour cibler tous les modules d'une catégorie)",
    )
    categories = models.JSONField(
        default=list,
        blank=True,
        help_text="Liste des catégories ciblées (A, B, C, D…). Vide = toutes.",
    )
    grades = models.JSONField(
        default=list,
        blank=True,
        help_text="Liste des grades ciblés (A3, A4, B1…). Vide = tous.",
    )
    createur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='questionnaires_crees',
    )
    # Mode anonyme
    anonyme = models.BooleanField(
        default=True,
        help_text="Si vrai, les réponses sont anonymisées",
    )
    # Paramètres d'obligatorité
    obligatoire_avant_validation = models.BooleanField(
        default=False,
        help_text="Questionnaire obligatoire avant validation du module",
    )
    obligatoire_avant_notes = models.BooleanField(
        default=False,
        help_text="Questionnaire obligatoire avant accès aux notes",
    )
    obligatoire_avant_attestation = models.BooleanField(
        default=False,
        help_text="Questionnaire obligatoire avant génération des attestations",
    )
    date_ouverture = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date/heure d'ouverture aux auditeurs",
    )
    date_fermeture = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date/heure de fermeture automatique",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Questionnaire'
        verbose_name_plural = 'Questionnaires'

    def __str__(self):
        titres_str = ', '.join(self.titres) if self.titres else '—'
        return f"{titres_str} ({self.get_cible_display()})"


class Question(models.Model):
    """Question appartenant à un questionnaire."""

    class TypeQuestion(models.TextChoices):
        NOTE      = 'NOTE',      'Note (1 à 5)'
        CHOIX_UN  = 'CHOIX_UN',  'Choix unique'
        CHOIX_MUL = 'CHOIX_MUL', 'Choix multiple'
        TEXTE     = 'TEXTE',     'Texte libre'
        OUI_NON   = 'OUI_NON',   'Oui / Non'

    questionnaire = models.ForeignKey(
        Questionnaire,
        on_delete=models.CASCADE,
        related_name='questions',
    )
    intitule = models.TextField(help_text="Libellé de la question")
    type_question = models.CharField(
        max_length=20,
        choices=TypeQuestion.choices,
        default=TypeQuestion.NOTE,
    )
    ordre = models.PositiveSmallIntegerField(default=1)
    obligatoire = models.BooleanField(default=True)

    class Meta:
        ordering = ['questionnaire', 'ordre']
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'

    def __str__(self):
        return f"Q{self.ordre} — {self.intitule[:60]}"


class ChoixQuestion(models.Model):
    """Option de réponse pour les questions à choix (unique ou multiple)."""

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='choix',
    )
    libelle = models.CharField(max_length=255)
    ordre = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['question', 'ordre']
        verbose_name = 'Choix de réponse'
        verbose_name_plural = 'Choix de réponse'

    def __str__(self):
        return self.libelle


class ReponseQuestionnaire(models.Model):
    """Soumission complète d'un questionnaire par un auditeur."""

    questionnaire = models.ForeignKey(
        Questionnaire,
        on_delete=models.CASCADE,
        related_name='reponses',
    )
    participant = models.ForeignKey(
        'formations.Participant',
        on_delete=models.CASCADE,
        related_name='evaluations_soumises',
    )
    soumis_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('questionnaire', 'participant')
        ordering = ['-soumis_le']
        verbose_name = 'Soumission'
        verbose_name_plural = 'Soumissions'

    def __str__(self):
        return f"{self.participant} → {self.questionnaire}"


class ReponseQuestion(models.Model):
    """Réponse à une question individuelle dans une soumission."""

    soumission = models.ForeignKey(
        ReponseQuestionnaire,
        on_delete=models.CASCADE,
        related_name='reponses_questions',
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='reponses',
    )
    # Note (1-5)
    note = models.PositiveSmallIntegerField(null=True, blank=True)
    # Texte libre
    texte = models.TextField(blank=True, default='')
    # Choix unique
    choix = models.ForeignKey(
        ChoixQuestion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reponses_choix_unique',
    )
    # Choix multiples
    choix_multiples = models.ManyToManyField(
        ChoixQuestion,
        blank=True,
        related_name='reponses_choix_multiple',
    )
    # Oui/Non
    reponse_oui_non = models.BooleanField(
        null=True,
        blank=True,
        help_text="Réponse Oui/Non"
    )

    class Meta:
        unique_together = ('soumission', 'question')
        verbose_name = 'Réponse à une question'
        verbose_name_plural = 'Réponses aux questions'

    def __str__(self):
        return f"{self.soumission} — {self.question}"


class TypeEpreuve(models.Model):
    """Types d'épreuves configurables (devoir, contrôle, examen, etc.)"""

    code = models.CharField(max_length=50, unique=True, help_text="Code unique (ex: DEVOIR, EXAMEN)")
    libelle = models.CharField(max_length=255, help_text="Libellé de l'épreuve")
    actif = models.BooleanField(default=True)
    ordre = models.PositiveSmallIntegerField(default=1, help_text="Ordre d'affichage")

    class Meta:
        ordering = ['ordre', 'libelle']
        verbose_name = 'Type d\'épreuve'
        verbose_name_plural = 'Types d\'épreuves'

    def __str__(self):
        return self.libelle


class Epreuve(models.Model):
    """Épreuve (examen, devoir, etc.) associée à un module"""

    class Statut(models.TextChoices):
        PLANIFIEE = 'PLANIFIEE', 'Planifiée'
        EN_COURS = 'EN_COURS', 'En cours'
        TERMINEE = 'TERMINEE', 'Terminée'
        ANNULEE = 'ANNULEE', 'Annulée'

    code = models.CharField(max_length=50, unique=True, blank=True)
    type_epreuve = models.ForeignKey(
        TypeEpreuve,
        on_delete=models.PROTECT,
        related_name='epreuves',
        help_text="Type d'épreuve"
    )
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='epreuves',
        help_text="Module concerné"
    )
    intitule = models.CharField(max_length=255, help_text="Intitulé de l'épreuve")
    description = models.TextField(blank=True, default='')
    coefficient = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1.0,
        validators=[MinValueValidator(0)],
        help_text="Coefficient de l'épreuve"
    )
    note_max = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20.0,
        validators=[MinValueValidator(0)],
        help_text="Note maximale possible"
    )
    date_epreuve = models.DateField(null=True, blank=True)
    heure_debut = models.TimeField(null=True, blank=True)
    heure_fin = models.TimeField(null=True, blank=True)
    duree_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="Durée en minutes")
    salle = models.CharField(max_length=255, blank=True, default='')
    anonyme = models.BooleanField(
        default=False,
        help_text="Si vrai, les notes sont saisies avec un code anonyme"
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.PLANIFIEE
    )
    publier_notes = models.BooleanField(
        default=False,
        help_text="Rendre les notes visibles aux auditeurs"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='epreuves_creees'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_epreuve', 'type_epreuve', 'intitule']
        verbose_name = 'Épreuve'
        verbose_name_plural = 'Épreuves'

    def save(self, *args, **kwargs):
        if not self.code:
            from django.db import transaction
            with transaction.atomic():
                last = Epreuve.objects.select_for_update().order_by('-id').first()
                next_id = (last.id + 1) if last else 1
                self.code = f'E{next_id:05d}'
                while Epreuve.objects.filter(code=self.code).exists():
                    next_id += 1
                    self.code = f'E{next_id:05d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.intitule} ({self.type_epreuve.libelle}) - {self.module.intitule}"


class NoteEpreuve(models.Model):
    """Note d'un participant à une épreuve"""

    epreuve = models.ForeignKey(
        Epreuve,
        on_delete=models.CASCADE,
        related_name='notes_epreuve'
    )
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='notes_epreuves'
    )
    note = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        help_text="Note sur 20"
    )
    mention = models.CharField(max_length=50, blank=True, default='')
    observations = models.TextField(blank=True, default='')
    absent = models.BooleanField(default=False, help_text="Absent à l'épreuve")
    exclu = models.BooleanField(default=False, help_text="Exclu de l'épreuve")
    anonymat_code = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="Code d'anonymat (si épreuve anonyme)"
    )
    saisie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notes_epreuves_saisies'
    )
    saisie_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('epreuve', 'participant')]
        ordering = ['epreuve', 'participant__nom', 'participant__prenom']
        verbose_name = 'Note d\'épreuve'
        verbose_name_plural = 'Notes d\'épreuves'

    def __str__(self):
        return f"{self.participant} - {self.epreuve.intitule}: {self.note}/20"

    @property
    def note_coefficientee(self):
        """Note pondérée par le coefficient de l'épreuve"""
        if self.note is None:
            return None
        return round(float(self.note) * float(self.epreuve.coefficient), 2)


class ParametresEvaluation(models.Model):
    """Paramètres d'évaluation pour une formation (seuils, coefficients)"""

    formation = models.OneToOneField(
        Formation,
        on_delete=models.CASCADE,
        related_name='parametres_evaluation',
        help_text="Formation concernée"
    )
    seuil_admission = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=12.0,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        help_text="Moyenne minimale pour être admis"
    )
    seuil_mention_bien = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=14.0,
        help_text="Seuil pour mention Bien"
    )
    seuil_mention_tres_bien = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=16.0,
        help_text="Seuil pour mention Très Bien"
    )
    taux_presence_min = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=80.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Taux de présence minimal requis (%)"
    )
    coefficient_devoirs = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1.0,
        help_text="Coefficient par défaut pour les devoirs"
    )
    coefficient_controles = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=2.0,
        help_text="Coefficient par défaut pour les contrôles continus"
    )
    coefficient_examens = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=3.0,
        help_text="Coefficient par défaut pour les examens"
    )
    coefficient_oraux = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=2.0,
        help_text="Coefficient par défaut pour les épreuves orales"
    )
    coefficient_pratiques = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=2.0,
        help_text="Coefficient par défaut pour les épreuves pratiques"
    )
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Paramètres d\'évaluation'
        verbose_name_plural = 'Paramètres d\'évaluation'

    def __str__(self):
        return f"Paramètres {self.formation.formation}"


class MoyenneModule(models.Model):
    """Moyenne calculée d'un participant sur un module"""

    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='moyennes'
    )
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='moyennes_modules'
    )
    moyenne = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)]
    )
    total_coefficients = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Somme des coefficients des épreuves"
    )
    somme_notes_coeff = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Somme des notes coefficientées"
    )
    nb_epreuves = models.PositiveSmallIntegerField(default=0)
    calculee_le = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('module', 'participant')]
        ordering = ['module', 'participant__nom']
        verbose_name = 'Moyenne module'
        verbose_name_plural = 'Moyennes modules'

    def __str__(self):
        return f"{self.participant} - {self.module}: {self.moyenne}/20"


class DecisionPedagogique(models.Model):
    """Décision pédagogique automatique ou manuelle pour un participant"""

    class TypeDecision(models.TextChoices):
        ADMIS = 'ADMIS', 'Admis'
        AJOURNE = 'AJOURNE', 'Ajourné'
        EXCLUSION = 'EXCLUSION', 'Exclusion'
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'

    class Mention(models.TextChoices):
        PASSABLE = 'PASSABLE', 'Passable'
        ASSEZ_BIEN = 'ASSEZ_BIEN', 'Assez bien'
        BIEN = 'BIEN', 'Bien'
        TRES_BIEN = 'TRES_BIEN', 'Très bien'

    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='decisions'
    )
    formation = models.ForeignKey(
        Formation,
        on_delete=models.CASCADE,
        related_name='decisions'
    )
    moyenne_generale = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)]
    )
    taux_presence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    total_heures_presence = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total heures de présence"
    )
    total_heures_prevues = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total heures prévues"
    )
    decision = models.CharField(
        max_length=20,
        choices=TypeDecision.choices,
        default=TypeDecision.EN_ATTENTE
    )
    mention = models.CharField(
        max_length=20,
        choices=Mention.choices,
        blank=True,
        default=''
    )
    appreciation = models.TextField(
        blank=True,
        default='',
        help_text="Appréciation pédagogique"
    )
    generee_auto = models.BooleanField(
        default=True,
        help_text="Décision générée automatiquement"
    )
    validee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='decisions_validees'
    )
    validee_le = models.DateTimeField(null=True, blank=True)
    criteres_appliques = models.JSONField(
        default=dict,
        help_text="Critères utilisés pour la décision (seuils, etc.)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('participant', 'formation')]
        ordering = ['-updated_at']
        verbose_name = 'Décision pédagogique'
        verbose_name_plural = 'Décisions pédagogiques'

    def __str__(self):
        return f"{self.participant} - {self.formation}: {self.get_decision_display()}"

    def calculer_decision(self, seuil_admission=12.0, taux_presence_min=80.0):
        """Calcule la décision pédagogique selon les seuils"""
        if self.moyenne_generale is None or self.taux_presence is None:
            self.decision = self.TypeDecision.EN_ATTENTE
            return

        moyenne = float(self.moyenne_generale)
        presence = float(self.taux_presence)

        if moyenne >= seuil_admission and presence >= taux_presence_min:
            self.decision = self.TypeDecision.ADMIS
            if moyenne >= 16:
                self.mention = self.Mention.TRES_BIEN
            elif moyenne >= 14:
                self.mention = self.Mention.BIEN
            elif moyenne >= 12:
                self.mention = self.Mention.ASSEZ_BIEN
            else:
                self.mention = self.Mention.PASSABLE
        elif moyenne < 8 or presence < 50:
            self.decision = self.TypeDecision.EXCLUSION
        else:
            self.decision = self.TypeDecision.AJOURNE


class FicheAuditeurAcademique(models.Model):
    """Fiche académique complète d'un auditeur (historique, notes, décisions)"""

    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='fiches_academiques'
    )
    formation = models.ForeignKey(
        Formation,
        on_delete=models.CASCADE,
        related_name='fiches_auditeurs'
    )
    modules_suivis = models.ManyToManyField(
        Module,
        through='SuiviModuleAuditeur',
        related_name='fiches'
    )
    moyenne_generale = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    classement = models.PositiveIntegerField(null=True, blank=True)
    decision_finale = models.ForeignKey(
        DecisionPedagogique,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fiches'
    )
    date_debut_formation = models.DateField(null=True, blank=True)
    date_fin_formation = models.DateField(null=True, blank=True)
    archive = models.BooleanField(default=False)
    annee_academique = models.CharField(max_length=20, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('participant', 'formation')]
        ordering = ['-created_at']
        verbose_name = 'Fiche auditeur académique'
        verbose_name_plural = 'Fiches auditeurs académiques'

    def __str__(self):
        return f"Fiche {self.participant} - {self.formation}"


class SuiviModuleAuditeur(models.Model):
    """Suivi détaillé d'un auditeur sur un module"""

    fiche = models.ForeignKey(
        FicheAuditeurAcademique,
        on_delete=models.CASCADE,
        related_name='suivi_modules'
    )
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='suivi_auditeurs'
    )
    heures_presence = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Heures de présence effectives"
    )
    heures_prevues = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Heures prévues"
    )
    taux_presence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    moyenne_module = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    nb_epreuves = models.PositiveSmallIntegerField(default=0)
    appreciation = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('fiche', 'module')]
        verbose_name = 'Suivi module auditeur'
        verbose_name_plural = 'Suivis modules auditeurs'

    def __str__(self):
        return f"{self.fiche.participant} - {self.module}"

    def calculer_taux_presence(self):
        """Calcule le taux de présence"""
        if self.heures_prevues and self.heures_prevues > 0:
            self.taux_presence = round(
                (float(self.heures_presence) / float(self.heures_prevues)) * 100, 2
            )
        return self.taux_presence


class FicheFormateur(models.Model):
    """Fiche de suivi pédagogique d'un formateur"""

    formateur = models.ForeignKey(
        Formateur,
        on_delete=models.CASCADE,
        related_name='fiches'
    )
    formation = models.ForeignKey(
        Formation,
        on_delete=models.CASCADE,
        related_name='fiches_formateurs',
        null=True,
        blank=True
    )
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='fiches_formateur',
        null=True,
        blank=True
    )
    heures_prevues = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Heures prévues"
    )
    heures_effectuees = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Heures effectivement réalisées"
    )
    taux_presence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    nb_seances = models.PositiveSmallIntegerField(default=0)
    nb_seances_realisees = models.PositiveSmallIntegerField(default=0)
    satisfaction_auditeurs = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Note moyenne de satisfaction des auditeurs (1-5)"
    )
    nb_evaluations = models.PositiveSmallIntegerField(default=0)
    appreciation_pedagogique = models.TextField(blank=True, default='')
    archive = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Fiche formateur'
        verbose_name_plural = 'Fiches formateurs'

    def __str__(self):
        return f"Fiche {self.formateur} - {self.module or self.formation}"

    def calculer_taux_presence(self):
        """Calcule le taux de présence du formateur"""
        if self.heures_prevues and self.heures_prevues > 0:
            self.taux_presence = round(
                (float(self.heures_effectuees) / float(self.heures_prevues)) * 100, 2
            )
        return self.taux_presence


class QuizManuel(models.Model):
    """Quiz d'évaluation des manuels didactiques"""

    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='quiz_manuels',
        help_text="Module concerné"
    )
    titre = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    chapitre = models.CharField(max_length=255, blank=True, default='')
    # Restriction d'accès par catégorie (ex: 'A') ou par grade (ex: 'A3').
    # Listes vides = accessibles à tous.
    categories = models.JSONField(default=list, blank=True, help_text="Liste des catégories autorisées")
    grades = models.JSONField(default=list, blank=True, help_text="Liste des grades autorisés")
    nb_questions = models.PositiveSmallIntegerField(default=5)
    seuil_reussite = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=70.0,
        help_text="Seuil de réussite (%)"
    )
    duree_max_minutes = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Durée maximale en minutes"
    )
    actif = models.BooleanField(default=True)
    date_ouverture = models.DateTimeField(null=True, blank=True)
    date_fermeture = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['module', 'titre']
        verbose_name = 'Quiz manuel'
        verbose_name_plural = 'Quiz manuels'

    def __str__(self):
        return f"{self.titre} - {self.module.intitule}"


class QuestionQuiz(models.Model):
    """Question d'un quiz de manuel"""

    class TypeQuestion(models.TextChoices):
        QCM = 'QCM', 'QCM'
        VRAI_FAUX = 'VRAI_FAUX', 'Vrai/Faux'
        OUVERTE = 'OUVERTE', 'Réponse ouverte'

    quiz = models.ForeignKey(
        QuizManuel,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    question = models.TextField()
    type_question = models.CharField(
        max_length=20,
        choices=TypeQuestion.choices,
        default=TypeQuestion.QCM
    )
    reponse_correcte = models.TextField(help_text="Réponse correcte")
    options = models.JSONField(
        default=list,
        help_text="Options pour QCM (liste de choix)"
    )
    points = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1.0,
        help_text="Points attribués"
    )
    ordre = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['ordre']
        verbose_name = 'Question de quiz'
        verbose_name_plural = 'Questions de quiz'

    def __str__(self):
        return f"Q{self.ordre} - {self.question[:50]}"


class ReponseQuiz(models.Model):
    """Réponse d'un auditeur à un quiz"""

    quiz = models.ForeignKey(
        QuizManuel,
        on_delete=models.CASCADE,
        related_name='reponses'
    )
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='reponses_quiz'
    )
    date_soumission = models.DateTimeField(auto_now_add=True)
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Score obtenu (%)"
    )
    reussi = models.BooleanField(null=True, blank=True)
    temps_pris_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    reponses_detail = models.JSONField(
        default=dict,
        help_text="Détail des réponses"
    )

    class Meta:
        unique_together = [('quiz', 'participant')]
        ordering = ['-date_soumission']
        verbose_name = 'Réponse au quiz'
        verbose_name_plural = 'Réponses aux quiz'

    def __str__(self):
        return f"{self.participant} - {self.quiz.titre}: {self.score}%"


class HistoriqueNoteModification(models.Model):
    """Traçabilité des modifications de notes"""

    note_epreuve = models.ForeignKey(
        NoteEpreuve,
        on_delete=models.CASCADE,
        related_name='historique_modifications'
    )
    ancienne_note = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    nouvelle_note = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    modifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    modifie_le = models.DateTimeField(auto_now_add=True)
    motif = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-modifie_le']
        verbose_name = 'Historique modification note'
        verbose_name_plural = 'Historiques modifications notes'

    def __str__(self):
        return f"Modif {self.note_epreuve} - {self.ancienne_note} → {self.nouvelle_note}"


class ExportRapport(models.Model):
    """Historique des exports PDF et Excel"""

    class TypeExport(models.TextChoices):
        PDF = 'PDF', 'PDF'
        EXCEL = 'EXCEL', 'Excel'
        CSV = 'CSV', 'CSV'

    class TypeRapport(models.TextChoices):
        FICHE_AUDITEUR = 'FICHE_AUDITEUR', 'Fiche auditeur'
        FICHE_FORMATEUR = 'FICHE_FORMATEUR', 'Fiche formateur'
        TABLEAU_BORD = 'TABLEAU_BORD', 'Tableau de bord'
        RAPPORT_ANNUEL = 'RAPPORT_ANNUEL', 'Rapport annuel'
        RAPPORT_FORMATION = 'RAPPORT_FORMATION', 'Rapport par formation'
        RAPPORT_MODULE = 'RAPPORT_MODULE', 'Rapport par module'
        LISTE_NOTES = 'LISTE_NOTES', 'Liste des notes'
        DECISIONS = 'DECISIONS', 'Décisions pédagogiques'

    type_export = models.CharField(max_length=10, choices=TypeExport.choices)
    type_rapport = models.CharField(max_length=20, choices=TypeRapport.choices)
    fichier = models.FileField(upload_to='exports/rapports/%Y/%m/')
    parametres = models.JSONField(default=dict, help_text="Paramètres utilisés pour l'export")
    genere_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exports_rapports'
    )
    genere_le = models.DateTimeField(auto_now_add=True)
    formation = models.ForeignKey(
        Formation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    module = models.ForeignKey(
        Module,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    participant = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-genere_le']
        verbose_name = 'Export rapport'
        verbose_name_plural = 'Exports rapports'

    def __str__(self):
        return f"{self.get_type_rapport_display()} - {self.get_type_export_display()}"
