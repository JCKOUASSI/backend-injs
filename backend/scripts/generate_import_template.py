#!/usr/bin/env python
"""
Génère les fichiers Excel modèles pour le chargement de la base de données.

Fichiers générés :
  1. import_formations.xlsx    — modules de formation uniquement
  2. import_formateurs.xlsx    — formateurs uniquement
  3. import_participants.xlsx   — participants + libellé de leur(s) formation(s)

Usage :
  python scripts/generate_import_template.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ── Styles ──────────────────────────────────────────────
header_font = Font(bold=True, color='FFFFFF', size=11)
header_fill_green = PatternFill(start_color='388E3C', end_color='388E3C', fill_type='solid')
header_fill_orange = PatternFill(start_color='F57C00', end_color='F57C00', fill_type='solid')
header_fill_blue = PatternFill(start_color='1565C0', end_color='1565C0', fill_type='solid')
example_fill = PatternFill(start_color='E8F5E9', end_color='E8F5E9', fill_type='solid')
note_font = Font(italic=True, color='888888', size=9)
thin_border = Border(
    left=Side(style='thin', color='CCCCCC'),
    right=Side(style='thin', color='CCCCCC'),
    top=Side(style='thin', color='CCCCCC'),
    bottom=Side(style='thin', color='CCCCCC'),
)


def _write_sheet(ws, headers, examples, notes=None, header_fill=None):
    """Écrit les en-têtes, les exemples et les notes dans une feuille."""
    fill = header_fill or header_fill_green
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = fill
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = thin_border

    for row_idx, example_row in enumerate(examples, 2):
        for col, val in enumerate(example_row, 1):
            cell = ws.cell(row=row_idx, column=col, value=val)
            cell.fill = example_fill
            cell.border = thin_border
            cell.alignment = Alignment(vertical='center')

    if notes:
        note_row = len(examples) + 3
        for col, note in enumerate(notes, 1):
            if note:
                cell = ws.cell(row=note_row, column=col, value=note)
                cell.font = note_font

    # Auto-width
    for col in range(1, len(headers) + 1):
        max_len = max(
            len(str(ws.cell(row=r, column=col).value or ''))
            for r in range(1, len(examples) + 3)
        )
        ws.column_dimensions[get_column_letter(col)].width = min(max(max_len + 4, 15), 45)


# ═════════════════════════════════════════════════════════
# 1. FORMATIONS (modules uniquement)
# ═════════════════════════════════════════════════════════
def generate_formations():
    wb = Workbook()
    ws = wb.active
    ws.title = 'Formations'
    _write_sheet(ws,
        headers=[
            'N°', 'Formation (cycle)', 'Module (titre)',
            'Date début', 'Date fin',
            'Volume horaire (h)', 'Catégorie', 'Grade', 'Groupe', 'Vague',
            'Site', 'Batiment', 'Salle',
        ],
        header_fill=header_fill_green,
        examples=[
            [1, 'FORMATION EN ADMINISTRATION DE BASE', 'Déontologie de la Fonction Publique',
             '2026-05-05 08:00', '2026-05-09 17:00', 40, 'FAB A', 'A4', 'GROUPE 1', 'SESSION 2026', 'CPFAE', '', 'SALLE A'],
            [2, 'FORMATION EN ADMINISTRATION DE BASE', 'Protocole et Savoir-vivre',
             '2026-05-12 08:00', '2026-05-13 17:00', 16, 'FAB A', 'A4', 'GROUPE 1', 'SESSION 2026', 'CPFAE', '', 'SALLE A'],
            [3, 'FORMATION EN ADMINISTRATION DE BASE', 'Finances Publiques',
             '2026-05-19 08:00', '2026-05-22 17:00', 30, 'FAB A', 'A4', 'GROUPE 1', 'SESSION 2026', 'CPFAE', '', 'SALLE A'],
            [4, 'FORMATION EN ADMINISTRATION DE BASE', 'Déontologie de la Fonction Publique',
             '2026-05-05 08:00', '2026-05-09 17:00', 40, 'FAB A', 'A4', 'GROUPE 2', 'SESSION 2026', 'CPFAE', '', 'SALLE B'],
            [5, 'FORMATION EN ADMINISTRATION DE BASE', 'Commande Publique',
             '2026-05-05 08:00', '2026-05-09 17:00', 40, 'FAB B', 'B3', 'GROUPE 1', 'SESSION 2026', 'CPFAE', '', 'SALLE C'],
            [6, 'FORMATION EN ADMINISTRATION DE BASE', 'Gestion du budget familial',
             '2026-05-05 08:00', '2026-05-08 17:00', 32, 'FAB B', 'B3', 'GROUPE 2', 'SESSION 2026', 'CPFAE', '', 'SALLE D'],
            [7, 'FORMATION SPECIALISEE EN GESTION', 'Management Public',
             '2026-07-01 08:00', '2026-07-10 17:00', 60, 'FAB C', 'C1', 'GROUPE 1', 'SESSION 2026', 'CPFAE', '', 'SALLE E'],
        ],
        notes=[
            'N° du module dans le cycle',
            'Titre du cycle de formation — Obligatoire',
            'Intitulé du module — Obligatoire',
            'AAAA-MM-JJ HH:MM',
            'AAAA-MM-JJ HH:MM',
            'Nombre (heures)',
            'FAB A, FAB B ou FAB C — détermine le secrétariat',
            'A4, A3, B1, C1…',
            'GROUPE 1, GROUPE 2… (pour auto-inscription)',
            'SESSION 2026, PREMIERE VAGUE… (optionnel)',
            'Centre de formation',
            'Bâtiment (optionnel)',
            'Salle (optionnel)',
        ],
    )
    return wb


# ═════════════════════════════════════════════════════════
# 2. FORMATEURS (uniquement)
# ═════════════════════════════════════════════════════════
def generate_formateurs():
    wb = Workbook()
    ws = wb.active
    ws.title = 'Formateurs'
    _write_sheet(ws,
        headers=[
            'Numéro', 'Nom', 'Prénoms', 'Email', 'Téléphone',
            'Spécialité', 'Organisation',
        ],
        header_fill=header_fill_blue,
        examples=[
            ['F0001', 'CHRAIBI', 'Nadia', 'nadia.chraibi@expert.ci', '0700000001',
             'Rédaction administrative', 'CPFAE'],
            ['F0002', 'BERRADA', 'Karim', 'karim.berrada@expert.ci', '0700000002',
             'Droit administratif', 'ENA'],
            ['F0003', 'HAJJI', 'Leila', 'leila.hajji@univ.ci', '0700000003',
             'Finances publiques', 'Université'],
            ['F0004', 'KOUASSI', 'Jean-Marc', 'jm.kouassi@gouv.ci', '0700000004',
             'Management des organisations', 'Ministère'],
            ['F0005', "N'GUESSAN", 'Awa', 'awa.nguessan@cpfae.ci', '0700000005',
             'Protocole et savoir vivre', 'CPFAE'],
        ],
        notes=[
            'Auto-généré si vide (F0001…)',
            'Obligatoire',
            'Obligatoire',
            'Optionnel',
            'Optionnel',
            'Optionnel',
            'Optionnel',
        ],
    )
    return wb


# ═════════════════════════════════════════════════════════
# 3. PARTICIPANTS + libellé de leurs formations
# ═════════════════════════════════════════════════════════
def generate_participants():
    wb = Workbook()
    ws = wb.active
    ws.title = 'Participants'
    _write_sheet(ws,
        headers=[
            'Matricule', 'Nom', 'Prénoms', 'Sexe',
            'Date naissance', 'Lieu naissance',
            'Email', 'Téléphone 1', 'Téléphone 2',
            'Type concours', 'Libelle concours',
            'Catégorie', 'Grade', 'Groupe', 'Grade/Groupe', 'Vague',
            'Site', 'Salle',
            'Formation(s)',
        ],
        header_fill=header_fill_orange,
        examples=[
            [
                'FNCP26-001', 'KOUAME', 'Jean-Marc', 'MASCULIN',
                '15/03/1990', 'Abidjan',
                'jm.kouame@gouv.ci', '0701001001', '',
                'Concours direct', 'Administrateur Civil',
                'FAB A', 'A4', 'GROUPE 1', 'A4/GROUPE 1', 'SESSION 2026',
                'CPFAE', 'SALLE A',
                'FORMATION EN ADMINISTRATION DE BASE',
            ],
            [
                'FNCP26-002', 'DIALLO', 'Mariam', 'FEMININ',
                '22/07/1992', 'Bouaké',
                'diallo.m@gouv.ci', '0702002002', '',
                'Concours direct', 'Administrateur Civil',
                'FAB A', 'A4', 'GROUPE 1', 'A4/GROUPE 1', 'SESSION 2026',
                'CPFAE', 'SALLE A',
                'FORMATION EN ADMINISTRATION DE BASE',
            ],
            [
                'FNCP26-003', 'BAMBA', 'Oumar', 'MASCULIN',
                '05/11/1988', 'Korhogo',
                '', '0703003003', '',
                'Concours direct', 'Administrateur Civil',
                'FAB A', 'A4', 'GROUPE 2', 'A4/GROUPE 2', 'SESSION 2026',
                'CPFAE', 'SALLE B',
                'FORMATION EN ADMINISTRATION DE BASE',
            ],
            [
                'FNCP26-004', 'KONE', 'Aissatou', 'FEMININ',
                '12/09/1993', 'Abidjan',
                'kone.a@gouv.ci', '0706006006', '',
                'Concours direct', 'Agent administratif',
                'FAB B', 'B3', 'GROUPE 1', 'B3/GROUPE 1', 'SESSION 2026',
                'CPFAE', 'SALLE D',
                'FORMATION EN ADMINISTRATION DE BASE',
            ],
        ],
        notes=[
            'Matricule UNIQUE et OBLIGATOIRE (clé de déduplication)',
            'Obligatoire',
            'Obligatoire',
            'MASCULIN / FEMININ',
            'JJ/MM/AAAA',
            'Optionnel',
            'Optionnel',
            'Optionnel',
            'Optionnel',
            'Optionnel (ex: Concours direct)',
            'Optionnel (ex: Administrateur Civil)',
            'FAB A, FAB B ou FAB C — détermine le secrétariat',
            'A4, A3, B3…',
            'GROUPE 1, GROUPE 2…',
            'Optionnel (ex: A4/GROUPE 1)',
            'Optionnel (ex: SESSION 2026)',
            'Optionnel (ex: CPFAE)',
            'Optionnel (ex: SALLE A)',
            'Titre(s) du cycle séparés par |',
        ],
    )
    return wb


def generate_participants_csv(filepath):
    """Génère le template CSV pour les participants."""
    import csv
    headers = [
        'Matricule', 'Nom', 'Prénoms', 'Sexe',
        'Date naissance', 'Lieu naissance',
        'Email', 'Téléphone 1', 'Téléphone 2',
        'Type concours', 'Libelle concours',
        'Catégorie', 'Grade', 'Groupe', 'Grade/Groupe', 'Vague',
        'Site', 'Salle',
        'Formation(s)',
    ]
    examples = [
        [
            'FNCP26-001', 'KOUAME', 'Jean-Marc', 'MASCULIN',
            '15/03/1990', 'Abidjan',
            'jm.kouame@gouv.ci', '0701001001', '',
            'Concours direct', 'Administrateur Civil',
            'FAB A', 'A4', 'GROUPE 1', 'A4/GROUPE 1', 'SESSION 2026',
            'CPFAE', 'SALLE A',
            'FORMATION EN ADMINISTRATION DE BASE',
        ],
        [
            'FNCP26-002', 'DIALLO', 'Mariam', 'FEMININ',
            '22/07/1992', 'Bouaké',
            'diallo.m@gouv.ci', '0702002002', '',
            'Concours direct', 'Administrateur Civil',
            'FAB A', 'A4', 'GROUPE 1', 'A4/GROUPE 1', 'SESSION 2026',
            'CPFAE', 'SALLE A',
            'FORMATION EN ADMINISTRATION DE BASE',
        ],
        [
            'FNCP26-003', 'BAMBA', 'Oumar', 'MASCULIN',
            '05/11/1988', 'Korhogo',
            '', '0703003003', '',
            'Concours direct', 'Administrateur Civil',
            'FAB A', 'A4', 'GROUPE 2', 'A4/GROUPE 2', 'SESSION 2026',
            'CPFAE', 'SALLE B',
            'FORMATION EN ADMINISTRATION DE BASE',
        ],
        [
            'FNCP26-004', 'KONE', 'Aissatou', 'FEMININ',
            '12/09/1993', 'Abidjan',
            'kone.a@gouv.ci', '0706006006', '',
            'Concours direct', 'Agent administratif',
            'FAB B', 'B3', 'GROUPE 1', 'B3/GROUPE 1', 'SESSION 2026',
            'CPFAE', 'SALLE D',
            'FORMATION EN ADMINISTRATION DE BASE',
        ],
    ]
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(examples)


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 1. Formations
    wb = generate_formations()
    p1 = os.path.join(base_dir, 'import_formations.xlsx')
    wb.save(p1)

    # 2. Formateurs
    wb = generate_formateurs()
    p2 = os.path.join(base_dir, 'import_formateurs.xlsx')
    wb.save(p2)

    # 3. Participants + formations (Excel)
    wb = generate_participants()
    p3 = os.path.join(base_dir, 'import_participants.xlsx')
    wb.save(p3)

    # 4. Participants (CSV)
    p4 = os.path.join(base_dir, 'import_participants.csv')
    generate_participants_csv(p4)

    print(f"✅ {p1}")
    print(f"   → Formations / modules uniquement")
    print(f"✅ {p2}")
    print(f"   → Formateurs uniquement")
    print(f"✅ {p3}")
    print(f"   → Participants + libellé de leur(s) formation(s) [Excel]")
    print(f"✅ {p4}")
    print(f"   → Participants + libellé de leur(s) formation(s) [CSV]")
    print()
    print("Ordre d'import :")
    print("  1. python manage.py import_excel import_formations.xlsx")
    print("  2. python manage.py import_excel import_formateurs.xlsx")
    print("  3. python manage.py import_excel import_participants.xlsx")
    print("     ou : python manage.py import_excel import_participants.csv")


if __name__ == '__main__':
    main()
