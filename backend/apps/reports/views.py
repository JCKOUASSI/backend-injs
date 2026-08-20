from rest_framework.views import APIView
from rest_framework.response import Response

from apps.students.models import Student, AcademicRecord
from apps.exams.models import ExamSession
from apps.core.export import export_to_pdf, export_to_excel, export_to_word
from apps.reports.services.transcript import build_semester_transcript, render_transcript_pdf
from apps.reports.services.statistics import (
    analytics_compat_payload,
    build_academic_statistics,
    parse_scope,
    parse_sections,
)


class AnalyticsDashboardView(APIView):
    permission_module = 'reports'

    def get(self, request):
        return Response(analytics_compat_payload(parse_scope(request.query_params)))


class AcademicStatisticsView(APIView):
    """Tableau de bord statistiques LMD (KPI, pédagogie, admin, historique, alertes)."""
    permission_module = 'reports'

    def get(self, request):
        scope = parse_scope(request.query_params)
        sections = parse_sections(request.query_params.get('sections'))
        return Response(build_academic_statistics(scope, sections))


class TranscriptPDFView(APIView):
    """Relevé de notes officiel INJS (bulletin semestriel PDF)."""
    permission_module = 'reports'

    def get(self, request, student_id):
        try:
            student = Student.objects.select_related(
                'user', 'program', 'specialization', 'promotion'
            ).get(id=student_id)
        except Student.DoesNotExist:
            return Response({'error': 'Étudiant introuvable'}, status=404)

        exam_session = self._resolve_exam_session(request)
        if not exam_session:
            return Response({'error': 'Session d\'examen introuvable'}, status=404)

        if request.query_params.get('format') == 'json':
            return Response(build_semester_transcript(student, exam_session))

        return render_transcript_pdf(student, exam_session)

    @staticmethod
    def _resolve_exam_session(request):
        session_id = request.query_params.get('exam_session')
        if session_id:
            return ExamSession.objects.select_related(
                'academic_year', 'semester'
            ).filter(id=session_id).first()

        semester_number = request.query_params.get('semester')
        academic_year = request.query_params.get('academic_year')
        qs = ExamSession.objects.select_related('academic_year', 'semester')
        if semester_number:
            qs = qs.filter(semester__number=semester_number)
        if academic_year:
            qs = qs.filter(academic_year__label=academic_year)
        return qs.order_by('-academic_year__start_date').first()


class TranscriptSummaryView(APIView):
    """Historique des relevés (tous semestres validés)."""
    permission_module = 'reports'

    def get(self, request, student_id):
        try:
            student = Student.objects.select_related('user', 'program').get(id=student_id)
        except Student.DoesNotExist:
            return Response({'error': 'Étudiant introuvable'}, status=404)

        records = AcademicRecord.objects.filter(student=student).select_related(
            'semester', 'academic_year'
        )
        headers = ['Année', 'Semestre', 'Moyenne', 'Crédits', 'Décision', 'Mention']
        rows = []
        for r in records:
            mention = (r.snapshot_data or {}).get('mention', '—')
            rows.append([
                r.academic_year.label, r.semester.name,
                r.semester_average, f'{r.credits_acquired}/{r.credits_total}',
                r.decision, mention,
            ])
        title = f'Historique académique — {student.user.get_full_name()} ({student.matricule})'
        export_format = request.query_params.get('export')
        if export_format == 'excel':
            return export_to_excel(headers, rows, f'historique_{student.matricule}')
        if export_format == 'word':
            return export_to_word(title, headers, rows, f'historique_{student.matricule}')
        if export_format == 'pdf':
            return export_to_pdf(title, headers, rows, f'historique_{student.matricule}')
        return Response({'student': student.matricule, 'records': rows})
