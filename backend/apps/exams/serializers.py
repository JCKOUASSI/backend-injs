from rest_framework import serializers
from apps.exams.models import ExamSession, Evaluation, Grade, Deliberation, Jury, Defense


class ExamSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamSession
        fields = '__all__'


class EvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evaluation
        fields = '__all__'


class GradeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    matricule = serializers.CharField(source='student.matricule', read_only=True)
    evaluation_name = serializers.CharField(source='evaluation.name', read_only=True)
    evaluation_type = serializers.CharField(source='evaluation.evaluation_type', read_only=True)
    max_score = serializers.DecimalField(
        source='evaluation.max_score', max_digits=5, decimal_places=2, read_only=True,
    )
    teaching_unit_code = serializers.CharField(source='evaluation.teaching_unit.code', read_only=True)
    teaching_unit_name = serializers.CharField(source='evaluation.teaching_unit.name', read_only=True)
    course_code = serializers.SerializerMethodField()
    course_name = serializers.SerializerMethodField()
    course_id = serializers.SerializerMethodField()
    passing_score = serializers.SerializerMethodField()
    has_course = serializers.SerializerMethodField()

    class Meta:
        model = Grade
        fields = '__all__'

    def get_course_code(self, obj):
        course = obj.evaluation.course
        if course:
            return course.code
        return obj.evaluation.teaching_unit.code

    def get_course_name(self, obj):
        course = obj.evaluation.course
        if course:
            return course.name
        return obj.evaluation.teaching_unit.name

    def get_course_id(self, obj):
        course = obj.evaluation.course
        return str(course.id) if course else str(obj.evaluation.teaching_unit_id)

    def get_passing_score(self, obj):
        from django.conf import settings
        course = obj.evaluation.course
        if course and course.passing_score is not None:
            return float(course.passing_score)
        ue = obj.evaluation.teaching_unit
        if ue and getattr(ue, 'passing_score', None) is not None:
            return float(ue.passing_score)
        return float(settings.LMD_PASSING_AVERAGE)

    def get_has_course(self, obj):
        return bool(obj.evaluation.course_id)


class DeliberationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deliberation
        fields = '__all__'


class JurySerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.get_full_name', read_only=True)

    class Meta:
        model = Jury
        fields = '__all__'


class DefenseSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)

    class Meta:
        model = Defense
        fields = '__all__'
