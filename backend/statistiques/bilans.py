"""
Bilans & Rapports — index par Module, Catégorie ou Formation.

Structure préparée pour accueillir les tableaux CPFAE fournis progressivement.
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.db.models import Q

from formations.models import Formation, Module, RefCategorie, Participant, ModuleParticipant, SessionModule
from presences.models import Pointage

from .effectifs import effectifs_tableau_agrege, session_ids_for_scope

User = get_user_model()

JUSTIFICATIFS_ABSENCES = [
    'Report de formation',
    'Injoignable',
    'Déficit d\'information',
    'Maladie',
    'Accouchement',
]

PERIODES_BILAN = [
    ('QUOTIDIEN', 'Quotidien'),
    ('HEBDOMADAIRE', 'Hebdomadaire'),
    ('MENSUEL', 'Mensuel'),
    ('TRIMESTRIEL', 'Trimestriel'),
    ('SEMESTRIEL', 'Semestriel'),
    ('ANNUEL', 'Annuel'),
    ('MI_PARCOURS', 'À mi-parcours'),
]


def _liste_categories(formation_id=None, secretariat_id=None):
    cats = set(RefCategorie.objects.filter(actif=True).values_list('libelle', flat=True))
    pq = Participant.objects.exclude(categorie='')
    if secretariat_id:
        pq = pq.filter(secretariat_id=secretariat_id)
    if formation_id:
        pq = pq.filter(modules_inscrits__module__formation_id=formation_id).distinct()
    cats.update(pq.values_list('categorie', flat=True))
    return sorted(cats, key=lambda c: (len(c), c))


def _modules_queryset(formation_id=None, secretariat_id=None, categorie=None, module_id=None):
    mq = Q()
    if formation_id:
        mq &= Q(formation_id=formation_id)
    if secretariat_id:
        mq &= Q(secretariat_id=secretariat_id)
    if module_id:
        mq &= Q(id=module_id)
    qs = Module.objects.filter(mq).select_related('formation').order_by(
        'formation__formation', 'grade', 'groupe', 'ordre', 'intitule',
    )
    if categorie:
        qs = qs.filter(
            module_participants__participant__categorie__iexact=categorie,
        ).distinct()
    return qs


def _formations_queryset(formation_id=None, secretariat_id=None):
    fq = Formation.objects.all()
    if formation_id:
        fq = fq.filter(id=formation_id)
    if secretariat_id:
        fq = fq.filter(modules__secretariat_id=secretariat_id).distinct()
    return fq.order_by('formation')


def _pct(num, den, decimals=2):
    return round(num / den * 100, decimals) if den else 0.0


def _session_ids_module(module_id, annee=None, mois=None, calendrier=None):
    return session_ids_for_scope([module_id], annee, mois, calendrier)


def _session_ids_modules(module_ids, annee=None, mois=None, calendrier=None):
    return session_ids_for_scope(module_ids, annee, mois, calendrier)


def _effectifs_tableau(participants, session_ids, module_ids):
    """Calcule auditeurs inscrits, présents/absents et H/F (inscrits + présents) sur séances terminées."""
    return effectifs_tableau_agrege(participants, session_ids, module_ids)


def compute_bilan_effectifs_module(
    module_id,
    categorie=None,
    annee=None,
    mois=None,
    calendrier=None,
    periode=None,
):
    """
    Tableau CPFAE « Bilan des effectifs module » :
    auditeurs, présents, répartition H/F, absents + pourcentages.
    """
    try:
        module = Module.objects.select_related('formation').get(pk=module_id)
    except Module.DoesNotExist:
        return None

    mp_qs = ModuleParticipant.objects.filter(module=module).select_related('participant')
    if categorie and categorie != '—':
        mp_qs = mp_qs.filter(participant__categorie__iexact=categorie)

    participants = {mp.participant_id: mp.participant for mp in mp_qs}
    session_ids = _session_ids_module(module_id, annee, mois, calendrier)
    stats = _effectifs_tableau(participants, session_ids, [module_id])

    module_nom = (module.intitule or f'Module {module.id}').strip().upper()

    return {
        'type': 'effectifs_module',
        'titre': f'BILAN DES EFFECTIFS MODULE {module_nom}',
        'module_id': module.id,
        'module': module.intitule,
        'formation': str(module.formation),
        **stats,
        'periode_label': dict(PERIODES_BILAN).get(periode, '') if periode else '',
    }


def compute_bilan_effectifs_categorie(
    categorie,
    formation_id=None,
    secretariat_id=None,
    annee=None,
    mois=None,
    calendrier=None,
    periode=None,
):
    """
    Tableau CPFAE « Bilan des effectifs catégorie » :
    auditeurs, présents, répartition H/F, absents + pourcentages.
    """
    if not categorie or categorie == '—':
        return None

    cat_label = categorie.strip().upper()
    mq = Module.objects.all()
    if formation_id:
        mq = mq.filter(formation_id=formation_id)
    if secretariat_id:
        mq = mq.filter(secretariat_id=secretariat_id)
    module_ids = list(
        mq.filter(
            module_participants__participant__categorie__iexact=categorie,
        ).distinct().values_list('id', flat=True)
    )

    mp_qs = ModuleParticipant.objects.filter(
        module_id__in=module_ids,
        participant__categorie__iexact=categorie,
    ).select_related('participant')
    participants = {mp.participant_id: mp.participant for mp in mp_qs}

    session_ids = _session_ids_modules(module_ids, annee, mois, calendrier)
    stats = _effectifs_tableau(participants, session_ids, module_ids)

    return {
        'type': 'effectifs_categorie',
        'titre': f'BILAN DES EFFECTIFS CATEGORIE ({cat_label})',
        'categorie': categorie,
        **stats,
        'periode_label': dict(PERIODES_BILAN).get(periode, '') if periode else '',
    }


def _date_inscrits_label(calendrier=None):
    if calendrier:
        try:
            return date.fromisoformat(str(calendrier)).strftime('%d/%m/%Y')
        except ValueError:
            pass
    return date.today().strftime('%d/%m/%Y')


def _modules_formation_categorie(formation_id, categorie, grade=None, secretariat_id=None):
    mq = Module.objects.filter(formation_id=formation_id)
    if secretariat_id:
        mq = mq.filter(secretariat_id=secretariat_id)
    if grade:
        mq = mq.filter(grade=grade)
    return mq.filter(
        module_participants__participant__categorie__iexact=categorie,
    ).distinct()


def _stats_ligne_formation(formation_id, categorie, grade, secretariat_id, annee, mois, calendrier):
    mq = _modules_formation_categorie(formation_id, categorie, grade, secretariat_id)
    module_ids = list(mq.values_list('id', flat=True))

    nb_groupes = mq.exclude(groupe='').values('groupe').distinct().count()
    if not nb_groupes and module_ids:
        nb_groupes = len(module_ids)

    nb_encadrants = mq.exclude(superviseur=None).values('superviseur').distinct().count()

    sec_ids = mq.exclude(secretariat=None).values_list('secretariat_id', flat=True).distinct()
    effectif_secretariat = User.objects.filter(
        role__in=[User.Role.SECRETARIAT, User.Role.CHEF_SECRETARIAT],
        secretariat_id__in=sec_ids,
    ).distinct().count()

    mp_q = ModuleParticipant.objects.filter(module_id__in=module_ids)
    auditeurs_listes = mp_q.values('participant_id').distinct().count()

    ref_q = Participant.objects.filter(
        modules_inscrits__module__formation_id=formation_id,
        categorie__iexact=categorie,
    ).distinct()
    if secretariat_id:
        ref_q = ref_q.filter(secretariat_id=secretariat_id)
    if grade:
        ref_q = ref_q.filter(modules_inscrits__module__grade=grade).distinct()
    inscrits_reference = ref_q.count()

    inscrits_actifs = auditeurs_listes
    inscrits_reference = max(inscrits_reference, inscrits_actifs)

    abs_q = Pointage.objects.filter(
        statut=Pointage.Statut.ABSENT_NON_BADGE,
        session__module_id__in=module_ids,
    )
    if calendrier:
        try:
            abs_q = abs_q.filter(session__date_journee=date.fromisoformat(str(calendrier)))
        except ValueError:
            pass
    else:
        if annee:
            abs_q = abs_q.filter(session__date_journee__year=annee)
        if mois:
            abs_q = abs_q.filter(session__date_journee__month=mois)
    absents_notoires = abs_q.values('participant_id').distinct().count()

    return {
        'grade': grade or '',
        'nb_groupes': nb_groupes,
        'nb_encadrants': nb_encadrants,
        'effectif_secretariat': effectif_secretariat,
        'inscrits_actifs': inscrits_actifs,
        'inscrits_reference': inscrits_reference,
        'pct_inscrits': _pct(inscrits_actifs, inscrits_reference),
        'auditeurs_listes': auditeurs_listes,
        'absents_notoires': absents_notoires,
        'pct_absents': _pct(absents_notoires, inscrits_reference),
    }


def _somme_lignes(lignes, keys):
    out = {}
    for k in keys:
        out[k] = sum(l.get(k, 0) or 0 for l in lignes)
    if out.get('inscrits_reference'):
        out['pct_inscrits'] = _pct(out.get('inscrits_actifs', 0), out['inscrits_reference'])
        out['pct_absents'] = _pct(out.get('absents_notoires', 0), out['inscrits_reference'])
    return out


def _ligne_categorie_formation(formation_id, categorie, secretariat_id, annee, mois, calendrier):
    grades = sorted({
        g for g in Module.objects.filter(
            formation_id=formation_id,
            module_participants__participant__categorie__iexact=categorie,
        ).exclude(grade='').values_list('grade', flat=True)
    })

    keys_sum = [
        'nb_groupes', 'nb_encadrants', 'effectif_secretariat',
        'inscrits_actifs', 'inscrits_reference', 'auditeurs_listes', 'absents_notoires',
    ]

    if len(grades) > 1:
        sous_lignes = [
            _stats_ligne_formation(formation_id, categorie, g, secretariat_id, annee, mois, calendrier)
            for g in grades
        ]
        totaux = _somme_lignes(sous_lignes, keys_sum)
        nb_enc = _stats_ligne_formation(
            formation_id, categorie, None, secretariat_id, annee, mois, calendrier,
        )
        totaux['nb_encadrants'] = nb_enc['nb_encadrants']
        totaux['effectif_secretariat'] = nb_enc['effectif_secretariat']
        return {
            'categorie': categorie,
            'multi_grade': True,
            'sous_lignes': sous_lignes,
            'totaux': totaux,
        }

    grade = grades[0] if grades else None
    stats = _stats_ligne_formation(
        formation_id, categorie, grade, secretariat_id, annee, mois, calendrier,
    )
    return {
        'categorie': categorie,
        'multi_grade': False,
        'sous_lignes': [],
        'totaux': stats,
    }


def compute_bilan_periode_formation(
    formation_id,
    annee=None,
    mois=None,
    calendrier=None,
    periode=None,
    secretariat_id=None,
    categorie_filter=None,
):
    """Tableau CPFAE « Bilan période » par formation (catégories A–D)."""
    try:
        formation = Formation.objects.get(pk=formation_id)
    except Formation.DoesNotExist:
        return None

    annee = annee or date.today().year
    formation_nom = (formation.formation or f'Formation {formation.id}').strip().upper()
    titre = f'BILAN PERIODE {formation_nom} {annee}'

    categories_ref = list(
        RefCategorie.objects.filter(actif=True).order_by('libelle').values_list('libelle', flat=True)
    )
    cats_data = _liste_categories(formation_id, secretariat_id)
    categories = [c for c in categories_ref if c in cats_data] or sorted(cats_data)
    if categorie_filter:
        categories = [c for c in categories if c.upper() == categorie_filter.upper()]

    lignes = [
        _ligne_categorie_formation(formation_id, cat, secretariat_id, annee, mois, calendrier)
        for cat in categories
    ]

    keys_sum = [
        'nb_groupes', 'nb_encadrants', 'effectif_secretariat',
        'inscrits_actifs', 'inscrits_reference', 'auditeurs_listes', 'absents_notoires',
    ]
    total = _somme_lignes([l['totaux'] for l in lignes], keys_sum)

    return {
        'type': 'bilan_periode_formation',
        'titre': titre,
        'formation_id': formation.id,
        'formation': formation.formation,
        'annee': annee,
        'date_inscrits': _date_inscrits_label(calendrier),
        'periode_label': dict(PERIODES_BILAN).get(periode, '') if periode else '',
        'justificatifs': JUSTIFICATIFS_ABSENCES,
        'lignes': lignes,
        'total': total,
    }


def _resume_module(module, categorie=None):
    mq = {'module': module}
    if categorie:
        mq['participant__categorie__iexact'] = categorie
    inscrits = ModuleParticipant.objects.filter(**mq).values('participant').distinct().count()
    sess_ids = session_ids_for_scope([module.id])
    return {
        'inscrits': inscrits,
        'nb_seances_terminees': len(sess_ids),
        'nb_pointages': Pointage.objects.filter(session_id__in=sess_ids).count() if sess_ids else 0,
    }


def compute_bilans(
    annee=None,
    mois=None,
    categorie=None,
    module_id=None,
    formation_id=None,
    secretariat_id=None,
    periode=None,
    calendrier=None,
    dimension='formation',
):
    """
    dimension : 'module' | 'categorie' | 'formation'
    Retourne la liste des bilans disponibles + métadonnées filtres.
    """
    annee = annee or date.today().year
    dimension = (dimension or 'formation').lower()
    if dimension not in ('module', 'categorie', 'formation'):
        dimension = 'formation'

    categories = _liste_categories(formation_id, secretariat_id)
    modules_qs = _modules_queryset(formation_id, secretariat_id, categorie, module_id)
    modules_liste = [
        {'id': m.id, 'intitule': m.intitule, 'formation_id': m.formation_id, 'formation': str(m.formation)}
        for m in modules_qs[:500]
    ]

    formations_qs = _formations_queryset(formation_id, secretariat_id)
    formations_liste = [{'id': f.id, 'formation': f.formation} for f in formations_qs[:200]]

    periode_label = dict(PERIODES_BILAN).get(periode, 'Toutes périodes') if periode else 'Toutes périodes'
    filtres_actifs = {
        'annee': annee,
        'mois': mois,
        'categorie': categorie or '',
        'module_id': module_id,
        'formation_id': formation_id,
        'secretariat_id': secretariat_id,
        'periode': periode or '',
        'periode_label': periode_label,
        'calendrier': calendrier or '',
        'dimension': dimension,
    }

    bilans = []

    if dimension == 'formation':
        for f in formations_qs:
            bilans.append({
                'id': f'formation-{f.id}-{annee}-{periode or "all"}',
                'dimension': 'formation',
                'formation_id': f.id,
                'formation': f.formation,
                'module_id': None,
                'module': None,
                'categorie': categorie or '—',
                'libelle': f.formation,
                'sous_titre': f'Bilan formation · {periode_label} · {annee}',
                'annee': annee,
                'mois': mois,
                'periode': periode or '',
                'periode_label': periode_label,
                'calendrier': calendrier or '',
                'tableau_pret': True,
            })

    elif dimension == 'categorie':
        cats = [categorie] if categorie else categories
        if not cats:
            cats = ['—']
        for cat in cats:
            bilans.append({
                'id': f'categorie-{cat}-{annee}-{periode or "all"}',
                'dimension': 'categorie',
                'formation_id': formation_id,
                'formation': None,
                'module_id': None,
                'module': None,
                'categorie': cat,
                'libelle': f'Catégorie {cat}',
                'sous_titre': f'Bilan catégorie · {periode_label} · {annee}',
                'annee': annee,
                'mois': mois,
                'periode': periode or '',
                'periode_label': periode_label,
                'calendrier': calendrier or '',
                'tableau_pret': True,
            })

    else:  # module
        for m in modules_qs:
            resume = _resume_module(m, categorie)
            bilans.append({
                'id': f'module-{m.id}-{annee}-{periode or "all"}',
                'dimension': 'module',
                'formation_id': m.formation_id,
                'formation': str(m.formation),
                'module_id': m.id,
                'module': m.intitule,
                'categorie': categorie or '—',
                'libelle': m.intitule,
                'sous_titre': f'{m.formation} · {periode_label} · {annee}',
                'annee': annee,
                'mois': mois,
                'periode': periode or '',
                'periode_label': periode_label,
                'calendrier': calendrier or '',
                'inscrits': resume['inscrits'],
                'nb_pointages': resume['nb_pointages'],
                'tableau_pret': True,
            })

    return {
        'annee': annee,
        'mois': mois,
        'bilans': bilans,
        'total_bilans': len(bilans),
        'categories': categories,
        'modules': modules_liste,
        'formations': formations_liste,
        'periodes': [{'value': v, 'label': l} for v, l in PERIODES_BILAN],
        'filtres_actifs': filtres_actifs,
    }


def _tableau_pour_bilan(bilan, categorie=None, annee=None, mois=None, calendrier=None,
                        periode=None, formation_id=None, secretariat_id=None):
    """Construit le tableau CPFAE détaillé pour une entrée de la liste bilans."""
    dim = bilan.get('dimension')
    cat = bilan.get('categorie')
    if cat in (None, '', '—'):
        cat = categorie

    if dim == 'module' and bilan.get('module_id'):
        return compute_bilan_effectifs_module(
            bilan['module_id'],
            categorie=cat,
            annee=annee,
            mois=mois,
            calendrier=calendrier,
            periode=periode,
        )
    if dim == 'formation' and bilan.get('formation_id'):
        return compute_bilan_periode_formation(
            bilan['formation_id'],
            annee=annee,
            mois=mois,
            calendrier=calendrier,
            periode=periode,
            secretariat_id=secretariat_id,
            categorie_filter=cat if cat and cat != '—' else None,
        )
    if dim == 'categorie' and cat and cat != '—':
        return compute_bilan_effectifs_categorie(
            cat,
            formation_id=formation_id or bilan.get('formation_id'),
            secretariat_id=secretariat_id,
            annee=annee,
            mois=mois,
            calendrier=calendrier,
            periode=periode,
        )
    return None


def compute_bilans_avec_tableaux(
    annee=None,
    mois=None,
    categorie=None,
    module_id=None,
    formation_id=None,
    secretariat_id=None,
    periode=None,
    calendrier=None,
    dimension='formation',
):
    """Index bilans + tous les tableaux CPFAE correspondants (vue d'ensemble)."""
    data = compute_bilans(
        annee=annee,
        mois=mois,
        categorie=categorie,
        module_id=module_id,
        formation_id=formation_id,
        secretariat_id=secretariat_id,
        periode=periode,
        calendrier=calendrier,
        dimension=dimension,
    )
    tableaux_complets = []
    for b in data['bilans']:
        tableau = _tableau_pour_bilan(
            b,
            categorie=categorie,
            annee=annee,
            mois=mois,
            calendrier=calendrier,
            periode=periode,
            formation_id=formation_id,
            secretariat_id=secretariat_id,
        )
        if tableau:
            tableaux_complets.append({
                'bilan_id': b['id'],
                'bilan': b,
                'tableau': tableau,
            })
    data['tableaux_complets'] = tableaux_complets
    data['total_tableaux'] = len(tableaux_complets)
    return data
