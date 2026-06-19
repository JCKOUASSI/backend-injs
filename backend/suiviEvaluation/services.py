"""
Moteur de calcul — évaluation académique :
- Moyennes des notes saisies (colonnes /20)
- Temps de cours effectué vs prévu (badgeages)
- Décisions : admis si moyenne ≥ 12/20 ET ≥ 80 % du temps de cours effectué
"""
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from formations.models import Module, Participant, Formation, ModuleParticipant
from formations.models import NoteModule
from presences.models import Pointage

from .models import ParametresEvaluation, MoyenneModule, DecisionPedagogique

DEFAULT_SEUIL_ADMISSION = 12.0
DEFAULT_TAUX_PRESENCE_MIN = 80.0
DEFAULT_SEUIL_MENTION_BIEN = 14.0
DEFAULT_SEUIL_MENTION_TRES_BIEN = 16.0


def _get_parametres(formation):
    """Seuils de la formation ou valeurs par défaut (12/20 et 80 %)."""
    params = ParametresEvaluation.objects.filter(formation=formation, actif=True).first()
    if params:
        return {
            'seuil_admission': float(params.seuil_admission),
            'taux_presence_min': float(params.taux_presence_min),
            'seuil_mention_bien': float(params.seuil_mention_bien),
            'seuil_mention_tres_bien': float(params.seuil_mention_tres_bien),
        }
    return {
        'seuil_admission': DEFAULT_SEUIL_ADMISSION,
        'taux_presence_min': DEFAULT_TAUX_PRESENCE_MIN,
        'seuil_mention_bien': DEFAULT_SEUIL_MENTION_BIEN,
        'seuil_mention_tres_bien': DEFAULT_SEUIL_MENTION_TRES_BIEN,
    }


def _heures_prevues_module(module, participant=None):
    """Volume horaire contractuel du module (référentiel / fiche, pas l'EDT)."""
    from formations.duree_prevue_resolve import resolve_module_volume_contractuel_heures

    heures, _ = resolve_module_volume_contractuel_heures(module, participant=participant)
    return heures


def calculer_presence_module(module, participant):
    """
    Retourne (heures_presence, heures_prevues, taux_presence).
    Le temps effectué est plafonné au temps prévu du module.
    """
    heures_prevues = _heures_prevues_module(module, participant)
    cap_minutes = heures_prevues * 60 if heures_prevues > 0 else 0.0

    agg = Pointage.objects.filter(
        session__module=module,
        participant=participant,
        duree_presence_minutes__isnull=False,
    ).aggregate(total=Sum('duree_presence_minutes'))
    minutes_presence = float(agg['total'] or 0)
    if cap_minutes > 0:
        minutes_presence = min(minutes_presence, cap_minutes)

    heures_presence = round(minutes_presence / 60.0, 2)
    taux = None
    if heures_prevues > 0:
        taux = round((heures_presence / heures_prevues) * 100, 2)
    return heures_presence, round(heures_prevues, 2), taux


def calculer_moyenne_notes_module(module, participant):
    """Moyenne /20 des notes saisies (colonnes normalisées sur 20)."""
    valeurs = NoteModule.objects.filter(
        colonne__module=module,
        participant=participant,
        note__isnull=False,
    ).select_related('colonne')
    normalized = []
    for v in valeurs:
        note_max = float(v.colonne.note_max or 20)
        if note_max <= 0:
            note_max = 20.0
        normalized.append(float(v.note) * 20.0 / note_max)
    if not normalized:
        return None, 0
    return round(sum(normalized) / len(normalized), 2), len(normalized)


def est_admissible(moyenne, taux_presence, params=None):
    """True si moyenne ≥ seuil ET taux présence ≥ seuil (défaut 12 et 80 %)."""
    params = params or {}
    seuil_note = params.get('seuil_admission', DEFAULT_SEUIL_ADMISSION)
    seuil_taux = params.get('taux_presence_min', DEFAULT_TAUX_PRESENCE_MIN)
    if moyenne is None or taux_presence is None:
        return False
    return float(moyenne) >= seuil_note and float(taux_presence) >= seuil_taux


def calculer_moyenne_module(module, participant, *, save=True):
    """Calcule et enregistre la moyenne + assiduité horaire sur un module."""
    moyenne, nb_notes = calculer_moyenne_notes_module(module, participant)
    hp, hprev, taux = calculer_presence_module(module, participant)

    defaults = {
        'moyenne': moyenne,
        'nb_notes': nb_notes,
        'heures_presence': hp,
        'heures_prevues': hprev,
        'taux_presence': taux,
    }
    if not save:
        obj = MoyenneModule(module=module, participant=participant, **defaults)
        return obj

    obj, _ = MoyenneModule.objects.update_or_create(
        module=module,
        participant=participant,
        defaults=defaults,
    )
    return obj


def calculer_moyennes_module_tous(module):
    """Recalcule les moyennes de tous les auditeurs inscrits au module."""
    participant_ids = ModuleParticipant.objects.filter(
        module=module,
    ).values_list('participant_id', flat=True)
    return [
        calculer_moyenne_module(module, Participant.objects.get(pk=pid))
        for pid in participant_ids
    ]


def calculer_moyenne_generale(participant, formation):
    """Moyenne générale pondérée par la durée prévue de chaque module."""
    modules = Module.objects.filter(formation=formation)
    somme = Decimal('0')
    total_poids = Decimal('0')

    for module in modules:
        mm = MoyenneModule.objects.filter(module=module, participant=participant).first()
        if not mm or mm.moyenne is None:
            moyenne, _ = calculer_moyenne_notes_module(module, participant)
            if moyenne is None:
                continue
        else:
            moyenne = float(mm.moyenne)
        poids = module.duree_prevue_heures or Decimal('1')
        if poids <= 0:
            poids = Decimal('1')
        somme += Decimal(str(moyenne)) * poids
        total_poids += poids

    if total_poids > 0:
        return round(float(somme / total_poids), 2)
    return None


def calculer_presence_formation(participant, formation):
    """Temps de cours effectué / prévu sur l'ensemble des modules de la formation."""
    modules = Module.objects.filter(formation=formation)
    total_presence = 0.0
    total_prevu = 0.0
    for module in modules:
        hp, hprev, _ = calculer_presence_module(module, participant)
        total_presence += hp
        total_prevu += hprev
    taux = None
    if total_prevu > 0:
        taux = round((total_presence / total_prevu) * 100, 2)
    return round(total_presence, 2), round(total_prevu, 2), taux


def _mention_pour_moyenne(moyenne, params):
    if moyenne is None:
        return ''
    m = float(moyenne)
    if m >= params['seuil_mention_tres_bien']:
        return DecisionPedagogique.Mention.TRES_BIEN
    if m >= params['seuil_mention_bien']:
        return DecisionPedagogique.Mention.BIEN
    if m >= params['seuil_admission']:
        return DecisionPedagogique.Mention.ASSEZ_BIEN
    return DecisionPedagogique.Mention.PASSABLE


def calculer_decision(participant, formation, generer_auto=True):
    """
    Décision automatique :
    - ADMIS : moyenne ≥ 12/20 ET temps effectué ≥ 80 % du temps prévu
    - EXCLUSION : moyenne < 8 ou taux < 50 %
    - AJOURNE : sinon
    - EN_ATTENTE : données insuffisantes
    """
    params = _get_parametres(formation)

    for module in Module.objects.filter(formation=formation):
        calculer_moyenne_module(module, participant)

    moyenne = calculer_moyenne_generale(participant, formation)
    heures_presence, heures_prevues, taux_presence = calculer_presence_formation(
        participant, formation,
    )

    decision_obj, _ = DecisionPedagogique.objects.get_or_create(
        participant=participant,
        formation=formation,
        defaults={'generee_auto': generer_auto},
    )

    if decision_obj.validee_le and not generer_auto:
        return decision_obj

    decision_obj.moyenne_generale = moyenne
    decision_obj.taux_presence = taux_presence
    decision_obj.total_heures_presence = heures_presence
    decision_obj.total_heures_prevues = heures_prevues
    decision_obj.generee_auto = generer_auto
    decision_obj.criteres_appliques = params

    if moyenne is None or taux_presence is None:
        decision_obj.decision = DecisionPedagogique.TypeDecision.EN_ATTENTE
        decision_obj.mention = ''
    elif est_admissible(moyenne, taux_presence, params):
        decision_obj.decision = DecisionPedagogique.TypeDecision.ADMIS
        decision_obj.mention = _mention_pour_moyenne(moyenne, params)
    elif float(moyenne) < 8 or float(taux_presence) < 50:
        decision_obj.decision = DecisionPedagogique.TypeDecision.EXCLUSION
        decision_obj.mention = ''
    else:
        decision_obj.decision = DecisionPedagogique.TypeDecision.AJOURNE
        decision_obj.mention = ''

    decision_obj.save()
    return decision_obj


def calculer_decisions_formation(formation):
    """Recalcule les décisions de tous les auditeurs inscrits à au moins un module."""
    participant_ids = ModuleParticipant.objects.filter(
        module__formation=formation,
    ).values_list('participant_id', flat=True).distinct()
    return [
        calculer_decision(Participant.objects.get(pk=pid), formation)
        for pid in participant_ids
    ]


def resume_module_participant(module, participant):
    """Résumé calculé pour affichage (notes + assiduité + admissibilité)."""
    params = _get_parametres(module.formation)
    moyenne, nb_notes = calculer_moyenne_notes_module(module, participant)
    hp, hprev, taux = calculer_presence_module(module, participant)
    return {
        'moyenne': moyenne,
        'nb_notes': nb_notes,
        'heures_presence': hp,
        'heures_prevues': hprev,
        'taux_presence': taux,
        'admissible': est_admissible(moyenne, taux, params),
        'criteres': params,
    }
