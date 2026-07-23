from rest_framework import serializers
from apps.students.models import Student, Enrollment, AcademicRecord
from apps.accounts.serializers import UserSerializer


class StudentSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    promotion_name = serializers.CharField(source='promotion.name', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    photo_url = serializers.SerializerMethodField()
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = '__all__'

    def get_photo_url(self, obj):
        if obj.user.photo:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.user.photo.url) if request else obj.user.photo.url
        return None

    def get_qr_code_url(self, obj):
        if obj.qr_code:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.qr_code.url) if request else obj.qr_code.url
        return None


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    matricule = serializers.CharField(source='student.matricule', read_only=True)

    class Meta:
        model = Enrollment
        fields = '__all__'


class AcademicRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    matricule = serializers.CharField(source='student.matricule', read_only=True)

    class Meta:
        model = AcademicRecord
        fields = '__all__'
