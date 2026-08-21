"""Moteur d'emploi du temps INJS.

Le module hebdomadaire historique reste exposé ici pour ne casser aucun import.
Le moteur calendaire (périodes, séances datées, charges) s'ajoute à côté.
"""
from apps.faculty.services.planning.weekly import (  # noqa: F401
    DAYS,
    DEFAULT_SLOTS,
    PlanningError,
    SEMESTER_WEEKS_DEFAULT,
    _overlaps,
    _weekly_session_count,
    courses_for_promotion,
    detect_conflicts,
    ensure_assignments_for_promotion,
    generate_for_academic_year,
    generate_for_promotion,
    open_sessions_for_schedules,
    timetable_grid,
)
from apps.faculty.services.planning.conflicts import detect_seance_conflicts  # noqa: F401
from apps.faculty.services.planning.engine import (  # noqa: F401
    expand_schedules_for_period,
    generate_for_period,
    iter_eligible_dates,
    publish_seances,
    ensure_teaching_loads,
)
