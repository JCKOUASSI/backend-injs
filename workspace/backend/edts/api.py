"""API du lot L8 — Emploi du temps.

Pattern @api_view cohérent avec administrations / finances_etudiantes.
Permissions :
- lecture pour tout authentifié ;
- création/édition réservée aux rôles de planification (Secrétariat, Chef Secrétariat,
  DFRC, DIRECTION, ADMIN, ENCADRANT) ;
- validation et publication réservées à DIRECTION/ADMIN.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from . import services
from .models import (
    AffectationCreneau,
    CreneauTemplate,
    ConflitCreneau,
    EmploiDuTemps,
)
from .permissions import (
    IsEdtPlanification,
    IsEdtValidation,
    IsEdtReadOnlyOrPlanification,
)


# ---------------------------------------------------------------------------
# Sérialiseurs légers
# ---------------------------------------------------------------------------


def _serialize_creneau_template(c):
    return {
        'id': c.id,
        'jour': c.jour,
        'heure_debut': c.heure_debut.isoformat() if c.heure_debut else None,
        'heure_fin': c.heure_fin.isoformat() if c.heure_fin else None,
        'duree_prevue_minutes': c.duree_prevue_minutes,
        'duree_heures': c.duree_heures,
    }


def _serialize_emploi_du_temps(e):
    return {
        'id': e.id,
        'titre': e.titre,
        'statut': e.statut,
        'annee_academique_id': e.annee_academique_id,
        'annee_academique': str(e.annee_academique),
        'population_type': e.population_type,
        'population_id': e.population_id,
        'population_label': e._population_label,
        'rentree': e.rentree.isoformat() if e.rentree else None,
        'semaine_debut': e.semaine_debut,
        'semaine_fin': e.semaine_fin,
        'creneaux_count': e.creneaux.count(),
        'affectations_count': e.affectations.count(),
        'conflits_count': e.conflits.filter(actif=True).count(),
        'cree_par': str(e.cree_par) if e.cree_par_id else None,
        'created_at': e.created_at.isoformat(),
        'updated_at': e.updated_at.isoformat(),
    }


def _serialize_affectation(a):
    return {
        'id': a.id,
        'emploi_du_temps_id': a.emploi_du_temps_id,
        'creneau_template_id': a.creneau_template_id,
        'creneau': _serialize_creneau_template(a.creneau_template) if a.creneau_template_id else None,
        'semaine_debut': a.semaine_debut,
        'semaine_fin': a.semaine_fin,
        'formation_id': a.formation_id,
        'formation': str(a.formation) if a.formation_id else None,
        'groupe_id': a.groupe_id,
        'groupe': str(a.groupe) if a.groupe_id else None,
        'enseignant_id': a.enseignant_id,
        'enseignant_nom': a.enseignant_nom,
        'nature': a.nature,
        'intitule': a.intitule,
        'commentaire': a.commentaire,
        'actif': a.actif,
        'cree_par': str(a.cree_par) if a.cree_par_id else None,
        'created_at': a.created_at.isoformat(),
        'updated_at': a.updated_at.isoformat(),
    }


def _serialize_conflit(c):
    return {
        'id': c.id,
        'emploi_du_temps_id': c.emploi_du_temps_id,
        'type_conflit': c.type_conflit,
        'description': c.description,
        'lignes_creneaux': c.lignes_creneaux,
        'actif': c.actif,
        'signale_par': str(c.signale_par) if c.signale_par_id else None,
        'created_at': c.created_at.isoformat(),
        'recalcule_le': c.recalcule_le.isoformat(),
    }


# ---------------------------------------------------------------------------
# Vues d'API
# ---------------------------------------------------------------------------


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def creneau_templates_api(request):
    creneaux = CreneauTemplate.objects.all().order_by('jour', 'heure_debut')
    data = [_serialize_creneau_template(c) for c in creneaux]
    return Response(data)


@api_view(['GET', 'POST'])
@permission_classes([IsEdtPlanification])
def creneau_template_detail_api(request, pk):
    try:
        c = CreneauTemplate.objects.get(pk=pk)
    except CreneauTemplate.DoesNotExist:
        return Response({'detail': 'Créneau type introuvable'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(_serialize_creneau_template(c))

    c.jour = request.data.get('jour', c.jour)
    c.heure_debut = request.data.get('heure_debut', c.heure_debut)
    c.heure_fin = request.data.get('heure_fin', c.heure_fin)
    c.full_clean()
    c.save()
    return Response(_serialize_creneau_template(c))


@api_view(['GET', 'POST'])
@permission_classes([IsEdtReadOnlyOrPlanification])
def emplois_du_temps_api(request):
    if request.method == 'GET':
        edts = EmploiDuTemps.objects.select_related('annee_academique', 'cree_par').order_by('-updated_at')
        data = [_serialize_emploi_du_temps(e) for e in edts]
        return Response(data)

    data = request.data
    e = EmploiDuTemps.objects.create(
        annee_academique_id=data.get('annee_academique_id'),
        population_type=data.get('population_type', 'FORMATION'),
        population_id=data.get('population_id'),
        population_denominateur=data.get('population_denominateur', ''),
        titre=data.get('titre', ''),
        statut=data.get('statut', 'BROUILLON'),
        rentree=data.get('rentree'),
        cree_par=request.user,
    )
    return Response(_serialize_emploi_du_temps(e), status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsEdtPlanification])
def emploi_du_temps_detail_api(request, pk):
    try:
        e = EmploiDuTemps.objects.get(pk=pk)
    except EmploiDuTemps.DoesNotExist:
        return Response({'detail': 'Emploi du temps introuvable'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(_serialize_emploi_du_temps(e))

    if request.method in ('PUT', 'PATCH'):
        data = request.data
        e.titre = data.get('titre', e.titre)
        e.population_denominateur = data.get('population_denominateur', e.population_denominateur)
        e.statut = data.get('statut', e.statut)
        e.rentree = data.get('rentree', e.rentree)
        e.save()
        return Response(_serialize_emploi_du_temps(e))

    if request.method == 'DELETE':
        e.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsEdtValidation])
def emploi_du_temps_valider_api(request, pk):
    try:
        e = EmploiDuTemps.objects.get(pk=pk)
    except EmploiDuTemps.DoesNotExist:
        return Response({'detail': 'Emploi du temps introuvable'}, status=status.HTTP_404_NOT_FOUND)

    new_statut = request.data.get('statut', 'VALIDE')
    if new_statut not in ('VALIDE', 'PUBLIE'):
        return Response({'detail': 'Statut de validation invalide'}, status=status.HTTP_400_BAD_REQUEST)

    e.statut = new_statut
    e.save()
    return Response(_serialize_emploi_du_temps(e))


@api_view(['POST'])
@permission_classes([IsEdtPlanification])
def emploi_du_temps_detecter_conflits_api(request, pk):
    try:
        e = EmploiDuTemps.objects.get(pk=pk)
    except EmploiDuTemps.DoesNotExist:
        return Response({'detail': 'Emploi du temps introuvable'}, status=status.HTTP_404_NOT_FOUND)

    stats = services.detecter_conflits(e)
    conflits = [
        _serialize_conflit(c) for c in e.conflits.filter(actif=True).order_by('-recalcule_le')
    ]
    return Response({
        'stats': stats,
        'conflits': conflits,
    })


@api_view(['GET', 'POST'])
@permission_classes([IsEdtReadOnlyOrPlanification])
def affectations_api(request):
    if request.method == 'GET':
        affects = AffectationCreneau.objects.select_related(
            'emploi_du_temps', 'creneau_template', 'formation', 'groupe'
        ).order_by('emploi_du_temps', 'creneau_template__jour', 'creneau_template__heure_debut')
        data = [_serialize_affectation(a) for a in affects]
        return Response(data)

    data = request.data
    a = AffectationCreneau.objects.create(
        emploi_du_temps_id=data.get('emploi_du_temps_id'),
        creneau_template_id=data.get('creneau_template_id'),
        semaine_debut=data.get('semaine_debut'),
        semaine_fin=data.get('semaine_fin'),
        salle_nom=data.get('salle_nom', ''),
        formation_id=data.get('formation_id'),
        groupe_id=data.get('groupe_id'),
        enseignant_id=data.get('enseignant_id'),
        enseignant_nom=data.get('enseignant_nom', ''),
        nature=data.get('nature', 'COURS'),
        intitule=data.get('intitule', ''),
        commentaire=data.get('commentaire', ''),
        cree_par=request.user,
    )
    return Response(_serialize_affectation(a), status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsEdtPlanification])
def affectation_detail_api(request, pk):
    try:
        a = AffectationCreneau.objects.get(pk=pk)
    except AffectationCreneau.DoesNotExist:
        return Response({'detail': 'Affectation introuvable'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        return Response(_serialize_affectation(a))
    if request.method in ('PUT', 'PATCH'):
        data = request.data
        a.semaine_debut = data.get('semaine_debut', a.semaine_debut)
        a.semaine_fin = data.get('semaine_fin', a.semaine_fin)
        a.salle_nom = data.get('salle_nom', a.salle_nom)
        a.nature = data.get('nature', a.nature)
        a.intitule = data.get('intitule', a.intitule)
        a.commentaire = data.get('commentaire', a.commentaire)
        a.actif = data.get('actif', a.actif)
        if 'formation_id' in data:
            a.formation_id = data['formation_id']
        if 'groupe_id' in data:
            a.groupe_id = data['groupe_id']
        if 'enseignant_id' in data:
            a.enseignant_id = data['enseignant_id']
            a.enseignant_nom = data.get('enseignant_nom', a.enseignant_nom)
        a.full_clean()
        a.save()
        return Response(_serialize_affectation(a))
    if request.method == 'DELETE':
        a.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def conflits_api(request):
    if request.method == 'GET':
        conflits = ConflitCreneau.objects.select_related('emploi_du_temps', 'signale_par').order_by('-recalcule_le')
        data = [_serialize_conflit(c) for c in conflits]
        return Response(data)
    data = request.data
    c = ConflitCreneau.objects.create(
        emploi_du_temps_id=data.get('emploi_du_temps_id'),
        type_conflit=data.get('type_conflit', 'MANUEL'),
        description=data.get('description', ''),
        lignes_creneaux=data.get('lignes_creneaux', []),
        signale_par=request.user,
    )
    return Response(_serialize_conflit(c), status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsEdtPlanification])
def conflit_resoudre_api(request, pk):
    try:
        c = ConflitCreneau.objects.get(pk=pk)
    except ConflitCreneau.DoesNotExist:
        return Response({'detail': 'Conflit introuvable'}, status=status.HTTP_404_NOT_FOUND)
    c.actif = False
    c.save(update_fields=['actif', 'recalcule_le'])
    return Response(_serialize_conflit(c))


@api_view(['GET'])
def edt_publics_api(request):
    edts = EmploiDuTemps.objects.filter(
        statut__in=['VALIDE', 'PUBLIE'], actif=True
    ).select_related('annee_academique').order_by('annee_academique', 'titre')
    data = [
        {
            'id': e.id,
            'titre': e.titre or e.population_denominateur,
            'statut': e.statut,
            'annee_academique_id': e.annee_academique_id,
            'annee_academique': str(e.annee_academique),
            'population_type': e.population_type,
            'population_id': e.population_id,
            'population_label': e.population_denominateur,
        }
        for e in edts
    ]
    return Response(data)

