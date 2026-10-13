"""Helpers d'export partagés (Excel) — utilisés par l'export Bilan FAC."""
import re

C_HEADER = 'FFFCE7B4'
C_HEADER_DARK = 'FFF4CF84'
C_GRAY = 'FFD9D9D9'
C_BLUE = 'FF99CCFF'
C_PINK = 'FFCCFF'
C_GREEN = 'FF77BCE7'
C_TD_BLUE = 'FFDDEBF7'
C_TD_TOTAL = 'FFFFE566'
C_TD_DATA = 'FFFFFDF5'
C_BLACK = 'FF000000'


def _safe_filename(text):
    return re.sub(r'[^\w\-]+', '_', text, flags=re.UNICODE).strip('_')[:80]


def _fmt_nb(n):
    return f'{int(n or 0):,}'.replace(',', '\u00a0')


def _xlsx_styles():
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    border = Border(
        left=Side(style='thin', color='000000'),
        right=Side(style='thin', color='000000'),
        top=Side(style='thin', color='000000'),
        bottom=Side(style='thin', color='000000'),
    )
    return {
        'border': border,
        'align': Alignment(horizontal='center', vertical='center', wrap_text=True),
        'align_left': Alignment(horizontal='left', vertical='top', wrap_text=True),
        'font_bold': Font(bold=True, size=10),
        'font_title': Font(bold=True, size=11, underline='single'),
        'font_hdr': Font(bold=True, size=8),
        'fills': {
            'header': PatternFill(start_color=C_HEADER, end_color=C_HEADER, fill_type='solid'),
            'header_dark': PatternFill(start_color=C_HEADER_DARK, end_color=C_HEADER_DARK, fill_type='solid'),
            'gray': PatternFill(start_color=C_GRAY, end_color=C_GRAY, fill_type='solid'),
            'blue': PatternFill(start_color=C_BLUE, end_color=C_BLUE, fill_type='solid'),
            'pink': PatternFill(start_color=C_PINK, end_color=C_PINK, fill_type='solid'),
            'green': PatternFill(start_color=C_GREEN, end_color=C_GREEN, fill_type='solid'),
            'td_blue': PatternFill(start_color=C_TD_BLUE, end_color=C_TD_BLUE, fill_type='solid'),
            'td_total': PatternFill(start_color=C_TD_TOTAL, end_color=C_TD_TOTAL, fill_type='solid'),
            'td_data': PatternFill(start_color=C_TD_DATA, end_color=C_TD_DATA, fill_type='solid'),
        },
    }


def _style_cell(cell, styles, fill='td_data', bold=False, align=None):
    cell.border = styles['border']
    cell.alignment = align or styles['align']
    cell.font = styles['font_bold'] if bold else styles['font_hdr']
    cell.fill = styles['fills'].get(fill, styles['fills']['td_data'])


