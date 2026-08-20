"""Statistiques académiques INJS — agrégations LMD (pas un clone CPFAE).

Mécanismes repris de SYGEP-CPFAE : filtre de périmètre, payload par sections,
formule de taux, seuils d'alerte. Dimensions et règles : programmes, spécialités,
ECTS, inscriptions, délibérations, frais étudiants.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncMonth

from apps.academics.models import AcademicYear, Department, Program, TeachingUnit
from apps.exams.models import Deliberation, Grade
from apps.faculty.models import Teacher
from apps.finance.models import StudentFee
from apps.students.models import AcademicRecord, Enrollment, Student

DEGREE_LABELS = {
    'L': 'Licence',
    'M': 'Master',
    'D': 'Doctorat',
    'DU': 'Diplôme Universitaire',
}

STATUS_LABELS = {
    'active': 'Actif',
    'suspended': 'Suspendu',
    'graduated': 'Diplômé',
    'withdrawn': 'Retiré',
}

ALL_SECTIONS = ('kpis', 'pedagogiques', 'admin', 'historique', 'alertes')

ALERT_THRESHOLDS = {
    'taux_validation_ects': {'warn': 70, 'crit': 50, 'inverse': True},
    'taux_reussite': {'warn': 70, 'crit': 50, 'inverse': True},
    'taux_impayes': {'warn': 20, 'crit': 40, 'inverse': False},
    'inscriptions_en_attente': {'warn': 15, 'crit': 30, 'inverse': False},
}


@dataclass
class StatsScope:
    academic_year_id: str | None = None
    department_id: str | None = None
    program_id: str | None = None
    specialization_id: str | None = None
    degree_type: str | None = None


def parse_scope(params) -> StatsScope:
    degree = (params.get('degree_type') or '').strip().upper() or None
    if degree and degree not in DEGREE_LABELS:
        degree = None
    return StatsScope(
        academic_year_id=params.get('academic_year') or None,
        department_id=params.get('department') or None,
        program_id=params.get('program') or None,
        specialization_id=params.get('specialization') or None,
        degree_type=degree,
    )


def parse_sections(raw) -> list[str]:
    if not raw:
        return list(ALL_SECTIONS)
    requested = [part.strip() for part in str(raw).split(',') if part.strip()]
    return [section for section in requested if section in ALL_SECTIONS] or list(ALL_SECTIONS)


def rate(numerator, denominator) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator) * 100, 1)


def build_academic_statistics(scope: StatsScope, sections: list[str] | None = None) -> dict:
    sections = sections or list(ALL_SECTIONS)
    students = _student_qs(scope)
    payload = {
        'filtre': _filtre_payload(scope, students.count()),
    }
    pedagogiques = None
    admin = None
    kpis = None

    if 'kpis' in sections or 'alertes' in sections:
        kpis = _kpis(scope, students)
    if 'pedagogiques' in sections or 'alertes' in sections:
        pedagogiques = _pedagogiques(scope, students)
    if 'admin' in sections or 'alertes' in sections:
        admin = _admin(scope, students)

    if 'kpis' in sections:
        payload['kpis'] = kpis
    if 'pedagogiques' in sections:
        payload['pedagogiques'] = pedagogiques
    if 'admin' in sections:
        payload['admin'] = admin
    if 'historique' in sections:
        payload['historique'] = _historique(students)
    if 'alertes' in sections:
        payload['alertes'] = _alertes(kpis, pedagogiques, admin)
    return payload


def analytics_compat_payload(scope: StatsScope | None = None) -> dict:
    """Conserve le contrat historique de /reports/analytics/."""
    data = build_academic_statistics(scope or StatsScope(), sections=['kpis', 'pedagogiques'])
    kpis = data['kpis']
    return {
        'total_students': kpis['students_active'],
        'total_teachers': kpis['teachers_active'],
        'pending_fees': kpis['fees_pending'],
        'paid_fees': kpis['fees_paid'],
        'average_grade': kpis['average_grade'],
        'passing_rates': data['pedagogiques']['passing_rates'],
    }


def _student_qs(scope: StatsScope):
    qs = Student.objects.select_related(
        'program', 'promotion', 'specialization', 'program__department',
    )
    if scope.program_id:
        qs = qs.filter(program_id=scope.program_id)
    if scope.department_id:
        qs = qs.filter(program__department_id=scope.department_id)
    if scope.specialization_id:
        qs = qs.filter(specialization_id=scope.specialization_id)
    if scope.degree_type:
        qs = qs.filter(program__degree_type=scope.degree_type)
    if scope.academic_year_id:
        qs = qs.filter(enrollments__academic_year_id=scope.academic_year_id).distinct()
    return qs


def _filtre_payload(scope: StatsScope, student_count: int) -> dict:
    year_label = None
    if scope.academic_year_id:
        year = AcademicYear.objects.filter(id=scope.academic_year_id).first()
        year_label = year.label if year else scope.academic_year_id
    return {
        'academic_year': scope.academic_year_id,
        'academic_year_label': year_label,
        'department': scope.department_id,
        'program': scope.program_id,
        'specialization': scope.specialization_id,
        'degree_type': scope.degree_type,
        'students_in_scope': student_count,
    }


def _kpis(scope: StatsScope, students):
    fees = _fee_qs(scope, students)
    grades = _grade_qs(scope, students)
    enrollments = _enrollment_qs(scope, students)
    teachers = Teacher.objects.filter(is_active=True)
    if scope.department_id:
        teachers = teachers.filter(department_id=scope.department_id)

    programs = Program.objects.filter(is_deleted=False, is_active=True)
    if scope.department_id:
        programs = programs.filter(department_id=scope.department_id)
    if scope.degree_type:
        programs = programs.filter(degree_type=scope.degree_type)

    departments = Department.objects.filter(is_deleted=False)
    teaching_units = TeachingUnit.objects.filter(is_deleted=False)
    if scope.department_id:
        teaching_units = teaching_units.filter(department_id=scope.department_id)

    avg_grade = grades.filter(score__isnull=False).aggregate(avg=Avg('score'))['avg']
    records = _record_qs(scope, students)
    credits = records.aggregate(
        acquired=Sum('credits_acquired'),
        total=Sum('credits_total'),
    )

    return {
        'students_total': students.count(),
        'students_active': students.filter(status='active').count(),
        'teachers_active': teachers.count(),
        'programs_active': programs.count(),
        'departments': departments.count(),
        'teaching_units': teaching_units.count(),
        'enrollments_approved': enrollments.filter(status='approved').count(),
        'enrollments_pending': enrollments.filter(status='pending').count(),
        'fees_pending': fees.filter(status='pending').count(),
        'fees_paid': fees.filter(status='paid').count(),
        'fees_overdue': fees.filter(status='overdue').count(),
        'average_grade': round(float(avg_grade), 2) if avg_grade is not None else None,
        'credits_acquired': int(credits['acquired'] or 0),
        'credits_total': int(credits['total'] or 0),
        'taux_validation_ects': rate(credits['acquired'] or 0, credits['total'] or 0),
    }


def _pedagogiques(scope: StatsScope, students):
    by_degree = [
        {
            'code': row['program__degree_type'],
            'label': DEGREE_LABELS.get(row['program__degree_type'], row['program__degree_type']),
            'total': row['total'],
        }
        for row in students.values('program__degree_type').annotate(total=Count('id')).order_by('program__degree_type')
    ]
    by_status = [
        {
            'code': row['status'],
            'label': STATUS_LABELS.get(row['status'], row['status']),
            'total': row['total'],
        }
        for row in students.values('status').annotate(total=Count('id')).order_by('status')
    ]
    by_specialization = [
        {
            'code': row['specialization__code'] or 'TC',
            'name': row['specialization__name'] or 'Non renseignée',
            'total': row['total'],
        }
        for row in students.values('specialization__code', 'specialization__name')
        .annotate(total=Count('id'))
        .order_by('-total')[:12]
    ]
    by_program = [
        {
            'code': row['program__code'],
            'name': row['program__name'],
            'degree_type': row['program__degree_type'],
            'total': row['total'],
        }
        for row in students.values('program__code', 'program__name', 'program__degree_type')
        .annotate(total=Count('id'))
        .order_by('-total')[:12]
    ]

    men = students.filter(gender='M').count()
    women = students.filter(gender='F').count()
    gendered = men + women

    grades = _grade_qs(scope, students).filter(score__isnull=False, is_absent=False)
    graded = grades.count()
    passed = grades.filter(score__gte=10).count()

    records = _record_qs(scope, students)
    record_count = records.count()
    validated = records.filter(is_validated=True).count()
    avg_record = records.aggregate(avg=Avg('semester_average'))['avg']

    enrollments = _enrollment_qs(scope, students)
    pedagogical = enrollments.filter(enrollment_type='pedagogical')
    administrative = enrollments.filter(enrollment_type='administrative')

    passing_rates = []
    deliberations = Deliberation.objects.select_related('program', 'promotion', 'exam_session').filter(
        status='published',
    )
    if scope.program_id:
        deliberations = deliberations.filter(program_id=scope.program_id)
    if scope.academic_year_id:
        deliberations = deliberations.filter(exam_session__academic_year_id=scope.academic_year_id)
    if scope.department_id:
        deliberations = deliberations.filter(program__department_id=scope.department_id)
    for deliberation in deliberations.order_by('-deliberation_date', '-created_at')[:8]:
        summary = deliberation.results_summary or {}
        passing_rates.append({
            'program': deliberation.program.name,
            'promotion': deliberation.promotion.name,
            'rate': summary.get('passing_rate', 0),
        })

    return {
        'by_degree': by_degree,
        'by_status': by_status,
        'by_specialization': by_specialization,
        'by_program': by_program,
        'gender': {
            'men': men,
            'women': women,
            'pct_men': rate(men, gendered),
            'pct_women': rate(women, gendered),
        },
        'grades_entered': graded,
        'grades_passed': passed,
        'taux_reussite': rate(passed, graded),
        'records_total': record_count,
        'records_validated': validated,
        'taux_semestres_valides': rate(validated, record_count),
        'average_semester': round(float(avg_record), 2) if avg_record is not None else None,
        'inscriptions_pedagogiques': pedagogical.count(),
        'inscriptions_pedagogiques_validees': pedagogical.filter(status='approved').count(),
        'inscriptions_administratives': administrative.count(),
        'inscriptions_administratives_validees': administrative.filter(status='approved').count(),
        'passing_rates': passing_rates,
    }


def _admin(scope: StatsScope, students):
    fees = _fee_qs(scope, students)
    fee_totals = fees.aggregate(due=Sum('amount_due'), paid=Sum('amount_paid'))
    due = fee_totals['due'] or 0
    paid = fee_totals['paid'] or 0
    enrollments = _enrollment_qs(scope, students)
    pending = enrollments.filter(status='pending').count()
    total_enrollments = enrollments.count()

    teachers = Teacher.objects.filter(is_active=True)
    if scope.department_id:
        teachers = teachers.filter(department_id=scope.department_id)
    by_grade = [
        {'code': row['grade'], 'total': row['total']}
        for row in teachers.values('grade').annotate(total=Count('id')).order_by('grade')
    ]

    return {
        'fees_due': float(due),
        'fees_collected': float(paid),
        'taux_recouvrement': rate(paid, due),
        'taux_impayes': rate(fees.filter(status__in=['pending', 'overdue', 'partial']).count(), fees.count()),
        'inscriptions_en_attente': pending,
        'taux_inscriptions_en_attente': rate(pending, total_enrollments),
        'teachers_by_grade': by_grade,
        'programs_by_degree': [
            {
                'code': row['degree_type'],
                'label': DEGREE_LABELS.get(row['degree_type'], row['degree_type']),
                'total': row['total'],
            }
            for row in Program.objects.filter(is_deleted=False, is_active=True)
            .values('degree_type')
            .annotate(total=Count('id'))
            .order_by('degree_type')
        ],
    }


def _historique(students):
    start = date.today().replace(day=1)
    months = []
    year, month = start.year, start.month
    for _ in range(12):
        months.append(f'{year:04d}-{month:02d}')
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    months.reverse()

    created = {
        row['month'].strftime('%Y-%m'): row['total']
        for row in students.annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total=Count('id'))
        if row['month']
    }
    enrolled = {
        row['month'].strftime('%Y-%m'): row['total']
        for row in Enrollment.objects.filter(student__in=students, status='approved')
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total=Count('id'))
        if row['month']
    }
    return {
        'months': months,
        'students_created': [created.get(key, 0) for key in months],
        'enrollments_approved': [enrolled.get(key, 0) for key in months],
    }


def _alertes(kpis, pedagogiques, admin):
    values = {
        'taux_validation_ects': (kpis or {}).get('taux_validation_ects'),
        'taux_reussite': (pedagogiques or {}).get('taux_reussite'),
        'taux_impayes': (admin or {}).get('taux_impayes'),
        'inscriptions_en_attente': (admin or {}).get('taux_inscriptions_en_attente'),
    }
    labels = {
        'taux_validation_ects': 'Validation ECTS',
        'taux_reussite': 'Taux de réussite (notes ≥ 10)',
        'taux_impayes': 'Frais non soldés',
        'inscriptions_en_attente': 'Inscriptions en attente',
    }
    items = []
    for code, value in values.items():
        threshold = ALERT_THRESHOLDS[code]
        niveau = _alert_level(value, threshold['warn'], threshold['crit'], threshold['inverse'])
        items.append({
            'code': code,
            'label': labels[code],
            'value': value,
            'seuil_avertissement': threshold['warn'],
            'seuil_critique': threshold['crit'],
            'niveau': niveau,
        })
    return {
        'ok': sum(1 for item in items if item['niveau'] == 'ok'),
        'avertissement': sum(1 for item in items if item['niveau'] == 'avertissement'),
        'critique': sum(1 for item in items if item['niveau'] == 'critique'),
        'indicateurs': items,
    }


def _alert_level(value, warn, crit, inverse) -> str:
    if value is None:
        return 'non_configure'
    if inverse:
        if value < crit:
            return 'critique'
        if value < warn:
            return 'avertissement'
        return 'ok'
    if value > crit:
        return 'critique'
    if value > warn:
        return 'avertissement'
    return 'ok'


def _fee_qs(scope: StatsScope, students):
    qs = StudentFee.objects.filter(student__in=students)
    if scope.academic_year_id:
        qs = qs.filter(fee_type__academic_year_id=scope.academic_year_id)
    return qs


def _grade_qs(scope: StatsScope, students):
    qs = Grade.objects.filter(student__in=students)
    if scope.academic_year_id:
        qs = qs.filter(evaluation__exam_session__academic_year_id=scope.academic_year_id)
    return qs


def _enrollment_qs(scope: StatsScope, students):
    qs = Enrollment.objects.filter(student__in=students)
    if scope.academic_year_id:
        qs = qs.filter(academic_year_id=scope.academic_year_id)
    return qs


def _record_qs(scope: StatsScope, students):
    qs = AcademicRecord.objects.filter(student__in=students)
    if scope.academic_year_id:
        qs = qs.filter(academic_year_id=scope.academic_year_id)
    return qs
