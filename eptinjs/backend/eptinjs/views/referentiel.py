"""Référentiel de planification : périodes, paramètres, jours fériés, groupes."""
from __future__ import annotations

from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.students.models import Student

from ..models import (
    GroupeMembre,
    GroupePedagogique,
    JourFerie,
    ParametresPlanification,
    PeriodeFormation,
    PlanningRun,
)
from ..serializers import (
    GroupeMembreSerializer,
    GroupePedagogiqueSerializer,
    JourFerieSerializer,
    ParametresPlanificationSerializer,
    PeriodeFormationSerializer,
    PlanningRunSerializer,
)
from ..services.common import parse_uuid_list


class PeriodeFormationViewSet(viewsets.ModelViewSet):
    """Périodes de formation : fenêtres calendaires de planification."""

    queryset = PeriodeFormation.objects.select_related('academic_year', 'semester')
    serializer_class = PeriodeFormationSerializer
    permission_module = 'academics'
    filterset_fields = ['academic_year', 'semester', 'statut', 'is_active']
    search_fields = ['code', 'libelle']
    ordering_fields = ['ordre', 'date_debut', 'code']

    def get_queryset(self):
        return super().get_queryset().annotate(
            seances_count=Count('seances', distinct=True),
            programmes_count=Count('programmes', distinct=True),
        ).order_by('-academic_year__start_date', 'ordre', 'date_debut')

    @action(detail=True, methods=['get', 'patch'], url_path='parametres')
    def parametres(self, request, pk=None):
        """Paramètres du moteur pour cette période (surcharge des valeurs par défaut)."""
        periode = self.get_object()
        instance = ParametresPlanification.objects.filter(periode=periode).first()

        if request.method == 'GET':
            if instance is None:
                # Renvoie les valeurs par défaut sans créer de surcharge.
                defaut = ParametresPlanification.resolve(None)
                donnees = ParametresPlanificationSerializer(defaut).data
                donnees['id'] = None
                donnees['periode'] = str(periode.id)
                donnees['herite'] = True
                return Response(donnees)
            donnees = ParametresPlanificationSerializer(instance).data
            donnees['herite'] = False
            return Response(donnees)

        if instance is None:
            base = ParametresPlanification.resolve(None)
            instance = ParametresPlanification.objects.create(
                periode=periode,
                jours_actifs=base.jours_actifs,
                matin_actif=base.matin_actif, matin_debut=base.matin_debut, matin_fin=base.matin_fin,
                soir_actif=base.soir_actif, soir_debut=base.soir_debut, soir_fin=base.soir_fin,
                duree_seance_minutes=base.duree_seance_minutes,
                max_seances_par_jour=base.max_seances_par_jour,
                tolerance_capacite_pct=base.tolerance_capacite_pct,
                verrouiller_salle_par_groupe=base.verrouiller_salle_par_groupe,
                poids_ecart_capacite=base.poids_ecart_capacite,
                poids_rotation_salle=base.poids_rotation_salle,
                poids_equilibrage_salles=base.poids_equilibrage_salles,
            )

        serializer = ParametresPlanificationSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(periode=periode)
        return Response({**serializer.data, 'herite': False})


class ParametresPlanificationViewSet(viewsets.ModelViewSet):
    """Jeu de paramètres par défaut de l'établissement (``periode`` nul)."""

    queryset = ParametresPlanification.objects.select_related('periode')
    serializer_class = ParametresPlanificationSerializer
    permission_module = 'academics'
    filterset_fields = ['periode']

    @action(detail=False, methods=['get', 'patch'], url_path='defaut')
    def defaut(self, request):
        instance = ParametresPlanification.resolve(None)
        if request.method == 'GET':
            return Response(ParametresPlanificationSerializer(instance).data)
        serializer = ParametresPlanificationSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(periode=None)
        return Response(serializer.data)


class JourFerieViewSet(viewsets.ModelViewSet):
    queryset = JourFerie.objects.select_related('institution')
    serializer_class = JourFerieSerializer
    permission_module = 'academics'
    filterset_fields = ['institution', 'is_active']
    search_fields = ['libelle']
    ordering_fields = ['date']


class GroupePedagogiqueViewSet(viewsets.ModelViewSet):
    """Sous-groupes TD/TP d'une promotion."""

    queryset = GroupePedagogique.objects.select_related('promotion', 'promotion__program')
    serializer_class = GroupePedagogiqueSerializer
    permission_module = 'academics'
    filterset_fields = ['promotion', 'is_active']
    search_fields = ['code', 'name']

    @action(detail=True, methods=['get'], url_path='membres')
    def membres(self, request, pk=None):
        groupe = self.get_object()
        membres = groupe.membres.select_related('student__user').order_by('student__matricule')
        return Response(GroupeMembreSerializer(membres, many=True).data)

    @action(detail=True, methods=['post'], url_path='ajouter-etudiants')
    def ajouter_etudiants(self, request, pk=None):
        groupe = self.get_object()
        ids = parse_uuid_list(request.data.get('students'))
        if not ids:
            return Response({'detail': 'Aucun étudiant fourni.'}, status=status.HTTP_400_BAD_REQUEST)

        eligibles = Student.objects.filter(id__in=ids, promotion=groupe.promotion)
        crees = GroupeMembre.objects.bulk_create(
            [GroupeMembre(groupe=groupe, student=etudiant) for etudiant in eligibles],
            ignore_conflicts=True,
        )
        return Response({'ajoutes': len(crees), 'effectif': groupe.effectif})

    @action(detail=True, methods=['post'], url_path='retirer-etudiants')
    def retirer_etudiants(self, request, pk=None):
        groupe = self.get_object()
        ids = parse_uuid_list(request.data.get('students'))
        supprimes, _ = GroupeMembre.objects.filter(groupe=groupe, student_id__in=ids).delete()
        return Response({'retires': supprimes, 'effectif': groupe.effectif})

    @action(detail=False, methods=['post'], url_path='repartir')
    def repartir(self, request):
        """Crée et remplit N groupes équilibrés pour une promotion.

        Équivalent de ``GroupeService.generer_automatiquement_par_grade`` : ici
        la répartition suit l'ordre des matricules, sans critère de grade.
        """
        promotion_ids = parse_uuid_list(request.data.get('promotion'))
        if not promotion_ids:
            return Response({'detail': 'Promotion requise.'}, status=status.HTTP_400_BAD_REQUEST)
        promotion_id = promotion_ids[0]

        try:
            nombre = int(request.data.get('nombre_groupes') or 0)
        except (TypeError, ValueError):
            nombre = 0
        try:
            effectif_max = int(request.data.get('effectif_max') or 30)
        except (TypeError, ValueError):
            effectif_max = 30

        etudiants = list(
            Student.objects.filter(promotion_id=promotion_id, status='active').order_by('matricule'),
        )
        if not etudiants:
            return Response({'detail': 'Aucun étudiant actif sur cette promotion.'},
                            status=status.HTTP_400_BAD_REQUEST)

        if nombre <= 0:
            nombre = max(1, -(-len(etudiants) // max(effectif_max, 1)))
        taille = -(-len(etudiants) // nombre)

        groupes = []
        for index in range(nombre):
            groupe, _ = GroupePedagogique.objects.get_or_create(
                promotion_id=promotion_id,
                code=f'G{index + 1}',
                defaults={'name': f'Groupe {index + 1}', 'effectif_max': max(taille, 1)},
            )
            GroupeMembre.objects.filter(groupe=groupe).delete()
            lot = etudiants[index * taille:(index + 1) * taille]
            GroupeMembre.objects.bulk_create(
                [GroupeMembre(groupe=groupe, student=etudiant) for etudiant in lot],
                ignore_conflicts=True,
            )
            groupes.append(groupe)

        return Response({
            'groupes': GroupePedagogiqueSerializer(groupes, many=True).data,
            'etudiants_repartis': len(etudiants),
        })


class PlanningRunViewSet(viewsets.ReadOnlyModelViewSet):
    """Historique des générations d'emploi du temps."""

    queryset = PlanningRun.objects.select_related('periode', 'started_by')
    serializer_class = PlanningRunSerializer
    permission_module = 'academics'
    filterset_fields = ['periode', 'statut', 'mode']
