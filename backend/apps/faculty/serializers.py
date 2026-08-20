from rest_framework import serializers
from apps.faculty.models import (
    Teacher, Room, CourseAssignment, Schedule, Attendance, AttendanceSession,
    RoomReservation, MaintenanceTicket, EquipmentAsset, StaffAttendance,
)


class TeacherSerializer(serializers.ModelSerializer):
    user_detail = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = '__all__'

    def get_user_detail(self, obj):
        from apps.accounts.serializers import UserSerializer
        return UserSerializer(obj.user, context=self.context).data

    def get_photo_url(self, obj):
        if obj.user.photo:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.user.photo.url) if request else obj.user.photo.url
        return None


class RoomSerializer(serializers.ModelSerializer):
    room_type_display = serializers.CharField(source='get_room_type_display', read_only=True)
    building_display = serializers.CharField(source='get_building_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    schedules_count = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = '__all__'

    def get_schedules_count(self, obj):
        return obj.schedules.filter(is_active=True).count()


class CourseAssignmentSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)
    supervisor_name = serializers.CharField(source='supervisor.user.get_full_name', read_only=True, allow_null=True)
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    teaching_unit_id = serializers.UUIDField(source='course.teaching_unit_id', read_only=True)
    teaching_unit_code = serializers.CharField(source='course.teaching_unit.code', read_only=True)
    teaching_unit_name = serializers.CharField(source='course.teaching_unit.name', read_only=True)
    promotion_name = serializers.CharField(source='promotion.name', read_only=True)
    program_id = serializers.UUIDField(source='promotion.program_id', read_only=True)
    program_name = serializers.CharField(source='promotion.program.name', read_only=True)
    academic_year_name = serializers.CharField(source='academic_year.label', read_only=True)
    hours_cm = serializers.IntegerField(source='course.hours_cm', read_only=True)
    hours_td = serializers.IntegerField(source='course.hours_td', read_only=True)
    hours_tp = serializers.IntegerField(source='course.hours_tp', read_only=True)
    students_count = serializers.SerializerMethodField()
    schedules_count = serializers.SerializerMethodField()

    class Meta:
        model = CourseAssignment
        fields = '__all__'

    def get_students_count(self, obj):
        return obj.promotion.students.filter(status='active').count()

    def get_schedules_count(self, obj):
        count = getattr(obj, 'schedules_count', None)
        if count is not None:
            return count
        return obj.schedules.filter(is_active=True).count()


class ScheduleSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='assignment.course.name', read_only=True)
    course_code = serializers.CharField(source='assignment.course.code', read_only=True)
    promotion_name = serializers.CharField(source='assignment.promotion.name', read_only=True)
    teacher_name = serializers.CharField(source='assignment.teacher.user.get_full_name', read_only=True)
    supervisor_name = serializers.SerializerMethodField()
    supervisor_id = serializers.SerializerMethodField()
    room_name = serializers.CharField(source='room.name', read_only=True)
    room_code = serializers.CharField(source='room.code', read_only=True)
    room_building = serializers.CharField(source='room.building', read_only=True)
    room_capacity = serializers.IntegerField(source='room.capacity', read_only=True)
    day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    session_kind_display = serializers.CharField(source='get_session_kind_display', read_only=True)

    class Meta:
        model = Schedule
        fields = '__all__'

    def get_supervisor_name(self, obj):
        person = obj.resolved_supervisor()
        return person.user.get_full_name() if person else None

    def get_supervisor_id(self, obj):
        person = obj.resolved_supervisor()
        return str(person.id) if person else None

    def validate(self, attrs):
        """Détecte les conflits de salle (même jour, plages horaires chevauchantes)."""
        room = attrs.get('room') or getattr(self.instance, 'room', None)
        day = attrs.get('day_of_week', getattr(self.instance, 'day_of_week', None))
        start = attrs.get('start_time', getattr(self.instance, 'start_time', None))
        end = attrs.get('end_time', getattr(self.instance, 'end_time', None))
        is_active = attrs.get('is_active', getattr(self.instance, 'is_active', True))

        if room and day is not None and start and end and is_active:
            if room.status == 'maintenance':
                raise serializers.ValidationError({
                    'room': f'La salle {room.code} est en maintenance.',
                })
            if room.status == 'inactive' or not room.is_active:
                raise serializers.ValidationError({
                    'room': f'La salle {room.code} est inactive.',
                })
            qs = Schedule.objects.filter(
                room=room,
                day_of_week=day,
                is_active=True,
            ).exclude(pk=getattr(self.instance, 'pk', None))
            conflict = qs.filter(start_time__lt=end, end_time__gt=start).first()
            if conflict:
                raise serializers.ValidationError({
                    'room': (
                        f'Conflit : {room.code} déjà occupée le {conflict.get_day_of_week_display()} '
                        f'de {conflict.start_time.strftime("%H:%M")} à {conflict.end_time.strftime("%H:%M")}.'
                    ),
                })

        # Conflits enseignant / promotion (inspiré EMPCPFAE)
        assignment = attrs.get('assignment') or getattr(self.instance, 'assignment', None)
        if assignment and day is not None and start and end and is_active:
            teacher_conflict = Schedule.objects.filter(
                is_active=True,
                day_of_week=day,
                assignment__teacher=assignment.teacher,
                start_time__lt=end,
                end_time__gt=start,
            ).exclude(pk=getattr(self.instance, 'pk', None)).select_related('assignment__course').first()
            if teacher_conflict:
                raise serializers.ValidationError({
                    'assignment': (
                        f'Conflit enseignant : déjà en cours '
                        f'({teacher_conflict.assignment.course.code}) '
                        f'{teacher_conflict.start_time.strftime("%H:%M")}–'
                        f'{teacher_conflict.end_time.strftime("%H:%M")}.'
                    ),
                })
            promo_conflict = Schedule.objects.filter(
                is_active=True,
                day_of_week=day,
                assignment__promotion=assignment.promotion,
                start_time__lt=end,
                end_time__gt=start,
            ).exclude(pk=getattr(self.instance, 'pk', None)).select_related('assignment__course').first()
            if promo_conflict:
                raise serializers.ValidationError({
                    'assignment': (
                        f'Conflit promotion : déjà en cours '
                        f'({promo_conflict.assignment.course.code}) '
                        f'{promo_conflict.start_time.strftime("%H:%M")}–'
                        f'{promo_conflict.end_time.strftime("%H:%M")}.'
                    ),
                })
        return attrs


class SessionQrSerializer(serializers.Serializer):
    schedule = serializers.UUIDField()
    date = serializers.DateField()
    payload = serializers.CharField(read_only=True)
    badge_url = serializers.CharField(read_only=True, required=False)
    qr_image_base64 = serializers.CharField(read_only=True)
    course_name = serializers.CharField(read_only=True)
    course_code = serializers.CharField(read_only=True)
    day_display = serializers.CharField(read_only=True)
    start_time = serializers.TimeField(read_only=True)
    end_time = serializers.TimeField(read_only=True)
    room_name = serializers.CharField(read_only=True, allow_null=True)
    room_code = serializers.CharField(read_only=True, allow_null=True, required=False)
    promotion_name = serializers.CharField(read_only=True)
    teacher_name = serializers.CharField(read_only=True, required=False)
    supervisor_name = serializers.CharField(read_only=True, required=False, allow_null=True)
    session_kind = serializers.CharField(read_only=True, required=False)
    session_kind_display = serializers.CharField(read_only=True, required=False)
    session_id = serializers.UUIDField(required=False)
    teacher_checked_in = serializers.BooleanField(required=False)
    supervisor_checked_in = serializers.BooleanField(required=False)
    grace_before_minutes = serializers.IntegerField(required=False)
    grace_after_minutes = serializers.IntegerField(required=False)
    geofence_required = serializers.BooleanField(required=False)
    geofence_radius_m = serializers.IntegerField(required=False, allow_null=True)


class CheckInSerializer(serializers.Serializer):
    session_token = serializers.CharField()
    device_id = serializers.CharField(required=False, allow_blank=True, max_length=80)
    device_label = serializers.CharField(required=False, allow_blank=True, max_length=120)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    accuracy_m = serializers.FloatField(required=False, allow_null=True)

    def validate(self, attrs):
        from apps.faculty.services.session_qr import parse_session_payload, get_schedule_or_raise, SessionQrError
        try:
            schedule_id, session_date = parse_session_payload(attrs['session_token'])
            schedule = get_schedule_or_raise(schedule_id)
        except SessionQrError as exc:
            raise serializers.ValidationError({'session_token': str(exc)}) from exc
        attrs['schedule'] = schedule
        attrs['session_date'] = session_date
        if (attrs.get('latitude') is None) ^ (attrs.get('longitude') is None):
            raise serializers.ValidationError('latitude et longitude doivent être fournis ensemble')
        return attrs


class AttendanceSessionSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='schedule.assignment.course.name', read_only=True)
    course_code = serializers.CharField(source='schedule.assignment.course.code', read_only=True)
    teacher_name = serializers.CharField(source='schedule.assignment.teacher.user.get_full_name', read_only=True)
    supervisor_name = serializers.SerializerMethodField()
    session_kind = serializers.CharField(source='schedule.session_kind', read_only=True)
    session_kind_display = serializers.CharField(source='schedule.get_session_kind_display', read_only=True)
    promotion_name = serializers.CharField(source='schedule.assignment.promotion.name', read_only=True)
    day_display = serializers.CharField(source='schedule.get_day_of_week_display', read_only=True)
    start_time = serializers.TimeField(source='schedule.start_time', read_only=True)
    end_time = serializers.TimeField(source='schedule.end_time', read_only=True)
    room_name = serializers.CharField(source='schedule.room.name', read_only=True, allow_null=True)
    room_code = serializers.CharField(source='schedule.room.code', read_only=True, allow_null=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    present_count = serializers.SerializerMethodField()
    roster_count = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceSession
        fields = '__all__'
        read_only_fields = [
            'created_by', 'teacher_checked_in', 'teacher_checked_in_at', 'teacher_checked_in_by',
            'supervisor_checked_in', 'supervisor_checked_in_at', 'supervisor_checked_in_by',
        ]

    def get_supervisor_name(self, obj):
        person = obj.schedule.resolved_supervisor()
        return person.user.get_full_name() if person else None

    def get_present_count(self, obj):
        return Attendance.objects.filter(
            schedule=obj.schedule,
            date=obj.session_date,
        ).exclude(status='absent').count()

    def get_roster_count(self, obj):
        return Attendance.objects.filter(
            schedule=obj.schedule,
            date=obj.session_date,
        ).count()


class AttendanceSessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceSession
        fields = ['schedule', 'session_date']

    def validate(self, attrs):
        from apps.faculty.services.session_qr import get_schedule_or_raise, validate_session_date, SessionQrError
        schedule = get_schedule_or_raise(str(attrs['schedule'].id))
        session_date = attrs['session_date']
        try:
            validate_session_date(schedule, session_date)
        except SessionQrError as exc:
            raise serializers.ValidationError({'session_date': str(exc)}) from exc
        attrs['schedule'] = schedule
        return attrs


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    matricule = serializers.CharField(source='student.matricule', read_only=True)
    course_name = serializers.CharField(source='schedule.assignment.course.name', read_only=True)
    gender = serializers.CharField(source='student.gender', read_only=True)
    status_label = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Attendance
        fields = '__all__'

    def get_status_label(self, obj):
        """Présent / Présente selon le genre ; Retard / Absente / etc."""
        gender = getattr(obj.student, 'gender', '') or ''
        feminine = gender == 'F'
        if obj.status == 'present':
            return 'Présente' if feminine else 'Présent'
        if obj.status == 'late':
            return 'En retard'
        if obj.status == 'excused':
            return 'Excusée' if feminine else 'Excusé'
        if obj.status == 'absent':
            return 'Absente' if feminine else 'Absent'
        return obj.get_status_display()


class StaffAttendanceSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)
    employee_id = serializers.CharField(source='teacher.employee_id', read_only=True)
    course_name = serializers.CharField(source='schedule.assignment.course.name', read_only=True)
    course_code = serializers.CharField(source='schedule.assignment.course.code', read_only=True)
    promotion_name = serializers.CharField(source='schedule.assignment.promotion.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    session_kind = serializers.CharField(source='schedule.session_kind', read_only=True)

    class Meta:
        model = StaffAttendance
        fields = '__all__'


class RoomReservationSerializer(serializers.ModelSerializer):
    room_code = serializers.CharField(source='room.code', read_only=True)
    room_name = serializers.CharField(source='room.name', read_only=True)
    room_capacity = serializers.IntegerField(source='room.capacity', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)

    class Meta:
        model = RoomReservation
        fields = '__all__'
        read_only_fields = ['requested_by']


class MaintenanceTicketSerializer(serializers.ModelSerializer):
    room_code = serializers.CharField(source='room.code', read_only=True)
    room_name = serializers.CharField(source='room.name', read_only=True)
    building = serializers.CharField(source='room.building', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    reported_by_name = serializers.CharField(source='reported_by.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)

    class Meta:
        model = MaintenanceTicket
        fields = '__all__'
        read_only_fields = ['reported_by', 'resolved_at']


class EquipmentAssetSerializer(serializers.ModelSerializer):
    room_code = serializers.CharField(source='room.code', read_only=True, allow_null=True)
    room_name = serializers.CharField(source='room.name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = EquipmentAsset
        fields = '__all__'
