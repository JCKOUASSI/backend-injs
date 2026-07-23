"""Moteur LMD INJS — règles officielles (CC 40% / CT 60%, compensation, mentions)."""
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings


def round_grade(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _d(value) -> Decimal:
    return Decimal(str(value))


def _passing() -> Decimal:
    return _d(settings.LMD_PASSING_AVERAGE)


def _compensation_floor() -> Decimal:
    return _d(settings.LMD_COMPENSATION_FLOOR)


def _cc_weight() -> Decimal:
    return _d(settings.LMD_CC_WEIGHT)


def _ct_weight() -> Decimal:
    return _d(settings.LMD_CT_WEIGHT)


def compute_mention(average: Decimal | None) -> str | None:
    """Mentions officielles sur relevé INJS."""
    if average is None:
        return None
    avg = float(average)
    thresholds = settings.LMD_MENTION_THRESHOLDS
    if avg >= thresholds['tres_bien']:
        return 'Très bien'
    if avg >= thresholds['bien']:
        return 'Bien'
    if avg >= thresholds['assez_bien']:
        return 'Assez bien'
    if avg >= thresholds['passable']:
        return 'Passable'
    return 'Ajourné'


def _get_student_score(student, evaluation) -> Decimal | None:
    from apps.exams.models import Grade

    try:
        grade = Grade.objects.get(student=student, evaluation=evaluation)
    except Grade.DoesNotExist:
        return None
    if grade.is_absent or grade.score is None:
        return None
    return _d(grade.score)


def _mean_scores(scores: list[Decimal]) -> Decimal | None:
    if not scores:
        return None
    return round_grade(sum(scores) / len(scores))


def _ecue_from_cc_ct(cc_avg: Decimal | None, ct_avg: Decimal | None) -> Decimal | None:
    """Moyenne ECUE = CC × 40% + CT × 60%."""
    if cc_avg is not None and ct_avg is not None:
        return round_grade(cc_avg * _cc_weight() + ct_avg * _ct_weight())
    if cc_avg is not None:
        return round_grade(cc_avg)
    if ct_avg is not None:
        return round_grade(ct_avg)
    return None


def _collect_cc_ct_scores(student, evaluations) -> tuple[Decimal | None, Decimal | None]:
    cc_scores = []
    ct_scores = []
    for ev in evaluations:
        score = _get_student_score(student, ev)
        if score is None:
            continue
        if ev.evaluation_type == 'exam':
            ct_scores.append(score)
        else:
            cc_scores.append(score)
    return _mean_scores(cc_scores), _mean_scores(ct_scores)


def calculate_ecue_average(student, course, exam_session) -> dict:
    """Validation ECUE : moyenne CC/CT ≥ 10/20."""
    from apps.exams.models import Evaluation

    evaluations = Evaluation.objects.filter(
        teaching_unit=course.teaching_unit,
        course=course,
        exam_session=exam_session,
    )
    cc_avg, ct_avg = _collect_cc_ct_scores(student, evaluations)
    average = _ecue_from_cc_ct(cc_avg, ct_avg)
    passing = _passing()
    if course.passing_score is not None:
        passing = _d(course.passing_score)
    validated = average is not None and average >= passing

    return {
        'course_id': str(course.id),
        'course_code': course.code,
        'course_name': course.name,
        'coefficient': float(course.coefficient),
        'cc_average': float(cc_avg) if cc_avg is not None else None,
        'ct_average': float(ct_avg) if ct_avg is not None else None,
        'average': float(average) if average is not None else None,
        'passing_score': float(passing),
        'validated': validated,
        'mention': compute_mention(average),
    }


def _calculate_ue_level_ecue(student, teaching_unit, exam_session) -> dict:
    """Fallback ECUE unique quand la UE n'a pas de cours distincts."""
    from apps.exams.models import Evaluation

    evaluations = Evaluation.objects.filter(
        teaching_unit=teaching_unit,
        exam_session=exam_session,
        course__isnull=True,
    )
    cc_avg, ct_avg = _collect_cc_ct_scores(student, evaluations)
    average = _ecue_from_cc_ct(cc_avg, ct_avg)
    passing = _passing()
    if getattr(teaching_unit, 'passing_score', None) is not None:
        passing = _d(teaching_unit.passing_score)
    validated = average is not None and average >= passing

    return {
        'course_id': None,
        'course_code': teaching_unit.code,
        'course_name': teaching_unit.name,
        'coefficient': float(teaching_unit.coefficient),
        'cc_average': float(cc_avg) if cc_avg is not None else None,
        'ct_average': float(ct_avg) if ct_avg is not None else None,
        'average': float(average) if average is not None else None,
        'passing_score': float(passing),
        'validated': validated,
        'mention': compute_mention(average),
    }


def _validate_ue(ecue_results: list[dict], ue_average: Decimal | None) -> tuple[bool, str]:
    """
    UE validée si :
    - tous les ECUE ≥ 10/20 (validation directe), ou
    - moyenne UE ≥ 10/20 ET aucun ECUE < 8/20 (compensation).
    """
    if ue_average is None:
        return False, 'non_calculable'

    passing = _passing()
    floor = _compensation_floor()
    ecue_averages = [_d(e['average']) for e in ecue_results if e.get('average') is not None]

    if not ecue_averages:
        return False, 'non_calculable'

    if all(avg >= passing for avg in ecue_averages):
        return True, 'direct'

    if ue_average >= passing and all(avg >= floor for avg in ecue_averages):
        return True, 'compensation'

    return False, 'echec'


def calculate_ue_average(student, teaching_unit, exam_session, credits: int | None = None) -> dict:
    """Calcule la moyenne UE et applique les règles de validation par ECUE."""
    from apps.academics.models import Course

    ue_credits = credits or teaching_unit.credits_ects
    courses = Course.objects.filter(teaching_unit=teaching_unit, is_deleted=False)

    if courses.exists():
        ecue_results = [calculate_ecue_average(student, course, exam_session) for course in courses]
    else:
        ecue_results = [_calculate_ue_level_ecue(student, teaching_unit, exam_session)]

    total_coef = Decimal('0')
    weighted_sum = Decimal('0')
    for ecue in ecue_results:
        if ecue['average'] is None:
            continue
        coef = _d(ecue['coefficient'])
        total_coef += coef
        weighted_sum += _d(ecue['average']) * coef

    ue_average = round_grade(weighted_sum / total_coef) if total_coef else None
    validated, validation_mode = _validate_ue(ecue_results, ue_average)

    return {
        'average': float(ue_average) if ue_average is not None else None,
        'credits': ue_credits if validated else 0,
        'validated': validated,
        'validation_mode': validation_mode,
        'mention': compute_mention(ue_average),
        'teaching_unit_code': teaching_unit.code,
        'teaching_unit_name': teaching_unit.name,
        'ecue_results': ecue_results,
    }


def _validate_semester(ue_results: list[dict], semester_avg: Decimal | None) -> tuple[bool, str]:
    """
    Semestre validé si :
    - toutes les UE sont validées (direct), ou
    - moyenne semestrielle pondérée ≥ 10/20 (compensation inter-UE).
    """
    if semester_avg is None or not ue_results:
        return False, 'non_calculable'

    passing = _passing()
    if all(ue['validated'] for ue in ue_results):
        return True, 'direct'

    if semester_avg >= passing:
        return True, 'compensation'

    return False, 'echec'


def calculate_semester_average(student, semester, exam_session) -> dict:
    """Moyenne semestrielle pondérée par crédits ECTS + validation semestre."""
    from django.db.models import Q
    from apps.academics.models import ProgramCourse

    program_courses = ProgramCourse.objects.filter(
        program=student.program,
        semester_number=semester.number,
    ).select_related('teaching_unit', 'specialization')

    if student.specialization_id:
        program_courses = program_courses.filter(
            Q(specialization__is_tronc_commun=True) | Q(specialization_id=student.specialization_id)
        )
    else:
        program_courses = program_courses.filter(
            Q(specialization__is_tronc_commun=True) | Q(specialization__isnull=True)
        )

    total_credits = 0
    weighted_sum = Decimal('0')
    credits_acquired = 0
    ue_results = []

    for pc in program_courses:
        ue = pc.teaching_unit
        credits = pc.credits
        total_credits += credits
        ue_result = calculate_ue_average(student, ue, exam_session, credits=credits)
        ue_results.append(ue_result)
        if ue_result['average'] is not None:
            weighted_sum += _d(ue_result['average']) * credits
        credits_acquired += ue_result['credits']

    semester_avg = round_grade(weighted_sum / total_credits) if total_credits else None
    is_validated, validation_mode = _validate_semester(ue_results, semester_avg)

    if is_validated:
        credits_acquired = total_credits

    if semester_avg is None:
        decision = 'Non calculable'
    elif is_validated:
        decision = 'Validé'
    elif semester_avg >= _passing():
        decision = 'Ajourné (compensation insuffisante)'
    else:
        decision = 'Ajourné'

    return {
        'semester_average': float(semester_avg) if semester_avg is not None else None,
        'credits_acquired': credits_acquired,
        'credits_total': total_credits,
        'is_validated': is_validated,
        'validation_mode': validation_mode,
        'mention': compute_mention(semester_avg),
        'decision': decision,
        'ue_results': ue_results,
    }


def calculate_year_result(student, academic_year, exam_sessions) -> dict:
    """
    Validation annuelle : 60 crédits (S1 + S2).
    Progression possible avec ≥ 80% des crédits (règle LMD INJS).
    """
    from apps.academics.models import Semester

    semesters = Semester.objects.filter(academic_year=academic_year).order_by('number')
    semester_results = []
    total_credits = 0
    credits_acquired = 0

    sessions_by_semester = {s.semester_id: s for s in exam_sessions}

    for sem in semesters:
        session = sessions_by_semester.get(sem.id)
        if not session:
            continue
        result = calculate_semester_average(student, sem, session)
        semester_results.append({
            'semester_number': sem.number,
            'semester_name': sem.name,
            **result,
        })
        total_credits += result['credits_total']
        credits_acquired += result['credits_acquired']

    min_ratio = _d(settings.LMD_MIN_CREDITS_RATIO)
    year_validated = credits_acquired >= 60 if total_credits >= 60 else credits_acquired >= total_credits
    can_progress = credits_acquired >= (total_credits * min_ratio) if total_credits else False

    return {
        'academic_year': academic_year.label,
        'credits_acquired': credits_acquired,
        'credits_total': total_credits,
        'year_validated': year_validated,
        'can_progress': can_progress,
        'semester_results': semester_results,
    }


def run_deliberation(deliberation) -> dict:
    """Exécute la délibération automatique pour une promotion."""
    from apps.students.models import Student, AcademicRecord

    students = Student.objects.filter(
        promotion=deliberation.promotion, status='active'
    ).select_related('user')

    exam_session = deliberation.exam_session
    semester = exam_session.semester
    results = []

    for student in students:
        sem_result = calculate_semester_average(student, semester, exam_session)
        results.append({
            'student_id': str(student.id),
            'matricule': student.matricule,
            'name': student.user.get_full_name(),
            **sem_result,
        })
        if deliberation.status == 'validated':
            AcademicRecord.objects.update_or_create(
                student=student,
                academic_year=exam_session.academic_year,
                semester=semester,
                defaults={
                    'semester_average': sem_result['semester_average'],
                    'credits_acquired': sem_result['credits_acquired'],
                    'credits_total': sem_result['credits_total'],
                    'is_validated': sem_result['is_validated'],
                    'decision': sem_result['decision'],
                    'snapshot_data': sem_result,
                },
            )

    passing_rate = sum(1 for r in results if r['is_validated']) / len(results) * 100 if results else 0
    summary = {
        'total_students': len(results),
        'validated_count': sum(1 for r in results if r['is_validated']),
        'passing_rate': round(passing_rate, 2),
        'results': results,
    }
    deliberation.results_summary = summary
    deliberation.save(update_fields=['results_summary'])
    return summary


def check_absence_impact(student, teaching_unit, exam_session) -> bool:
    """True si le taux d'absence dépasse le seuil autorisé pour l'UE."""
    from apps.faculty.models import Attendance, CourseAssignment, Schedule

    max_rate = settings.LMD_MAX_ABSENCE_RATE
    assignments = CourseAssignment.objects.filter(
        course__teaching_unit=teaching_unit,
        promotion=student.promotion,
        academic_year=exam_session.academic_year,
    )
    schedule_ids = Schedule.objects.filter(assignment__in=assignments).values_list('id', flat=True)
    total = Attendance.objects.filter(student=student, schedule_id__in=schedule_ids).count()
    if total == 0:
        return False
    absences = Attendance.objects.filter(
        student=student, schedule_id__in=schedule_ids, status='absent'
    ).count()
    return (absences / total) > max_rate
