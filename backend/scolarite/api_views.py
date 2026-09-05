"""API des référentiels LMD et de la maquette pédagogique.

Suit les conventions du projet : vues fonctions ``@api_view``, routes ``path()``
explicites, filtrage manuel via ``request.query_params``.
"""

from django.core.exceptions import ValidationError
from django.db.models import Count, Sum
from django.db.models.deletion import ProtectedError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework.response import Response

from authentication.permissions import IsDFRC, IsSecretariatOrDFRC

from .models import (
    AnneeAcademique,
    ECUE,
    Groupe,
    Maquette,
    Niveau,
    Parcours,
    RegimeEtudes,
    Semestre,
    StatutEtudiant,
    TypeFormation,
    UE,
)

# Champs exposés et acceptés en écriture pour chaque référentiel simple.
REFERENTIEL_FIELDS = {
    'annees': (AnneeAcademique, ['id', 'libelle', 'date_debut', 'date_fin', 'courante', 'actif']),
    'types-formation': (TypeFormation, ['id', 'code', 'libelle', 'actif']),
    'niveaux': (Niveau, ['id', 'code', 'libelle', 'cycle', 'ordre', 'credits_requis', 'actif']),
    'semestres': (Semestre, ['id', 'niveau_id', 'numero', 'libelle', 'actif']),
    'regimes': (RegimeEtudes, ['id', 'code', 'libelle', 'actif']),
    'statuts-etudiant': (StatutEtudiant, ['id', 'code', 'libelle', 'bloque_inscription', 'actif']),
    'parcours': (Parcours, ['id', 'ref_formation_id', 'type_formation_id', 'code', 'intitule', 'actif']),
    'groupes': (Groupe, [
        'id', 'annee_academique_id', 'ref_formation_id', 'parcours_id', 'niveau_id',
        'vague_id', 'site_id', 'nom', 'capacite_max', 'actif',
    ]),
}

# Filtres exacts autorisés par référentiel, pour éviter toute injection de lookup.
REFERENTIEL_FILTERS = {
    'semestres': ['niveau_id', 'actif'],
    'parcours': ['ref_formation_id', 'type_formation_id', 'actif'],
    'groupes': [
        'annee_academique_id', 'ref_formation_id', 'parcours_id', 'niveau_id',
        'vague_id', 'site_id', 'actif',
    ],
    'annees': ['courante', 'actif'],
    'niveaux': ['cycle', 'actif'],
    'types-formation': ['actif'],
    'regimes': ['actif'],
    'statuts-etudiant': ['actif'],
}

_BOOLEAN_TRUE = {'1', 'true', 'True', 'oui'}
_BOOLEAN_FALSE = {'0', 'false', 'False', 'non'}


def _coerce(value):
    """Convertit les valeurs de query string en type Python exploitable par l'ORM."""
    if value in _BOOLEAN_TRUE:
        return True
    if value in _BOOLEAN_FALSE:
        return False
    return value


def _apply_filters(queryset, ressource, query_params):
    for champ in REFERENTIEL_FILTERS.get(ressource, []):
        if champ in query_params:
            queryset = queryset.filter(**{champ: _coerce(query_params[champ])})
    return queryset


def _payload_for_write(fields, data):
    """Construit le dictionnaire d'attributs à écrire, en ignorant les champs absents."""
    valeurs = {}
    for champ in fields:
        if champ == 'id' or champ not in data:
            continue
        valeur = data[champ]
        valeurs[champ] = None if valeur == '' and champ.endswith('_id') else valeur
    return valeurs


def _valider(obj):
    """Valide l'objet et renvoie une réponse 400 exploitable par formatApiErrors côté frontend."""
    try:
        obj.full_clean()
    except ValidationError as erreur:
        return Response(erreur.message_dict, status=400)
    return None


def _referentiel_list(request, ressource):
    model, fields = REFERENTIEL_FIELDS[ressource]
    if request.method == 'GET':
        queryset = _apply_filters(model.objects.all(), ressource, request.query_params)
        return Response(list(queryset.values(*fields)))
    obj = model(**_payload_for_write(fields, request.data))
    erreur = _valider(obj)
    if erreur is not None:
        return erreur
    obj.save()
    return Response(model.objects.filter(pk=obj.pk).values(*fields).first(), status=201)


def _referentiel_detail(request, ressource, pk):
    model, fields = REFERENTIEL_FIELDS[ressource]
    obj = model.objects.filter(pk=pk).first()
    if obj is None:
        return Response({'error': 'Introuvable'}, status=404)
    if request.method == 'DELETE':
        try:
            obj.delete()
        except ProtectedError:
            return Response(
                {'error': "Suppression impossible : cet élément est référencé ailleurs."},
                status=409,
            )
        return Response(status=204)
    for champ, valeur in _payload_for_write(fields, request.data).items():
        setattr(obj, champ, valeur)
    erreur = _valider(obj)
    if erreur is not None:
        return erreur
    obj.save()
    return Response(model.objects.filter(pk=obj.pk).values(*fields).first())


class LectureScolariteEcritureDFRC(BasePermission):
    """Lecture ouverte au personnel de scolarité, écriture réservée à l'administration.

    Les écrans de candidature et d'inscription ont besoin de lire niveaux,
    semestres et groupes ; les modifier reste un acte de paramétrage.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return IsSecretariatOrDFRC().has_permission(request, view)
        return IsDFRC().has_permission(request, view)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, LectureScolariteEcritureDFRC])
def referentiel_list(request, ressource):
    if ressource not in REFERENTIEL_FIELDS:
        return Response({'error': 'Référentiel inconnu'}, status=404)
    return _referentiel_list(request, ressource)


@api_view(['PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated, IsDFRC])
def referentiel_detail(request, ressource, pk):
    if ressource not in REFERENTIEL_FIELDS:
        return Response({'error': 'Référentiel inconnu'}, status=404)
    return _referentiel_detail(request, ressource, pk)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def annee_courante(request):
    """Année académique courante, utilisée comme valeur par défaut par le frontend."""
    annee = AnneeAcademique.courante_ou_none()
    if annee is None:
        return Response({'annee': None})
    return Response({
        'annee': {
            'id': annee.id,
            'libelle': annee.libelle,
            'date_debut': annee.date_debut,
            'date_fin': annee.date_fin,
        },
    })


def _serialize_ecue(ecue):
    return {
        'id': ecue.id,
        'code': ecue.code,
        'intitule': ecue.intitule,
        'credits': ecue.credits,
        'coefficient': ecue.coefficient,
        'volume_cm': ecue.volume_cm,
        'volume_td': ecue.volume_td,
        'volume_tp': ecue.volume_tp,
        'volume_total': ecue.volume_total,
        'ref_module_id': ecue.ref_module_id,
        'ordre': ecue.ordre,
    }


def _serialize_ue(ue):
    return {
        'id': ue.id,
        'code': ue.code,
        'intitule': ue.intitule,
        'credits': ue.credits,
        'caractere': ue.caractere,
        'ordre': ue.ordre,
        'semestre': {
            'id': ue.semestre_id,
            'numero': ue.semestre.numero,
            'libelle': ue.semestre.libelle,
        },
        'ecues': [_serialize_ecue(ecue) for ecue in ue.ecues.all()],
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsDFRC])
def maquette_list(request):
    """Liste des maquettes, avec le nombre d'UE et le total de crédits."""
    queryset = Maquette.objects.select_related(
        'annee_academique', 'ref_formation', 'parcours', 'niveau',
    ).annotate(
        nb_ue=Count('unites_enseignement', distinct=True),
        total_credits=Sum('unites_enseignement__credits'),
    )
    for champ in ('annee_academique_id', 'ref_formation_id', 'parcours_id', 'niveau_id', 'statut'):
        if champ in request.query_params:
            queryset = queryset.filter(**{champ: request.query_params[champ]})
    return Response([
        {
            'id': maquette.id,
            'libelle': str(maquette),
            'annee_academique_id': maquette.annee_academique_id,
            'annee_academique': maquette.annee_academique.libelle,
            'ref_formation_id': maquette.ref_formation_id,
            'ref_formation': maquette.ref_formation.intitule,
            'parcours_id': maquette.parcours_id,
            'parcours': maquette.parcours.intitule if maquette.parcours else None,
            'niveau_id': maquette.niveau_id,
            'niveau': maquette.niveau.code,
            'version': maquette.version,
            'statut': maquette.statut,
            'nb_ue': maquette.nb_ue,
            'total_credits': maquette.total_credits or 0,
        }
        for maquette in queryset
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsDFRC])
def maquette_detail(request, pk):
    """Détail d'une maquette : UE groupées par semestre, avec leurs ECUE."""
    maquette = Maquette.objects.select_related(
        'annee_academique', 'ref_formation', 'parcours', 'niveau',
    ).filter(pk=pk).first()
    if maquette is None:
        return Response({'error': 'Introuvable'}, status=404)
    unites = (
        UE.objects.filter(maquette=maquette)
        .select_related('semestre')
        .prefetch_related('ecues')
    )
    return Response({
        'id': maquette.id,
        'libelle': str(maquette),
        'annee_academique': maquette.annee_academique.libelle,
        'ref_formation': maquette.ref_formation.intitule,
        'parcours': maquette.parcours.intitule if maquette.parcours else None,
        'niveau': maquette.niveau.code,
        'version': maquette.version,
        'statut': maquette.statut,
        'unites_enseignement': [_serialize_ue(ue) for ue in unites],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsDFRC])
def maquette_ecues_semestre(request, pk, semestre_id):
    """ECUE d'un semestre donné d'une maquette.

    Sert de source à la génération automatique des inscriptions pédagogiques (lot 5).
    """
    if not Maquette.objects.filter(pk=pk).exists():
        return Response({'error': 'Maquette introuvable'}, status=404)
    if not Semestre.objects.filter(pk=semestre_id).exists():
        return Response({'error': 'Semestre introuvable'}, status=404)
    ecues = (
        ECUE.objects.filter(ue__maquette_id=pk, ue__semestre_id=semestre_id)
        .select_related('ue')
        .order_by('ue__ordre', 'ordre')
    )
    return Response([
        {**_serialize_ecue(ecue), 'ue_id': ecue.ue_id, 'ue_code': ecue.ue.code}
        for ecue in ecues
    ])
