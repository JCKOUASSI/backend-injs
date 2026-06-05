"""
Point journalier — format CPFAE (fichiers « POINT JOURNALIER CAT … »).

Optimisé : pré-chargement bulk des séances, inscriptions et pointages
pour éviter les requêtes N+1 sur les filtres larges (année entière, etc.).
"""
from collections import defaultdict
from datetime import date

from django.db.models import Q

from formations.models import Formation, Module, ModuleParticipant, SessionModule, RefCategorie, Participant
from presences.models import Pointage

from .effectifs import filter_sessions, presents_par_session, stats_creneau_module

MOIS_FR = [
    '', 'JANVIER', 'FÉVRIER', 'MARS', 'AVRIL', 'MAI', 'JUIN',
    'JUILLET', 'AOÛT', 'SEPTEMBRE', 'OCTOBRE', 'NOVEMBRE', 'DÉCEMBRE',
]

MAX_GROUP_COLS = 17
ORGANISME_DEFAULT = 'CPFAE'
DEFAULT_HORAIRES = {'MATIN': '08H00-12H00', 'SOIR': '13H00-17H00'}


def _creneau(session):
    label = (session.intitule or '').lower()
    if any(k in label for k in ('matin', 'mat ', 'mat.')):
        return 'MATIN'
    if any(k in label for k in ('soir', 'après-midi', 'apres-midi', 'après midi', 'apres midi', 'pm')):
        return 'SOIR'
    if session.heure_debut_prevue:
        return 'MATIN' if session.heure_debut_prevue.hour < 13 else 'SOIR'
    return 'MATIN' if (session.numero or 1) <= 1 else 'SOIR'


def _fmt_heure(t):
    if not t:
        return None
    return f"{t.hour:02d}H{t.minute:02d}"


def _horaire_creneau(sessions, creneau):
    filtered = [s for s in sessions if _creneau(s) == creneau]
    if not filtered:
        return DEFAULT_HORAIRES.get(creneau, '—')
    starts = [s.heure_debut_prevue for s in filtered if s.heure_debut_prevue]
    ends = [s.heure_fin_prevue for s in filtered if s.heure_fin_prevue]
    if starts and ends:
        return f"{_fmt_heure(min(starts))}-{_fmt_heure(max(ends))}"
    if starts:
        h = _fmt_heure(starts[0])
        default_end = DEFAULT_HORAIRES.get(creneau, '').split('-')[-1]
        return f"{h}-{default_end}" if default_end else h
    return DEFAULT_HORAIRES.get(creneau, creneau)


def _group_label(module, multi_grade):
    g = (module.groupe or '').strip()
    gr = (module.grade or '').strip()
    if multi_grade and gr and g:
        g_short = g.replace('GROUPE ', 'G').replace('Groupe ', 'G')
        return f"{gr}-{g_short}" if not g.startswith(gr) else g_short or f"{gr}-{g}"
    if g:
        return g.replace('GROUPE ', 'G').replace('Groupe ', 'G')
    if gr:
        return gr
    return module.intitule[:20] if module.intitule else f"Module {module.id}"


def _salle_label(module):
    return (module.salle or module.batiment or '').strip() or '—'


def _titre_ligne1(formation):
    formation_upper = formation.formation.upper()
    if 'ADMINISTRATION DE BASE' in formation_upper or 'FAB' in formation_upper:
        return 'FORMATION EN ADMINISTRATION DE BASE_POINT DES PRÉSENCES_CPFAE'
    return f"{formation_upper}_POINT DES PRÉSENCES_CPFAE"


def _jours_activite(annee, mois=None, formation_id=None, secretariat_id=None):
    sm_q = filter_sessions(seulement_terminees=True).filter(date_journee__year=annee)
    if mois:
        sm_q = sm_q.filter(date_journee__month=mois)
    if formation_id:
        sm_q = sm_q.filter(module__formation_id=formation_id)
    if secretariat_id:
        sm_q = sm_q.filter(module__secretariat_id=secretariat_id)
    today = date.today()
    dates = sorted(set(sm_q.values_list('date_journee', flat=True)))
    return [d for d in dates if d <= today]


def _liste_categories(formation_id=None, secretariat_id=None):
    cats = set(RefCategorie.objects.filter(actif=True).values_list('libelle', flat=True))
    pq = Participant.objects.exclude(categorie='')
    if secretariat_id:
        pq = pq.filter(secretariat_id=secretariat_id)
    if formation_id:
        pq = pq.filter(modules_inscrits__module__formation_id=formation_id).distinct()
    cats.update(pq.values_list('categorie', flat=True))
    return sorted(cats, key=lambda c: (len(c), c))


def _categories_pour_formation(formation_id, secretariat_id=None, cache=None):
    if cache and formation_id in cache['cats_by_formation']:
        return cache['cats_by_formation'][formation_id]
    mq = {'module__formation_id': formation_id}
    if secretariat_id:
        mq['module__secretariat_id'] = secretariat_id
    cats = sorted(set(
        ModuleParticipant.objects.filter(**mq)
        .exclude(participant__categorie='')
        .values_list('participant__categorie', flat=True)
    ))
    return cats


def _formation_ids_for_scope(annee, mois, formation_id, secretariat_id):
    if formation_id:
        return [formation_id]
    fq = Formation.objects.filter(
        modules__sessions__date_journee__year=annee,
    )
    if mois:
        fq = fq.filter(modules__sessions__date_journee__month=mois)
    if secretariat_id:
        fq = fq.filter(modules__secretariat_id=secretariat_id)
    return list(fq.distinct().values_list('id', flat=True))


def _build_pj_cache(annee, mois, formation_ids, jours, secretariat_id=None):
    """Pré-charge modules, séances, inscriptions et pointages pour la période."""
    cache = {
        'formations': {},
        'modules_by_formation': defaultdict(list),
        'modules': {},
        'sessions_by_mod_day': defaultdict(list),
        'all_sessions_by_mod_day': defaultdict(list),
        'participants_by_mod': defaultdict(set),
        'participants_by_mod_cat': defaultdict(set),
        'participant_cat': {},
        'presents_by_session': defaultdict(set),
        'cats_by_formation': defaultdict(list),
    }

    if not formation_ids or not jours:
        return cache

    formations = Formation.objects.filter(id__in=formation_ids)
    cache['formations'] = {f.id: f for f in formations}

    mq = Q(formation_id__in=formation_ids)
    if secretariat_id:
        mq &= Q(secretariat_id=secretariat_id)

    modules = list(Module.objects.filter(mq).order_by('formation_id', 'grade', 'groupe', 'ordre', 'intitule'))
    module_ids = []
    for mod in modules:
        cache['modules'][mod.id] = mod
        cache['modules_by_formation'][mod.formation_id].append(mod)
        module_ids.append(mod.id)

    if not module_ids:
        return cache

    mp_rows = ModuleParticipant.objects.filter(module_id__in=module_ids).values_list(
        'module_id', 'participant_id', 'participant__categorie',
    )
    for mod_id, pid, cat in mp_rows:
        cache['participants_by_mod'][mod_id].add(pid)
        c = (cat or '').strip()
        cache['participant_cat'][pid] = c
        if c:
            cache['participants_by_mod_cat'][(mod_id, c.upper())].add(pid)

    sessions = list(
        filter_sessions(module_ids=module_ids, seulement_terminees=True).filter(
            date_journee__in=jours,
        )
    )
    session_ids = []
    for sess in sessions:
        key = (sess.module_id, sess.date_journee)
        cache['all_sessions_by_mod_day'][key].append(sess)
        session_ids.append(sess.id)

    for sid, pids in presents_par_session(session_ids).items():
        cache['presents_by_session'][sid] = pids

    for fid in formation_ids:
        mod_ids = [m.id for m in cache['modules_by_formation'][fid]]
        cats = set()
        for mid in mod_ids:
            for pid in cache['participants_by_mod'][mid]:
                c = cache['participant_cat'].get(pid, '')
                if c:
                    cats.add(c)
        cache['cats_by_formation'][fid] = sorted(cats)

    return cache


def _stats_groupe_cached(module, jour, creneau, categorie, cache):
    if categorie and categorie != '—':
        participant_ids = cache['participants_by_mod_cat'].get(
            (module.id, categorie.upper()), set(),
        )
        if not participant_ids:
            # fallback case-insensitive
            participant_ids = {
                pid for pid in cache['participants_by_mod'][module.id]
                if cache['participant_cat'].get(pid, '').upper() == categorie.upper()
            }
    else:
        participant_ids = cache['participants_by_mod'][module.id]

    effectif = len(participant_ids)
    sessions = [
        s for s in cache['all_sessions_by_mod_day'].get((module.id, jour), [])
        if _creneau(s) == creneau
    ]

    return stats_creneau_module(
        participant_ids,
        sessions,
        cache['presents_by_session'],
    )


def _aggregate_total(groupes):
    effectif = sum(g['effectif'] for g in groupes)
    presents = sum(g['presents'] for g in groupes)
    absents = sum(g['absents'] for g in groupes)
    return {
        'effectif': effectif,
        'presents': presents,
        'absents': absents,
        'taux_presence': round(presents / effectif, 4) if effectif else 0.0,
        'taux_absence': round(absents / effectif, 4) if effectif else 0.0,
    }


def _bloc_creneau_cached(modules, jour, creneau, categorie, multi_grade, all_sessions, cache):
    groupes = []
    for mod in modules:
        stats = _stats_groupe_cached(mod, jour, creneau, categorie, cache)
        if stats['effectif'] == 0:
            continue
        groupes.append({
            'module_id': mod.id,
            'label': _group_label(mod, multi_grade),
            'salle': _salle_label(mod),
            **stats,
        })
    return {
        'horaire': _horaire_creneau(all_sessions, creneau),
        'groupes': groupes,
        'total': _aggregate_total(groupes),
    }


def _modules_for_tableau(formation, categorie, cache, secretariat_id=None):
    modules = list(cache['modules_by_formation'].get(formation.id, []))
    if not modules:
        return [], False

    if categorie and categorie != '—':
        mod_ids = {
            mid for (mid, cat), pids in cache['participants_by_mod_cat'].items()
            if cat.upper() == categorie.upper() and pids
        }
        modules = [m for m in modules if m.id in mod_ids]
    else:
        mod_ids = {m.id for m in modules if cache['participants_by_mod'][m.id]}
        modules = [m for m in modules if m.id in mod_ids]

    if not modules:
        return [], False

    grades = {m.grade for m in modules if m.grade}
    return modules, len(grades) > 1


def _compute_tableau_cached(formation, categorie, jour, cache, secretariat_id=None,
                            full_detail=True, organisme=ORGANISME_DEFAULT):
    modules, multi_grade = _modules_for_tableau(formation, categorie, cache, secretariat_id)
    if not modules:
        return None

    all_sessions = []
    for mod in modules:
        all_sessions.extend(cache['all_sessions_by_mod_day'].get((mod.id, jour), []))
    if not all_sessions:
        return None

    matin = _bloc_creneau_cached(modules, jour, 'MATIN', categorie, multi_grade, all_sessions, cache)
    soir = _bloc_creneau_cached(modules, jour, 'SOIR', categorie, multi_grade, all_sessions, cache)

    if not matin['groupes'] and not soir['groupes']:
        return None

    taux_presence_jour = round(
        (matin['total']['taux_presence'] + soir['total']['taux_presence']) / 2, 4
    ) if (matin['total']['effectif'] or soir['total']['effectif']) else 0.0
    taux_absence_jour = round(
        (matin['total']['taux_absence'] + soir['total']['taux_absence']) / 2, 4
    ) if (matin['total']['effectif'] or soir['total']['effectif']) else 0.0

    base = {
        'id': f"{formation.id}-{categorie}-{jour.isoformat()}",
        'categorie': categorie,
        'formation_id': formation.id,
        'formation': str(formation),
        'date': jour.isoformat(),
        'date_fr': jour.strftime('%d/%m/%Y'),
        'jour': jour.day,
        'mois': jour.month,
        'mois_libelle': MOIS_FR[jour.month],
        'annee': jour.year,
        'organisme': organisme,
        'titre_ligne1': _titre_ligne1(formation),
        'titre': f"POINT JOURNALIER CAT {categorie} — {formation.formation} — {jour.strftime('%d/%m/%Y')}",
        'taux_presence_jour': taux_presence_jour,
        'taux_absence_jour': taux_absence_jour,
        'matin_horaire': matin['horaire'],
        'soir_horaire': soir['horaire'],
    }

    if not full_detail:
        return base

    base['matin'] = matin
    base['soir'] = soir
    return base


def compute_tableau_jour(formation, categorie, jour, secretariat_id=None, organisme=ORGANISME_DEFAULT):
    """Construit un point journalier complet pour UNE journée (exports / détail)."""
    cache = _build_pj_cache(
        jour.year, jour.month, [formation.id], [jour], secretariat_id=secretariat_id,
    )
    if isinstance(formation, int):
        formation = cache['formations'].get(formation) or Formation.objects.get(pk=formation)
    return _compute_tableau_cached(
        formation, categorie, jour, cache,
        secretariat_id=secretariat_id, full_detail=True, organisme=organisme,
    )


def get_tableau_detail(annee, formation_id, categorie, jour, secretariat_id=None):
    """Retourne un seul tableau complet (lazy load côté frontend)."""
    if isinstance(jour, str):
        jour = date.fromisoformat(jour)
    cache = _build_pj_cache(annee, jour.month, [formation_id], [jour], secretariat_id=secretariat_id)
    formation = cache['formations'].get(formation_id)
    if not formation:
        try:
            formation = Formation.objects.get(pk=formation_id)
        except Formation.DoesNotExist:
            return None
    return _compute_tableau_cached(
        formation, categorie, jour, cache,
        secretariat_id=secretariat_id, full_detail=True,
    )


def compute_point_journalier(
    annee=None,
    mois=None,
    categorie=None,
    formation_id=None,
    secretariat_id=None,
    jour=None,
    index_only=False,
):
    """
    Retourne les tableaux journaliers (1 par jour × catégorie × formation).
    index_only=True : métadonnées légères pour la liste (sans blocs MATIN/SOIR).
    """
    annee = annee or date.today().year

    if jour:
        try:
            if isinstance(jour, str):
                jour = date.fromisoformat(jour)
        except ValueError:
            jour = None

    jours = [jour] if jour else _jours_activite(annee, mois, formation_id, secretariat_id)
    formation_ids = _formation_ids_for_scope(annee, mois, formation_id, secretariat_id)

    cache = _build_pj_cache(annee, mois, formation_ids, jours, secretariat_id=secretariat_id)

    tableaux = []
    for fid in formation_ids:
        formation = cache['formations'].get(fid)
        if not formation:
            continue

        cats = [categorie] if categorie else _categories_pour_formation(fid, secretariat_id, cache)
        if not cats:
            cats = ['—']

        for cat in cats:
            for j in jours:
                tb = _compute_tableau_cached(
                    formation, cat, j, cache, secretariat_id=secretariat_id,
                    full_detail=not index_only,
                )
                if tb:
                    tableaux.append(tb)

    tableaux.sort(key=lambda t: (t['date'], t['categorie'], t['formation_id']))

    categories_avec_donnees = sorted({t['categorie'] for t in tableaux})
    categories = _liste_categories(formation_id, secretariat_id)
    formations_idx = {t['formation_id']: t['formation'] for t in tableaux}

    sm_q = SessionModule.objects.filter(
        date_journee__year=annee, date_journee__lte=date.today(),
    )
    if formation_id:
        sm_q = sm_q.filter(module__formation_id=formation_id)
    if secretariat_id:
        sm_q = sm_q.filter(module__secretariat_id=secretariat_id)
    mois_avec_donnees = sorted(set(sm_q.values_list('date_journee__month', flat=True)))

    return {
        'annee': annee,
        'mois': mois,
        'tableaux': tableaux,
        'total_tableaux': len(tableaux),
        'categories': categories,
        'categories_avec_donnees': categories_avec_donnees,
        'mois_avec_donnees': mois_avec_donnees,
        'formations': [{'id': k, 'formation': v} for k, v in sorted(formations_idx.items())],
    }


PJ_META_KEYS = (
    'id', 'categorie', 'formation_id', 'formation', 'date', 'date_fr', 'jour', 'mois',
    'mois_libelle', 'annee', 'organisme', 'titre_ligne1', 'titre',
    'taux_presence_jour', 'taux_absence_jour', 'matin_horaire', 'soir_horaire',
)


def compute_point_journalier_avec_tableaux(
    annee=None,
    mois=None,
    categorie=None,
    formation_id=None,
    secretariat_id=None,
):
    """Index léger + tous les tableaux complets (vue d'ensemble Point Journalier)."""
    data = compute_point_journalier(
        annee=annee,
        mois=mois,
        categorie=categorie,
        formation_id=formation_id,
        secretariat_id=secretariat_id,
        index_only=False,
    )
    tableaux_complets = []
    tableaux_index = []
    for tb in data['tableaux']:
        meta = {k: tb[k] for k in PJ_META_KEYS if k in tb}
        tableaux_complets.append({
            'tableau_id': tb['id'],
            'meta': meta,
            'tableau': tb,
        })
        tableaux_index.append(meta)
    data['tableaux'] = tableaux_index
    data['tableaux_complets'] = tableaux_complets
    return data
