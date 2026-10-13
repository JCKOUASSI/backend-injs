"""Accès effectifs d'un compte (refonte « Utilisateurs & Accès », phase 5).

Principe : **une seule source de vérité, le moteur** ``est_autorise()``.

Les permissions *candidates* sont celles qui pourraient être détenues :
permissions portées par les rôles actifs, dérogations actives (octrois et
retraits), permissions et rôles délégués par une délégation active. Chaque
candidate est évaluée par le moteur, qui seul décide : statut du compte,
périmètre, délégation validée, retrait, MFA… sont donc pris en compte comme
au moment d'une requête réelle. Aucune logique parallèle n'est introduite.

Lecture seule : ce module ne modifie aucun droit.
"""
from django.utils import timezone

from ..models import (
    AttributionRole,
    DelegationHabilitation,
    PermissionAttribuee,
    PermissionMetier,
)
from .moteur import est_autorise


def _decomposer(code):
    """``module.ressource.action`` -> (module, ressource, action)."""
    morceaux = (code or '').split('.')
    morceaux += [''] * (3 - len(morceaux))
    return morceaux[0], morceaux[1], morceaux[2]


def _entree(code, cache):
    return cache.setdefault(code, {
        'roles': set(),
        'derogation': False,
        'retrait': False,
        'delegations': set(),
    })


def acces_effectifs(compte):
    """Photographie des accès effectifs d'un ``CompteUtilisateur``."""
    aujourdhui = timezone.localdate()
    candidats = {}

    # 1) Rôles : attributions ACTIVE à la date du jour ; les autres sont listées
    #    à part (expirées ou pas encore entrées en vigueur).
    attributions = list(
        compte.attributions.select_related('role').order_by('role__code')
    )
    roles_actifs = [
        a for a in attributions
        if a.statut == AttributionRole.Statut.ACTIVE and a.est_active(aujourdhui)
    ]
    roles_hors_periode = [
        a for a in attributions
        if a.statut == AttributionRole.Statut.ACTIVE and a not in roles_actifs
    ]
    role_ids = [a.role_id for a in roles_actifs]
    if role_ids:
        liens = PermissionMetier.objects.filter(
            roles_octroyants__in=role_ids,
        ).values_list('code', 'roles_octroyants__code')
        for code, role_code in liens:
            _entree(code, candidats)['roles'].add(role_code)

    # 2) Dérogations actives (OCTROI ajoute, RETRAIT retire).
    derogations = compte.derogations.filter(
        statut=PermissionAttribuee.Statut.ACTIVE,
    ).select_related('permission')
    for derogation in derogations:
        if not derogation.est_active(aujourdhui):
            continue
        entree = _entree(derogation.permission.code, candidats)
        if derogation.sens == PermissionAttribuee.Sens.OCTROI:
            entree['derogation'] = True
        else:
            entree['retrait'] = True

    # 3) Délégations reçues actives : permissions directes et rôles délégués.
    delegations = (
        compte.delegations_recues
        .filter(statut=DelegationHabilitation.Statut.ACTIVE)
        .select_related('delegant__user')
        .prefetch_related('permissions', 'roles')
    )
    delegations_actives = []
    for delegation in delegations:
        if not delegation.est_active(aujourdhui):
            continue
        delegations_actives.append(delegation)
        nom = delegation.delegant.user.get_username() if delegation.delegant.user else ''
        for permission in delegation.permissions.all():
            _entree(permission.code, candidats)['delegations'].add(nom)
        codes_roles_delegues = [r.code for r in delegation.roles.all()]
        if codes_roles_delegues:
            liens = PermissionMetier.objects.filter(
                roles_octroyants__code__in=codes_roles_delegues,
            ).values_list('code', flat=True)
            for code in liens:
                _entree(code, candidats)['delegations'].add(nom)

    # 4) Décision du moteur pour chaque candidat.
    utilisateur = compte.user
    permissions = []
    for code in sorted(candidats):
        info = candidats[code]
        decision = est_autorise(utilisateur, code, canal='WEB')
        module, ressource, action = _decomposer(code)
        permissions.append({
            'code': code,
            'module': module,
            'ressource': ressource,
            'action': action,
            'autorise': bool(decision.autorise),
            'gouverne': bool(decision.gouverne),
            'motifs': list(decision.motifs),
            'sources': {
                'roles': sorted(info['roles']),
                'derogation': info['derogation'],
                'retrait': info['retrait'],
                'delegations': sorted(d for d in info['delegations'] if d),
            },
        })

    modules = sorted({p['module'] for p in permissions if p['autorise']})
    return {
        'compte_id': compte.pk,
        'username': compte.user.get_username() if compte.user else None,
        'statut_compte': compte.statut,
        'date_reference': aujourdhui.isoformat(),
        'roles_actifs': [
            _ligne_role(a, actif=True) for a in roles_actifs
        ],
        'roles_hors_periode': [
            _ligne_role(a, actif=False) for a in roles_hors_periode
        ],
        'delegations_actives': [
            {
                'id': d.pk,
                'delegant': d.delegant.user.get_username() if d.delegant.user else None,
                'date_fin': d.date_fin.isoformat() if d.date_fin else None,
            }
            for d in delegations_actives
        ],
        'permissions': permissions,
        'modules_accessibles': modules,
        'synthese': {
            'candidates': len(permissions),
            'autorisees': sum(1 for p in permissions if p['autorise']),
            'refusees': sum(1 for p in permissions if not p['autorise']),
        },
    }


def _ligne_role(attribution, *, actif):
    role = attribution.role
    return {
        'code': role.code,
        'libelle': role.libelle,
        'sensible': bool(role.sensible),
        'date_debut': attribution.date_debut.isoformat() if attribution.date_debut else None,
        'date_fin': attribution.date_fin.isoformat() if attribution.date_fin else None,
        'actif_aujourdhui': actif,
    }
