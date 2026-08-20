from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO

import openpyxl

from apps.academics.models import (
    AcademicYear,
    Department,
    Institution,
    Program,
    Promotion,
    Semester,
    Specialization,
)


RESOURCE_HEADERS = {
    'specializations': ['code', 'name', 'track', 'is_tronc_commun', 'description'],
    'departments': ['institution_code', 'code', 'name', 'description'],
    'programs': [
        'department_code',
        'code',
        'name',
        'degree_type',
        'track',
        'duration_semesters',
        'total_credits',
        'description',
        'is_active',
    ],
    'academic_years': [
        'institution_code',
        'label',
        'start_date',
        'end_date',
        'is_current',
        'is_archived',
    ],
    'semesters': ['academic_year_label', 'number', 'name', 'start_date', 'end_date', 'is_current'],
    'promotions': ['program_code', 'name', 'entry_year', 'current_semester', 'is_active'],
}

TRACK_VALUES = {'PL', 'PC', 'BOTH', ''}
PROGRAM_DEGREE_VALUES = {'L', 'M', 'D', 'DU'}
TRUE_VALUES = {'1', 'true', 'vrai', 'oui', 'yes', 'x'}
FALSE_VALUES = {'0', 'false', 'faux', 'non', 'no', ''}
DATE_FORMATS = ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y')


@dataclass
class ImportReport:
    resource: str
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] | None = None

    def as_dict(self):
        return {
            'resource': self.resource,
            'created': self.created,
            'updated': self.updated,
            'skipped': self.skipped,
            'errors': self.errors or [],
        }


def import_referential_workbook(resource: str, workbook_file: str | BinaryIO) -> dict:
    if resource not in RESOURCE_HEADERS:
        raise ValueError(f"Ressource d'import inconnue: {resource}")

    wb = openpyxl.load_workbook(workbook_file, read_only=True, data_only=True)
    try:
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
    finally:
        wb.close()

    if not rows:
        raise ValueError("Le fichier Excel est vide.")

    header = [_normalize_header(value) for value in rows[0]]
    expected_header = RESOURCE_HEADERS[resource]
    if header[: len(expected_header)] != expected_header:
        raise ValueError(
            f"Colonnes invalides pour {resource}. Attendu: {', '.join(expected_header)}"
        )

    report = ImportReport(resource=resource, errors=[])
    for index, row in enumerate(rows[1:], start=2):
        if _row_is_empty(row):
            continue
        try:
            payload = _map_row(expected_header, row)
            created = _dispatch_import(resource, payload)
            if created:
                report.created += 1
            else:
                report.updated += 1
        except Exception as exc:  # noqa: BLE001 - user-facing import report
            report.errors.append(f"Ligne {index}: {exc}")
            report.skipped += 1

    return report.as_dict()


def _dispatch_import(resource: str, payload: dict) -> bool:
    if resource == 'specializations':
        return _import_specialization(payload)
    if resource == 'departments':
        return _import_department(payload)
    if resource == 'programs':
        return _import_program(payload)
    if resource == 'academic_years':
        return _import_academic_year(payload)
    if resource == 'semesters':
        return _import_semester(payload)
    if resource == 'promotions':
        return _import_promotion(payload)
    raise ValueError(f"Ressource non prise en charge: {resource}")


def _import_specialization(payload: dict) -> bool:
    track = str(payload['track'] or 'BOTH').upper()
    if track not in {'PL', 'PC', 'BOTH'}:
        raise ValueError("track doit valoir PL, PC ou BOTH")
    _, created = Specialization.objects.update_or_create(
        code=str(payload['code']).strip().upper(),
        defaults={
            'name': str(payload['name']).strip(),
            'track': track,
            'is_tronc_commun': _parse_bool(payload['is_tronc_commun']),
            'description': str(payload['description'] or '').strip(),
        },
    )
    return created


def _import_department(payload: dict) -> bool:
    institution = Institution.objects.get(code=str(payload['institution_code']).strip().upper())
    _, created = Department.objects.update_or_create(
        institution=institution,
        code=str(payload['code']).strip().upper(),
        defaults={
            'name': str(payload['name']).strip(),
            'description': str(payload['description'] or '').strip(),
        },
    )
    return created


def _import_program(payload: dict) -> bool:
    department = Department.objects.get(code=str(payload['department_code']).strip().upper(), is_deleted=False)
    degree_type = str(payload['degree_type']).strip().upper()
    track = str(payload['track'] or '').strip().upper()
    if degree_type not in PROGRAM_DEGREE_VALUES:
        raise ValueError("degree_type doit valoir L, M, D ou DU")
    if track not in TRACK_VALUES:
        raise ValueError("track doit valoir PL, PC, BOTH ou vide")
    _, created = Program.objects.update_or_create(
        department=department,
        code=str(payload['code']).strip().upper(),
        defaults={
            'name': str(payload['name']).strip(),
            'degree_type': degree_type,
            'track': '' if track == 'BOTH' else track,
            'duration_semesters': _parse_int(payload['duration_semesters']),
            'total_credits': _parse_int(payload['total_credits']),
            'description': str(payload['description'] or '').strip(),
            'is_active': _parse_bool(payload['is_active']),
        },
    )
    return created


def _import_academic_year(payload: dict) -> bool:
    institution = Institution.objects.get(code=str(payload['institution_code']).strip().upper())
    _, created = AcademicYear.objects.update_or_create(
        institution=institution,
        label=str(payload['label']).strip(),
        defaults={
            'start_date': _parse_date(payload['start_date']),
            'end_date': _parse_date(payload['end_date']),
            'is_current': _parse_bool(payload['is_current']),
            'is_archived': _parse_bool(payload['is_archived']),
        },
    )
    return created


def _import_semester(payload: dict) -> bool:
    academic_year = AcademicYear.objects.get(label=str(payload['academic_year_label']).strip())
    _, created = Semester.objects.update_or_create(
        academic_year=academic_year,
        number=_parse_int(payload['number']),
        defaults={
            'name': str(payload['name']).strip(),
            'start_date': _parse_date(payload['start_date']),
            'end_date': _parse_date(payload['end_date']),
            'is_current': _parse_bool(payload['is_current']),
        },
    )
    return created


def _import_promotion(payload: dict) -> bool:
    program = Program.objects.get(code=str(payload['program_code']).strip().upper(), is_deleted=False)
    _, created = Promotion.objects.update_or_create(
        program=program,
        name=str(payload['name']).strip(),
        defaults={
            'entry_year': _parse_int(payload['entry_year']),
            'current_semester': _parse_int(payload['current_semester']),
            'is_active': _parse_bool(payload['is_active']),
        },
    )
    return created


def _normalize_header(value) -> str:
    return str(value or '').strip().lower()


def _map_row(expected_header: list[str], row: tuple) -> dict:
    values = list(row or [])
    while len(values) < len(expected_header):
        values.append('')
    return {expected_header[index]: values[index] for index in range(len(expected_header))}


def _row_is_empty(row: tuple) -> bool:
    return all(value in (None, '') for value in row)


def _parse_bool(value) -> bool:
    normalized = str(value or '').strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(f"Valeur booléenne invalide: {value}")


def _parse_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Valeur entière invalide: {value}") from exc


def _parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if hasattr(value, 'year') and hasattr(value, 'month') and hasattr(value, 'day'):
        return value
    raw = str(value or '').strip()
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(raw, date_format).date()
        except ValueError:
            continue
    raise ValueError(f"Date invalide: {value}")
