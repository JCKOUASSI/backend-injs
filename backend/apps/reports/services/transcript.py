"""Génération du relevé de notes officiel INJS (modèle bulletin semestre)."""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.exams.services.lmd_engine import calculate_semester_average

INJS_BLUE = colors.HexColor('#0D47A1')
SESSION_LABELS = {'normal': 'Première Session', 'retake': 'Session de rattrapage'}


def _fmt(value) -> str:
    if value is None:
        return '—'
    if isinstance(value, float):
        return f'{value:.2f}'
    return str(value)


def build_semester_transcript(student, exam_session) -> dict[str, Any]:
    """Construit les données du bulletin semestriel via le moteur LMD."""
    semester = exam_session.semester
    result = calculate_semester_average(student, semester, exam_session)

    total_acquired = sum(
        r.credits_acquired for r in student.academic_records.all()
    )

    spec_label = ''
    if student.specialization_id:
        spec_label = student.specialization.name
    elif student.program.track:
        track = student.program.get_track_display()
        spec_label = f'{student.program.name} ({track})'
    else:
        spec_label = student.program.name

    return {
        'student': {
            'full_name': student.user.get_full_name(),
            'matricule': student.matricule,
            'date_of_birth': student.date_of_birth.strftime('%d/%m/%Y') if student.date_of_birth else '—',
            'place_of_birth': student.place_of_birth or '—',
            'gender': student.get_gender_display() if student.gender else '—',
            'program': spec_label,
            'enrollment_date': student.enrollment_date.strftime('%B %Y') if student.enrollment_date else '—',
            'program_credits': student.program.total_credits,
            'credits_acquired_total': total_acquired + (
                result['credits_acquired'] if result['is_validated'] else 0
            ),
        },
        'session': {
            'academic_year': exam_session.academic_year.label,
            'semester_number': semester.number,
            'semester_name': semester.name,
            'session_type': SESSION_LABELS.get(exam_session.session_type, exam_session.session_type),
        },
        'summary': {
            'semester_average': result['semester_average'],
            'credits_acquired': result['credits_acquired'],
            'credits_total': result['credits_total'],
            'is_validated': result['is_validated'],
            'decision': result['decision'],
            'mention': result['mention'],
            'validation_mode': result['validation_mode'],
        },
        'ue_results': result['ue_results'],
    }


def _student_info_table(data: dict) -> Table:
    s = data['student']
    rows = [
        ['Nom et Prénoms', s['full_name'], 'N° Matricule', s['matricule']],
        ['Date et lieu de naissance', f"{s['date_of_birth']} à {s['place_of_birth']}", 'Sexe', s['gender']],
        ['Nom du programme', s['program'], 'Première inscription', s['enrollment_date']],
        ['Crédits programme', str(s['program_credits']), 'Total acquis', f"{s['credits_acquired_total']} / {s['program_credits']}"],
        ['Nom du diplôme', 'Licence en Sciences et Techniques des Activités Physiques et Sportives', '', ''],
    ]
    table = Table(rows, colWidths=[4.5 * cm, 7 * cm, 4 * cm, 5 * cm])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return table


def _grades_table(ue_results: list[dict]) -> Table:
    headers = [
        'Code UE', 'Unité d\'enseignement (UE)', 'ECUE',
        'ECTS', 'CC /20', 'CT /20', 'Moy. ECUE', 'Moy. UE',
        'ECTS obtenus', 'Validation', 'Mention',
    ]
    rows = [headers]

    for ue in ue_results:
        ecues = ue.get('ecue_results') or [{}]
        for idx, ecue in enumerate(ecues):
            ue_credits = ue['credits'] if ue.get('validated') else 0
            validation = 'Validée' if ue.get('validated') else 'Non validée'
            rows.append([
                ue['teaching_unit_code'] if idx == 0 else '',
                ue['teaching_unit_name'] if idx == 0 else '',
                ecue.get('course_name') or ecue.get('course_code') or '—',
                _fmt(ecue.get('coefficient') or ''),
                _fmt(ecue.get('cc_average')),
                _fmt(ecue.get('ct_average')),
                _fmt(ecue.get('average')),
                _fmt(ue.get('average')) if idx == 0 else '',
                str(ue_credits) if idx == 0 else '',
                validation if idx == 0 else '',
                ue.get('mention') or '—' if idx == 0 else '',
            ])

    col_widths = [1.8 * cm, 4.2 * cm, 4.5 * cm, 1.1 * cm, 1.3 * cm, 1.3 * cm,
                  1.5 * cm, 1.5 * cm, 1.6 * cm, 2 * cm, 2 * cm]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), INJS_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (3, 0), (8, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F9FF')]),
    ]))
    return table


def render_transcript_pdf(student, exam_session) -> HttpResponse:
    """Génère le PDF bulletin semestre conforme au modèle INJS."""
    data = build_semester_transcript(student, exam_session)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=1.2 * cm, leftMargin=1.2 * cm,
        topMargin=1 * cm, bottomMargin=1 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'INJSHeader', parent=styles['Normal'],
        fontSize=9, alignment=1, textColor=INJS_BLUE, spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        'INJSSub', parent=styles['Normal'],
        fontSize=8, alignment=1, spaceAfter=6,
    )

    sess = data['session']
    summary = data['summary']
    elements = [
        Paragraph('REPUBLIQUE DE COTE D\'IVOIRE', title_style),
        Paragraph('Union — Discipline — Travail', subtitle_style),
        Paragraph('MINISTERE DES SPORTS', title_style),
        Paragraph('INSTITUT NATIONAL DE LA JEUNESSE ET DES SPORTS', title_style),
        Spacer(1, 8),
        _student_info_table(data),
        Spacer(1, 10),
        _grades_table(data['ue_results']),
        Spacer(1, 12),
        Paragraph(
            f"<b>BULLETIN</b> — Licence STAPS / Semestre {sess['semester_number']} — "
            f"{sess['session_type']} {sess['academic_year']}",
            styles['Heading3'],
        ),
        Spacer(1, 6),
        Paragraph(
            f"<b>Bilan du semestre {sess['semester_number']} :</b><br/>"
            f"Moyenne du semestre : <b>{_fmt(summary['semester_average'])}</b><br/>"
            f"Total des crédits validés : <b>{summary['credits_acquired']} / {summary['credits_total']}</b><br/>"
            f"Décision du jury : <b>{summary['decision']}</b><br/>"
            f"Mention : <b>{summary['mention'] or '—'}</b>",
            styles['Normal'],
        ),
        Spacer(1, 16),
        Paragraph(
            f"Fait à Abidjan, le {datetime.now().strftime('%d/%m/%Y')}<br/>"
            f"<b>Le Directeur Général de l'INJS</b><br/><br/>_______________________",
            ParagraphStyle('Sig', parent=styles['Normal'], alignment=2, fontSize=9),
        ),
    ]
    doc.build(elements)
    buffer.seek(0)
    filename = f"releve_{student.matricule}_S{sess['semester_number']}.pdf"
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
