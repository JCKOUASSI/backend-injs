from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import (
    Questionnaire, Question, ChoixQuestion,
    ReponseQuestionnaire, ReponseQuestion,
    TypeEpreuve, Epreuve, NoteEpreuve, ParametresEvaluation, MoyenneModule,
    DecisionPedagogique, FicheAuditeurAcademique, SuiviModuleAuditeur,
    FicheFormateur, QuizManuel, QuestionQuiz, ReponseQuiz,
    HistoriqueNoteModification, ExportRapport,
)


class ChoixQuestionInline(TabularInline):
    model = ChoixQuestion
    extra = 2
    fields = ['ordre', 'libelle']


class QuestionInline(TabularInline):
    model = Question
    extra = 1
    fields = ['ordre', 'intitule', 'type_question', 'obligatoire']
    show_change_link = True


@admin.register(Questionnaire)
class QuestionnaireAdmin(ModelAdmin):
    list_display = ['get_titres', 'cible', 'statut', 'get_categories', 'module', 'createur', 'created_at']
    list_filter = ['cible', 'statut']
    search_fields = ['titres', 'module__intitule']
    inlines = [QuestionInline]
    autocomplete_fields = ['module']

    @admin.display(description='Titres')
    def get_titres(self, obj):
        return ', '.join(obj.titres) if obj.titres else '—'

    @admin.display(description='Catégories')
    def get_categories(self, obj):
        try:
            cats = obj.categories or []
            return ', '.join(cats) if cats else '—'
        except Exception:
            return '—'


@admin.register(Question)
class QuestionAdmin(ModelAdmin):
    list_display = ['questionnaire', 'ordre', 'intitule', 'type_question', 'obligatoire']
    list_filter = ['type_question', 'obligatoire']
    search_fields = ['intitule']
    inlines = [ChoixQuestionInline]


@admin.register(ReponseQuestionnaire)
class ReponseQuestionnaireAdmin(ModelAdmin):
    list_display = ['participant', 'questionnaire', 'soumis_le']
    list_filter = ['questionnaire__cible', 'questionnaire__statut']
    search_fields = ['participant__nom', 'participant__prenom']
    readonly_fields = ['soumis_le']


@admin.register(TypeEpreuve)
class TypeEpreuveAdmin(ModelAdmin):
    list_display = ['libelle', 'code', 'ordre', 'actif']
    list_filter = ['actif']
    search_fields = ['code', 'libelle']


class NoteEpreuveInline(TabularInline):
    model = NoteEpreuve
    extra = 0
    fields = ['participant', 'note', 'mention', 'absent', 'exclu']
    autocomplete_fields = ['participant']


@admin.register(Epreuve)
class EpreuveAdmin(ModelAdmin):
    list_display = ['code', 'intitule', 'type_epreuve', 'module', 'coefficient', 'date_epreuve', 'statut', 'publier_notes']
    list_filter = ['statut', 'type_epreuve', 'anonyme', 'publier_notes']
    search_fields = ['code', 'intitule', 'module__intitule']
    autocomplete_fields = ['module', 'type_epreuve']
    inlines = [NoteEpreuveInline]


@admin.register(NoteEpreuve)
class NoteEpreuveAdmin(ModelAdmin):
    list_display = ['participant', 'epreuve', 'note', 'mention', 'absent', 'exclu', 'saisie_par']
    list_filter = ['absent', 'exclu', 'epreuve__type_epreuve']
    search_fields = ['participant__nom', 'participant__prenom', 'epreuve__intitule']
    autocomplete_fields = ['participant', 'epreuve']


@admin.register(ParametresEvaluation)
class ParametresEvaluationAdmin(ModelAdmin):
    list_display = ['formation', 'seuil_admission', 'taux_presence_min', 'actif']
    list_filter = ['actif']
    autocomplete_fields = ['formation']


@admin.register(MoyenneModule)
class MoyenneModuleAdmin(ModelAdmin):
    list_display = ['participant', 'module', 'moyenne', 'nb_epreuves', 'calculee_le']
    search_fields = ['participant__nom', 'participant__prenom', 'module__intitule']
    autocomplete_fields = ['participant', 'module']


@admin.register(DecisionPedagogique)
class DecisionPedagogiqueAdmin(ModelAdmin):
    list_display = ['participant', 'formation', 'moyenne_generale', 'taux_presence', 'decision', 'mention', 'generee_auto']
    list_filter = ['decision', 'mention', 'generee_auto']
    search_fields = ['participant__nom', 'participant__prenom']
    autocomplete_fields = ['participant', 'formation', 'validee_par']


class SuiviModuleAuditeurInline(TabularInline):
    model = SuiviModuleAuditeur
    extra = 0
    fields = ['module', 'heures_presence', 'heures_prevues', 'taux_presence', 'moyenne_module']
    autocomplete_fields = ['module']


@admin.register(FicheAuditeurAcademique)
class FicheAuditeurAcademiqueAdmin(ModelAdmin):
    list_display = ['participant', 'formation', 'moyenne_generale', 'classement', 'archive']
    list_filter = ['archive', 'annee_academique']
    search_fields = ['participant__nom', 'participant__prenom']
    autocomplete_fields = ['participant', 'formation']
    inlines = [SuiviModuleAuditeurInline]


@admin.register(FicheFormateur)
class FicheFormateurAdmin(ModelAdmin):
    list_display = ['formateur', 'module', 'heures_prevues', 'heures_effectuees', 'taux_presence', 'satisfaction_auditeurs']
    list_filter = ['archive']
    search_fields = ['formateur__nom', 'formateur__prenom']
    autocomplete_fields = ['formateur', 'module', 'formation']


class QuestionQuizInline(TabularInline):
    model = QuestionQuiz
    extra = 1
    fields = ['ordre', 'question', 'type_question', 'reponse_correcte', 'points']


@admin.register(QuizManuel)
class QuizManuelAdmin(ModelAdmin):
    list_display = ['titre', 'module', 'chapitre', 'get_categories', 'seuil_reussite', 'actif']
    list_filter = ['actif']
    search_fields = ['titre', 'module__intitule']
    autocomplete_fields = ['module']
    inlines = [QuestionQuizInline]

    @admin.display(description='Catégories')
    def get_categories(self, obj):
        return ', '.join(obj.categories) if obj.categories else '—'


@admin.register(ReponseQuiz)
class ReponseQuizAdmin(ModelAdmin):
    list_display = ['participant', 'quiz', 'score', 'reussi', 'date_soumission']
    list_filter = ['reussi']
    search_fields = ['participant__nom', 'participant__prenom', 'quiz__titre']


@admin.register(HistoriqueNoteModification)
class HistoriqueNoteModificationAdmin(ModelAdmin):
    list_display = ['note_epreuve', 'ancienne_note', 'nouvelle_note', 'modifie_par', 'modifie_le']
    search_fields = ['note_epreuve__participant__nom']
    readonly_fields = ['modifie_le']


@admin.register(ExportRapport)
class ExportRapportAdmin(ModelAdmin):
    list_display = ['type_rapport', 'type_export', 'genere_par', 'genere_le']
    list_filter = ['type_rapport', 'type_export']
    readonly_fields = ['genere_le']
