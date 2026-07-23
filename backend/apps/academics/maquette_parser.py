"""Parseur de la maquette STAPS 2026 INJS (docx)."""
from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
UE_CODE_RE = re.compile(r'^[A-Z]{2,5}\d{4}$')
ECUE_CODE_RE = re.compile(r'^[A-Z0-9]{5,14}$')
SEMESTER_RE = re.compile(r'SEMESTRE\s*:?\s*(\d)', re.I)
SPEC_RE = re.compile(
    r'SPECIALITE\s*\d*\s*:\s*(Education et Motricit[eé]|Entra[iî]nement Sportif|Management du Sport|Activit[eé]s Physiques Adapt[eé]es)',
    re.I,
)
SEMESTER_SPEC_RE = re.compile(r'SEMESTRE\s*:?\s*\d+\s+(EM|ES|MS|APA)\b', re.I)
OPTION_TC_RE = re.compile(r'OPTION\s*:\s*TRONC COMMUN', re.I)


@dataclass
class ParsedEcue:
    code: str
    name: str
    hours_cm: int = 0
    hours_td: int = 0
    hours_tp: int = 0
    credits_ects: int = 0


@dataclass
class ParsedUe:
    code: str
    name: str
    semester: int
    specialization_code: str
    track: str
    credits_ects: int = 0
    category: str = ''
    ecues: list[ParsedEcue] = field(default_factory=list)


def _cell_text(cell) -> str:
    parts = []
    for t in cell.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
        if t.text:
            parts.append(t.text)
        if t.tail:
            parts.append(t.tail)
    return ' '.join(''.join(parts).split())


def _parse_int(value: str) -> int:
    if not value:
        return 0
    try:
        return int(float(value.replace(',', '.')))
    except ValueError:
        return 0


def _normalize_spec(text: str) -> str:
    mapping = {
        'education et motricité': 'EM',
        'education et motricite': 'EM',
        'entraînement sportif': 'ES',
        'entrainement sportif': 'ES',
        'management du sport': 'MS',
        'activités physiques adaptées': 'APA',
        'activites physiques adaptees': 'APA',
    }
    return mapping.get(text.lower().strip(), 'TC')


def _parse_table_meta(rows: list[list[str]]) -> tuple[int, str, str]:
    header_parts = []
    for row in rows[:4]:
        if not row:
            continue
        text = row[0]
        if text.startswith('Code de'):
            break
        header_parts.append(text)
    header_text = ' '.join(header_parts)

    semester = 1
    match = SEMESTER_RE.search(header_text)
    if match:
        semester = int(match.group(1))

    specialization = 'TC'
    if OPTION_TC_RE.search(header_text):
        specialization = 'TC'
    else:
        spec_match = SPEC_RE.search(header_text)
        sem_spec = SEMESTER_SPEC_RE.search(header_text)
        if spec_match:
            specialization = _normalize_spec(spec_match.group(1))
        elif sem_spec:
            specialization = sem_spec.group(1).upper()
        else:
            upper = f' {header_text.upper()} '
            for token, code in [(' APA ', 'APA'), (' EM ', 'EM'), (' ES ', 'ES'), (' MS ', 'MS')]:
                if token in upper:
                    specialization = code
                    break

    track = 'BOTH'
    upper = header_text.upper()
    if ' PL ' in f' {upper} ' and ' PC ' not in f' {upper} ':
        track = 'PL'
    elif ' PC ' in f' {upper} ' and ' PL ' not in f' {upper} ':
        track = 'PC'

    return semester, specialization, track


def _is_category_row(row: list[str]) -> bool:
    if not row:
        return True
    first = row[0]
    if not first and len(row) > 1 and row[1].startswith('UE '):
        return True
    return first.startswith('UE ') or first in ('TOTAL',)


def parse_maquette_docx(path: str | Path) -> list[ParsedUe]:
    path = Path(path)
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read('word/document.xml'))

    parsed: list[ParsedUe] = []
    current_ue: ParsedUe | None = None
    current_category = ''

    for table in root.findall('.//w:tbl', NS):
        rows = []
        for tr in table.findall('w:tr', NS):
            row = [_cell_text(tc) for tc in tr.findall('w:tc', NS)]
            if any(row):
                rows.append(row)
        if len(rows) < 4:
            continue

        header_blob = rows[0][0] if rows[0] else ''
        if not SEMESTER_RE.search(header_blob) and not OPTION_TC_RE.search(header_blob):
            if not any(SEMESTER_RE.search(r[0]) for r in rows[:3] if r):
                continue

        semester, specialization, track = _parse_table_meta(rows)
        data_start = 3 if len(rows) > 3 and rows[2] and rows[2][0] in ('', 'Code de l\'UE') else 2

        for row in rows[data_start:]:
            if _is_category_row(row):
                if row and row[0].startswith('UE '):
                    current_category = row[0]
                elif len(row) > 1 and row[1].startswith('UE '):
                    current_category = row[1]
                current_ue = None
                continue

            ue_code = row[0] if len(row) > 0 else ''
            ue_name = row[1] if len(row) > 1 else ''
            ecue_code = row[2] if len(row) > 2 else ''
            ecue_name = row[3] if len(row) > 3 else ''

            if ue_code and UE_CODE_RE.match(ue_code):
                ue_credits = _parse_int(row[9]) if len(row) > 9 else _parse_int(row[8])
                current_ue = ParsedUe(
                    code=ue_code,
                    name=ue_name,
                    semester=semester,
                    specialization_code=specialization,
                    track=track,
                    credits_ects=ue_credits,
                    category=current_category,
                )
                parsed.append(current_ue)
            elif current_ue and ue_name and UE_CODE_RE.match(ue_name):
                # Fusion de cellules : code UE en colonne 1
                ue_credits = _parse_int(row[9]) if len(row) > 9 else _parse_int(row[8])
                current_ue = ParsedUe(
                    code=ue_name,
                    name=ue_code,
                    semester=semester,
                    specialization_code=specialization,
                    track=track,
                    credits_ects=ue_credits,
                    category=current_category,
                )
                parsed.append(current_ue)
                ue_code = current_ue.code
                ecue_code = row[2] if len(row) > 2 else ''
                ecue_name = row[3] if len(row) > 3 else ''

            if not current_ue:
                continue

            if ecue_code and ECUE_CODE_RE.match(ecue_code) and ecue_name:
                ecue_credits = _parse_int(row[9]) if len(row) > 9 else 0
                if ecue_credits == 0 and current_ue.credits_ects:
                    ecue_credits = max(1, current_ue.credits_ects // max(len(current_ue.ecues) + 1, 1))
                current_ue.ecues.append(ParsedEcue(
                    code=ecue_code,
                    name=ecue_name,
                    hours_cm=_parse_int(row[4]) if len(row) > 4 else 0,
                    hours_td=_parse_int(row[5]) if len(row) > 5 else 0,
                    hours_tp=_parse_int(row[6]) if len(row) > 6 else 0,
                    credits_ects=ecue_credits,
                ))
                if current_ue.credits_ects == 0 and ecue_credits:
                    current_ue.credits_ects = sum(e.credits_ects for e in current_ue.ecues)

    # Dédupliquer UE (même code) en fusionnant ECUE
    merged: dict[str, ParsedUe] = {}
    for ue in parsed:
        key = ue.code
        if key not in merged:
            merged[key] = ue
            continue
        existing = merged[key]
        existing_codes = {e.code for e in existing.ecues}
        for ecue in ue.ecues:
            if ecue.code not in existing_codes:
                existing.ecues.append(ecue)
        if ue.credits_ects > existing.credits_ects:
            existing.credits_ects = ue.credits_ects

    return list(merged.values())


SPECIALIZATION_LABELS = {
    'TC': ('Tronc Commun', True),
    'EM': ('Education et Motricité', False),
    'ES': ('Entraînement Sportif', False),
    'MS': ('Management du Sport', False),
    'APA': ('Activités Physiques Adaptées', False),
}

DEFAULT_MAQUETTE_PATH = (
    Path(__file__).resolve().parents[3]
    / 'elements'
    / 'MAQUETTE REVISEE TC EM ES MS APA  LMD PROFESSEUR DE LYCEE ET DE COLLEGE 2026 CONSOLIDEE.docx'
)
