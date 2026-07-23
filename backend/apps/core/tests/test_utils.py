"""Fixtures partagées pour les tests INJS."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, Permission

from apps.accounts.models import User, GroupProfile
from apps.accounts.rbac import sync_module_permissions, make_perm
from apps.academics.models import (
    AcademicYear, Department, Institution, Program, Promotion, Specialization,
)
from apps.students.models import Student

TEST_PASSWORD = 'Test@INJS2026!'


def ensure_permissions():
    sync_module_permissions()


def create_institution_bundle():
    inst = Institution.objects.create(code='INJS', name='INJS', acronym='INJS')
    dept = Department.objects.create(institution=inst, code='STAPS', name='STAPS')
    program = Program.objects.create(
        department=dept, code='L-STAPS-PL', name='Licence STAPS PL',
        degree_type='L', track='PL', total_credits=180,
    )
    promotion = Promotion.objects.create(
        program=program, name='L1-TEST', entry_year=2025, current_semester=1,
    )
    ay = AcademicYear.objects.create(
        institution=inst, label='2025-2026',
        start_date=date(2025, 9, 1), end_date=date(2026, 8, 31), is_current=True,
    )
    return inst, dept, program, promotion, ay


def create_specializations():
    specs = {}
    for code, name in (
        ('APA', 'Activités Physiques Adaptées'),
        ('EM', 'Éducation et Motricité'),
        ('ES', 'Entraînement Sportif'),
        ('MS', 'Management du Sport'),
    ):
        specs[code], _ = Specialization.objects.get_or_create(code=code, defaults={'name': name})
    return specs


def create_student(
    *,
    email='student@test.ci',
    matricule='TEST001',
    program=None,
    promotion=None,
    specialization=None,
):
    if program is None or promotion is None:
        _, _, program, promotion, _ = create_institution_bundle()
    user = User.objects.create_user(
        email=email, password=TEST_PASSWORD,
        first_name='Aya', last_name='Kone',
    )
    student = Student.objects.create(
        user=user, matricule=matricule, program=program, promotion=promotion,
        specialization=specialization, status='active',
        date_of_birth=date(2001, 1, 1), gender='F',
    )
    return user, student


def create_user_with_permission(module: str, action: str, *, level: int = 2, email: str | None = None):
    ensure_permissions()
    code = f'test_{module}_{action}'
    group, _ = Group.objects.get_or_create(name=f'INJS Test {module}.{action}')
    GroupProfile.objects.get_or_create(
        group=group,
        defaults={'code': code, 'level': level},
    )
    perm = Permission.objects.get(codename=f'{module}_{action}')
    group.permissions.add(perm)
    user = User.objects.create_user(
        email=email or f'{module}.{action}@test.ci',
        password=TEST_PASSWORD,
        first_name='Test', last_name='User',
    )
    user.groups.add(group)
    return user


def create_finance_user():
    ensure_permissions()
    group, _ = Group.objects.get_or_create(name='INJS Test Finance')
    GroupProfile.objects.get_or_create(group=group, defaults={'code': 'test_finance', 'level': 1})
    for action in ('view', 'create', 'update'):
        perm = Permission.objects.get(codename=f'finance_{action}')
        group.permissions.add(perm)
    user = User.objects.create_user(
        email='finance@test.ci', password=TEST_PASSWORD,
        first_name='Finance', last_name='User',
    )
    user.groups.add(group)
    return user


def create_students_viewer():
    return create_user_with_permission('students', 'view', level=2, email='students.view@test.ci')
