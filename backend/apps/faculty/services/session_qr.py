import base64
import io
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from urllib.parse import parse_qs, quote, unquote, urlparse

import qrcode
from django.conf import settings
from django.utils import timezone

from apps.faculty.models import Attendance, AttendanceSession, Schedule, StaffAttendance

SESSION_PREFIX = 'INJS:SESSION:'
SESSION_PATTERN = re.compile(
    r'^INJS:SESSION:(?P<schedule_id>[0-9a-f-]{36}):(?P<session_date>\d{4}-\d{2}-\d{2})$'
)

# Fenêtre de badgeage (style SYGEP, adaptée campus INJS)
GRACE_BEFORE_MINUTES = 30
GRACE_AFTER_MINUTES = 30


class SessionQrError(Exception):
    def __init__(self, message, code='invalid'):
        super().__init__(message)
        self.code = code


def build_session_payload(schedule_id, session_date: date) -> str:
    return f'{SESSION_PREFIX}{schedule_id}:{session_date.isoformat()}'


def extract_session_token(raw: str) -> str:
    """Accepte payload brut ou URL deep-link …/etudiant/presences?token=… (alias badgeage)."""
    value = (raw or '').strip()
    if not value:
        return value
    if 'token=' in value:
        if value.startswith('http://') or value.startswith('https://'):
            qs = parse_qs(urlparse(value).query)
            tok = (qs.get('token') or [None])[0]
            if tok:
                return unquote(tok)
        match = re.search(r'token=([^&\s#]+)', value)
        if match:
            return unquote(match.group(1))
    return value


def parse_session_payload(payload: str) -> tuple[str, date]:
    token = extract_session_token(payload)
    match = SESSION_PATTERN.match(token)
    if not match:
        raise SessionQrError('QR de séance invalide', 'invalid_token')
    return match.group('schedule_id'), date.fromisoformat(match.group('session_date'))


def frontend_base_url(request=None) -> str:
    configured = getattr(settings, 'INJS_FRONTEND_URL', None) or 'http://127.0.0.1:5173'
    if request:
        origin = request.headers.get('Origin') or request.headers.get('Referer')
        if origin:
            parsed = urlparse(origin)
            if parsed.scheme and parsed.netloc:
                return f'{parsed.scheme}://{parsed.netloc}'
    return configured.rstrip('/')


def build_badge_url(payload: str, request=None) -> str:
    base = frontend_base_url(request)
    return f'{base}/etudiant/presences?token={quote(payload, safe="")}'


def generate_session_qr_image(data: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#0D47A1', back_color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('ascii')


def get_schedule_or_raise(schedule_id: str) -> Schedule:
    try:
        schedule = Schedule.objects.select_related(
            'assignment__course',
            'assignment__promotion',
            'assignment__teacher__user',
            'room',
        ).get(pk=schedule_id, is_active=True)
    except Schedule.DoesNotExist as exc:
        raise SessionQrError('Créneau introuvable', 'schedule_not_found') from exc
    return schedule


def validate_session_date(schedule: Schedule, session_date: date) -> None:
    today = timezone.localdate()
    if session_date < today - timedelta(days=1):
        raise SessionQrError('Cette séance est expirée', 'expired')
    if session_date > today + timedelta(days=1):
        raise SessionQrError('Date de séance invalide', 'future_date')
    if session_date.weekday() != schedule.day_of_week:
        raise SessionQrError(
            f'Ce QR correspond à un cours du {schedule.get_day_of_week_display()}, pas à cette date',
            'wrong_day',
        )


def validate_session_time_window(schedule: Schedule, session_date: date) -> None:
    """Contrôle la fenêtre horaire du créneau (SYGEP-like)."""
    now = timezone.localtime()
    today = now.date()
    if session_date != today:
        # Autoriser J-1 / J+1 uniquement hors fenêtre stricte si admin force — pour badgeage : jour exact
        raise SessionQrError(
            'Le badgeage n\'est autorisé que le jour de la séance',
            'wrong_day',
        )

    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(session_date, schedule.start_time), tz)
    end_dt = timezone.make_aware(datetime.combine(session_date, schedule.end_time), tz)
    open_at = start_dt - timedelta(minutes=GRACE_BEFORE_MINUTES)
    close_at = end_dt + timedelta(minutes=GRACE_AFTER_MINUTES)

    if now < open_at:
        raise SessionQrError(
            f'Badgeage pas encore ouvert (dès {open_at.strftime("%H:%M")})',
            'too_early',
        )
    if now > close_at:
        raise SessionQrError(
            f'Fenêtre de badgeage terminée (jusqu\'à {close_at.strftime("%H:%M")})',
            'too_late',
        )


def assert_is_admin(user) -> None:
    if user.is_superuser or user.get_group_level() <= 2:
        return
    raise SessionQrError('Seule l\'administration peut gérer les séances de badgeage', 'admin_only')


def schedule_supervisor(schedule: Schedule):
    return schedule.resolved_supervisor()


def is_session_formateur(teacher, schedule: Schedule) -> bool:
    return bool(teacher) and schedule.assignment.teacher_id == teacher.id


def is_session_encadrant(teacher, schedule: Schedule) -> bool:
    supervisor = schedule_supervisor(schedule)
    return bool(teacher and supervisor and supervisor.id == teacher.id)


def assert_can_view_session(user, schedule: Schedule) -> None:
    if user.is_superuser or user.get_group_level() <= 2:
        return
    teacher = getattr(user, 'teacher_profile', None)
    if teacher and (is_session_formateur(teacher, schedule) or is_session_encadrant(teacher, schedule)):
        return
    raise SessionQrError('Accès non autorisé à cette séance', 'forbidden')


def assert_can_mark_attendance(user, schedule: Schedule) -> None:
    """Admin, formateur ou encadrant de la séance."""
    if user.is_superuser or user.get_group_level() <= 2:
        return
    teacher = getattr(user, 'teacher_profile', None)
    if teacher and (is_session_formateur(teacher, schedule) or is_session_encadrant(teacher, schedule)):
        return
    raise SessionQrError('Vous ne pouvez pas saisir les présences de cette séance', 'forbidden')


def ensure_sessions_for_date(session_date: date) -> list[AttendanceSession]:
    """Ouvre automatiquement les séances selon l'emploi du temps (créneaux du jour)."""
    today = timezone.localdate()
    if session_date < today - timedelta(days=1) or session_date > today + timedelta(days=1):
        return list(
            AttendanceSession.objects.filter(session_date=session_date, is_active=True)
            .select_related('schedule__assignment__course')
        )

    weekday = session_date.weekday()
    schedules = Schedule.objects.filter(
        is_active=True,
        day_of_week=weekday,
    ).select_related(
        'assignment__course',
        'assignment__teacher__user',
        'assignment__promotion',
        'room',
    )

    sessions = []
    for schedule in schedules:
        session, created = AttendanceSession.objects.get_or_create(
            schedule=schedule,
            session_date=session_date,
            defaults={'is_active': True},
        )
        if created:
            from apps.faculty.services.campus_ops import seed_session_roster
            try:
                seed_session_roster(session, default_status='absent')
            except Exception:
                pass
            try:
                seed_staff_roster(session)
            except Exception:
                pass
        else:
            try:
                seed_staff_roster(session)
            except Exception:
                pass
        if session.is_active:
            sessions.append(session)
    return sessions


def get_active_session(schedule: Schedule, session_date: date) -> AttendanceSession:
    ensure_sessions_for_date(session_date)
    try:
        session = AttendanceSession.objects.get(
            schedule=schedule,
            session_date=session_date,
            is_active=True,
        )
    except AttendanceSession.DoesNotExist as exc:
        raise SessionQrError(
            'Séance non disponible pour ce créneau. Vérifiez l\'emploi du temps.',
            'session_not_open',
        ) from exc
    return session


def build_session_qr_data(schedule: Schedule, session_date: date, request=None) -> dict:
    payload = build_session_payload(str(schedule.id), session_date)
    badge_url = build_badge_url(payload, request=request)
    # QR encode l'URL deep-link (scan téléphone → page étudiant)
    return {
        'schedule': schedule.id,
        'date': session_date,
        'payload': payload,
        'badge_url': badge_url,
        'qr_image_base64': generate_session_qr_image(badge_url),
        'course_name': schedule.assignment.course.name,
        'course_code': schedule.assignment.course.code,
        'day_display': schedule.get_day_of_week_display(),
        'start_time': schedule.start_time,
        'end_time': schedule.end_time,
        'room_name': schedule.room.name if schedule.room_id else None,
        'room_code': schedule.room.code if schedule.room_id else None,
        'promotion_name': schedule.assignment.promotion.name,
        'teacher_name': schedule.assignment.teacher.user.get_full_name(),
        'supervisor_name': (
            schedule_supervisor(schedule).user.get_full_name()
            if schedule_supervisor(schedule) else None
        ),
        'session_kind': schedule.session_kind,
        'session_kind_display': schedule.get_session_kind_display(),
        'grace_before_minutes': GRACE_BEFORE_MINUTES,
        'grace_after_minutes': GRACE_AFTER_MINUTES,
    }


def assert_can_manage_session(user, schedule: Schedule) -> None:
    assert_can_view_session(user, schedule)


def check_in_student(*, student, schedule: Schedule, session_date: date, recorded_by=None) -> Attendance:
    if student.promotion_id != schedule.assignment.promotion_id:
        raise SessionQrError('Ce cours ne concerne pas votre promotion', 'wrong_promotion')
    if student.status != 'active':
        raise SessionQrError('Profil étudiant inactif', 'inactive_student')

    validate_session_date(schedule, session_date)
    validate_session_time_window(schedule, session_date)
    get_active_session(schedule, session_date)

    attendance, created = Attendance.objects.get_or_create(
        student=student,
        schedule=schedule,
        date=session_date,
        defaults={'status': 'present', 'recorded_by': recorded_by},
    )
    if not created:
        if attendance.status == 'present':
            raise SessionQrError('Vous avez déjà badgé cette séance', 'already_scanned')
        if attendance.status == 'absent':
            # Late if after start
            now = timezone.localtime()
            tz = timezone.get_current_timezone()
            start_dt = timezone.make_aware(datetime.combine(session_date, schedule.start_time), tz)
            attendance.status = 'late' if now > start_dt + timedelta(minutes=10) else 'present'
            attendance.recorded_by = recorded_by
            attendance.save(update_fields=['status', 'recorded_by', 'updated_at'])
            created = True
    return attendance, created


def presence_status_label(gender: str, status: str) -> str:
    """Libellé accordé au genre : Présent / Présente."""
    feminine = (gender or '') == 'F'
    if status == 'present':
        return 'Présente' if feminine else 'Présent'
    if status == 'late':
        return 'En retard'
    if status == 'excused':
        return 'Excusée' if feminine else 'Excusé'
    if status == 'absent':
        return 'Absente' if feminine else 'Absent'
    return status


def force_badge_students(session, student_ids, recorded_by=None, motif='', status='present'):
    """
    Forçage admin du badgeage (un ou plusieurs étudiants), hors fenêtre horaire.
    """
    if not session:
        raise SessionQrError('Séance introuvable', 'session_not_found')
    if status not in dict(Attendance.STATUSES):
        status = 'present'
    if not student_ids:
        raise SessionQrError('Aucun étudiant sélectionné', 'no_students')

    from apps.students.models import Student

    promotion = session.schedule.assignment.promotion
    students = list(
        Student.objects.filter(
            id__in=student_ids,
            promotion=promotion,
            status='active',
        ).select_related('user')
    )
    found = {str(s.id) for s in students}
    missing = [sid for sid in student_ids if str(sid) not in found]
    if missing:
        raise SessionQrError(
            'Certains étudiants ne font pas partie de la promotion de la séance.',
            'student_not_in_promotion',
        )

    updated = 0
    created = 0
    results = []
    for student in students:
        attendance, was_created = Attendance.objects.get_or_create(
            student=student,
            schedule=session.schedule,
            date=session.session_date,
            defaults={'status': status, 'recorded_by': recorded_by},
        )
        if was_created:
            created += 1
        elif attendance.status != status:
            attendance.status = status
            attendance.recorded_by = recorded_by
            attendance.save(update_fields=['status', 'recorded_by', 'updated_at'])
            updated += 1
        results.append({
            'student_id': str(student.id),
            'matricule': student.matricule,
            'name': student.user.get_full_name(),
            'gender': student.gender or '',
            'status': status,
            'status_label': presence_status_label(student.gender, status),
        })

    return {
        'forced': created + updated,
        'created': created,
        'updated': updated,
        'motif': motif or '',
        'students': results,
        'session_id': str(session.id),
    }


def seed_staff_roster(session, recorded_by=None, default_status='absent'):
    """Pré-enregistre formateur et encadrant (absent) pour la séance."""
    if not session:
        return {'created': 0}
    schedule = session.schedule
    created = 0
    staff = [
        ('formateur', schedule.assignment.teacher),
        ('encadrant', schedule_supervisor(schedule)),
    ]
    for role, person in staff:
        if not person:
            continue
        _, was_created = StaffAttendance.objects.get_or_create(
            teacher=person,
            schedule=schedule,
            date=session.session_date,
            role=role,
            defaults={'status': default_status, 'recorded_by': recorded_by},
        )
        if was_created:
            created += 1
    return {'created': created, 'session_id': str(session.id)}


def record_staff_attendance(*, teacher, schedule, session_date, role, recorded_by=None, status='present'):
    attendance, created = StaffAttendance.objects.get_or_create(
        teacher=teacher,
        schedule=schedule,
        date=session_date,
        role=role,
        defaults={'status': status, 'recorded_by': recorded_by},
    )
    if not created and attendance.status != status:
        attendance.status = status
        attendance.recorded_by = recorded_by
        attendance.save(update_fields=['status', 'recorded_by', 'updated_at'])
    return attendance, created


def check_in_teacher(*, teacher, schedule: Schedule, session_date: date) -> AttendanceSession:
    if not is_session_formateur(teacher, schedule):
        raise SessionQrError('Ce cours ne vous est pas assigné comme formateur', 'wrong_teacher')
    validate_session_date(schedule, session_date)
    session = get_active_session(schedule, session_date)
    if not session.teacher_checked_in:
        session.teacher_checked_in = True
        session.teacher_checked_in_at = timezone.now()
        session.teacher_checked_in_by = teacher
        session.save(update_fields=[
            'teacher_checked_in', 'teacher_checked_in_at', 'teacher_checked_in_by', 'updated_at',
        ])
    record_staff_attendance(
        teacher=teacher, schedule=schedule, session_date=session_date,
        role='formateur', recorded_by=teacher.user, status='present',
    )
    seed_staff_roster(session, recorded_by=teacher.user)
    return session


def check_in_supervisor(*, teacher, schedule: Schedule, session_date: date) -> AttendanceSession:
    if not is_session_encadrant(teacher, schedule):
        raise SessionQrError('Vous n\'êtes pas encadrant de cette séance', 'wrong_supervisor')
    validate_session_date(schedule, session_date)
    session = get_active_session(schedule, session_date)
    if not session.supervisor_checked_in:
        session.supervisor_checked_in = True
        session.supervisor_checked_in_at = timezone.now()
        session.supervisor_checked_in_by = teacher
        session.save(update_fields=[
            'supervisor_checked_in', 'supervisor_checked_in_at', 'supervisor_checked_in_by', 'updated_at',
        ])
    record_staff_attendance(
        teacher=teacher, schedule=schedule, session_date=session_date,
        role='encadrant', recorded_by=teacher.user, status='present',
    )
    seed_staff_roster(session, recorded_by=teacher.user)
    return session


def check_in_staff(*, teacher, schedule: Schedule, session_date: date) -> dict:
    """Badgeage formateur et/ou encadrant selon le rôle sur le créneau."""
    is_formateur = is_session_formateur(teacher, schedule)
    is_encadrant = is_session_encadrant(teacher, schedule)
    if not is_formateur and not is_encadrant:
        raise SessionQrError('Ce cours ne vous est pas assigné', 'wrong_teacher')

    session = None
    roles = []
    if is_formateur:
        session = check_in_teacher(teacher=teacher, schedule=schedule, session_date=session_date)
        roles.append('formateur')
    if is_encadrant:
        session = check_in_supervisor(teacher=teacher, schedule=schedule, session_date=session_date)
        roles.append('encadrant')
    role = 'formateur_encadrant' if len(roles) > 1 else roles[0]
    return {
        'session': session,
        'role': role,
        'roles': roles,
        'teacher_checked_in': session.teacher_checked_in,
        'supervisor_checked_in': session.supervisor_checked_in,
    }


def mark_student_attendances(session, student_ids, status='present', recorded_by=None, notes=''):
    """Saisie manuelle des présences étudiants (formateur / encadrant / admin)."""
    if status not in dict(Attendance.STATUSES):
        raise SessionQrError('Statut de présence invalide', 'invalid_status')
    if not student_ids:
        raise SessionQrError('Aucun étudiant sélectionné', 'no_students')

    from apps.students.models import Student

    promotion = session.schedule.assignment.promotion
    students = list(
        Student.objects.filter(
            id__in=student_ids,
            promotion=promotion,
            status='active',
        ).select_related('user')
    )
    found = {str(s.id) for s in students}
    missing = [sid for sid in student_ids if str(sid) not in found]
    if missing:
        raise SessionQrError(
            'Certains étudiants ne font pas partie de la promotion de la séance.',
            'student_not_in_promotion',
        )

    updated = created = 0
    results = []
    for student in students:
        attendance, was_created = Attendance.objects.get_or_create(
            student=student,
            schedule=session.schedule,
            date=session.session_date,
            defaults={'status': status, 'recorded_by': recorded_by, 'notes': notes},
        )
        if was_created:
            created += 1
        elif attendance.status != status or (notes and attendance.notes != notes):
            attendance.status = status
            attendance.recorded_by = recorded_by
            if notes:
                attendance.notes = notes
            attendance.save(update_fields=['status', 'recorded_by', 'notes', 'updated_at'])
            updated += 1
        results.append({
            'student_id': str(student.id),
            'matricule': student.matricule,
            'name': student.user.get_full_name(),
            'status': status,
            'status_label': presence_status_label(student.gender, status),
        })
    return {
        'marked': created + updated,
        'created': created,
        'updated': updated,
        'status': status,
        'students': results,
        'session_id': str(session.id),
    }


def notify_session_absences(session):
    """Notifie les étudiants encore absents à la fermeture de séance."""
    from apps.notifications.models import Notification

    course = session.schedule.assignment.course
    absents = Attendance.objects.filter(
        schedule=session.schedule,
        date=session.session_date,
        status='absent',
    ).select_related('student__user')
    created = 0
    for row in absents:
        _, was = Notification.objects.get_or_create(
            recipient=row.student.user,
            notification_type='absence',
            title=f'Absence — {course.code} ({session.session_date.isoformat()})',
            defaults={
                'message': (
                    f"Vous êtes marqué(e) absent(e) au cours {course.name} "
                    f"du {session.session_date.isoformat()}."
                ),
                'data': {
                    'schedule_id': str(session.schedule_id),
                    'session_id': str(session.id),
                    'date': session.session_date.isoformat(),
                },
            },
        )
        if was:
            created += 1
    return created


def absence_report(*, promotion=None, academic_year=None, student=None, teaching_unit=None):
    """Taux d'absence étudiants (seuil LMD) pour une promo / UE."""
    from django.conf import settings

    qs = Attendance.objects.all()
    if student:
        qs = qs.filter(student=student)
    if promotion:
        qs = qs.filter(student__promotion=promotion)
    if academic_year:
        qs = qs.filter(schedule__assignment__academic_year=academic_year)
    if teaching_unit:
        qs = qs.filter(schedule__assignment__course__teaching_unit=teaching_unit)

    qs = qs.select_related('student__user', 'schedule__assignment__course')
    by_student = defaultdict(lambda: {'present': 0, 'absent': 0, 'late': 0, 'excused': 0, 'total': 0})
    for row in qs:
        bucket = by_student[str(row.student_id)]
        bucket['name'] = row.student.user.get_full_name()
        bucket['matricule'] = row.student.matricule
        bucket['student_id'] = str(row.student_id)
        bucket['total'] += 1
        bucket[row.status] = bucket.get(row.status, 0) + 1

    max_rate = float(getattr(settings, 'LMD_MAX_ABSENCE_RATE', 0.25))
    results = []
    for data in by_student.values():
        total = data['total'] or 1
        rate = round(data.get('absent', 0) / total, 3)
        data['absence_rate'] = rate
        data['absence_rate_percent'] = round(rate * 100, 1)
        data['exceeds_threshold'] = rate > max_rate
        results.append(data)
    results.sort(key=lambda r: r['absence_rate'], reverse=True)
    return {
        'threshold': max_rate,
        'count': len(results),
        'exceeding': sum(1 for r in results if r['exceeds_threshold']),
        'results': results,
    }


def staff_session_payload(session) -> dict:
    if not session:
        return {
            'teacher_checked_in': False,
            'supervisor_checked_in': False,
            'staff': [],
        }
    rows = StaffAttendance.objects.filter(
        schedule=session.schedule, date=session.session_date,
    ).select_related('teacher__user')
    return {
        'teacher_checked_in': session.teacher_checked_in,
        'supervisor_checked_in': session.supervisor_checked_in,
        'staff': [
            {
                'teacher_id': str(r.teacher_id),
                'name': r.teacher.user.get_full_name(),
                'role': r.role,
                'role_display': r.get_role_display(),
                'status': r.status,
                'status_display': r.get_status_display(),
            }
            for r in rows
        ],
    }


def attendance_dashboard_stats(user, session_date: date | None = None) -> dict:
    """KPIs badgeage pour tableaux de bord admin / professeur / étudiant."""
    from django.db.models import Q

    day = session_date or timezone.localdate()
    ensure_sessions_for_date(day)

    sessions_qs = AttendanceSession.objects.filter(session_date=day).select_related(
        'schedule__assignment__course',
        'schedule__assignment__teacher',
        'schedule__assignment__supervisor',
        'schedule__assignment__promotion',
        'schedule__supervisor',
        'schedule__room',
    )

    student = getattr(user, 'student_profile', None)
    teacher = getattr(user, 'teacher_profile', None)
    is_admin = user.is_superuser or user.get_group_level() <= 2

    if teacher and not is_admin:
        sessions_qs = sessions_qs.filter(
            Q(schedule__assignment__teacher=teacher)
            | Q(schedule__supervisor=teacher)
            | Q(schedule__assignment__supervisor=teacher)
        )
    elif student and not is_admin:
        sessions_qs = sessions_qs.filter(schedule__assignment__promotion_id=student.promotion_id)

    open_sessions = sessions_qs.filter(is_active=True)
    closed = sessions_qs.filter(is_active=False).count()

    schedule_ids = list(open_sessions.values_list('schedule_id', flat=True))
    attendances = Attendance.objects.filter(date=day, schedule_id__in=schedule_ids)
    if student and not is_admin:
        attendances = attendances.filter(student=student)

    present = attendances.exclude(status='absent').count()
    absent = attendances.filter(status='absent').count()
    late = attendances.filter(status='late').count()
    total_roster = present + absent
    rate = round(100 * present / total_roster, 1) if total_roster else 0

    teacher_ok = open_sessions.filter(teacher_checked_in=True).count()
    supervisor_ok = open_sessions.filter(supervisor_checked_in=True).count()
    staff_rows = StaffAttendance.objects.filter(date=day, schedule_id__in=schedule_ids)
    formateurs_present = staff_rows.filter(role='formateur').exclude(status='absent').count()
    encadrants_present = staff_rows.filter(role='encadrant').exclude(status='absent').count()
    staff_total = staff_rows.count()
    staff_rate = round(100 * staff_rows.exclude(status='absent').count() / staff_total, 1) if staff_total else 0

    my_today = None
    if student:
        my_rows = list(
            Attendance.objects.filter(student=student, date=day)
            .select_related('schedule__assignment__course', 'student')
            .order_by('schedule__start_time')
        )
        my_today = [
            {
                'course_code': a.schedule.assignment.course.code,
                'course_name': a.schedule.assignment.course.name,
                'status': a.status,
                'status_display': a.get_status_display(),
                'status_label': presence_status_label(a.student.gender, a.status),
                'gender': a.student.gender or '',
                'start_time': a.schedule.start_time.strftime('%H:%M'),
            }
            for a in my_rows
        ]

    present_rows = list(
        attendances.exclude(status='absent')
        .select_related('student__user', 'schedule__assignment__course')
        .order_by('schedule__start_time', 'student__matricule')[:80]
    )
    present_students = [
        {
            'attendance_id': str(a.id),
            'student_id': str(a.student_id),
            'matricule': a.student.matricule,
            'name': a.student.user.get_full_name(),
            'gender': a.student.gender or '',
            'status': a.status,
            'status_label': presence_status_label(a.student.gender, a.status),
            'course_code': a.schedule.assignment.course.code,
            'course_name': a.schedule.assignment.course.name,
            'start_time': a.schedule.start_time.strftime('%H:%M'),
        }
        for a in present_rows
    ]

    upcoming = []
    for s in open_sessions.order_by('schedule__start_time')[:8]:
        upcoming.append({
            'id': str(s.id),
            'course_code': s.schedule.assignment.course.code,
            'course_name': s.schedule.assignment.course.name,
            'promotion_name': s.schedule.assignment.promotion.name,
            'room_code': s.schedule.room.code if s.schedule.room_id else None,
            'start_time': s.schedule.start_time.strftime('%H:%M'),
            'end_time': s.schedule.end_time.strftime('%H:%M'),
            'teacher_checked_in': s.teacher_checked_in,
            'supervisor_checked_in': s.supervisor_checked_in,
            'session_kind': s.schedule.session_kind,
            'present_count': Attendance.objects.filter(
                schedule=s.schedule, date=day,
            ).exclude(status='absent').count(),
            'is_active': s.is_active,
        })

    return {
        'date': day.isoformat(),
        'sessions_open': open_sessions.count(),
        'sessions_closed': closed,
        'teachers_badged': teacher_ok,
        'supervisors_badged': supervisor_ok,
        'formateurs_present': formateurs_present,
        'encadrants_present': encadrants_present,
        'staff_attendance_rate': staff_rate,
        'present': present,
        'absent': absent,
        'late': late,
        'roster_total': total_roster,
        'attendance_rate': rate,
        'upcoming_sessions': upcoming,
        'present_students': present_students,
        'my_today': my_today,
    }
