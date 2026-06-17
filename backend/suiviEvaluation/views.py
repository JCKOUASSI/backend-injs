from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from formations.models import Module, Participant, Formateur, Formation

from .models import (
    Questionnaire, Question, ChoixQuestion, ReponseQuestionnaire, ReponseQuestion,
    TypeEpreuve, Epreuve, NoteEpreuve, ParametresEvaluation, MoyenneModule,
    DecisionPedagogique, FicheAuditeurAcademique, SuiviModuleAuditeur,
    FicheFormateur, QuizManuel, QuestionQuiz, ReponseQuiz, HistoriqueNoteModification,
)

from .permissions import (
    IsSuperviseur, IsAuditeur, IsGestionNotes, IsGestionNotesOrReadOnly,
    IsDecisionValidator,
)
from .serializers import (
    QuestionnaireListSerializer,
    QuestionnaireDetailSerializer,
    QuestionWriteSerializer,
    SoumissionSerializer,
    ResultatsSerializer,
    TypeEpreuveSerializer, EpreuveSerializer, NoteEpreuveSerializer,
    NoteEpreuveBulkItemSerializer, ParametresEvaluationSerializer,
    MoyenneModuleSerializer, DecisionPedagogiqueSerializer,
    FicheAuditeurAcademiqueSerializer, FicheFormateurSerializer,
    QuizManuelSerializer, QuizManuelDetailSerializer, QuizManuelPublicSerializer,
    QuestionQuizSerializer, ReponseQuizSerializer,
    HistoriqueNoteModificationSerializer,
)

from . import services as services
from . import exports as exports_helpers


# ─────────────────────────────────────────────────────────────
# QUESTIONNAIRES — Superviseurs
# ─────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsSuperviseur])
def questionnaire_list_create(request):
    """
    GET  : liste des questionnaires (filtrables par module_id, cible, statut)
    POST : créer un nouveau questionnaire
    """
    if request.method == 'GET':
        qs = Questionnaire.objects.select_related('module', 'createur').all()

        module_id = request.query_params.get('module_id')
        if module_id:
            qs = qs.filter(module_id=module_id)

        cible = request.query_params.get('cible')
        if cible:
            qs = qs.filter(cible__iexact=cible)

        statut = request.query_params.get('statut')
        if statut:
            qs = qs.filter(statut__iexact=statut)

        serializer = QuestionnaireListSerializer(qs, many=True)
        return Response(serializer.data)

    # POST
    data = request.data.copy()
    data['createur'] = request.user.pk
    serializer = QuestionnaireListSerializer(data=data)
    if serializer.is_valid():
        serializer.save(createur=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsSuperviseur])
def questionnaire_detail(request, pk):
    """Détail, modification ou suppression d'un questionnaire."""
    questionnaire = get_object_or_404(Questionnaire, pk=pk)

    if request.method == 'GET':
        serializer = QuestionnaireDetailSerializer(questionnaire)
        return Response(serializer.data)

    if request.method == 'PATCH':
        serializer = QuestionnaireListSerializer(questionnaire, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE
    if questionnaire.reponses.exists():
        return Response(
            {'detail': 'Impossible de supprimer un questionnaire ayant des réponses.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    questionnaire.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsSuperviseur])
def questionnaire_publier(request, pk):
    """Publier ou fermer un questionnaire."""
    questionnaire = get_object_or_404(Questionnaire, pk=pk)
    nouveau_statut = request.data.get('statut')
    if nouveau_statut not in (Questionnaire.Statut.PUBLIE, Questionnaire.Statut.FERME, Questionnaire.Statut.BROUILLON):
        return Response({'detail': 'statut invalide.'}, status=status.HTTP_400_BAD_REQUEST)
    questionnaire.statut = nouveau_statut
    questionnaire.save(update_fields=['statut'])
    return Response({'statut': questionnaire.statut})


# ─────────────────────────────────────────────────────────────
# QUESTIONS — Superviseurs
# ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsSuperviseur])
def question_create(request, questionnaire_pk):
    """Ajouter une question à un questionnaire."""
    questionnaire = get_object_or_404(Questionnaire, pk=questionnaire_pk)
    if questionnaire.statut == Questionnaire.Statut.PUBLIE:
        return Response(
            {'detail': 'Impossible de modifier un questionnaire publié.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    serializer = QuestionWriteSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(questionnaire=questionnaire)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsSuperviseur])
def question_detail(request, questionnaire_pk, pk):
    """Modifier ou supprimer une question."""
    questionnaire = get_object_or_404(Questionnaire, pk=questionnaire_pk)
    question = get_object_or_404(Question, pk=pk, questionnaire=questionnaire)

    if questionnaire.statut == Questionnaire.Statut.PUBLIE:
        return Response(
            {'detail': 'Impossible de modifier un questionnaire publié.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if request.method == 'PATCH':
        serializer = QuestionWriteSerializer(question, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE
    question.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────
# ÉVALUATION — Auditeurs
# ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuditeur])
def questionnaires_disponibles(request):
    """
    Retourne les questionnaires publiés accessibles à l'auditeur connecté
    en fonction de son grade et de sa catégorie (JSONField categories/grades).
    Un questionnaire est accessible si :
      - ses listes categories ET grades sont toutes deux vides (cible tout le monde), OU
      - sa liste categories contient la catégorie de l'auditeur (ex: 'A'), OU
      - sa liste grades contient le grade exact de l'auditeur (ex: 'A3').
    """
    try:
        participant = request.user.participant_profile
    except Exception:
        return Response({'detail': 'Profil auditeur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

    grade = (participant.grade or '').strip().upper()
    categorie = grade[0] if grade else ''

    qs = Questionnaire.objects.filter(statut=Questionnaire.Statut.PUBLIE)

    # Exclure ceux déjà soumis
    deja_soumis = ReponseQuestionnaire.objects.filter(
        participant=participant
    ).values_list('questionnaire_id', flat=True)
    qs = qs.exclude(id__in=deja_soumis)

    # Filtrage Python sur JSONField (compatible SQLite et PostgreSQL)
    result = []
    for q in qs:
        cats = q.categories or []
        grades = q.grades or []
        # Accessible si aucun filtre défini
        if not cats and not grades:
            result.append(q)
            continue
        # Accessible si la catégorie de l'auditeur est dans la liste
        if categorie and categorie in cats:
            result.append(q)
            continue
        # Accessible si le grade exact de l'auditeur est dans la liste
        if grade and grade in grades:
            result.append(q)
            continue

    serializer = QuestionnaireDetailSerializer(result, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuditeur])
def soumettre_evaluation(request):
    """Soumettre les réponses d'un auditeur à un questionnaire."""
    try:
        participant = request.user.participant_profile
    except Exception:
        return Response({'detail': 'Profil auditeur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

    data = request.data.copy()
    data['participant'] = participant.pk

    serializer = SoumissionSerializer(data=data)
    if serializer.is_valid():
        soumission = serializer.save()
        return Response(
            {'detail': 'Évaluation soumise avec succès.', 'id': soumission.pk},
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────────────────────
# RÉSULTATS — Superviseurs
# ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSuperviseur])
def resultats_questionnaire(request, pk):
    """Résultats agrégés d'un questionnaire."""
    questionnaire = get_object_or_404(Questionnaire, pk=pk)
    serializer = ResultatsSerializer(questionnaire)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsSuperviseur])
def resultats_par_module(request, module_pk):
    """Résultats de tous les questionnaires d'un module."""
    module = get_object_or_404(Module, pk=module_pk)
    questionnaires = Questionnaire.objects.filter(module=module)
    serializer = ResultatsSerializer(questionnaires, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsSuperviseur])
def analyse_qualitative(request, pk):
    """
    Analyse qualitative complète d'un questionnaire :
    - Méta : nb soumissions, taux de participation par grade/catégorie
    - Par question : distribution des notes (1-5), verbatims texte, stats choix
    - Score global moyen (questions NOTE uniquement)
    """
    from django.db.models import Avg, Count
    from collections import defaultdict

    questionnaire = get_object_or_404(Questionnaire, pk=pk)

    soumissions = questionnaire.reponses.select_related('participant').prefetch_related(
        'reponses_questions__question',
        'reponses_questions__choix',
        'reponses_questions__choix_multiples',
    )

    nb_soumissions = soumissions.count()

    # Distribution par grade et catégorie
    grade_counts = defaultdict(int)
    categorie_counts = defaultdict(int)
    for s in soumissions:
        grade = (s.participant.grade or '').strip().upper()
        if grade:
            grade_counts[grade] += 1
            cat = grade[0]
            categorie_counts[cat] += 1

    # Analyse par question
    questions_data = []
    notes_globales = []

    for q in questionnaire.questions.prefetch_related('choix', 'reponses').order_by('ordre'):
        item = {
            'id': q.id,
            'intitule': q.intitule,
            'type_question': q.type_question,
            'ordre': q.ordre,
            'obligatoire': q.obligatoire,
        }

        if q.type_question == 'NOTE':
            reponses_note = q.reponses.filter(note__isnull=False)
            notes = list(reponses_note.values_list('note', flat=True))
            agg = reponses_note.aggregate(moyenne=Avg('note'), total=Count('id'))
            moyenne = round(agg['moyenne'], 2) if agg['moyenne'] else None
            item['moyenne'] = moyenne
            item['total_reponses'] = agg['total']
            item['distribution'] = {str(i): notes.count(i) for i in range(1, 6)}
            if moyenne:
                notes_globales.append(moyenne)

        elif q.type_question in ('CHOIX_UN', 'CHOIX_MUL'):
            choix_stats = []
            total_rep = 0
            for c in q.choix.all():
                nb_unique = q.reponses.filter(choix=c).count()
                nb_multiple = c.reponses_choix_multiple.filter(
                    soumission__questionnaire=questionnaire
                ).count()
                nb = nb_unique + nb_multiple
                total_rep += nb
                choix_stats.append({'id': c.id, 'libelle': c.libelle, 'nb_reponses': nb})
            item['choix_stats'] = choix_stats
            item['total_reponses'] = total_rep

        elif q.type_question == 'TEXTE':
            verbatims_qs = q.reponses.exclude(texte='').select_related(
                'soumission__participant'
            )
            verbatims = []
            for r in verbatims_qs:
                grade = (r.soumission.participant.grade or '').strip().upper()
                verbatims.append({
                    'texte': r.texte,
                    'grade': grade,
                    'categorie': grade[0] if grade else '',
                })
            item['verbatims'] = verbatims
            item['nb_reponses_texte'] = len(verbatims)

        questions_data.append(item)

    score_global = round(sum(notes_globales) / len(notes_globales), 2) if notes_globales else None

    return Response({
        'id': questionnaire.pk,
        'titres': questionnaire.titres,
        'cible': questionnaire.cible,
        'statut': questionnaire.statut,
        'categories': questionnaire.categories,
        'grades': questionnaire.grades,
        'nb_soumissions': nb_soumissions,
        'score_global': score_global,
        'distribution_grades': dict(sorted(grade_counts.items())),
        'distribution_categories': dict(sorted(categorie_counts.items())),
        'questions': questions_data,
    })


# ─────────────────────────────────────────────────────────────
# TYPES D'ÉPREUVES
# ─────────────────────────────────────────────────────────────


@api_view(['GET', 'POST'])
@permission_classes([IsGestionNotesOrReadOnly])
def type_epreuve_list_create(request):
    if request.method == 'GET':
        qs = TypeEpreuve.objects.all()
        if request.query_params.get('actif') == 'true':
            qs = qs.filter(actif=True)
        return Response(TypeEpreuveSerializer(qs, many=True).data)

    serializer = TypeEpreuveSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsGestionNotesOrReadOnly])
def type_epreuve_detail(request, pk):
    obj = get_object_or_404(TypeEpreuve, pk=pk)
    if request.method == 'GET':
        return Response(TypeEpreuveSerializer(obj).data)
    if request.method == 'PATCH':
        serializer = TypeEpreuveSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    if obj.epreuves.exists():
        return Response(
            {'detail': "Impossible de supprimer un type d'épreuve utilisé."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    obj.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────
# ÉPREUVES
# ─────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsGestionNotesOrReadOnly])
def epreuve_list_create(request):
    if request.method == 'GET':
        qs = Epreuve.objects.select_related('type_epreuve', 'module').all()
        module_id = request.query_params.get('module_id')
        if module_id:
            qs = qs.filter(module_id=module_id)
        statut = request.query_params.get('statut')
        if statut:
            qs = qs.filter(statut__iexact=statut)
        return Response(EpreuveSerializer(qs, many=True).data)

    serializer = EpreuveSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsGestionNotesOrReadOnly])
def epreuve_detail(request, pk):
    obj = get_object_or_404(Epreuve, pk=pk)
    if request.method == 'GET':
        return Response(EpreuveSerializer(obj).data)
    if request.method == 'PATCH':
        serializer = EpreuveSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    obj.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────
# NOTES D'ÉPREUVES
# ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsGestionNotesOrReadOnly])
def notes_epreuve_list(request, epreuve_pk):
    """
    Liste de tous les auditeurs inscrits au module de l'épreuve,
    fusionnés avec leur note (si déjà saisie). Permet de construire
    directement la grille de saisie côté frontend.
    """
    from formations.models import ModuleParticipant
    epreuve = get_object_or_404(Epreuve, pk=epreuve_pk)

    # Notes déjà saisies indexées par participant
    notes_par_participant = {
        ne.participant_id: ne
        for ne in epreuve.notes_epreuve.select_related('participant', 'saisie_par')
    }

    # Roster complet des auditeurs attendus sur le module
    inscriptions = ModuleParticipant.objects.filter(
        module=epreuve.module
    ).select_related('participant').order_by('participant__nom', 'participant__prenom')

    resultats = []
    for insc in inscriptions:
        p = insc.participant
        ne = notes_par_participant.get(p.id)
        resultats.append({
            'note_id': ne.id if ne else None,
            'participant': p.id,
            'nom': p.nom,
            'prenom': p.prenom,
            'matricule': p.matricule,
            'grade': p.grade,
            'note': ne.note if ne else None,
            'mention': ne.mention if ne else '',
            'observations': ne.observations if ne else '',
            'absent': ne.absent if ne else False,
            'exclu': ne.exclu if ne else False,
            'anonymat_code': ne.anonymat_code if ne else '',
            'saisie_par': (ne.saisie_par.get_full_name() or ne.saisie_par.username)
                          if ne and ne.saisie_par else '',
            'modifie_le': ne.modifie_le if ne else None,
        })
    return Response(resultats)


@api_view(['POST'])
@permission_classes([IsGestionNotes])
def notes_epreuve_bulk_save(request, epreuve_pk):
    """
    Saisie/màj groupée des notes d'une épreuve.
    Body : {"notes": [{participant, note, mention, observations, absent, exclu, anonymat_code}, ...]}
    Recalcule automatiquement la moyenne du module.
    """
    epreuve = get_object_or_404(Epreuve, pk=epreuve_pk)
    items = request.data.get('notes', [])
    serializer = NoteEpreuveBulkItemSerializer(data=items, many=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    saved = []
    for item in serializer.validated_data:
        participant = Participant.objects.filter(pk=item['participant']).first()
        if not participant:
            continue
        note_existante = NoteEpreuve.objects.filter(
            epreuve=epreuve, participant=participant
        ).first()
        ancienne_note = note_existante.note if note_existante else None

        obj, _ = NoteEpreuve.objects.update_or_create(
            epreuve=epreuve,
            participant=participant,
            defaults={
                'note': item.get('note'),
                'mention': item.get('mention', ''),
                'observations': item.get('observations', ''),
                'absent': item.get('absent', False),
                'exclu': item.get('exclu', False),
                'anonymat_code': item.get('anonymat_code', ''),
                'saisie_par': request.user,
            },
        )
        # Traçabilité si modification d'une note existante
        if ancienne_note != obj.note:
            HistoriqueNoteModification.objects.create(
                note_epreuve=obj,
                ancienne_note=ancienne_note,
                nouvelle_note=obj.note,
                modifie_par=request.user,
                motif=request.data.get('motif', ''),
            )
        saved.append(obj)

    # Recalcul des moyennes du module
    services.calculer_moyennes_module_tous(epreuve.module)

    return Response(
        {'detail': f'{len(saved)} note(s) enregistrée(s).',
         'notes': NoteEpreuveSerializer(saved, many=True).data},
        status=status.HTTP_200_OK,
    )


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsGestionNotes])
def note_epreuve_detail(request, pk):
    obj = get_object_or_404(NoteEpreuve, pk=pk)
    if request.method == 'PATCH':
        ancienne_note = obj.note
        serializer = NoteEpreuveSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(saisie_par=request.user)
            if ancienne_note != obj.note:
                HistoriqueNoteModification.objects.create(
                    note_epreuve=obj,
                    ancienne_note=ancienne_note,
                    nouvelle_note=obj.note,
                    modifie_par=request.user,
                    motif=request.data.get('motif', ''),
                )
            services.calculer_moyenne_module(obj.epreuve.module, obj.participant)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    module, participant = obj.epreuve.module, obj.participant
    obj.delete()
    services.calculer_moyenne_module(module, participant)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsGestionNotesOrReadOnly])
def historique_note(request, note_pk):
    note = get_object_or_404(NoteEpreuve, pk=note_pk)
    hist = note.historique_modifications.select_related('modifie_par')
    return Response(HistoriqueNoteModificationSerializer(hist, many=True).data)


# ─────────────────────────────────────────────────────────────
# PARAMÈTRES D'ÉVALUATION
# ─────────────────────────────────────────────────────────────

@api_view(['GET', 'PUT'])
@permission_classes([IsDecisionValidator])
def parametres_evaluation(request, formation_pk):
    formation = get_object_or_404(Formation, pk=formation_pk)
    if request.method == 'GET':
        obj = ParametresEvaluation.objects.filter(formation=formation).first()
        if not obj:
            return Response({'detail': 'Aucun paramètre défini.', 'formation': formation.pk})
        return Response(ParametresEvaluationSerializer(obj).data)

    obj = ParametresEvaluation.objects.filter(formation=formation).first()
    serializer = ParametresEvaluationSerializer(obj, data={**request.data, 'formation': formation.pk}, partial=bool(obj))
    if serializer.is_valid():
        serializer.save(formation=formation)
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────────────────────
# MOYENNES
# ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsGestionNotesOrReadOnly])
def moyennes_module(request, module_pk):
    module = get_object_or_404(Module, pk=module_pk)
    moyennes = MoyenneModule.objects.filter(module=module).select_related('participant')
    return Response(MoyenneModuleSerializer(moyennes, many=True).data)


@api_view(['POST'])
@permission_classes([IsGestionNotes])
def recalculer_moyennes_module(request, module_pk):
    module = get_object_or_404(Module, pk=module_pk)
    resultats = services.calculer_moyennes_module_tous(module)
    return Response(
        {'detail': f'{len(resultats)} moyenne(s) recalculée(s).',
         'moyennes': MoyenneModuleSerializer(resultats, many=True).data}
    )


# ─────────────────────────────────────────────────────────────
# DÉCISIONS PÉDAGOGIQUES
# ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsDecisionValidator])
def decisions_formation(request, formation_pk):
    formation = get_object_or_404(Formation, pk=formation_pk)
    decisions = DecisionPedagogique.objects.filter(
        formation=formation
    ).select_related('participant', 'validee_par')
    decision_filter = request.query_params.get('decision')
    if decision_filter:
        decisions = decisions.filter(decision=decision_filter)
    return Response(DecisionPedagogiqueSerializer(decisions, many=True).data)


@api_view(['POST'])
@permission_classes([IsDecisionValidator])
def recalculer_decisions_formation(request, formation_pk):
    formation = get_object_or_404(Formation, pk=formation_pk)
    resultats = services.calculer_decisions_formation(formation)
    return Response(
        {'detail': f'{len(resultats)} décision(s) recalculée(s).',
         'decisions': DecisionPedagogiqueSerializer(resultats, many=True).data}
    )


@api_view(['PATCH'])
@permission_classes([IsDecisionValidator])
def decision_detail(request, pk):
    """Validation/ajustement manuel d'une décision pédagogique."""
    obj = get_object_or_404(DecisionPedagogique, pk=pk)
    serializer = DecisionPedagogiqueSerializer(obj, data=request.data, partial=True)
    if serializer.is_valid():
        obj = serializer.save(
            generee_auto=False,
            validee_par=request.user,
            validee_le=timezone.now(),
        )
        return Response(DecisionPedagogiqueSerializer(obj).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────────────────────
# FICHES AUDITEUR
# ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsGestionNotesOrReadOnly])
def fiche_auditeur(request, participant_pk, formation_pk):
    participant = get_object_or_404(Participant, pk=participant_pk)
    formation = get_object_or_404(Formation, pk=formation_pk)
    fiche = services.generer_fiche_auditeur(participant, formation)
    return Response(FicheAuditeurAcademiqueSerializer(fiche).data)


@api_view(['GET'])
@permission_classes([IsGestionNotesOrReadOnly])
def export_fiche_auditeur_pdf(request, participant_pk, formation_pk):
    """Génère et renvoie la fiche auditeur en PDF, enregistre l'ExportRapport."""
    participant = get_object_or_404(Participant, pk=participant_pk)
    formation = get_object_or_404(Formation, pk=formation_pk)
    fiche = services.generer_fiche_auditeur(participant, formation)
    try:
        buf = exports_helpers.export_fiche_auditeur_pdf(fiche)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    filename = f"fiche_auditeur_{participant.id}_{formation.id}.pdf"
    # Enregistrement historique
    try:
        exports_helpers.save_export_report(buf, filename, 'PDF', 'FICHE_AUDITEUR', user=request.user, formation=formation, participant=participant)
    except Exception:
        pass
    return HttpResponse(buf.getvalue(), content_type='application/pdf', headers={
        'Content-Disposition': f'attachment; filename="{filename}"'
    })


@api_view(['GET'])
@permission_classes([IsGestionNotesOrReadOnly])
def export_fiche_auditeur_excel(request, participant_pk, formation_pk):
    participant = get_object_or_404(Participant, pk=participant_pk)
    formation = get_object_or_404(Formation, pk=formation_pk)
    fiche = services.generer_fiche_auditeur(participant, formation)
    try:
        buf = exports_helpers.export_fiche_auditeur_excel(fiche)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    filename = f"fiche_auditeur_{participant.id}_{formation.id}.xlsx"
    try:
        exports_helpers.save_export_report(buf, filename, 'EXCEL', 'FICHE_AUDITEUR', user=request.user, formation=formation, participant=participant)
    except Exception:
        pass
    return HttpResponse(buf.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={
        'Content-Disposition': f'attachment; filename="{filename}"'
    })


@api_view(['GET'])
@permission_classes([IsAuditeur])
def ma_fiche_auditeur(request):
    """Fiche académique de l'auditeur connecté (toutes ses formations)."""
    try:
        participant = request.user.participant_profile
    except Exception:
        return Response({'detail': 'Profil auditeur introuvable.'}, status=status.HTTP_404_NOT_FOUND)
    fiches = FicheAuditeurAcademique.objects.filter(participant=participant)
    return Response(FicheAuditeurAcademiqueSerializer(fiches, many=True).data)


@api_view(['POST'])
@permission_classes([IsGestionNotes])
def generer_fiches_formation(request, formation_pk):
    """Génère les fiches de tous les auditeurs d'une formation + classement."""
    from formations.models import ModuleParticipant
    formation = get_object_or_404(Formation, pk=formation_pk)
    participant_ids = ModuleParticipant.objects.filter(
        module__formation=formation
    ).values_list('participant_id', flat=True).distinct()
    count = 0
    for pid in participant_ids:
        participant = Participant.objects.get(pk=pid)
        services.generer_fiche_auditeur(participant, formation)
        count += 1
    services.calculer_classements(formation)
    return Response({'detail': f'{count} fiche(s) générée(s).'})


# ─────────────────────────────────────────────────────────────
# FICHES FORMATEUR
# ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsGestionNotesOrReadOnly])
def fiche_formateur(request, formateur_pk, module_pk):
    formateur = get_object_or_404(Formateur, pk=formateur_pk)
    module = get_object_or_404(Module, pk=module_pk)
    fiche = services.generer_fiche_formateur(formateur, module)
    return Response(FicheFormateurSerializer(fiche).data)


@api_view(['GET'])
@permission_classes([IsGestionNotesOrReadOnly])
def export_fiche_formateur_pdf(request, formateur_pk, module_pk):
    formateur = get_object_or_404(Formateur, pk=formateur_pk)
    module = get_object_or_404(Module, pk=module_pk)
    fiche = services.generer_fiche_formateur(formateur, module)
    try:
        buf = exports_helpers.export_fiche_formateur_pdf(fiche)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    filename = f"fiche_formateur_{formateur.id}_{module.id}.pdf"
    try:
        exports_helpers.save_export_report(buf, filename, 'PDF', 'FICHE_FORMATEUR', user=request.user, formation=module.formation, module=module)
    except Exception:
        pass
    return HttpResponse(buf.getvalue(), content_type='application/pdf', headers={
        'Content-Disposition': f'attachment; filename="{filename}"'
    })


@api_view(['GET'])
@permission_classes([IsGestionNotesOrReadOnly])
def export_fiche_formateur_excel(request, formateur_pk, module_pk):
    formateur = get_object_or_404(Formateur, pk=formateur_pk)
    module = get_object_or_404(Module, pk=module_pk)
    fiche = services.generer_fiche_formateur(formateur, module)
    try:
        buf = exports_helpers.export_fiche_formateur_excel(fiche)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    filename = f"fiche_formateur_{formateur.id}_{module.id}.xlsx"
    try:
        exports_helpers.save_export_report(buf, filename, 'EXCEL', 'FICHE_FORMATEUR', user=request.user, formation=module.formation, module=module)
    except Exception:
        pass
    return HttpResponse(buf.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={
        'Content-Disposition': f'attachment; filename="{filename}"'
    })


@api_view(['GET'])
@permission_classes([IsGestionNotesOrReadOnly])
def fiches_formateur_module(request, module_pk):
    module = get_object_or_404(Module, pk=module_pk)
    fiches = FicheFormateur.objects.filter(module=module).select_related('formateur')
    return Response(FicheFormateurSerializer(fiches, many=True).data)


# ─────────────────────────────────────────────────────────────
# QUIZ MANUELS — Gestion
# ─────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsGestionNotesOrReadOnly])
def quiz_list_create(request):
    if request.method == 'GET':
        qs = QuizManuel.objects.select_related('module').all()
        module_id = request.query_params.get('module_id')
        if module_id:
            qs = qs.filter(module_id=module_id)
        return Response(QuizManuelSerializer(qs, many=True).data)
    serializer = QuizManuelSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsGestionNotesOrReadOnly])
def quiz_detail(request, pk):
    obj = get_object_or_404(QuizManuel, pk=pk)
    if request.method == 'GET':
        return Response(QuizManuelDetailSerializer(obj).data)
    if request.method == 'PATCH':
        serializer = QuizManuelSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    obj.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsGestionNotes])
def quiz_question_create(request, quiz_pk):
    quiz = get_object_or_404(QuizManuel, pk=quiz_pk)
    data = {**request.data, 'quiz': quiz.pk}
    serializer = QuestionQuizSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsGestionNotes])
def quiz_question_detail(request, quiz_pk, pk):
    question = get_object_or_404(QuestionQuiz, pk=pk, quiz_id=quiz_pk)
    if request.method == 'PATCH':
        serializer = QuestionQuizSerializer(question, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    question.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsGestionNotesOrReadOnly])
def quiz_resultats(request, pk):
    """Résultats agrégés d'un quiz."""
    quiz = get_object_or_404(QuizManuel, pk=pk)
    reponses = quiz.reponses.select_related('participant')
    nb = reponses.count()
    nb_reussis = reponses.filter(reussi=True).count()
    scores = [float(r.score) for r in reponses if r.score is not None]
    score_moyen = round(sum(scores) / len(scores), 2) if scores else None
    return Response({
        'quiz': QuizManuelSerializer(quiz).data,
        'nb_participations': nb,
        'nb_reussis': nb_reussis,
        'taux_reussite': round((nb_reussis / nb) * 100, 2) if nb else None,
        'score_moyen': score_moyen,
        'reponses': ReponseQuizSerializer(reponses, many=True).data,
    })


# ─────────────────────────────────────────────────────────────
# QUIZ MANUELS — Auditeurs
# ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuditeur])
def quiz_disponibles(request):
    """Quiz actifs disponibles pour l'auditeur (sans réponses correctes)."""
    try:
        participant = request.user.participant_profile
    except Exception:
        return Response({'detail': 'Profil auditeur introuvable.'}, status=status.HTTP_404_NOT_FOUND)
    now = timezone.now()
    qs = QuizManuel.objects.filter(actif=True)

    # Exclure ceux déjà faits
    deja_faits = ReponseQuiz.objects.filter(
        participant=participant
    ).values_list('quiz_id', flat=True)
    qs = qs.exclude(id__in=deja_faits)

    # Filtrage par grade/catégorie (JSONField) — compatible SQLite/Postgres
    grade = (participant.grade or '').strip().upper()
    categorie = grade[0] if grade else ''

    result = []
    for q in qs:
        cats = q.categories or []
        grades = q.grades or []
        # Accessible si aucun filtre défini
        if not cats and not grades:
            result.append(q)
            continue
        if categorie and categorie in cats:
            result.append(q)
            continue
        if grade and grade in grades:
            result.append(q)
            continue

    return Response(QuizManuelPublicSerializer(result, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuditeur])
def quiz_soumettre(request, quiz_pk):
    """
    Soumission d'un quiz par un auditeur avec correction automatique.
    Body : {"reponses": {"<question_id>": "<reponse>", ...}, "temps_pris_minutes": int}
    """
    try:
        participant = request.user.participant_profile
    except Exception:
        return Response({'detail': 'Profil auditeur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

    quiz = get_object_or_404(QuizManuel, pk=quiz_pk)
    if not quiz.actif:
        return Response({'detail': "Ce quiz n'est pas ouvert."}, status=status.HTTP_400_BAD_REQUEST)
    if ReponseQuiz.objects.filter(quiz=quiz, participant=participant).exists():
        return Response({'detail': 'Vous avez déjà répondu à ce quiz.'}, status=status.HTTP_400_BAD_REQUEST)

    reponses = request.data.get('reponses', {})
    questions = quiz.questions.all()
    total_points = 0.0
    points_obtenus = 0.0
    detail = {}

    for q in questions:
        total_points += float(q.points)
        reponse_donnee = reponses.get(str(q.id), '')
        correcte = str(reponse_donnee).strip().lower() == str(q.reponse_correcte).strip().lower()
        if correcte:
            points_obtenus += float(q.points)
        detail[str(q.id)] = {
            'reponse_donnee': reponse_donnee,
            'correcte': correcte,
        }

    score = round((points_obtenus / total_points) * 100, 2) if total_points > 0 else 0
    reussi = score >= float(quiz.seuil_reussite)

    obj = ReponseQuiz.objects.create(
        quiz=quiz,
        participant=participant,
        score=score,
        reussi=reussi,
        temps_pris_minutes=request.data.get('temps_pris_minutes'),
        reponses_detail=detail,
    )
    return Response(
        {'detail': 'Quiz soumis.', 'score': score, 'reussi': reussi,
         'id': obj.pk},
        status=status.HTTP_201_CREATED,
    )
