from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.export import export_to_excel, export_to_pdf, export_to_word


class ExportMixin:
    """Mixin for ViewSets supporting PDF/Excel/Word export."""

    export_headers: list[str] = []
    export_title: str = 'Export INJS'
    export_filename: str = 'export_injs'

    def get_export_rows(self):
        raise NotImplementedError

    @action(detail=False, methods=['get'], url_path='export/(?P<export_format>pdf|excel|word)')
    def export(self, request, export_format=None):
        rows = self.get_export_rows()
        headers = self.export_headers
        filename = self.export_filename
        if export_format == 'pdf':
            return export_to_pdf(self.export_title, headers, rows, filename)
        if export_format == 'excel':
            return export_to_excel(headers, rows, filename)
        if export_format == 'word':
            return export_to_word(self.export_title, headers, rows, filename)
        return Response({'error': 'Format non supporté'}, status=400)
