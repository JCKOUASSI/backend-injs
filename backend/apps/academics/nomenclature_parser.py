"""Parseur de la nomenclature des emplois STAPS INJS (xlsx)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import openpyxl

DEFAULT_NOMENCLATURE_PATH = (
    Path(__file__).resolve().parents[3] / 'elements'
    / 'TABLEAU DE LA NOMENCLATURE DES EMPLOIS EN STAPS.xlsx'
)

SPECIALIZATION_ALIASES = {
    'ACTIVITE PHYSIQUE ADAPTEE': 'APA',
    'ACTIVITES PHYSIQUES ADAPTEES': 'APA',
    'EDUCATIN ET MOTRICITE': 'EM',
    'EDUCATION ET MOTRICITE': 'EM',
    'ENTRAINEMENT SPORTIF': 'ES',
    'ENTRAÎNEMENT SPORTIF': 'ES',
    'MANAGEMENT DU SPORT': 'MS',
}

FORMATION_ALIASES = {
    'MASTER STAPS': 'M',
    'LICENCE STAPS': 'L',
}

GRADE_TRACKS = {
    'A3': 'PC',
    'A4': 'PL',
}

DIPLOMA_CODES = {
    "CERTIFICAT D'APTITUDE AU PROFESSORAT DE SPORT (CAPS)": 'CAPS',
    "CERTIFICAT D'APTITUDE AU PROFESSORAT D'EPS (CAPEPS)": 'CAPEPS',
    "CERTIFICAT D'APTITUDE AU PROFESSORAT DE COLLEGE SPORT (CAPCS)": 'CAPCS',
    "CERTIFICAT D'APTITUDE AU PROFESSORAT DE COLLEGE EPS (CAPCEPS)": 'CAPCEPS',
}

DURATION_RE = re.compile(r'(\d+)\s*an', re.I)


@dataclass
class ParsedJobNomenclature:
    degree_type: str
    specialization_code: str
    civil_service_grade: str
    track: str
    job_title: str
    duration_years: int
    competencies: str
    career_outcomes: str
    diploma_code: str
    diploma_label: str
    employers: str


def _normalize_label(value: str) -> str:
    return ' '.join(str(value or '').upper().split())


def _map_specialization(label: str) -> str:
    normalized = _normalize_label(label)
    if normalized in SPECIALIZATION_ALIASES:
        return SPECIALIZATION_ALIASES[normalized]
    for key, code in SPECIALIZATION_ALIASES.items():
        if key in normalized or normalized in key:
            return code
    raise ValueError(f'Spécialité non reconnue: {label}')


def _map_formation(label: str) -> str:
    normalized = _normalize_label(label)
    if normalized in FORMATION_ALIASES:
        return FORMATION_ALIASES[normalized]
    raise ValueError(f'Formation non reconnue: {label}')


def _parse_duration(value: str) -> int:
    match = DURATION_RE.search(str(value or ''))
    return int(match.group(1)) if match else 0


def _parse_diploma(label: str) -> tuple[str, str]:
    cleaned = ' '.join(str(label or '').split())
    code = DIPLOMA_CODES.get(_normalize_label(cleaned), '')
    if not code:
        upper = _normalize_label(cleaned)
        for token in ('CAPCEPS', 'CAPEPS', 'CAPCS', 'CAPS'):
            if token in upper:
                code = token
                break
    return code, cleaned


def parse_nomenclature_xlsx(path: str | Path | None = None) -> list[ParsedJobNomenclature]:
    """Extrait les lignes de nomenclature emplois depuis le fichier Excel officiel."""
    workbook_path = Path(path or DEFAULT_NOMENCLATURE_PATH)
    wb = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
    ws = wb.active

    entries: list[ParsedJobNomenclature] = []
    current_formation = ''

    for row in ws.iter_rows(min_row=1, values_only=True):
        cells = list(row or [])
        while len(cells) < 11:
            cells.append(None)

        formation_cell = cells[2]
        if formation_cell and _normalize_label(str(formation_cell)) in FORMATION_ALIASES:
            current_formation = str(formation_cell).strip()

        specialty = cells[3]
        grade = cells[4]
        if not specialty or not grade:
            continue

        grade = str(grade).strip().upper()
        if grade not in GRADE_TRACKS:
            continue
        if not current_formation:
            continue

        diploma_code, diploma_label = _parse_diploma(cells[9])
        entries.append(ParsedJobNomenclature(
            degree_type=_map_formation(current_formation),
            specialization_code=_map_specialization(str(specialty)),
            civil_service_grade=grade,
            track=GRADE_TRACKS[grade],
            job_title=str(cells[5] or '').strip(),
            duration_years=_parse_duration(str(cells[6] or '')),
            competencies=str(cells[7] or '').strip(),
            career_outcomes=str(cells[8] or '').strip(),
            diploma_code=diploma_code,
            diploma_label=diploma_label,
            employers=str(cells[10] or '').strip(),
        ))

    wb.close()
    return entries
