"""API des dossiers étudiants et des inscriptions administratives."""

from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from admissions.models import Admission
from authentication.permissions import IsSecretariatOrDFRC

from . import inscription_services
from .models import DossierEtudiant, InscriptionAdministrative

INSCRIPTION_CHAMPS = [
    'annee_academique_id', 'ref_formation_id', 'parcours_id', 'niveau_id', 'vague_id',
    'categorie_id', 'grade_id', 'regime_id', 'statut_etudiant_id',
    'type_inscription', 'date_inscription', 'observations',
]


def _serialize_dossier(dossier, detail=False):
    data = {
        'id': dossier.id,
        'uuid': str(dossier.uuid),
        'participant_id': dossier.participant_id,
        'matricule': dossier.matricule,
        'nom': dossier.participant.nom,
        'prenom': dossier.participant.prenom,
        'nom_complet': dossier.nom_complet,
        'statut_id': dossier.statut_id,
        'statut': dossier.statut.libelle if dossier.statut else None,
        'date_premiere_inscription': dossier.date_premiere_inscription,
    }
    if detail:
        courante = dossier.inscription_courante
        data.update({
            'observations': dossier.observations,
            'email': dossier.participant.email,
            'telephone': dossier.participant.telephone,
            'date_naissance': dossier.participant.date_naissance,
            'lieu_naissance': dossier.participant.lieu_naissance,
            'sexe': dossier.participant.sexe,
            'inscription_courante': _serialize_inscription(courante) if courante else None,
            'inscriptions': [
                _serialize_inscription(i)
                for i in dossier.inscriptions.select_related(
                    'annee_academique', 'ref_formation', 'niveau',
                )
            ],
        })
    return data


def _serialize_inscription(inscription, detail=False):
    data = {
        'id': inscription.id,
        'etudiant_id': inscription.etudiant_id,
        'matricule': inscription.etudiant.matricule,
        'etudiant': inscription.etudiant.nom_complet,
        'annee_academique_id': inscription.annee_academique_id,
        'annee_academique': inscription.annee_academique.libelle,
        'ref_formation_id': inscription.ref_formation_id,
        'ref_formation': inscription.ref_formation.intitule,
        'parcours_id': inscription.parcours_id,
        'niveau_id': inscription.niveau_id,
        'niveau': inscription.niveau.code,
        'vague_id': inscription.vague_id,
        'categorie_id': inscription.categorie_id,
        'grade_id': inscription.grade_id,
        'regime_id': inscription.regime_id,
        'type_inscription': inscription.type_inscription,
        'type_inscription_libelle': inscription.get_type_inscription_display(),
        'statut': inscription.statut,
        'statut_libelle': inscription.get_statut_display(),
        'date_inscription': inscription.date_inscription,
        'date_validation': inscription.date_validation,
        'admission_id': inscription.admission_id,
    }
    if detail:
        data.update({
            'observations': inscription.observations,
            'valide_par': inscription.valide_par.username if inscription.valide_par else None,
            'transitions_possibles': inscription_services.transitions_possibles(inscription),
        })
    return data


def _inscription_queryset():
    return InscriptionAdministrative.objects.select_related(
        'etudiant__participant', 'annee_academique', 'ref_formation', 'niveau', 'valide_par',
    )


# ── Dossiers étudiants ──────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSecretariatOrDFRC])
def etudiant_list(request):
    queryset = DossierEtudiant.objects.select_related('participant', 'statut')
    recherche = request.query_params.get('q')
    if recherche:
        queryset = queryset.filter(
            Q(participant__matricule__icontains=recherche)
            | Q(participant__nom__icontains=recherche)
            | Q(participant__prenom__icontains=recherche)
        )
    for champ, filtre in (
        ('annee_academique_id', 'inscriptions__annee_academique_id'),
        ('niveau_id', 'inscriptions__niveau_id'),
        ('ref_formation_id', 'inscriptions__ref_formation_id'),
    ):
        if champ in request.query_params:
            queryset = queryset.filter(**{filtre: request.query_params[champ]})
    return Response([_serialize_dossier(d) for d in queryset.distinct()[:500]])


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated, IsSecretariatOrDFRC])
def etudiant_detail(request, pk):
    dossier = DossierEtudiant.objects.select_related('participant', 'statut').filter(pk=pk).first()
    if dossier is None:
        return Response({'error': 'Introuvable'}, status=404)
    if request.method == 'PATCH':
        # Le matricule n'est pas modifiable ici : il appartient au Participant.
        for champ in ('statut_id', 'observations'):
            if champ in request.data:
                setattr(dossier, champ, request.data[champ] or None)
        try:
            dossier.full_clean()
        except ValidationError as erreur:
            return Response(erreur.message_dict, status=400)
        dossier.save()
    return Response(_serialize_dossier(dossier, detail=True))


# ── Inscriptions administratives ────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSecretariatOrDFRC])
def inscription_list(request):
    queryset = _inscription_queryset()
    for champ in (
        'statut', 'type_inscription', 'annee_academique_id',
        'ref_formation_id', 'niveau_id', 'etudiant_id', 'vague_id',
    ):
        if champ in request.query_params:
            queryset = queryset.filter(**{champ: request.query_params[champ]})
    recherche = request.query_params.get('q')
    if recherche:
        queryset = queryset.filter(
            Q(etudiant__participant__matricule__icontains=recherche)
            | Q(etudiant__participant__nom__icontains=recherche)
            | Q(etudiant__participant__prenom__icontains=recherche)
        )
    return Response([_serialize_inscription(i) for i in queryset[:500]])


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated, IsSecretariatOrDFRC])
def inscription_detail(request, pk):
    inscription = _inscription_queryset().filter(pk=pk).first()
    if inscription is None:
        return Response({'error': 'Introuvable'}, status=404)
    if request.method == 'PATCH':
        # Le statut ne se modifie que par l'endpoint de transition.
        # Lot L1/L3 : un changement de parcours passe par le service dédié
        # (historisation JournalScolarite + EvenementScolarite REORIENTATION).
        nouveau_parcours_id = request.data.get('parcours_id')
        changement_parcours = (
            nouveau_parcours_id
            and nouveau_parcours_id != inscription.parcours_id
        )
        for champ in INSCRIPTION_CHAMPS:
            if champ in request.data and champ != 'parcours_id':
                valeur = request.data[champ]
                setattr(inscription, champ, valeur if valeur != '' else None)
        if changement_parcours:
            from .models import Parcours
            nouveau_parcours = Parcours.objects.filter(pk=nouveau_parcours_id).first()
            if nouveau_parcours is None:
                return Response({'parcours_id': ['Parcours introuvable.']}, status=400)
            inscription_services.changer_parcours(
                inscription, nouveau_parcours, acteur=request.user,
                motif=request.data.get('motif_parcours', ''),
            )
        try:
            inscription.full_clean(exclude=['date_validation'])
        except ValidationError as erreur:
            return Response(erreur.message_dict, status=400)
        inscription.save()
    return Response(_serialize_inscription(inscription, detail=True))


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSecretariatOrDFRC])
def inscription_transition(request, pk):
    inscription = _inscription_queryset().filter(pk=pk).first()
    if inscription is None:
        return Response({'error': 'Introuvable'}, status=404)
    statut = request.data.get('statut')
    if statut not in InscriptionAdministrative.Statut.values:
        return Response({'statut': ['Statut inconnu.']}, status=400)
    try:
        inscription_services.appliquer_transition(
            inscription, statut, acteur=request.user,
            commentaire=request.data.get('commentaire', ''),
        )
    except inscription_services.InscriptionImpossible as erreur:
        return Response({'error': erreur.messages[0]}, status=409)
    return Response(_serialize_inscription(inscription, detail=True))


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSecretariatOrDFRC])
def inscrire_depuis_admission(request):
    """Convertit une admission en inscription administrative, en une transaction."""
    admission = Admission.objects.select_related(
        'candidature', 'candidat', 'annee_academique', 'ref_formation', 'niveau',
    ).filter(pk=request.data.get('admission_id')).first()
    if admission is None:
        return Response({'admission_id': ['Admission introuvable.']}, status=400)

    surcharges = {
        champ: request.data[champ]
        for champ in INSCRIPTION_CHAMPS
        if request.data.get(champ) not in (None, '')
    }
    try:
        inscription = inscription_services.convertir_admission_en_inscription(
            admission,
            acteur=request.user,
            matricule=request.data.get('matricule') or None,
            valider=bool(request.data.get('valider')),
            **surcharges,
        )
    except inscription_services.InscriptionImpossible as erreur:
        return Response({'error': erreur.messages[0]}, status=409)
    except ValidationError as erreur:
        return Response(getattr(erreur, 'message_dict', {'error': str(erreur)}), status=400)
    return Response(_serialize_inscription(inscription, detail=True), status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSecretariatOrDFRC])
def inscription_stats(request):
    """Effectifs inscrits, par statut puis par niveau, formation, vague et catégorie."""
    queryset = InscriptionAdministrative.objects.all()
    if 'annee_academique_id' in request.query_params:
        queryset = queryset.filter(annee_academique_id=request.query_params['annee_academique_id'])

    validees = queryset.filter(statut=InscriptionAdministrative.Statut.VALIDEE)

    def repartition(champ, libelle):
        return {
            (ligne[libelle] or 'Non renseigné'): ligne['total']
            for ligne in validees.values(libelle).annotate(total=Count('id')).order_by()
        }

    return Response({
        'total': queryset.count(),
        'par_statut': {
            ligne['statut']: ligne['total']
            for ligne in queryset.values('statut').annotate(total=Count('id'))
        },
        'inscrits': validees.count(),
        'par_niveau': repartition('niveau', 'niveau__code'),
        'par_formation': repartition('ref_formation', 'ref_formation__intitule'),
        'par_vague': repartition('vague', 'vague__libelle'),
        'par_categorie': repartition('categorie', 'categorie__libelle'),
    })


# ── Lot L1/L3 — radiation, changement de parcours, clôture d'année ───────────


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSecretariatOrDFRC])
def inscription_radier(request, pk):
    """Radie une inscription VALIDEE : statut SUSPENDUE + événement RADIATION.

    Aucune donnée n'est supprimée (dossier, notes, historique intacts).
    """
    inscription = _inscription_queryset().filter(pk=pk).first()
    if inscription is None:
        return Response({'error': 'Introuvable'}, status=404)
    try:
        inscription_services.radier_inscription(
            inscription, acteur=request.user,
            motif=request.data.get('motif', ''),
        )
    except inscription_services.InscriptionImpossible as erreur:
        return Response({'error': erreur.messages}, status=400)
    return Response(_serialize_inscription(inscription, detail=True))


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSecretariatOrDFRC])
def inscription_changer_parcours(request, pk):
    """Changement de parcours — historisé (JournalScolarite + REORIENTATION)."""
    inscription = _inscription_queryset().filter(pk=pk).first()
    if inscription is None:
        return Response({'error': 'Introuvable'}, status=404)
    from .models import Parcours
    nouveau_parcours = Parcours.objects.filter(pk=request.data.get('parcours_id')).first()
    if nouveau_parcours is None:
        return Response({'error': 'Parcours introuvable.'}, status=400)
    try:
        inscription_services.changer_parcours(
            inscription, nouveau_parcours, acteur=request.user,
            motif=request.data.get('motif', ''),
        )
    except inscription_services.InscriptionImpossible as erreur:
        return Response({'error': erreur.messages}, status=400)
    return Response(_serialize_inscription(inscription, detail=True))


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSecretariatOrDFRC])
def annee_cloturer(request, pk):
    """Clôture une année académique (plus aucune nouvelle inscription)."""
    from .models import AnneeAcademique
    from . import annee_services
    annee = AnneeAcademique.objects.filter(pk=pk).first()
    if annee is None:
        return Response({'error': 'Introuvable'}, status=404)
    try:
        annee_services.cloturer_annee(annee, acteur=request.user,
                                      commentaire=request.data.get('commentaire', ''))
    except ValidationError as erreur:
        return Response({'error': erreur.messages}, status=400)
    return Response({
        'id': annee.id, 'libelle': annee.libelle,
        'cloturee': annee.cloturee, 'date_cloture': annee.date_cloture,
        'courante': annee.courante,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSecretariatOrDFRC])
def annee_rouvrir(request, pk):
    """Réouvre une année clôturée : elle redevient l'année courante."""
    from .models import AnneeAcademique
    from . import annee_services
    annee = AnneeAcademique.objects.filter(pk=pk).first()
    if annee is None:
        return Response({'error': 'Introuvable'}, status=404)
    try:
        annee_services.rouvrir_annee(annee, acteur=request.user,
                                     commentaire=request.data.get('commentaire', ''))
    except ValidationError as erreur:
        return Response({'error': erreur.messages}, status=400)
    return Response({
        'id': annee.id, 'libelle': annee.libelle,
        'cloturee': annee.cloturee, 'courante': annee.courante,
    })
