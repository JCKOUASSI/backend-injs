"""Programmes de période : volumes d'ECUE à planifier."""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import PeriodeFormation, ProgrammePeriode
from ..serializers import ProgrammePeriodeSerializer
from ..services.common import paires_ecue_promotion, parse_uuid, promotions_filtrees

VOLUMES_PAR_NATURE = {'cm': 'hours_cm', 'td': 'hours_td', 'tp': 'hours_tp'}


class ProgrammePeriodeViewSet(viewsets.ModelViewSet):
    queryset = ProgrammePeriode.objects.select_related(
        'periode', 'course', 'course__teaching_unit', 'promotion', 'teacher__user',
        'supervisor__user', 'salle_preferee',
    ).prefetch_related('groupes')
    serializer_class = ProgrammePeriodeSerializer
    permission_module = 'academics'
    filterset_fields = ['periode', 'course', 'promotion', 'session_kind', 'teacher', 'is_active']
    search_fields = ['course__code', 'course__name', 'promotion__name']
    ordering_fields = ['periode__ordre', 'course__code']

    @action(detail=False, methods=['post'], url_path='importer-maquette')
    def importer_maquette(self, request):
        """Crée les programmes d'une période à partir de la maquette LMD.

        Pour chaque couple (ECUE, promotion) rattaché à la filière, un programme
        est créé par nature de séance (CM/TD/TP) dont le volume maquette est non nul.
        """
        periode_id = parse_uuid(request.data.get('periode'))
        periode = PeriodeFormation.objects.filter(pk=periode_id).first()
        if periode is None:
            return Response({'detail': 'Période introuvable.'}, status=status.HTTP_400_BAD_REQUEST)

        promotions = promotions_filtrees(
            department_id=parse_uuid(request.data.get('department')),
            program_id=parse_uuid(request.data.get('program')),
            promotion_id=parse_uuid(request.data.get('promotion')),
        )
        semester_number = request.data.get('semester_number')
        try:
            semester_number = int(semester_number) if semester_number not in (None, '') else None
        except (TypeError, ValueError):
            semester_number = None

        paires = paires_ecue_promotion(promotions, semester_number=semester_number)
        if not paires:
            return Response(
                {'detail': 'Aucun ECUE rattaché à ce périmètre dans la maquette.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        natures = request.data.get('session_kinds') or list(VOLUMES_PAR_NATURE)
        crees, ignores = [], 0

        for course, promotion in paires:
            for nature in natures:
                champ = VOLUMES_PAR_NATURE.get(nature)
                if not champ:
                    continue
                volume_heures = getattr(course, champ, 0) or 0
                if volume_heures <= 0:
                    continue
                programme, created = ProgrammePeriode.objects.get_or_create(
                    periode=periode,
                    course=course,
                    promotion=promotion,
                    session_kind=nature,
                    defaults={'volume_horaire_minutes': volume_heures * 60},
                )
                if created:
                    crees.append(programme)
                else:
                    ignores += 1

        return Response({
            'crees': len(crees),
            'deja_presents': ignores,
            'periode': periode.code,
            'results': ProgrammePeriodeSerializer(crees[:100], many=True).data,
        })

    @action(detail=False, methods=['post'], url_path='affecter-enseignant')
    def affecter_enseignant(self, request):
        """Affecte titulaire et/ou encadrant à plusieurs programmes d'un coup."""
        ids = request.data.get('programmes') or []
        teacher_id = request.data.get('teacher')
        supervisor_id = request.data.get('supervisor')
        if not ids:
            return Response({'detail': 'Aucun programme fourni.'}, status=status.HTTP_400_BAD_REQUEST)

        champs = {}
        if 'teacher' in request.data:
            champs['teacher_id'] = parse_uuid(teacher_id)
        if 'supervisor' in request.data:
            champs['supervisor_id'] = parse_uuid(supervisor_id)
        if not champs:
            return Response({'detail': 'Renseignez un enseignant ou un encadrant.'},
                            status=status.HTTP_400_BAD_REQUEST)

        modifies = ProgrammePeriode.objects.filter(id__in=ids).update(**champs)

        # Les séances déjà planifiées et non démarrées suivent l'affectation.
        from ..models import Seance
        Seance.objects.filter(
            programme_id__in=ids, statut='planifiee', started_at__isnull=True,
        ).update(**champs)

        return Response({'modifies': modifies})
