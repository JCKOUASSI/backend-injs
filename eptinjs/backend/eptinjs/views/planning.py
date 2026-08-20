"""Emploi du temps : séances, génération, conflits, présences."""
from __future__ import annotations

from django.db.models import Count, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.faculty.models import Teacher
from apps.students.models import Student

from ..models import PeriodeFormation, PlanningAuditLog, Seance
from ..planning import detecter_conflits, generer_planning
from ..planning.engine import PlanificationImpossible
from ..serializers import (
    GenerationRequestSerializer,
    MarquageSerializer,
    SeanceSerializer,
    SeanceWriteSerializer,
)
from ..services import presence as presence_service
from ..services.grid import construire_grille, seances_filtrees, statistiques
from ..services.qrcode_image import payload_qr


class SeanceViewSet(viewsets.ModelViewSet):
    """CRUD des séances et opérations d'exploitation associées."""

    queryset = Seance.objects.select_related(
        'periode', 'programme', 'course', 'course__teaching_unit', 'promotion',
        'promotion__program', 'groupe', 'room', 'teacher__user', 'supervisor__user',
    )
    filterset_fields = [
        'periode', 'programme', 'course', 'promotion', 'groupe',
        'teacher', 'room', 'session_kind', 'statut', 'date',
    ]
    search_fields = ['course__code', 'course__name', 'intitule', 'promotion__name']
    ordering_fields = ['date', 'heure_debut', 'course__code']

    @property
    def permission_module(self):
        """``mon-planning`` est auto-restreint au demandeur : pas de droit « faculty » requis."""
        return None if self.action == 'mon_planning' else 'faculty'

    def get_serializer_class(self):
        if self.action in {'create', 'update', 'partial_update'}:
            return SeanceWriteSerializer
        return SeanceSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'list':
            queryset = seances_filtrees(self.request.query_params, base=queryset).annotate(
                attendus_count_annotated=Count('pointages', distinct=True),
                presents_count_annotated=Count(
                    'pointages',
                    filter=Q(pointages__statut__in=['present', 'retard', 'force']),
                    distinct=True,
                ),
            )
        return queryset

    def perform_create(self, serializer):
        seance = serializer.save(origine='manuelle')
        PlanningAuditLog.log(
            'create', actor=self.request.user, periode=seance.periode, seance=seance,
        )

    def perform_update(self, serializer):
        seance = serializer.save()
        PlanningAuditLog.log(
            'update', actor=self.request.user, periode=seance.periode, seance=seance,
        )

    def perform_destroy(self, instance):
        if instance.started_at is not None:
            raise ValueError('Une séance démarrée ne peut pas être supprimée ; annulez-la.')
        PlanningAuditLog.log(
            'delete', actor=self.request.user, periode=instance.periode,
            course=instance.course.code, date=instance.date.isoformat(),
        )
        instance.delete()

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ValueError as erreur:
            return Response({'detail': str(erreur)}, status=status.HTTP_409_CONFLICT)

    # ------------------------------------------------------------------ lecture

    @action(detail=False, methods=['get'])
    def grille(self, request):
        """Grille d'emploi du temps, toutes périodes par défaut."""
        return Response(construire_grille(request.query_params))

    @action(detail=False, methods=['get'])
    def conflits(self, request):
        periode = PeriodeFormation.objects.filter(
            pk=request.query_params.get('periode'),
        ).first() if request.query_params.get('periode') else None
        seances = list(seances_filtrees(request.query_params))
        return Response(detecter_conflits(periode, seances=seances))

    @action(detail=False, methods=['get'], url_path='statistiques')
    def statistiques_edt(self, request):
        return Response(statistiques(request.query_params))

    @action(detail=False, methods=['get'], url_path='mon-planning')
    def mon_planning(self, request):
        """Emploi du temps du professeur ou de l'étudiant connecté."""
        params = request.query_params.dict()
        params.pop('promotion', None)
        params.pop('teacher', None)
        ouvertes = Seance.objects.exclude(statut='annulee')

        etudiant = Student.objects.filter(user=request.user).first()
        if etudiant is not None:
            groupes = list(etudiant.groupes_pedagogiques.values_list('groupe_id', flat=True))
            base = ouvertes.filter(promotion_id=etudiant.promotion_id).filter(
                Q(groupe__isnull=True) | Q(groupe_id__in=groupes),
            )
            return Response({**construire_grille(params, base=base), 'profil': 'etudiant'})

        enseignant = Teacher.objects.filter(user=request.user).first()
        if enseignant is not None:
            base = ouvertes.filter(
                Q(teacher_id=enseignant.id) | Q(supervisor_id=enseignant.id),
            )
            return Response({**construire_grille(params, base=base), 'profil': 'enseignant'})

        return Response(
            {'detail': 'Aucun profil étudiant ou enseignant rattaché à ce compte.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    # ---------------------------------------------------------------- génération

    @action(detail=False, methods=['post'], url_path='generer')
    def generer(self, request):
        serializer = GenerationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data

        periode = PeriodeFormation.objects.filter(pk=donnees['periode']).first()
        if periode is None:
            return Response({'detail': 'Période introuvable.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            resultat = generer_planning(
                periode,
                promotions=donnees.get('promotions'),
                courses=donnees.get('courses'),
                mode=donnees['mode'],
                remplacer=donnees['remplacer'],
                dry_run=donnees['dry_run'],
                actor=request.user,
            )
        except PlanificationImpossible as erreur:
            return Response(
                {'detail': str(erreur), 'mode': 'strict'},
                status=status.HTTP_409_CONFLICT,
            )

        return Response({
            'synthese': resultat.synthese,
            'echecs': resultat.echecs,
            'run': str(resultat.run.id) if resultat.run else None,
            'seances': SeanceSerializer(resultat.seances[:200], many=True).data,
        })

    # ----------------------------------------------------------- cycle de séance

    @action(detail=True, methods=['post'])
    def demarrer(self, request, pk=None):
        seance = self.get_object()
        try:
            token = presence_service.demarrer_seance(seance, actor=request.user)
        except presence_service.BadgeageRefuse as erreur:
            return Response({'detail': str(erreur)}, status=status.HTTP_409_CONFLICT)
        return Response({
            'seance': SeanceSerializer(seance).data,
            'qr': payload_qr(token, request),
        })

    @action(detail=True, methods=['post'])
    def terminer(self, request, pk=None):
        seance = self.get_object()
        resultat = presence_service.cloturer_seance(seance, actor=request.user)
        return Response({'seance': SeanceSerializer(seance).data, **resultat})

    @action(detail=True, methods=['post'])
    def annuler(self, request, pk=None):
        seance = self.get_object()
        seance.statut = 'annulee'
        seance.notes = request.data.get('motif') or seance.notes
        seance.save(update_fields=['statut', 'notes', 'updated_at'])
        seance.qr_tokens.filter(is_active=True).update(is_active=False)
        PlanningAuditLog.log('update', actor=request.user, periode=seance.periode, seance=seance,
                             annulation=True)
        return Response(SeanceSerializer(seance).data)

    # ----------------------------------------------------------------- badgeage

    @action(detail=True, methods=['get', 'post'], url_path='qr')
    def qr(self, request, pk=None):
        """Récupère le jeton QR actif, ou le régénère en POST."""
        seance = self.get_object()
        regenerer = request.method == 'POST' and bool(request.data.get('regenerer'))
        if request.method == 'GET':
            token = seance.token_actif()
            if token is None:
                return Response(
                    {'detail': 'Aucun QR actif. Démarrez la séance ou régénérez un jeton.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            token = presence_service.generer_token(seance, actor=request.user, regenerer=regenerer)

        return Response({
            **payload_qr(token, request),
            'resume': presence_service.resume_seance(seance)['compteurs'],
        })

    @action(detail=True, methods=['get', 'post'], url_path='emargement')
    def emargement(self, request, pk=None):
        """Feuille d'émargement de la séance ; POST (re)constitue la liste."""
        seance = self.get_object()
        if request.method == 'POST':
            ajoutes = presence_service.constituer_liste(seance)
            return Response({**presence_service.resume_seance(seance), 'ajoutes': ajoutes})
        return Response(presence_service.resume_seance(seance))

    @action(detail=True, methods=['post'])
    def marquer(self, request, pk=None):
        seance = self.get_object()
        serializer = MarquageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data
        modifies = presence_service.marquer(
            seance,
            statut=donnees['statut'],
            students=donnees.get('students'),
            teachers=donnees.get('teachers'),
            notes=donnees.get('notes', ''),
            actor=request.user,
        )
        return Response({'modifies': modifies, **presence_service.resume_seance(seance)})

    @action(detail=True, methods=['post'], url_path='forcer-badgeage')
    def forcer_badgeage(self, request, pk=None):
        seance = self.get_object()
        try:
            taux_min = int(request.data.get('taux_min', 80))
            taux_max = int(request.data.get('taux_max', 95))
        except (TypeError, ValueError):
            taux_min, taux_max = 80, 95
        resultat = presence_service.forcer_badgeage(
            seance, taux_min=taux_min, taux_max=taux_max, actor=request.user,
        )
        return Response({**resultat, **presence_service.resume_seance(seance)})
