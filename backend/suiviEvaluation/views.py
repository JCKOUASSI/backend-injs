from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from formations.models import Module, Participant, Formation

from .models import (
    Questionnaire, Question, ChoixQuestion, ReponseQuestionnaire, ReponseQuestion,
)

from .permissions import (
    IsSuperviseur, IsAuditeur,
)
from .serializers import (
    QuestionnaireListSerializer,
    QuestionnaireDetailSerializer,
    QuestionWriteSerializer,
    SoumissionSerializer,
    ResultatsSerializer,
)



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

