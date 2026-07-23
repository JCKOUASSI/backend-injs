from django.contrib import admin
from apps.academics.models import (
    Institution, Department, Program, Promotion, AcademicYear,
    Semester, TeachingUnit, Course, ProgramCourse, Specialization,
    StapsJobNomenclature,
)

admin.site.register(Institution)
admin.site.register(Department)
admin.site.register(Specialization)
admin.site.register(Program)
admin.site.register(Promotion)
admin.site.register(AcademicYear)
admin.site.register(Semester)
admin.site.register(TeachingUnit)
admin.site.register(Course)
admin.site.register(ProgramCourse)


@admin.register(StapsJobNomenclature)
class StapsJobNomenclatureAdmin(admin.ModelAdmin):
    list_display = [
        'degree_type', 'specialization', 'civil_service_grade', 'job_title',
        'diploma_code', 'duration_years', 'is_active',
    ]
    list_filter = ['degree_type', 'civil_service_grade', 'track', 'diploma_code', 'is_active']
    search_fields = ['job_title', 'diploma_label', 'specialization__code', 'specialization__name']
    readonly_fields = ['created_at', 'updated_at']
