"""Contrat de données à destination de l'application d'emploi du temps.

Ces endpoints sont **strictement en lecture**. Ils exposent, sous une forme
stable et versionnée, ce dont un planificateur a besoin : les groupes et leurs
effectifs, les enseignements à placer avec leurs volumes horaires, et la liste
nominative des étudiants concernés.

Rien ici ne modifie l'application de gestion, et rien n'impose à l'application
d'emploi du temps de consommer ce contrat : le circuit d'échange actuel par
fichier Excel reste inchangé et pleinement fonctionnel.

Le champ ``version`` permet de faire évoluer le format sans casser un
consommateur existant : tout ajout se fait par nouveau champ, jamais par
renommage ou suppression d'un champ publié.
"""

import csv

from django.db.models import Count, Q
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from authentication.permissions import IsSecretariatOrDFRC

from .models import (
    AffectationGroupe,
    AnneeAcademique,
    Groupe,
    InscriptionAdministrative,
    InscriptionPedagogique,
)

VERSION_CONTRAT = '1.0'


def _annee_demandee(request):
    """Année académique ciblée : celle demandée, sinon l'année courante."""
    identifiant = request.query_params.get('annee_academique_id')
    if identifiant:
        return AnneeAcademique.objects.filter(pk=identifiant).first()
    return AnneeAcademique.courante_ou_none()


def _filtrer(queryset, request, correspondances):
    for parametre, champ in correspondances.items():
        if request.query_params.get(parametre):
            queryset = queryset.filter(**{champ: request.query_params[parametre]})
    return queryset


def _csv_demande(request):
    """Le paramètre s'appelle ``export`` : ``format`` est réservé par DRF."""
    return request.query_params.get('export') == 'csv'


def _reponse_csv(nom_fichier, colonnes, lignes):
    reponse = HttpResponse(content_type='text/csv; charset=utf-8')
    reponse['Content-Disposition'] = f'attachment; filename="{nom_fichier}"'
    reponse.write('\ufeff')  # BOM : Excel ouvre correctement les accents.
    ecrivain = csv.DictWriter(reponse, fieldnames=colonnes, extrasaction='ignore')
    ecrivain.writeheader()
    ecrivain.writerows(lignes)
    return reponse


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSecretariatOrDFRC])
def contrat(request):
    """Description du contrat et volumétrie disponible."""
    annee = _annee_demandee(request)
    inscriptions = InscriptionAdministrative.objects.filter(
        statut=InscriptionAdministrative.Statut.VALIDEE,
    )
    if annee is not None:
        inscriptions = inscriptions.filter(annee_academique=annee)

    return Response({
        'version': VERSION_CONTRAT,
        'source': 'app-injs-lmd / module Scolarité',
        'annee_academique': {
            'id': annee.id, 'libelle': annee.libelle,
        } if annee else None,
        'ressources': {
            'groupes': request.build_absolute_uri('./groupes/'),
            'enseignements': request.build_absolute_uri('./enseignements/'),
            'etudiants': request.build_absolute_uri('./etudiants/'),
        },
        'parametres': [
            'annee_academique_id', 'ref_formation_id', 'niveau_id', 'parcours_id', 'groupe_id',
        ],
        'formats': {'json': 'par défaut', 'csv': 'ajouter export=csv'},
        'volumetrie': {
            'inscriptions_validees': inscriptions.count(),
            'groupes': Groupe.objects.filter(
                annee_academique=annee, actif=True,
            ).count() if annee else 0,
        },
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSecretariatOrDFRC])
def groupes(request):
    """Groupes à planifier, avec leur effectif réel."""
    annee = _annee_demandee(request)
    queryset = Groupe.objects.filter(actif=True).select_related(
        'annee_academique', 'ref_formation', 'niveau', 'parcours', 'site', 'vague',
    )
    if annee is not None:
        queryset = queryset.filter(annee_academique=annee)
    queryset = _filtrer(queryset, request, {
        'ref_formation_id': 'ref_formation_id',
        'niveau_id': 'niveau_id',
        'parcours_id': 'parcours_id',
        'groupe_id': 'id',
    })
    queryset = queryset.annotate(
        effectif=Count('affectations', filter=Q(affectations__active=True)),
    )

    lignes = [
        {
            'groupe_id': groupe.id,
            'groupe': groupe.nom,
            'annee_academique': groupe.annee_academique.libelle,
            'formation': groupe.ref_formation.intitule,
            'parcours': groupe.parcours.intitule if groupe.parcours_id else '',
            'niveau': groupe.niveau.code,
            'vague': groupe.vague.libelle if groupe.vague_id else '',
            'site': groupe.site.libelle if groupe.site_id else '',
            'effectif': groupe.effectif,
            'capacite_max': groupe.capacite_max or '',
        }
        for groupe in queryset
    ]

    if _csv_demande(request):
        return _reponse_csv('edt_groupes.csv', list(lignes[0].keys()) if lignes else [
            'groupe_id', 'groupe', 'annee_academique', 'formation', 'parcours',
            'niveau', 'vague', 'site', 'effectif', 'capacite_max',
        ], lignes)

    return Response({'version': VERSION_CONTRAT, 'resultats': lignes})


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSecretariatOrDFRC])
def enseignements(request):
    """Enseignements à placer : une ligne par ECUE, semestre et groupe.

    L'effectif est le nombre d'étudiants réellement inscrits à cet enseignement,
    ce qui permet au planificateur de choisir une salle adaptée.
    """
    annee = _annee_demandee(request)
    queryset = InscriptionPedagogique.objects.exclude(
        statut=InscriptionPedagogique.Statut.ABANDONNEE,
    ).filter(
        inscription__statut=InscriptionAdministrative.Statut.VALIDEE,
    ).select_related(
        'ecue', 'ecue__ue', 'ecue__ref_module', 'semestre', 'groupe',
        'inscription__ref_formation', 'inscription__niveau', 'inscription__parcours',
    )
    if annee is not None:
        queryset = queryset.filter(inscription__annee_academique=annee)
    queryset = _filtrer(queryset, request, {
        'ref_formation_id': 'inscription__ref_formation_id',
        'niveau_id': 'inscription__niveau_id',
        'parcours_id': 'inscription__parcours_id',
        'groupe_id': 'groupe_id',
    })

    # Regroupement par enseignement plutôt que par étudiant : c'est la maille
    # que manipule un emploi du temps.
    agregats = {}
    for ligne in queryset:
        cle = (
            ligne.ecue_id, ligne.semestre_id, ligne.groupe_id,
            ligne.inscription.ref_formation_id, ligne.inscription.niveau_id,
        )
        entree = agregats.get(cle)
        if entree is None:
            ecue = ligne.ecue
            entree = agregats[cle] = {
                'ecue_id': ecue.id,
                'ecue_code': ecue.code,
                'ecue_intitule': ecue.intitule,
                'ue_code': ecue.ue.code,
                'ue_intitule': ecue.ue.intitule,
                'module_referentiel': ecue.ref_module.intitule if ecue.ref_module_id else '',
                'semestre': ligne.semestre.libelle,
                'formation': ligne.inscription.ref_formation.intitule,
                'parcours': (
                    ligne.inscription.parcours.intitule if ligne.inscription.parcours_id else ''
                ),
                'niveau': ligne.inscription.niveau.code,
                'groupe_id': ligne.groupe_id or '',
                'groupe': ligne.groupe.nom if ligne.groupe_id else '',
                'credits': ecue.credits,
                'volume_cm': float(ecue.volume_cm),
                'volume_td': float(ecue.volume_td),
                'volume_tp': float(ecue.volume_tp),
                'volume_total': float(ecue.volume_total),
                'effectif': 0,
            }
        entree['effectif'] += 1

    lignes = sorted(
        agregats.values(),
        key=lambda entree: (entree['semestre'], entree['ue_code'], entree['ecue_code']),
    )

    if _csv_demande(request):
        colonnes = [
            'ecue_id', 'ecue_code', 'ecue_intitule', 'ue_code', 'ue_intitule',
            'module_referentiel', 'semestre', 'formation', 'parcours', 'niveau',
            'groupe_id', 'groupe', 'credits', 'volume_cm', 'volume_td', 'volume_tp',
            'volume_total', 'effectif',
        ]
        return _reponse_csv('edt_enseignements.csv', colonnes, lignes)

    return Response({'version': VERSION_CONTRAT, 'resultats': lignes})


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSecretariatOrDFRC])
def etudiants(request):
    """Liste nominative des étudiants inscrits, avec leur groupe actif."""
    annee = _annee_demandee(request)
    queryset = InscriptionAdministrative.objects.filter(
        statut=InscriptionAdministrative.Statut.VALIDEE,
    ).select_related(
        'etudiant__participant', 'ref_formation', 'niveau', 'parcours', 'vague',
    )
    if annee is not None:
        queryset = queryset.filter(annee_academique=annee)
    queryset = _filtrer(queryset, request, {
        'ref_formation_id': 'ref_formation_id',
        'niveau_id': 'niveau_id',
        'parcours_id': 'parcours_id',
    })
    if request.query_params.get('groupe_id'):
        queryset = queryset.filter(
            affectations__groupe_id=request.query_params['groupe_id'],
            affectations__active=True,
        )

    groupes_actifs = {
        affectation.inscription_id: affectation.groupe.nom
        for affectation in AffectationGroupe.objects
        .filter(active=True, inscription__in=queryset)
        .select_related('groupe')
    }

    lignes = [
        {
            'matricule': inscription.etudiant.matricule,
            'nom': inscription.etudiant.participant.nom,
            'prenom': inscription.etudiant.participant.prenom,
            'formation': inscription.ref_formation.intitule,
            'parcours': inscription.parcours.intitule if inscription.parcours_id else '',
            'niveau': inscription.niveau.code,
            'groupe': groupes_actifs.get(inscription.id, ''),
            'vague': inscription.vague.libelle if inscription.vague_id else '',
        }
        for inscription in queryset
    ]

    if _csv_demande(request):
        colonnes = [
            'matricule', 'nom', 'prenom', 'formation', 'parcours',
            'niveau', 'groupe', 'vague',
        ]
        return _reponse_csv('edt_etudiants.csv', colonnes, lignes)

    return Response({'version': VERSION_CONTRAT, 'resultats': lignes})
