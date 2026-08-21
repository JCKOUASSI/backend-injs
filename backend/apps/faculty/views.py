from datetime import datetime

from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from django.db.models import Count, Q

from apps.faculty.models import (
    Teacher, Room, CourseAssignment, Schedule, Attendance, AttendanceSession,
    RoomReservation, MaintenanceTicket, EquipmentAsset, StaffAttendance,
    Seance, TeachingLoad, StudentGroup, StudentGroupMember, PlanningSettings,
    TimetableRun, GroupSchedulingConfig, BadgeEvent,
)
from apps.faculty.serializers import (
    TeacherSerializer, RoomSerializer, CourseAssignmentSerializer,
    ScheduleSerializer, AttendanceSerializer, SessionQrSerializer,
    CheckInSerializer, AttendanceSessionSerializer, AttendanceSessionCreateSerializer,
    RoomReservationSerializer, MaintenanceTicketSerializer, EquipmentAssetSerializer,
    StaffAttendanceSerializer, SeanceSerializer, TeachingLoadSerializer,
    StudentGroupSerializer, StudentGroupMemberSerializer, PlanningSettingsSerializer,
    TimetableRunSerializer, GroupSchedulingConfigSerializer, BadgeEventSerializer,
)
from apps.faculty.services.session_qr import (
    build_session_qr_data,
    build_seance_qr_data,
    get_schedule_or_raise,
    assert_can_view_session,
    assert_is_admin,
    check_in_student,
    check_in_staff,
    ensure_sessions_for_date,
    attendance_dashboard_stats,
    force_badge_students,
    mark_student_attendances,
    notify_session_absences,
    absence_report,
    seed_staff_roster,
    staff_session_payload,
    assert_can_mark_attendance,
    heartbeat_presence,
    SessionQrError,
)
from apps.faculty.services.campus_ops import (
    find_available_rooms,
    auto_assign_room,
    seed_session_roster,
    seed_schedule_roster,
    list_schedule_roster,
    add_students_to_roster,
    remove_students_from_roster,
    next_occurrence,
    sync_room_status_from_tickets,
    approve_reservation,
    CampusOpsError,
)
from apps.faculty.services.planning import (
    detect_conflicts,
    generate_for_promotion,
    generate_for_academic_year,
    timetable_grid,
    PlanningError,
    detect_seance_conflicts,
    generate_for_period,
    expand_schedules_for_period,
    publish_seances,
)
from apps.faculty.services.edt_access import (
    require_edt_planner, scope_seances, scope_badge_events, scope_attendances,
)
from apps.faculty.services.badge_security import record_badge_event
from apps.core.mixins import ExportMixin


def _truthy(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in ('1', 'true', 'yes', 'on')


class TeacherViewSet(ExportMixin, viewsets.ModelViewSet):
    queryset = Teacher.objects.select_related('user', 'department').filter(is_active=True)
    serializer_class = TeacherSerializer
    permission_module = 'faculty'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['department', 'grade']
    export_headers = ['ID', 'Nom', 'Grade', 'Département']
    export_title = 'Enseignants INJS'
    export_filename = 'enseignants_injs'

    def get_export_rows(self):
        return [
            [t.employee_id, t.user.get_full_name(), t.get_grade_display(), t.department.name]
            for t in self.filter_queryset(self.get_queryset())
        ]

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        teacher = getattr(request.user, 'teacher_profile', None)
        if not teacher:
            return Response({'detail': 'Profil enseignant introuvable'}, status=status.HTTP_404_NOT_FOUND)
        return Response(TeacherSerializer(teacher, context={'request': request}).data)


class RoomViewSet(ExportMixin, viewsets.ModelViewSet):
    queryset = Room.objects.filter(is_active=True).select_related('institution')
    serializer_class = RoomSerializer
    permission_module = 'faculty'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['institution', 'room_type', 'building', 'status']
    search_fields = ['code', 'name', 'building', 'notes']
    ordering_fields = ['code', 'name', 'capacity', 'building', 'room_type']
    ordering = ['building', 'code']
    export_headers = ['Code', 'Nom', 'Type', 'Bâtiment', 'Capacité', 'Statut', 'Étage']
    export_title = 'Salles campus INJS'
    export_filename = 'salles_injs'

    def get_export_rows(self):
        return [
            [
                r.code, r.name, r.get_room_type_display(), r.get_building_display() or r.building,
                r.capacity, r.get_status_display(), r.floor or '—',
            ]
            for r in self.filter_queryset(self.get_queryset())
        ]

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.status = 'inactive'
        instance.save(update_fields=['is_active', 'status', 'updated_at'])

    @action(detail=False, methods=['get'], url_path='meta')
    def meta(self, request):
        """Référentiels pour filtres / formulaires (types, bâtiments, statuts)."""
        return Response({
            'room_types': [{'value': v, 'label': l} for v, l in Room.ROOM_TYPES],
            'buildings': [{'value': v, 'label': l} for v, l in Room.BUILDINGS],
            'statuses': [{'value': v, 'label': l} for v, l in Room.STATUSES],
            'counts': {
                'total': self.get_queryset().count(),
                'by_building': {
                    b: self.get_queryset().filter(building=b).count()
                    for b, _ in Room.BUILDINGS
                    if self.get_queryset().filter(building=b).exists()
                },
                'by_type': {
                    t: self.get_queryset().filter(room_type=t).count()
                    for t, _ in Room.ROOM_TYPES
                    if self.get_queryset().filter(room_type=t).exists()
                },
            },
        })

    @action(detail=False, methods=['get'], url_path='available')
    def available(self, request):
        """Salles disponibles pour un créneau (capacité, équipements, type, jour, horaires)."""
        min_capacity = request.query_params.get('min_capacity')
        try:
            min_capacity = int(min_capacity) if min_capacity else 1
        except ValueError:
            min_capacity = 1

        equipment_raw = request.query_params.get('equipment') or request.query_params.get('required_equipment') or ''
        required_equipment = [e.strip() for e in equipment_raw.split(',') if e.strip()]

        day = request.query_params.get('day_of_week')
        start = request.query_params.get('start_time')
        end = request.query_params.get('end_time')
        room_type = request.query_params.get('room_type') or None
        building = request.query_params.get('building') or None

        day_int = None
        if day is not None and day != '':
            try:
                day_int = int(day)
            except ValueError:
                day_int = None

        rooms = find_available_rooms(
            min_capacity=min_capacity,
            day_of_week=day_int,
            start_time=start,
            end_time=end,
            required_equipment=required_equipment,
            room_type=room_type,
            building=building,
        )
        return Response(RoomSerializer(rooms, many=True).data)

    @action(detail=False, methods=['get'], url_path='geo')
    def geo(self, request):
        """Salles géolocalisées pour la carte campus."""
        qs = self.filter_queryset(self.get_queryset()).exclude(
            latitude__isnull=True,
        ).exclude(longitude__isnull=True)
        data = RoomSerializer(qs, many=True).data
        return Response({
            'count': len(data),
            'results': data,
            'bounds': {
                'lat_min': float(min(r.latitude for r in qs)) if qs else None,
                'lat_max': float(max(r.latitude for r in qs)) if qs else None,
                'lng_min': float(min(r.longitude for r in qs)) if qs else None,
                'lng_max': float(max(r.longitude for r in qs)) if qs else None,
            },
        })


class CourseAssignmentViewSet(viewsets.ModelViewSet):
    queryset = CourseAssignment.objects.select_related(
        'teacher__user', 'supervisor__user', 'course__teaching_unit',
        'promotion__program', 'academic_year',
    ).annotate(
        schedules_count=Count('schedules', filter=Q(schedules__is_active=True), distinct=True),
    ).all()
    serializer_class = CourseAssignmentSerializer
    permission_module = 'faculty'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['teacher', 'supervisor', 'academic_year', 'promotion', 'course']
    search_fields = [
        'course__code', 'course__name', 'course__teaching_unit__code',
        'teacher__user__first_name', 'teacher__user__last_name', 'promotion__name',
    ]
    ordering_fields = ['created_at', 'course__code', 'promotion__name']
    ordering = ['course__code']


class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.select_related(
        'assignment__course', 'assignment__teacher__user', 'assignment__supervisor__user',
        'assignment__promotion', 'assignment__academic_year', 'room', 'supervisor__user',
    ).filter(is_active=True)
    serializer_class = ScheduleSerializer
    permission_module = 'faculty'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['assignment', 'day_of_week', 'room', 'session_kind']

    def get_queryset(self):
        qs = super().get_queryset()
        promotion = self.request.query_params.get('promotion')
        teacher = self.request.query_params.get('teacher')
        academic_year = self.request.query_params.get('academic_year')
        if promotion:
            qs = qs.filter(assignment__promotion=promotion)
        if teacher:
            qs = qs.filter(
                Q(assignment__teacher=teacher)
                | Q(supervisor=teacher)
                | Q(assignment__supervisor=teacher)
            )
        if academic_year:
            qs = qs.filter(assignment__academic_year=academic_year)
        return qs

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])

    @action(detail=True, methods=['post'], url_path='auto-assign-room')
    def auto_assign_room_action(self, request, pk=None):
        schedule = self.get_object()
        equipment_raw = request.data.get('equipment') or request.data.get('required_equipment') or []
        if isinstance(equipment_raw, str):
            equipment_raw = [e.strip() for e in equipment_raw.split(',') if e.strip()]
        try:
            room = auto_assign_room(
                schedule,
                required_equipment=equipment_raw,
                room_type=request.data.get('room_type'),
            )
        except CampusOpsError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'message': f'Salle {room.code} affectée automatiquement',
            'schedule': ScheduleSerializer(schedule).data,
            'room': RoomSerializer(room).data,
        })

    def _parse_roster_date(self, request, schedule):
        """Date de séance : query/body `date`, sinon prochaine occurrence du jour du créneau."""
        raw = request.query_params.get('date') or request.data.get('date')
        if raw:
            try:
                return datetime.strptime(raw, '%Y-%m-%d').date()
            except ValueError as exc:
                raise SessionQrError('Format de date invalide (AAAA-MM-JJ)', 'invalid_date') from exc
        return next_occurrence(schedule.day_of_week, timezone.localdate())

    @action(detail=True, methods=['get'], url_path='roster')
    def roster(self, request, pk=None):
        """Liste étudiants affectés / disponibles pour un créneau + date."""
        schedule = self.get_object()
        try:
            session_date = self._parse_roster_date(request, schedule)
            data = list_schedule_roster(schedule, session_date)
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        except CampusOpsError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data)

    @action(detail=True, methods=['post'], url_path='seed-roster')
    def seed_roster(self, request, pk=None):
        """Affectation automatique : tous les étudiants actifs de la promotion."""
        schedule = self.get_object()
        default_status = request.data.get('status', 'absent')
        if default_status not in dict(Attendance.STATUSES):
            default_status = 'absent'
        try:
            session_date = self._parse_roster_date(request, schedule)
            result = seed_schedule_roster(
                schedule, session_date,
                recorded_by=request.user,
                default_status=default_status,
            )
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        except CampusOpsError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'message': f"{result['attendances_created']} étudiant(s) affecté(s) ({result['promotion']})",
            **result,
            **list_schedule_roster(schedule, session_date),
        })

    @action(detail=True, methods=['post'], url_path='add-students')
    def add_students(self, request, pk=None):
        """Ajout manuel d'étudiants au créneau (ids de la promotion)."""
        schedule = self.get_object()
        student_ids = request.data.get('student_ids') or []
        if isinstance(student_ids, str):
            student_ids = [s.strip() for s in student_ids.split(',') if s.strip()]
        default_status = request.data.get('status', 'absent')
        if default_status not in dict(Attendance.STATUSES):
            default_status = 'absent'
        try:
            session_date = self._parse_roster_date(request, schedule)
            result = add_students_to_roster(
                schedule, session_date, student_ids,
                recorded_by=request.user,
                default_status=default_status,
            )
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        except CampusOpsError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'message': f"{result['added']} étudiant(s) ajouté(s)",
            **result,
        })

    @action(detail=True, methods=['post'], url_path='remove-students')
    def remove_students(self, request, pk=None):
        """Retrait manuel d'étudiants du créneau."""
        schedule = self.get_object()
        student_ids = request.data.get('student_ids') or []
        attendance_ids = request.data.get('attendance_ids') or []
        try:
            session_date = self._parse_roster_date(request, schedule)
            result = remove_students_from_roster(
                schedule, session_date,
                student_ids=student_ids or None,
                attendance_ids=attendance_ids or None,
            )
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        except CampusOpsError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'message': f"{result['removed']} étudiant(s) retiré(s)",
            **result,
        })

    @action(detail=False, methods=['get'], url_path='conflicts')
    def conflicts(self, request):
        """Rapport de conflits EDT (salle / enseignant / promotion / capacité)."""
        qs = self.filter_queryset(self.get_queryset())
        items = detect_conflicts(qs)
        return Response({
            'count': len(items),
            'errors': sum(1 for c in items if c['severity'] == 'error'),
            'warnings': sum(1 for c in items if c['severity'] == 'warning'),
            'results': items,
        })

    @action(detail=False, methods=['get'], url_path='grid')
    def grid(self, request):
        """Grille hebdomadaire structurée pour l'UI."""
        qs = self.filter_queryset(self.get_queryset())
        return Response(timetable_grid(qs))

    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        """
        Génération automatique EDT pour une promotion (ou toutes).
        Body: academic_year, promotion?, generate_all?, replace_existing?, dry_run?,
              auto_assign_teachers?, open_sessions?, max_sessions_per_day?
        """
        from apps.academics.models import Promotion, AcademicYear
        year_id = request.data.get('academic_year')
        promo_id = request.data.get('promotion')
        generate_all = _truthy(request.data.get('generate_all'))
        if not year_id:
            return Response(
                {'detail': 'Paramètre academic_year requis'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not generate_all and not promo_id:
            return Response(
                {'detail': 'Paramètres promotion et academic_year requis (ou generate_all=true)'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        year = AcademicYear.objects.filter(pk=year_id).first()
        if not year:
            return Response({'detail': 'Année académique introuvable'}, status=status.HTTP_404_NOT_FOUND)

        kwargs = {
            'replace_existing': _truthy(request.data.get('replace_existing')),
            'max_sessions_per_day': int(request.data.get('max_sessions_per_day') or 3),
            'dry_run': _truthy(request.data.get('dry_run')),
            'auto_seed_roster': _truthy(request.data.get('auto_seed_roster'), default=True),
            'seed_from_date': request.data.get('seed_from_date'),
            'seed_weeks': int(request.data.get('seed_weeks') or 1),
            'recorded_by': request.user,
            'auto_assign_teachers': _truthy(request.data.get('auto_assign_teachers'), default=True),
            'semester_weeks': int(request.data.get('semester_weeks') or 15),
            'open_sessions': _truthy(request.data.get('open_sessions'), default=True),
        }
        try:
            if generate_all:
                result = generate_for_academic_year(year, **kwargs)
            else:
                promotion = Promotion.objects.filter(pk=promo_id).first()
                if not promotion:
                    return Response({'detail': 'Promotion introuvable'}, status=status.HTTP_404_NOT_FOUND)
                result = generate_for_promotion(promotion=promotion, academic_year=year, **kwargs)
        except PlanningError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class AttendanceSessionViewSet(viewsets.ModelViewSet):
    queryset = AttendanceSession.objects.select_related(
        'schedule__assignment__course',
        'schedule__assignment__teacher__user',
        'schedule__assignment__promotion',
        'schedule__room',
        'created_by',
    ).all()
    permission_module = 'faculty'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['schedule', 'session_date', 'is_active']

    def get_serializer_class(self):
        if self.action == 'create':
            return AttendanceSessionCreateSerializer
        return AttendanceSessionSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy', 'close', 'seed_roster'):
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or user.get_group_level() <= 2:
            return qs
        teacher = getattr(user, 'teacher_profile', None)
        if teacher:
            return qs.filter(
                Q(schedule__assignment__teacher=teacher)
                | Q(schedule__supervisor=teacher)
                | Q(schedule__assignment__supervisor=teacher)
            )
        return qs.none()

    def list(self, request, *args, **kwargs):
        session_date_param = request.query_params.get('session_date')
        if session_date_param:
            try:
                session_date = datetime.strptime(session_date_param, '%Y-%m-%d').date()
                ensure_sessions_for_date(session_date)
            except ValueError:
                pass
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        try:
            assert_is_admin(request.user)
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session, created = AttendanceSession.objects.get_or_create(
            schedule=serializer.validated_data['schedule'],
            session_date=serializer.validated_data['session_date'],
            defaults={'created_by': request.user, 'is_active': True},
        )
        if not created and not session.is_active:
            session.is_active = True
            session.created_by = request.user
            session.save(update_fields=['is_active', 'created_by', 'updated_at'])

        auto_seed = request.data.get('auto_seed_roster', True)
        roster_info = None
        if auto_seed in (True, 'true', '1', 1) and (created or not Attendance.objects.filter(
            schedule=session.schedule, date=session.session_date,
        ).exists()):
            try:
                roster_info = seed_session_roster(session, recorded_by=request.user)
            except CampusOpsError:
                roster_info = None

        output = AttendanceSessionSerializer(session, context={'request': request}).data
        qr_data = build_session_qr_data(session.schedule, session.session_date, request=request)
        payload = {**output, **qr_data}
        if roster_info:
            payload['roster'] = roster_info
        try:
            payload['staff_roster'] = seed_staff_roster(session, recorded_by=request.user)
        except Exception:
            payload['staff_roster'] = None
        payload.update(staff_session_payload(session))
        return Response(payload, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        try:
            assert_is_admin(request.user)
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        try:
            assert_is_admin(request.user)
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        try:
            assert_is_admin(request.user)
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get'], url_path='qr')
    def qr(self, request, pk=None):
        session = self.get_object()
        try:
            assert_can_view_session(request.user, session.schedule)
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_403_FORBIDDEN)
        if not session.is_active:
            return Response({'detail': 'Séance fermée'}, status=status.HTTP_400_BAD_REQUEST)
        data = build_session_qr_data(session.schedule, session.session_date, request=request)
        data['session_id'] = session.id
        data['teacher_checked_in'] = session.teacher_checked_in
        data['supervisor_checked_in'] = session.supervisor_checked_in
        return Response(SessionQrSerializer(data).data)

    @action(detail=True, methods=['post'], url_path='close')
    def close(self, request, pk=None):
        session = self.get_object()
        try:
            assert_is_admin(request.user)
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_403_FORBIDDEN)
        session.is_active = False
        session.save(update_fields=['is_active', 'updated_at'])
        notified = notify_session_absences(session)
        data = AttendanceSessionSerializer(session).data
        data['absences_notified'] = notified
        return Response(data)

    @action(detail=True, methods=['post'], url_path='force-badge')
    def force_badge(self, request, pk=None):
        """Forçage admin du badgeage d'un ou plusieurs étudiants (hors fenêtre)."""
        session = self.get_object()
        try:
            assert_is_admin(request.user)
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_403_FORBIDDEN)

        student_ids = request.data.get('student_ids') or []
        if isinstance(student_ids, str):
            student_ids = [s.strip() for s in student_ids.split(',') if s.strip()]
        motif = (request.data.get('motif') or '').strip()
        badge_status = request.data.get('status', 'present')
        try:
            result = force_badge_students(
                session,
                student_ids,
                recorded_by=request.user,
                motif=motif,
                status=badge_status,
            )
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': f"{result['forced']} badgeage(s) forcé(s)",
            **result,
        })

    @action(detail=True, methods=['post'], url_path='seed-roster')
    def seed_roster(self, request, pk=None):
        """Affecte automatiquement les étudiants de la promotion à la séance."""
        session = self.get_object()
        try:
            assert_is_admin(request.user)
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_403_FORBIDDEN)
        default_status = request.data.get('status', 'absent')
        if default_status not in dict(Attendance.STATUSES):
            default_status = 'absent'
        try:
            result = seed_session_roster(session, recorded_by=request.user, default_status=default_status)
            roster = list_schedule_roster(session.schedule, session.session_date)
        except CampusOpsError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'message': f"{result['attendances_created']} étudiant(s) affecté(s) ({result['promotion']})",
            **result,
            **roster,
        })

    @action(detail=True, methods=['get'], url_path='roster')
    def roster(self, request, pk=None):
        session = self.get_object()
        try:
            data = list_schedule_roster(session.schedule, session.session_date)
        except CampusOpsError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data)

    @action(detail=True, methods=['post'], url_path='add-students')
    def add_students(self, request, pk=None):
        session = self.get_object()
        try:
            assert_is_admin(request.user)
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_403_FORBIDDEN)
        student_ids = request.data.get('student_ids') or []
        if isinstance(student_ids, str):
            student_ids = [s.strip() for s in student_ids.split(',') if s.strip()]
        try:
            result = add_students_to_roster(
                session.schedule, session.session_date, student_ids,
                recorded_by=request.user,
                default_status=request.data.get('status', 'absent'),
            )
        except CampusOpsError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': f"{result['added']} étudiant(s) ajouté(s)", **result})

    @action(detail=True, methods=['post'], url_path='remove-students')
    def remove_students(self, request, pk=None):
        session = self.get_object()
        try:
            assert_is_admin(request.user)
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_403_FORBIDDEN)
        try:
            result = remove_students_from_roster(
                session.schedule,
                session.session_date,
                student_ids=request.data.get('student_ids') or None,
                attendance_ids=request.data.get('attendance_ids') or None,
            )
        except CampusOpsError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': f"{result['removed']} étudiant(s) retiré(s)", **result})

    @action(detail=True, methods=['post'], url_path='mark-students')
    def mark_students(self, request, pk=None):
        """Saisie manuelle des présences (formateur, encadrant ou admin)."""
        session = self.get_object()
        try:
            assert_can_mark_attendance(request.user, session.schedule)
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_403_FORBIDDEN)
        student_ids = request.data.get('student_ids') or []
        if isinstance(student_ids, str):
            student_ids = [s.strip() for s in student_ids.split(',') if s.strip()]
        try:
            result = mark_student_attendances(
                session,
                student_ids,
                status=request.data.get('status', 'present'),
                recorded_by=request.user,
                notes=request.data.get('notes') or '',
            )
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'message': f"{result['marked']} présence(s) mise(s) à jour",
            **result,
        })


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.select_related(
        'student__user', 'schedule__assignment__course', 'seance__course',
    ).order_by('-date', '-created_at')
    serializer_class = AttendanceSerializer
    permission_module = 'faculty'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['student', 'schedule', 'seance', 'date', 'status']

    def get_permissions(self):
        if self.action in ('check_in', 'heartbeat', 'dashboard_stats', 'my_history', 'absence_report', 'my_staff_history'):
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        return scope_attendances(super().get_queryset(), self.request.user)

    def perform_update(self, serializer):
        previous = serializer.instance.status
        attendance = serializer.save()
        if previous != attendance.status:
            record_badge_event(
                kind='correction',
                source='admin' if self.request.user.get_group_level() <= 2 or self.request.user.is_superuser else 'teacher',
                actor=self.request.user,
                attendance=attendance,
                previous_status=previous,
                new_status=attendance.status,
                reason=self.request.data.get('notes') or attendance.notes,
            )

    @action(detail=False, methods=['get'], url_path='dashboard-stats')
    def dashboard_stats(self, request):
        raw = request.query_params.get('date')
        session_date = None
        if raw:
            try:
                session_date = datetime.strptime(raw, '%Y-%m-%d').date()
            except ValueError:
                return Response({'detail': 'Format de date invalide'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(attendance_dashboard_stats(request.user, session_date))

    @action(detail=False, methods=['get'], url_path='my-history')
    def my_history(self, request):
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({'detail': 'Profil étudiant requis'}, status=status.HTTP_403_FORBIDDEN)
        rows = list(
            Attendance.objects.filter(student=student).select_related(
                'schedule__assignment__course', 'schedule__room',
            ).order_by('-date', 'schedule__start_time')[:50]
        )
        return Response({
            'count': len(rows),
            'results': AttendanceSerializer(rows, many=True).data,
        })

    @action(detail=False, methods=['post'], url_path='check-in')
    def check_in(self, request):
        serializer = CheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        schedule = serializer.validated_data['schedule']
        session_date = serializer.validated_data['session_date']

        student = getattr(request.user, 'student_profile', None)
        teacher = getattr(request.user, 'teacher_profile', None)

        try:
            if student:
                attendance, created = check_in_student(
                    student=student,
                    schedule=schedule,
                    session_date=session_date,
                    recorded_by=request.user,
                    badge_context=_badge_context(serializer.validated_data),
                )
                return Response({
                    'role': 'etudiant',
                    'message': 'Présence enregistrée' if created else 'Sortie enregistrée',
                    'attendance': AttendanceSerializer(attendance).data,
                    'course_name': schedule.assignment.course.name,
                    'session_date': session_date,
                }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

            if teacher:
                result = check_in_staff(
                    teacher=teacher,
                    schedule=schedule,
                    session_date=session_date,
                    badge_context=_badge_context(serializer.validated_data),
                )
                session = result['session']
                return Response({
                    'role': result['role'],
                    'roles': result['roles'],
                    'message': (
                        'Badgeage encadrant enregistré'
                        if result['role'] == 'encadrant'
                        else 'Badgeage formateur enregistré'
                    ),
                    'course_name': schedule.assignment.course.name,
                    'session_date': session_date,
                    'teacher_checked_in': session.teacher_checked_in,
                    'supervisor_checked_in': session.supervisor_checked_in,
                })

            return Response(
                {'detail': 'Profil étudiant, formateur ou encadrant requis pour badger'},
                status=status.HTTP_403_FORBIDDEN,
            )
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='heartbeat')
    def heartbeat(self, request):
        serializer = CheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = heartbeat_presence(
                user=request.user,
                schedule=serializer.validated_data['schedule'],
                session_date=serializer.validated_data['session_date'],
                badge_context=_badge_context(serializer.validated_data),
            )
            return Response({'message': 'Heartbeat enregistré', **result})
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='session-summary')
    def session_summary(self, request):
        schedule_id = request.query_params.get('schedule')
        date_param = request.query_params.get('date')
        if not schedule_id or not date_param:
            return Response(
                {'detail': 'Paramètres schedule et date requis'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            session_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            return Response({'detail': 'Format de date invalide'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            schedule = get_schedule_or_raise(schedule_id)
            assert_can_view_session(request.user, schedule)
        except SessionQrError as exc:
            status_code = status.HTTP_403_FORBIDDEN if exc.code in ('forbidden', 'admin_only') else status.HTTP_404_NOT_FOUND
            return Response({'detail': str(exc), 'code': exc.code}, status=status_code)

        session = AttendanceSession.objects.filter(
            schedule=schedule, session_date=session_date,
        ).first()

        attendances = Attendance.objects.filter(schedule=schedule, date=session_date).select_related(
            'student__user',
        ).order_by('student__matricule')
        present = attendances.exclude(status='absent').count()
        absent = attendances.filter(status='absent').count()
        present_list = AttendanceSerializer(
            attendances.exclude(status='absent'),
            many=True,
        ).data
        staff = staff_session_payload(session)
        supervisor = schedule.resolved_supervisor()
        return Response({
            'schedule': schedule_id,
            'date': session_date,
            'session_open': bool(session and session.is_active),
            'teacher_checked_in': session.teacher_checked_in if session else False,
            'supervisor_checked_in': session.supervisor_checked_in if session else False,
            'course_name': schedule.assignment.course.name,
            'course_code': schedule.assignment.course.code,
            'session_kind': schedule.session_kind,
            'teacher_name': schedule.assignment.teacher.user.get_full_name(),
            'supervisor_name': supervisor.user.get_full_name() if supervisor else None,
            'present': present,
            'absent': absent,
            'total': present + absent,
            'attendances': AttendanceSerializer(attendances, many=True).data,
            'present_list': present_list,
            **staff,
        })

    @action(detail=False, methods=['get'], url_path='absence-report')
    def absence_report(self, request):
        """Taux d'absence par étudiant (seuil LMD)."""
        student = getattr(request.user, 'student_profile', None)
        is_admin = request.user.is_superuser or request.user.get_group_level() <= 2
        student_id = request.query_params.get('student')
        if student and not is_admin:
            student_id = str(student.id)
        return Response(absence_report(
            promotion=request.query_params.get('promotion'),
            academic_year=request.query_params.get('academic_year'),
            student=student_id,
            teaching_unit=request.query_params.get('teaching_unit'),
        ))

    @action(detail=False, methods=['get'], url_path='my-staff-history')
    def my_staff_history(self, request):
        teacher = getattr(request.user, 'teacher_profile', None)
        if not teacher:
            return Response({'detail': 'Profil formateur / encadrant requis'}, status=status.HTTP_403_FORBIDDEN)
        rows = StaffAttendance.objects.filter(teacher=teacher).select_related(
            'schedule__assignment__course', 'schedule__room',
        ).order_by('-date', 'schedule__start_time')[:50]
        return Response({
            'count': rows.count() if hasattr(rows, 'count') else len(rows),
            'results': StaffAttendanceSerializer(rows, many=True).data,
        })


class StaffAttendanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StaffAttendance.objects.select_related(
        'teacher__user', 'schedule__assignment__course', 'schedule__assignment__promotion',
        'schedule__room',
    ).all()
    serializer_class = StaffAttendanceSerializer
    permission_module = 'faculty'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['teacher', 'schedule', 'date', 'role', 'status']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or user.get_group_level() <= 2:
            return qs
        teacher = getattr(user, 'teacher_profile', None)
        if teacher:
            return qs.filter(teacher=teacher)
        return qs.none()


class RoomReservationViewSet(viewsets.ModelViewSet):
    queryset = RoomReservation.objects.select_related('room', 'requested_by').all()
    serializer_class = RoomReservationSerializer
    permission_module = 'faculty'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['room', 'status']
    search_fields = ['title', 'purpose', 'room__code', 'room__name']
    ordering = ['-start_datetime']

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        reservation = self.get_object()
        try:
            approve_reservation(reservation, actor=request.user)
        except CampusOpsError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RoomReservationSerializer(reservation).data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        reservation = self.get_object()
        reservation.status = 'rejected'
        reservation.notes = (reservation.notes or '') + f"\n[Refus] {request.data.get('reason', '')}".strip()
        reservation.save(update_fields=['status', 'notes', 'updated_at'])
        return Response(RoomReservationSerializer(reservation).data)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        reservation = self.get_object()
        reservation.status = 'cancelled'
        reservation.save(update_fields=['status', 'updated_at'])
        return Response(RoomReservationSerializer(reservation).data)


class MaintenanceTicketViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceTicket.objects.select_related('room', 'reported_by', 'assigned_to').all()
    serializer_class = MaintenanceTicketSerializer
    permission_module = 'faculty'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['room', 'status', 'priority']
    search_fields = ['title', 'description', 'room__code']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        ticket = serializer.save(reported_by=self.request.user)
        sync_room_status_from_tickets(ticket.room)

    def perform_update(self, serializer):
        ticket = serializer.save()
        if ticket.status in ('resolved', 'closed') and not ticket.resolved_at:
            from django.utils import timezone
            ticket.resolved_at = timezone.now()
            ticket.save(update_fields=['resolved_at', 'updated_at'])
        sync_room_status_from_tickets(ticket.room)


class EquipmentAssetViewSet(viewsets.ModelViewSet):
    queryset = EquipmentAsset.objects.filter(is_active=True).select_related('room', 'institution')
    serializer_class = EquipmentAssetSerializer
    permission_module = 'faculty'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['institution', 'room', 'status', 'category']
    search_fields = ['code', 'name', 'serial_number', 'category']
    ordering = ['category', 'code']

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.status = 'retired'
        instance.save(update_fields=['is_active', 'status', 'updated_at'])

    @action(detail=False, methods=['post'], url_path='sync-room-tags')
    def sync_room_tags(self, request):
        """Agrège capability_tags des assets vers Room.equipment (union)."""
        room_id = request.data.get('room')
        qs = self.get_queryset()
        if room_id:
            qs = qs.filter(room_id=room_id)
        updated = 0
        rooms = {}
        for asset in qs.filter(room__isnull=False):
            rooms.setdefault(asset.room_id, set())
            for tag in (asset.capability_tags or []):
                rooms[asset.room_id].add(str(tag).lower())
        for rid, tags in rooms.items():
            room = Room.objects.filter(pk=rid).first()
            if not room:
                continue
            existing = {str(t).lower() for t in (room.equipment or [])}
            merged = sorted(existing | tags)
            room.equipment = merged
            room.save(update_fields=['equipment', 'updated_at'])
            updated += 1
        return Response({'rooms_updated': updated})


def _badge_context(data) -> dict:
    return {
        'device_id': data.get('device_id') or '',
        'device_label': data.get('device_label') or '',
        'latitude': data.get('latitude'),
        'longitude': data.get('longitude'),
        'accuracy_m': data.get('accuracy_m'),
    }


class StudentGroupViewSet(viewsets.ModelViewSet):
    queryset = StudentGroup.objects.select_related('promotion')
    serializer_class = StudentGroupSerializer
    permission_module = 'faculty'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['promotion', 'is_active']
    search_fields = ['name']


class StudentGroupMemberViewSet(viewsets.ModelViewSet):
    queryset = StudentGroupMember.objects.select_related('group', 'student__user')
    serializer_class = StudentGroupMemberSerializer
    permission_module = 'faculty'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['group', 'student']


class GroupSchedulingConfigViewSet(viewsets.ModelViewSet):
    queryset = GroupSchedulingConfig.objects.select_related('group')
    serializer_class = GroupSchedulingConfigSerializer
    permission_module = 'faculty'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['group']


class PlanningSettingsViewSet(viewsets.ModelViewSet):
    queryset = PlanningSettings.objects.select_related('period')
    serializer_class = PlanningSettingsSerializer
    permission_module = 'faculty'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['period', 'is_global']

    def perform_create(self, serializer):
        require_edt_planner(self.request.user)
        serializer.save()

    def perform_update(self, serializer):
        require_edt_planner(self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        require_edt_planner(self.request.user)
        instance.delete()

    @action(detail=False, methods=['get', 'put', 'patch'], url_path='defaults')
    def defaults(self, request):
        if request.method != 'GET':
            require_edt_planner(request.user)
        if request.method == 'GET':
            settings = PlanningSettings.resolve()
            if settings._state.adding:
                settings = PlanningSettings.set_global()
            return Response(PlanningSettingsSerializer(settings).data)
        payload = request.data.copy()
        payload.pop('period', None)
        payload.pop('id', None)
        settings = PlanningSettings.set_global(**{
            key: value for key, value in payload.items()
            if key in {field.name for field in PlanningSettings._meta.fields}
        })
        return Response(PlanningSettingsSerializer(settings).data)


class TeachingLoadViewSet(viewsets.ModelViewSet):
    queryset = TeachingLoad.objects.select_related(
        'period', 'course', 'promotion', 'group', 'teacher__user', 'supervisor__user',
    )
    serializer_class = TeachingLoadSerializer
    permission_module = 'faculty'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['period', 'course', 'promotion', 'group', 'session_kind', 'is_active']


class SeanceViewSet(ExportMixin, viewsets.ModelViewSet):
    queryset = Seance.objects.select_related(
        'course', 'promotion', 'group', 'teacher__user', 'supervisor__user',
        'room', 'period', 'schedule', 'teaching_load',
    )
    serializer_class = SeanceSerializer
    permission_module = 'faculty'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'period', 'promotion', 'course', 'group', 'teacher', 'supervisor',
        'room', 'status', 'session_kind', 'date', 'schedule',
    ]
    search_fields = ['course__code', 'course__name', 'notes']
    ordering_fields = ['date', 'start_time', 'status']
    export_headers = [
        'Date', 'Début', 'Fin', 'ECUE', 'Libellé', 'Type', 'Promotion',
        'Groupe', 'Professeur', 'Salle', 'Statut',
    ]
    export_title = 'Emploi du temps INJS'
    export_filename = 'edt_seances'

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'dashboard', 'qr', 'export'):
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        visible = str(params.get('visible') or '').lower()
        if visible in ('1', 'true', 'yes'):
            qs = qs.filter(status__in=Seance.VISIBLE_STATUSES)
        return scope_seances(qs, self.request.user)

    def get_export_rows(self):
        rows = []
        for seance in self.filter_queryset(self.get_queryset()).order_by('date', 'start_time'):
            teacher = seance.teacher.user.get_full_name() if seance.teacher_id else ''
            rows.append([
                seance.date.isoformat(),
                seance.start_time.strftime('%H:%M'),
                seance.end_time.strftime('%H:%M'),
                seance.course.code,
                seance.course.name,
                seance.get_session_kind_display(),
                seance.promotion.name,
                seance.group.name if seance.group_id else '',
                teacher,
                seance.room.code if seance.room_id else '',
                seance.get_status_display(),
            ])
        return rows

    def perform_create(self, serializer):
        require_edt_planner(self.request.user)
        serializer.save()

    def perform_update(self, serializer):
        require_edt_planner(self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        require_edt_planner(self.request.user)
        instance.delete()

    @action(detail=False, methods=['get'], url_path='conflicts')
    def conflicts(self, request):
        require_edt_planner(request.user)
        qs = self.filter_queryset(self.get_queryset())
        items = detect_seance_conflicts(qs)
        return Response({
            'count': len(items),
            'errors': sum(1 for row in items if row['severity'] == 'error'),
            'warnings': sum(1 for row in items if row['severity'] == 'warning'),
            'results': items,
        })

    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        qs = self.filter_queryset(self.get_queryset())
        today = timezone.localdate()
        by_status = dict(qs.values_list('status').annotate(total=Count('id')).values_list('status', 'total'))
        return Response({
            'total': qs.count(),
            'published': by_status.get('published', 0),
            'generated': by_status.get('generated', 0),
            'in_progress': by_status.get('in_progress', 0),
            'done': by_status.get('done', 0),
            'cancelled': by_status.get('cancelled', 0),
            'upcoming': qs.filter(date__gte=today).exclude(status__in=('cancelled', 'archived', 'done')).count(),
            'conflicts': sum(
                1 for row in detect_seance_conflicts(qs) if row['severity'] == 'error'
            ),
        })

    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        require_edt_planner(request.user)
        from apps.academics.models import FormationPeriod, Promotion
        period_id = request.data.get('period')
        promo_id = request.data.get('promotion')
        if not period_id or not promo_id:
            return Response(
                {'detail': 'Les paramètres period et promotion sont requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        period = FormationPeriod.objects.filter(pk=period_id).select_related('academic_year').first()
        promotion = Promotion.objects.filter(pk=promo_id).first()
        if not period:
            return Response({'detail': 'Période de formation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if not promotion:
            return Response({'detail': 'Promotion introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            result = generate_for_period(
                period=period,
                promotion=promotion,
                replace_existing=_truthy(request.data.get('replace_existing')),
                dry_run=_truthy(request.data.get('dry_run')),
                mode=request.data.get('mode') or 'best_effort',
                actor=request.user,
                auto_create_loads=_truthy(request.data.get('auto_create_loads'), default=True),
            )
        except PlanningError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)

    @action(detail=True, methods=['get'], url_path='qr')
    def qr(self, request, pk=None):
        seance = self.get_object()
        try:
            data = build_seance_qr_data(seance, request=request)
            schedule = get_schedule_or_raise(str(data['schedule']))
            assert_can_view_session(request.user, schedule)
        except SessionQrError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data)

    @action(detail=False, methods=['post'], url_path='expand')
    def expand(self, request):
        require_edt_planner(request.user)
        from apps.academics.models import FormationPeriod, Promotion
        period = FormationPeriod.objects.filter(pk=request.data.get('period')).first()
        promotion = Promotion.objects.filter(pk=request.data.get('promotion')).first()
        if not period or not promotion:
            return Response(
                {'detail': 'Les paramètres period et promotion sont requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = expand_schedules_for_period(
                period=period,
                promotion=promotion,
                replace_existing=_truthy(request.data.get('replace_existing')),
                dry_run=_truthy(request.data.get('dry_run')),
                actor=request.user,
            )
        except PlanningError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)

    @action(detail=False, methods=['post'], url_path='publish')
    def publish(self, request):
        require_edt_planner(request.user)
        qs = self.filter_queryset(self.get_queryset())
        if request.data.get('ids'):
            qs = qs.filter(id__in=request.data['ids'])
        if request.data.get('period'):
            qs = qs.filter(period_id=request.data['period'])
        if request.data.get('promotion'):
            qs = qs.filter(promotion_id=request.data['promotion'])
        try:
            result = publish_seances(qs, actor=request.user)
        except PlanningError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class BadgeEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BadgeEvent.objects.select_related(
        'actor', 'student__user', 'teacher__user',
        'attendance', 'staff_attendance',
        'seance__course', 'schedule__assignment__course',
    )
    serializer_class = BadgeEventSerializer
    permission_module = 'faculty'
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['kind', 'source', 'student', 'teacher', 'seance', 'schedule', 'attendance', 'session_date']
    ordering_fields = ['occurred_at']

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_queryset(self):
        return scope_badge_events(super().get_queryset(), self.request.user)


class TimetableRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TimetableRun.objects.select_related('period', 'promotion', 'actor')
    serializer_class = TimetableRunSerializer
    permission_module = 'faculty'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['period', 'promotion', 'status', 'mode']
