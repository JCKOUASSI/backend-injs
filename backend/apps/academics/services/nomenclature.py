"""Services liés à la nomenclature emplois STAPS."""
from __future__ import annotations

from apps.academics.models import StapsJobNomenclature


def resolve_job_nomenclature(student, degree_type: str | None = None):
    """Retourne la ligne nomenclature correspondant au parcours étudiant."""
    if not student.specialization_id:
        return None

    degree = degree_type
    if not degree:
        degree = student.program.degree_type

    return StapsJobNomenclature.objects.filter(
        degree_type=degree,
        specialization=student.specialization,
        is_active=True,
    ).select_related('specialization').first()


def list_career_paths(specialization_code: str | None = None):
    """Liste les parcours professionnels, optionnellement filtrés par spécialité."""
    qs = StapsJobNomenclature.objects.filter(is_active=True).select_related('specialization')
    if specialization_code:
        qs = qs.filter(specialization__code=specialization_code.upper())
    return qs.order_by('degree_type', 'specialization__code')
