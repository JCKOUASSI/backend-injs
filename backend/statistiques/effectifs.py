"""
Calculs d'effectifs — source unique pour le module Statistiques.

Règles alignées sur l'écran Présences (ModuleDetail) et le point journalier :
- Attendu : auditeur inscrit au module (ModuleParticipant).
- Séance comptabilisable : date atteinte (EDT / import), officiellement terminée,
  ou avec au moins une présence enregistrée.
- Présent : pointage entrée sur la séance, hors ABSENT_NON_BADGE, et
  (encore en salle OU sortie avec durée > 0).
- Absent : inscrit sans présence valide sur la séance (agrégats : non présent sur
  au moins une séance du périmètre, ou créneau sans badge présent).
- Auditeur notoire : inscrit au périmètre sans aucun pointage, ou motif_notoire renseigné.
"""
from collections import defaultdict
from datetime import date

from django.db.models import Q, Exists, OuterRef

from formations.models import ModuleParticipant, SessionModule, Participant
from presences.models import Pointage


def q_pointage_present():
    """Filtre ORM : pointage compté comme présence valide."""
    return (
        Q(participant__isnull=False)
        & ~Q(statut=Pointage.Statut.ABSENT_NON_BADGE)
        & (
            Q(timestamp_entree__isnull=False, timestamp_sortie__isnull=True)
            | Q(timestamp_sortie__isnull=False, duree_presence_minutes__gt=0)
        )
    )


def filter_sessions(
    module_ids=None,
    session_ids=None,
    annee=None,
    mois=None,
    calendrier=None,
    date_debut=None,
    date_fin=None,
    *,
    seulement_terminees=True,
):
    """
    Séances comptabilisables du périmètre (aligné point journalier / EDT importé).

    Règle : date atteinte (``date_journee <= today``), séance officiellement terminée,
    ou au moins une présence valide enregistrée — sans exiger ``demarree_le`` (import EDT).
    """
    qs = SessionModule.objects.all()
    if seulement_terminees:
        today = date.today()
        present_sur_seance = Pointage.objects.filter(
            session_id=OuterRef('pk'),
        ).filter(q_pointage_present())
        qs = qs.filter(
            Q(date_journee__lte=today)
            | Q(terminee_le__isnull=False)
            | Exists(present_sur_seance),
        )
    if session_ids is not None:
        qs = qs.filter(id__in=session_ids)
    if module_ids is not None:
        qs = qs.filter(module_id__in=module_ids)
    if calendrier:
        try:
            d = date.fromisoformat(str(calendrier))
            qs = qs.filter(date_journee=d)
        except ValueError:
            pass
    else:
        if annee:
            qs = qs.filter(date_journee__year=annee)
        if mois:
            qs = qs.filter(date_journee__month=mois)
    if date_debut:
        qs = qs.filter(date_journee__gte=date_debut)
    if date_fin:
        qs = qs.filter(date_journee__lte=date_fin)
    return qs


def _module_participant_qs(
    module_ids=None,
    formation_id=None,
    secretariat_id=None,
    grade=None,
    categorie=None,
):
    q = ModuleParticipant.objects.all()
    if module_ids is not None:
        q = q.filter(module_id__in=module_ids)
    if formation_id:
        q = q.filter(module__formation_id=formation_id)
    if secretariat_id:
        q = q.filter(module__secretariat_id=secretariat_id)
    if grade:
        q = q.filter(module__grade=grade)
    if categorie and categorie != '—':
        q = q.filter(participant__categorie__iexact=categorie)
    return q


def participant_ids_inscrits(
    module_ids=None,
    formation_id=None,
    secretariat_id=None,
    grade=None,
    categorie=None,
):
    """IDs des auditeurs inscrits au périmètre."""
    return set(
        _module_participant_qs(
            module_ids, formation_id, secretariat_id, grade, categorie,
        ).values_list('participant_id', flat=True).distinct()
    )


def participant_ids_notoires(
    module_ids=None,
    formation_id=None,
    secretariat_id=None,
    grade=None,
    categorie=None,
):
    """
    Auditeurs notoires : inscrits sans aucun pointage, ou avec motif_notoire renseigné.
    Source unique pour dashboard, bilans et Bilan FAC.
    """
    inscrits = participant_ids_inscrits(
        module_ids, formation_id, secretariat_id, grade, categorie,
    )
    if not inscrits:
        return set()
    avec_pointage = set(
        Pointage.objects.filter(participant_id__in=inscrits)
        .values_list('participant_id', flat=True)
        .distinct()
    )
    jamais_badge = inscrits - avec_pointage
    motif_ids = set(
        Participant.objects.filter(id__in=inscrits)
        .exclude(motif_notoire='')
        .values_list('id', flat=True)
    )
    return jamais_badge | motif_ids


def count_auditeurs_notoires(
    module_ids=None,
    formation_id=None,
    secretariat_id=None,
    grade=None,
    categorie=None,
):
    return len(participant_ids_notoires(
        module_ids, formation_id, secretariat_id, grade, categorie,
    ))


def session_ids_for_scope(
    module_ids, annee=None, mois=None, calendrier=None, date_debut=None, date_fin=None,
):
    if not module_ids:
        return []
    return list(
        filter_sessions(
            module_ids=module_ids,
            annee=annee,
            mois=mois,
            calendrier=calendrier,
            date_debut=date_debut,
            date_fin=date_fin,
        ).values_list('id', flat=True)
    )


def count_sessions_comptabilisables(
    module_ids=None,
    annee=None,
    mois=None,
    calendrier=None,
    date_debut=None,
    date_fin=None,
):
    """Nombre de séances comptabilisables (KPI, pédagogique, admin — même règle)."""
    return filter_sessions(
        module_ids=module_ids,
        annee=annee,
        mois=mois,
        calendrier=calendrier,
        date_debut=date_debut,
        date_fin=date_fin,
    ).count()


def participants_par_module(module_ids, categorie=None):
    """{module_id: {participant_id: Participant}}"""
    mq = ModuleParticipant.objects.filter(module_id__in=module_ids).select_related('participant')
    if categorie and categorie != '—':
        mq = mq.filter(participant__categorie__iexact=categorie)
    out = defaultdict(dict)
    for mp in mq:
        out[mp.module_id][mp.participant_id] = mp.participant
    return out


def presents_par_session(session_ids):
    """{session_id: set(participant_id)} pour les présences valides."""
    result = defaultdict(set)
    if not session_ids:
        return result
    for sid, pid in Pointage.objects.filter(
        session_id__in=session_ids,
    ).filter(q_pointage_present()).values_list('session_id', 'participant_id'):
        result[sid].add(pid)
    return result


def repartition_hf(participants_dict, participant_ids=None):
    """Compte H/F sur un ensemble de participants (dict id -> Participant)."""
    pids = participant_ids if participant_ids is not None else participants_dict.keys()
    masculin = feminin = 0
    for pid in pids:
        p = participants_dict.get(pid)
        if not p:
            continue
        if p.sexe == Participant.Sexe.MASCULIN:
            masculin += 1
        elif p.sexe == Participant.Sexe.FEMININ:
            feminin += 1
    return masculin, feminin


def stats_creneau_module(participant_ids, sessions, presents_by_session):
    """
    Effectifs pour un module sur un créneau (une ou plusieurs séances terminées).
    participant_ids : set des inscrits.
    """
    effectif = len(participant_ids)
    if not sessions or effectif == 0:
        return {
            'effectif': effectif,
            'presents': 0,
            'absents': effectif,
            'taux_presence': 0.0,
            'taux_absence': 1.0 if effectif else 0.0,
            'actif': bool(sessions),
        }

    presents = {
        pid for s in sessions for pid in presents_by_session.get(s.id, set())
        if pid in participant_ids
    }
    nb_presents = len(presents)
    absents = max(effectif - nb_presents, 0)
    return {
        'effectif': effectif,
        'presents': nb_presents,
        'absents': absents,
        'taux_presence': round(nb_presents / effectif, 4) if effectif else 0.0,
        'taux_absence': round(absents / effectif, 4) if effectif else 0.0,
        'actif': True,
    }


def effectifs_tableau_agrege(participants, session_ids, module_ids):
    """
    Bilan effectifs module / catégorie :
    auditeurs inscrits, présents (≥1 séance terminée), absents, H/F inscrits et H/F présents.
    """
    participants = participants or {}
    effectif_total = len(participants)
    session_ids = session_ids or []
    module_ids = module_ids or []

    if not effectif_total:
        return _empty_effectifs_tableau()

    if not session_ids and module_ids:
        session_ids = session_ids_for_scope(module_ids)

    present_pids = set()
    if session_ids:
        for pids in presents_par_session(session_ids).values():
            present_pids |= pids
        present_pids &= set(participants.keys())

    effectif_presents = len(present_pids)
    absents = max(effectif_total - effectif_presents, 0)

    m_insc, f_insc = repartition_hf(participants)
    m_pres, f_pres = repartition_hf(participants, present_pids)

    return {
        'effectifs_auditeurs': effectif_total,
        'effectifs_presents': effectif_presents,
        'pct_presents_total': _pct(effectif_presents, effectif_total),
        'masculin_inscrits': m_insc,
        'feminin_inscrits': f_insc,
        'pct_masculin_inscrits': _pct(m_insc, effectif_total),
        'pct_feminin_inscrits': _pct(f_insc, effectif_total),
        'masculin': m_pres,
        'feminin': f_pres,
        'pct_masculin_presents': _pct(m_pres, effectif_presents),
        'pct_feminin_presents': _pct(f_pres, effectif_presents),
        'absents': absents,
        'pct_absents_total': _pct(absents, effectif_total),
        'nb_seances_terminees': len(session_ids),
    }


def aggregation_seances_modules(module_ids, session_ids=None, categorie=None):
    """
    Agrégation fine : places séance (inscrits × séances) et présences par séance.
    Utile pour les KPI globaux (taux réel de présence).
    """
    module_ids = list(module_ids or [])
    if not module_ids:
        return {
            'inscrits_distinct': 0,
            'presents_distinct': 0,
            'absents_distinct': 0,
            'places_attendues': 0,
            'places_presentes': 0,
            'places_absentes': 0,
            'nb_seances_terminees': 0,
        }

    par_mod = participants_par_module(module_ids, categorie)
    inscrits_distinct = {pid for mod in par_mod.values() for pid in mod}
    if session_ids is None:
        session_ids = session_ids_for_scope(module_ids)
    sessions = list(
        SessionModule.objects.filter(id__in=session_ids).values_list('id', 'module_id')
    )
    presents_map = presents_par_session(session_ids)

    places_attendues = 0
    places_presentes = 0
    present_any = set()

    for sid, mid in sessions:
        pids_mod = set(par_mod.get(mid, {}))
        places_attendues += len(pids_mod)
        pres = presents_map.get(sid, set()) & pids_mod
        places_presentes += len(pres)
        present_any |= pres

    presents_distinct = len(present_any & inscrits_distinct)
    inscrits_n = len(inscrits_distinct)

    return {
        'inscrits_distinct': inscrits_n,
        'presents_distinct': presents_distinct,
        'absents_distinct': max(inscrits_n - presents_distinct, 0),
        'places_attendues': places_attendues,
        'places_presentes': places_presentes,
        'places_absentes': max(places_attendues - places_presentes, 0),
        'nb_seances_terminees': len(sessions),
    }


def _pct(num, den, decimals=2):
    return round(num / den * 100, decimals) if den else 0.0


def _empty_effectifs_tableau():
    return {
        'effectifs_auditeurs': 0,
        'effectifs_presents': 0,
        'pct_presents_total': 0.0,
        'masculin_inscrits': 0,
        'feminin_inscrits': 0,
        'pct_masculin_inscrits': 0.0,
        'pct_feminin_inscrits': 0.0,
        'masculin': 0,
        'feminin': 0,
        'pct_masculin_presents': 0.0,
        'pct_feminin_presents': 0.0,
        'absents': 0,
        'pct_absents_total': 0.0,
        'nb_seances_terminees': 0,
    }
