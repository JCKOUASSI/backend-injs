from django.db import models
from django.conf import settings


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
        default='COURS',
        help_text="Valeur legacy — le questionnaire comporte désormais deux sections (cours + formateur).",
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

    class Section(models.TextChoices):
        COURS      = 'COURS',     'Évaluation du cours'
        FORMATEUR  = 'FORMATEUR', 'Évaluation du formateur'

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
    section = models.CharField(
        max_length=20,
        choices=Section.choices,
        default=Section.COURS,
        help_text="Section du questionnaire : cours ou formateur",
    )
    ordre = models.PositiveSmallIntegerField(default=1)
    obligatoire = models.BooleanField(default=True)

    class Meta:
        ordering = ['questionnaire', 'section', 'ordre']
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


# ─────────────────────────────────────────────────────────────
# QUIZ MANUELS
# ─────────────────────────────────────────────────────────────

class QuizManuel(models.Model):
    """Quiz à correction automatique créé par un superviseur."""

    module = models.ForeignKey(
        'formations.Module',
        on_delete=models.CASCADE,
        related_name='quiz_manuels',
        null=True, blank=True,
    )
    titre = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    chapitre = models.CharField(max_length=255, blank=True, default='')
    categories = models.JSONField(default=list, blank=True)
    grades = models.JSONField(default=list, blank=True)
    nb_questions = models.PositiveSmallIntegerField(default=0)
    seuil_reussite = models.DecimalField(max_digits=5, decimal_places=2, default=60)
    duree_max_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    actif = models.BooleanField(default=True)
    date_ouverture = models.DateTimeField(null=True, blank=True)
    date_fermeture = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='quiz_crees',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Quiz manuel'
        verbose_name_plural = 'Quiz manuels'

    def __str__(self):
        return self.titre


class QuestionQuiz(models.Model):
    """Question d'un quiz manuel."""

    quiz = models.ForeignKey(
        QuizManuel,
        on_delete=models.CASCADE,
        related_name='questions',
    )
    question = models.TextField()
    type_question = models.CharField(
        max_length=20,
        choices=[('QCM', 'QCM'), ('VRAI_FAUX', 'Vrai/Faux'), ('TEXTE', 'Texte libre')],
        default='QCM',
    )
    reponse_correcte = models.TextField(blank=True, default='')
    options = models.JSONField(default=list, blank=True)
    points = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    ordre = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['quiz', 'ordre']
        verbose_name = 'Question de quiz'
        verbose_name_plural = 'Questions de quiz'

    def __str__(self):
        return f"{self.quiz} — Q{self.ordre}"


class ReponseQuiz(models.Model):
    """Soumission d'un quiz par un auditeur."""

    quiz = models.ForeignKey(
        QuizManuel,
        on_delete=models.CASCADE,
        related_name='reponses',
    )
    participant = models.ForeignKey(
        'formations.Participant',
        on_delete=models.CASCADE,
        related_name='reponses_quiz',
    )
    date_soumission = models.DateTimeField(auto_now_add=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    reussi = models.BooleanField(default=False)
    temps_pris_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    reponses_detail = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('quiz', 'participant')
        ordering = ['-date_soumission']
        verbose_name = 'Réponse à un quiz'
        verbose_name_plural = 'Réponses aux quiz'

    def __str__(self):
        return f"{self.participant} → {self.quiz}"
