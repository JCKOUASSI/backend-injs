from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from formations.models import Formation, Module

from .models import DecisionPedagogique, MoyenneModule
from .permissions import IsGestionNotes, IsDecisionValidator
from .services import (
    calculer_decisions_formation,
    calculer_moyennes_module_tous,
    calculer_moyenne_module,
    _get_parametres,
)


def _serialize_decision(d):
    p = d.participant
    validee_par = d.validee_par
    return {
        'id': d.id,
        'participant_id': p.id,
        'participant_nom': f'{p.nom} {p.prenom}'.strip(),
        'participant_matricule': p.matricule or '',
        'moyenne_generale': float(d.moyenne_generale) if d.moyenne_generale is not None else None,
        'taux_presence': float(d.taux_presence) if d.taux_presence is not None else None,
        'total_heures_presence': float(d.total_heures_presence) if d.total_heures_presence is not None else None,
        'total_heures_prevues': float(d.total_heures_prevues) if d.total_heures_prevues is not None else None,
        'decision': d.decision,
        'mention': d.mention,
        'generee_auto': d.generee_auto,
        'validee_le': d.validee_le.isoformat() if d.validee_le else None,
        'validee_par_nom': (
            validee_par.get_full_name() or validee_par.username if validee_par else None
        ),
        'criteres_appliques': d.criteres_appliques or {},
    }


def _serialize_moyenne_module(mm):
    p = mm.participant
    params = _get_parametres(mm.module.formation)
    moy = float(mm.moyenne) if mm.moyenne is not None else None
    taux = float(mm.taux_presence) if mm.taux_presence is not None else None
    admis = (
        moy is not None and taux is not None
        and moy >= params['seuil_admission']
        and taux >= params['taux_presence_min']
    )
    return {
        'participant_id': p.id,
        'nom': p.nom,
        'prenom': p.prenom,
        'matricule': p.matricule or '',
        'grade': p.grade or '',
        'moyenne': moy,
        'nb_notes': mm.nb_notes,
        'heures_presence': float(mm.heures_presence),
        'heures_prevues': float(mm.heures_prevues),
        'taux_presence': taux,
        'admissible': admis,
    }


@api_view(['GET'])
@permission_classes([IsGestionNotes])
def formation_decisions_list(request, formation_pk):
    formation = get_object_or_404(Formation, pk=formation_pk)
    qs = DecisionPedagogique.objects.filter(
        formation=formation,
    ).select_related('participant', 'validee_par').order_by('participant__nom', 'participant__prenom')
    criteres = _get_parametres(formation)
    return Response({
        'criteres': criteres,
        'decisions': [_serialize_decision(d) for d in qs],
    })


@api_view(['POST'])
@permission_classes([IsGestionNotes])
def formation_decisions_recalc(request, formation_pk):
    formation = get_object_or_404(Formation, pk=formation_pk)
    resultats = calculer_decisions_formation(formation)
    return Response({
        'detail': f'{len(resultats)} décision(s) recalculée(s).',
        'count': len(resultats),
    })


@api_view(['PATCH'])
@permission_classes([IsDecisionValidator])
def decision_detail(request, pk):
    decision = get_object_or_404(
        DecisionPedagogique.objects.select_related('participant', 'formation'),
        pk=pk,
    )
    if decision.validee_le and request.data.get('decision') and not request.user:
        pass

    for field in ('decision', 'mention', 'appreciation'):
        if field in request.data:
            setattr(decision, field, request.data[field])

    if request.data.get('valider', True):
        decision.validee_le = timezone.now()
        decision.validee_par = request.user
        decision.generee_auto = False

    decision.save()
    return Response(_serialize_decision(decision))


@api_view(['GET'])
@permission_classes([IsGestionNotes])
def module_moyennes_list(request, module_pk):
    module = get_object_or_404(Module, pk=module_pk)
    qs = MoyenneModule.objects.filter(module=module).select_related('participant')
    if not qs.exists():
        calculer_moyennes_module_tous(module)
        qs = MoyenneModule.objects.filter(module=module).select_related('participant')
    return Response({
        'criteres': _get_parametres(module.formation),
        'moyennes': [_serialize_moyenne_module(mm) for mm in qs],
    })


@api_view(['POST'])
@permission_classes([IsGestionNotes])
def module_moyennes_recalc(request, module_pk):
    module = get_object_or_404(Module, pk=module_pk)
    resultats = calculer_moyennes_module_tous(module)
    return Response({
        'detail': f'{len(resultats)} moyenne(s) recalculée(s).',
        'count': len(resultats),
        'moyennes': [_serialize_moyenne_module(mm) for mm in resultats],
    })
