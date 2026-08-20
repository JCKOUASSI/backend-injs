from rest_framework import serializers
from apps.academics.models import (
    Institution, Department, Program, Promotion, AcademicYear,
    Semester, TeachingUnit, Course, ProgramCourse, Specialization,
    StapsJobNomenclature,
)


class InstitutionSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Institution
        fields = '__all__'

    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.logo.url) if request else obj.logo.url
        return None


class DepartmentSerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(source='institution.name', read_only=True)
    head_name = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = '__all__'

    def get_head_name(self, obj):
        if not obj.head_id:
            return None
        return obj.head.get_full_name() or obj.head.email


class SpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialization
        fields = '__all__'


class ProgramSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    degree_type_display = serializers.CharField(source='get_degree_type_display', read_only=True)

    class Meta:
        model = Program
        fields = '__all__'


class PromotionSerializer(serializers.ModelSerializer):
    program_name = serializers.CharField(source='program.name', read_only=True)

    class Meta:
        model = Promotion
        fields = '__all__'


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = '__all__'


class SemesterSerializer(serializers.ModelSerializer):
    academic_year_label = serializers.CharField(source='academic_year.label', read_only=True)

    class Meta:
        model = Semester
        fields = '__all__'


class CourseSerializer(serializers.ModelSerializer):
    teaching_unit_code = serializers.CharField(source='teaching_unit.code', read_only=True)
    teaching_unit_name = serializers.CharField(source='teaching_unit.name', read_only=True)
    teaching_unit_semester = serializers.IntegerField(source='teaching_unit.semester_number', read_only=True)
    hours_total = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = '__all__'

    def get_hours_total(self, obj):
        return (obj.hours_cm or 0) + (obj.hours_td or 0) + (obj.hours_tp or 0)


class TeachingUnitSerializer(serializers.ModelSerializer):
    courses = CourseSerializer(many=True, read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = TeachingUnit
        fields = '__all__'


class ProgramCourseSerializer(serializers.ModelSerializer):
    teaching_unit_detail = TeachingUnitSerializer(source='teaching_unit', read_only=True)
    specialization_detail = SpecializationSerializer(source='specialization', read_only=True)
    credits = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProgramCourse
        fields = '__all__'


class StapsJobNomenclatureSerializer(serializers.ModelSerializer):
    specialization_detail = SpecializationSerializer(source='specialization', read_only=True)
    degree_type_display = serializers.CharField(source='get_degree_type_display', read_only=True)
    civil_service_grade_display = serializers.CharField(
        source='get_civil_service_grade_display', read_only=True
    )
    track_display = serializers.CharField(source='get_track_display', read_only=True)
    diploma_code_display = serializers.CharField(source='get_diploma_code_display', read_only=True)

    class Meta:
        model = StapsJobNomenclature
        fields = '__all__'
