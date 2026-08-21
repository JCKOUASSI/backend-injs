"""Accès au module EDT selon les niveaux RBAC existants (pas de nouveau module)."""
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from apps.faculty.models import Seance
from apps.faculty.services.session_qr import SessionQrError, assert_is_admin


def require_edt_planner(user):
    """Génération / publication / réglages : direction et responsables (niveau ≤ 2)."""
    try:
        assert_is_admin(user)
    except SessionQrError as exc:
        raise PermissionDenied(detail=str(exc))


def is_edt_planner(user) -> bool:
    return bool(user and (user.is_superuser or user.get_group_level() <= 2))


def scope_seances(qs, user):
    if is_edt_planner(user):
        return qs
    teacher = getattr(user, 'teacher_profile', None)
    if teacher:
        return qs.filter(Q(teacher=teacher) | Q(supervisor=teacher))
    student = getattr(user, 'student_profile', None)
    if student and student.promotion_id:
        return qs.filter(
            promotion_id=student.promotion_id,
            status__in=Seance.VISIBLE_STATUSES,
        )
    return qs.none()


def scope_badge_events(qs, user):
    if is_edt_planner(user):
        return qs
    teacher = getattr(user, 'teacher_profile', None)
    if teacher:
        return qs.filter(Q(teacher=teacher) | Q(seance__teacher=teacher) | Q(seance__supervisor=teacher))
    student = getattr(user, 'student_profile', None)
    if student:
        return qs.filter(student=student)
    return qs.none()


def scope_attendances(qs, user):
    """Un formateur ne voit que ses séances ; un étudiant, que les siennes."""
    if is_edt_planner(user):
        return qs
    teacher = getattr(user, 'teacher_profile', None)
    if teacher:
        return qs.filter(
            Q(schedule__assignment__teacher=teacher)
            | Q(schedule__supervisor=teacher)
            | Q(schedule__assignment__supervisor=teacher)
            | Q(seance__teacher=teacher)
            | Q(seance__supervisor=teacher)
        )
    student = getattr(user, 'student_profile', None)
    if student:
        return qs.filter(student=student)
    return qs.none()
