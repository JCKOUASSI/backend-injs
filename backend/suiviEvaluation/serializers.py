from rest_framework import serializers
from .models import (
    Questionnaire, Question, ChoixQuestion,
    ReponseQuestionnaire, ReponseQuestion,
    TypeEpreuve, Epreuve, NoteEpreuve, ParametresEvaluation, MoyenneModule,
    DecisionPedagogique, FicheAuditeurAcademique, SuiviModuleAuditeur,
    FicheFormateur, QuizManuel, QuestionQuiz, ReponseQuiz,
    HistoriqueNoteModification,
)


class ChoixQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChoixQuestion
        fields = ['id', 'libelle', 'ordre']


class QuestionSerializer(serializers.ModelSerializer):
    choix = ChoixQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'intitule', 'type_question', 'ordre', 'obligatoire', 'choix']


class QuestionnaireListSerializer(serializers.ModelSerializer):
    nb_questions = serializers.IntegerField(source='questions.count', read_only=True)
    createur_nom = serializers.SerializerMethodField()
    module_intitule = serializers.SerializerMethodField()

    class Meta:
        model = Questionnaire
        fields = [
            'id', 'titres', 'cible', 'statut', 'categories', 'grades',
            'module', 'module_intitule',
            'createur', 'createur_nom',
            'date_ouverture', 'date_fermeture',
            'nb_questions', 'created_at',
        ]

    def get_createur_nom(self, obj):
        if obj.createur:
            return obj.createur.get_full_name() or obj.createur.username
        return ''

    def get_module_intitule(self, obj):
        if obj.module:
            return obj.module.intitule
        return ''


class QuestionnaireDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    createur_nom = serializers.SerializerMethodField()
    module_intitule = serializers.SerializerMethodField()

    class Meta:
        model = Questionnaire
        fields = [
            'id', 'titres', 'cible', 'statut', 'categories', 'grades',
            'module', 'module_intitule',
            'createur', 'createur_nom',
            'date_ouverture', 'date_fermeture',
            'questions', 'created_at', 'updated_at',
        ]

    def get_createur_nom(self, obj):
        if obj.createur:
            return obj.createur.get_full_name() or obj.createur.username
        return ''

    def get_module_intitule(self, obj):
        if obj.module:
            return obj.module.intitule
        return ''


class QuestionWriteSerializer(serializers.ModelSerializer):
    choix = ChoixQuestionSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ['id', 'intitule', 'type_question', 'ordre', 'obligatoire', 'choix']

    def create(self, validated_data):
        choix_data = validated_data.pop('choix', [])
        question = Question.objects.create(**validated_data)
        for c in choix_data:
            ChoixQuestion.objects.create(question=question, **c)
        return question

    def update(self, instance, validated_data):
        choix_data = validated_data.pop('choix', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if choix_data is not None:
            instance.choix.all().delete()
            for c in choix_data:
                ChoixQuestion.objects.create(question=instance, **c)
        return instance


class ReponseQuestionSerializer(serializers.ModelSerializer):
    choix_multiples = serializers.PrimaryKeyRelatedField(
        queryset=ChoixQuestion.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = ReponseQuestion
        fields = ['question', 'note', 'texte', 'choix', 'choix_multiples']


class SoumissionSerializer(serializers.ModelSerializer):
    reponses_questions = ReponseQuestionSerializer(many=True)

    class Meta:
        model = ReponseQuestionnaire
        fields = ['id', 'questionnaire', 'participant', 'soumis_le', 'reponses_questions']
        read_only_fields = ['id', 'soumis_le']

    def validate(self, data):
        questionnaire = data['questionnaire']
        participant = data['participant']
        if questionnaire.statut != Questionnaire.Statut.PUBLIE:
            raise serializers.ValidationError("Ce questionnaire n'est pas ouvert.")
        if ReponseQuestionnaire.objects.filter(
            questionnaire=questionnaire, participant=participant
        ).exists():
            raise serializers.ValidationError("Vous avez déjà répondu à ce questionnaire.")
        return data

    def create(self, validated_data):
        reponses_data = validated_data.pop('reponses_questions')
        soumission = ReponseQuestionnaire.objects.create(**validated_data)
        for rep in reponses_data:
            choix_mult = rep.pop('choix_multiples', [])
            rq = ReponseQuestion.objects.create(soumission=soumission, **rep)
            if choix_mult:
                rq.choix_multiples.set(choix_mult)
        return soumission


class ResultatsSerializer(serializers.ModelSerializer):
    """Résumé statistique d'un questionnaire pour les superviseurs."""
    nb_soumissions = serializers.IntegerField(source='reponses.count', read_only=True)
    questions = serializers.SerializerMethodField()

    class Meta:
        model = Questionnaire
        fields = ['id', 'titres', 'cible', 'statut', 'categories', 'grades', 'nb_soumissions', 'questions']

    def get_questions(self, obj):
        from django.db.models import Avg, Count
        result = []
        for q in obj.questions.prefetch_related('choix', 'reponses').order_by('ordre'):
            item = {
                'id': q.id,
                'intitule': q.intitule,
                'type_question': q.type_question,
                'ordre': q.ordre,
            }
            if q.type_question == Question.TypeQuestion.NOTE:
                agg = q.reponses.filter(note__isnull=False).aggregate(
                    moyenne=Avg('note'), total=Count('id')
                )
                item['moyenne'] = round(agg['moyenne'], 2) if agg['moyenne'] else None
                item['total_reponses'] = agg['total']
            elif q.type_question in (
                Question.TypeQuestion.CHOIX_UN,
                Question.TypeQuestion.CHOIX_MUL,
            ):
                choix_stats = []
                for c in q.choix.all():
                    nb_unique = q.reponses.filter(choix=c).count()
                    nb_multiple = c.reponses_choix_multiple.filter(
                        soumission__questionnaire=obj
                    ).count()
                    choix_stats.append({
                        'id': c.id,
                        'libelle': c.libelle,
                        'nb_reponses': nb_unique + nb_multiple,
                    })
                item['choix_stats'] = choix_stats
            else:
                item['nb_reponses_texte'] = q.reponses.exclude(texte='').count()
            result.append(item)
        return result


# ─────────────────────────────────────────────────────────────
# TYPES D'ÉPREUVES
# ─────────────────────────────────────────────────────────────

class TypeEpreuveSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeEpreuve
        fields = ['id', 'code', 'libelle', 'actif', 'ordre']


# ─────────────────────────────────────────────────────────────
# ÉPREUVES
# ─────────────────────────────────────────────────────────────

class EpreuveSerializer(serializers.ModelSerializer):
    type_epreuve_libelle = serializers.CharField(source='type_epreuve.libelle', read_only=True)
    module_intitule = serializers.CharField(source='module.intitule', read_only=True)
    nb_notes = serializers.SerializerMethodField()

    class Meta:
        model = Epreuve
        fields = [
            'id', 'code', 'type_epreuve', 'type_epreuve_libelle',
            'module', 'module_intitule', 'intitule', 'description',
            'coefficient', 'note_max', 'date_epreuve', 'heure_debut',
            'heure_fin', 'duree_minutes', 'salle', 'anonyme', 'statut',
            'publier_notes', 'created_by', 'created_at', 'updated_at',
            'nb_notes',
        ]
        read_only_fields = ['id', 'code', 'created_by', 'created_at', 'updated_at']

    def get_nb_notes(self, obj):
        return obj.notes_epreuve.count()


# ─────────────────────────────────────────────────────────────
# NOTES D'ÉPREUVES
# ─────────────────────────────────────────────────────────────

class NoteEpreuveSerializer(serializers.ModelSerializer):
    participant_nom = serializers.SerializerMethodField()
    participant_matricule = serializers.CharField(source='participant.matricule', read_only=True)
    epreuve_intitule = serializers.CharField(source='epreuve.intitule', read_only=True)
    note_coefficientee = serializers.ReadOnlyField()
    saisie_par_nom = serializers.SerializerMethodField()

    class Meta:
        model = NoteEpreuve
        fields = [
            'id', 'epreuve', 'epreuve_intitule', 'participant',
            'participant_nom', 'participant_matricule', 'note', 'mention',
            'observations', 'absent', 'exclu', 'anonymat_code',
            'note_coefficientee', 'saisie_par', 'saisie_par_nom',
            'saisie_le', 'modifie_le',
        ]
        read_only_fields = ['id', 'saisie_par', 'saisie_le', 'modifie_le']

    def get_participant_nom(self, obj):
        return f"{obj.participant.nom} {obj.participant.prenom}"

    def get_saisie_par_nom(self, obj):
        if obj.saisie_par:
            return obj.saisie_par.get_full_name() or obj.saisie_par.username
        return ''


class NoteEpreuveBulkItemSerializer(serializers.Serializer):
    """Item pour la saisie groupée de notes."""
    participant = serializers.IntegerField()
    note = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    mention = serializers.CharField(required=False, allow_blank=True, default='')
    observations = serializers.CharField(required=False, allow_blank=True, default='')
    absent = serializers.BooleanField(required=False, default=False)
    exclu = serializers.BooleanField(required=False, default=False)
    anonymat_code = serializers.CharField(required=False, allow_blank=True, default='')


# ─────────────────────────────────────────────────────────────
# PARAMÈTRES D'ÉVALUATION
# ─────────────────────────────────────────────────────────────

class ParametresEvaluationSerializer(serializers.ModelSerializer):
    formation_libelle = serializers.CharField(source='formation.formation', read_only=True)

    class Meta:
        model = ParametresEvaluation
        fields = [
            'id', 'formation', 'formation_libelle', 'seuil_admission',
            'seuil_mention_bien', 'seuil_mention_tres_bien',
            'taux_presence_min', 'coefficient_devoirs', 'coefficient_controles',
            'coefficient_examens', 'coefficient_oraux', 'coefficient_pratiques',
            'actif', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ─────────────────────────────────────────────────────────────
# MOYENNES
# ─────────────────────────────────────────────────────────────

class MoyenneModuleSerializer(serializers.ModelSerializer):
    participant_nom = serializers.SerializerMethodField()
    module_intitule = serializers.CharField(source='module.intitule', read_only=True)

    class Meta:
        model = MoyenneModule
        fields = [
            'id', 'module', 'module_intitule', 'participant', 'participant_nom',
            'moyenne', 'total_coefficients', 'somme_notes_coeff',
            'nb_epreuves', 'calculee_le',
        ]
        read_only_fields = fields

    def get_participant_nom(self, obj):
        return f"{obj.participant.nom} {obj.participant.prenom}"


# ─────────────────────────────────────────────────────────────
# DÉCISIONS PÉDAGOGIQUES
# ─────────────────────────────────────────────────────────────

class DecisionPedagogiqueSerializer(serializers.ModelSerializer):
    participant_nom = serializers.SerializerMethodField()
    participant_matricule = serializers.CharField(source='participant.matricule', read_only=True)
    formation_libelle = serializers.CharField(source='formation.formation', read_only=True)
    decision_display = serializers.CharField(source='get_decision_display', read_only=True)
    mention_display = serializers.CharField(source='get_mention_display', read_only=True)
    validee_par_nom = serializers.SerializerMethodField()

    class Meta:
        model = DecisionPedagogique
        fields = [
            'id', 'participant', 'participant_nom', 'participant_matricule',
            'formation', 'formation_libelle', 'moyenne_generale',
            'taux_presence', 'total_heures_presence', 'total_heures_prevues',
            'decision', 'decision_display', 'mention', 'mention_display',
            'appreciation', 'generee_auto', 'validee_par', 'validee_par_nom',
            'validee_le', 'criteres_appliques', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'validee_par', 'validee_le', 'created_at', 'updated_at',
        ]

    def get_participant_nom(self, obj):
        return f"{obj.participant.nom} {obj.participant.prenom}"

    def get_validee_par_nom(self, obj):
        if obj.validee_par:
            return obj.validee_par.get_full_name() or obj.validee_par.username
        return ''


# ─────────────────────────────────────────────────────────────
# FICHES AUDITEUR
# ─────────────────────────────────────────────────────────────

class SuiviModuleAuditeurSerializer(serializers.ModelSerializer):
    module_intitule = serializers.CharField(source='module.intitule', read_only=True)

    class Meta:
        model = SuiviModuleAuditeur
        fields = [
            'id', 'fiche', 'module', 'module_intitule', 'heures_presence',
            'heures_prevues', 'taux_presence', 'moyenne_module',
            'nb_epreuves', 'appreciation', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FicheAuditeurAcademiqueSerializer(serializers.ModelSerializer):
    participant_nom = serializers.SerializerMethodField()
    participant_matricule = serializers.CharField(source='participant.matricule', read_only=True)
    formation_libelle = serializers.CharField(source='formation.formation', read_only=True)
    suivi_modules = SuiviModuleAuditeurSerializer(many=True, read_only=True)
    decision_finale_detail = DecisionPedagogiqueSerializer(source='decision_finale', read_only=True)

    class Meta:
        model = FicheAuditeurAcademique
        fields = [
            'id', 'participant', 'participant_nom', 'participant_matricule',
            'formation', 'formation_libelle', 'moyenne_generale', 'classement',
            'decision_finale', 'decision_finale_detail', 'date_debut_formation',
            'date_fin_formation', 'archive', 'annee_academique',
            'suivi_modules', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_participant_nom(self, obj):
        return f"{obj.participant.nom} {obj.participant.prenom}"


# ─────────────────────────────────────────────────────────────
# FICHES FORMATEUR
# ─────────────────────────────────────────────────────────────

class FicheFormateurSerializer(serializers.ModelSerializer):
    formateur_nom = serializers.SerializerMethodField()
    module_intitule = serializers.SerializerMethodField()
    formation_libelle = serializers.SerializerMethodField()

    class Meta:
        model = FicheFormateur
        fields = [
            'id', 'formateur', 'formateur_nom', 'formation', 'formation_libelle',
            'module', 'module_intitule', 'heures_prevues', 'heures_effectuees',
            'taux_presence', 'nb_seances', 'nb_seances_realisees',
            'satisfaction_auditeurs', 'nb_evaluations',
            'appreciation_pedagogique', 'archive', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_formateur_nom(self, obj):
        return f"{obj.formateur.nom} {obj.formateur.prenom}"

    def get_module_intitule(self, obj):
        return obj.module.intitule if obj.module else ''

    def get_formation_libelle(self, obj):
        return obj.formation.formation if obj.formation else ''


# ─────────────────────────────────────────────────────────────
# QUIZ MANUELS
# ─────────────────────────────────────────────────────────────

class QuestionQuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionQuiz
        fields = [
            'id', 'quiz', 'question', 'type_question', 'reponse_correcte',
            'options', 'points', 'ordre',
        ]
        read_only_fields = ['id']


class QuestionQuizPublicSerializer(serializers.ModelSerializer):
    """Version sans la réponse correcte (pour les auditeurs)."""
    class Meta:
        model = QuestionQuiz
        fields = ['id', 'question', 'type_question', 'options', 'points', 'ordre']


class QuizManuelSerializer(serializers.ModelSerializer):
    module_intitule = serializers.CharField(source='module.intitule', read_only=True)
    nb_questions_reelles = serializers.SerializerMethodField()

    class Meta:
        model = QuizManuel
        fields = [
            'id', 'module', 'module_intitule', 'titre', 'description',
            'chapitre', 'categories', 'grades', 'nb_questions', 'nb_questions_reelles', 'seuil_reussite',
            'duree_max_minutes', 'actif', 'date_ouverture', 'date_fermeture',
            'created_by', 'created_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at']

    def get_nb_questions_reelles(self, obj):
        return obj.questions.count()


class QuizManuelDetailSerializer(QuizManuelSerializer):
    questions = QuestionQuizSerializer(many=True, read_only=True)

    class Meta(QuizManuelSerializer.Meta):
        fields = QuizManuelSerializer.Meta.fields + ['questions']


class QuizManuelPublicSerializer(QuizManuelSerializer):
    """Pour les auditeurs : questions sans réponses correctes."""
    questions = QuestionQuizPublicSerializer(many=True, read_only=True)

    class Meta(QuizManuelSerializer.Meta):
        fields = QuizManuelSerializer.Meta.fields + ['questions']


class ReponseQuizSerializer(serializers.ModelSerializer):
    participant_nom = serializers.SerializerMethodField()
    quiz_titre = serializers.CharField(source='quiz.titre', read_only=True)

    class Meta:
        model = ReponseQuiz
        fields = [
            'id', 'quiz', 'quiz_titre', 'participant', 'participant_nom',
            'date_soumission', 'score', 'reussi', 'temps_pris_minutes',
            'reponses_detail',
        ]
        read_only_fields = ['id', 'date_soumission', 'score', 'reussi']

    def get_participant_nom(self, obj):
        return f"{obj.participant.nom} {obj.participant.prenom}"


# ─────────────────────────────────────────────────────────────
# HISTORIQUE MODIFICATIONS
# ─────────────────────────────────────────────────────────────

class HistoriqueNoteModificationSerializer(serializers.ModelSerializer):
    modifie_par_nom = serializers.SerializerMethodField()

    class Meta:
        model = HistoriqueNoteModification
        fields = [
            'id', 'note_epreuve', 'ancienne_note', 'nouvelle_note',
            'modifie_par', 'modifie_par_nom', 'modifie_le', 'motif',
        ]
        read_only_fields = fields

    def get_modifie_par_nom(self, obj):
        if obj.modifie_par:
            return obj.modifie_par.get_full_name() or obj.modifie_par.username
        return ''
