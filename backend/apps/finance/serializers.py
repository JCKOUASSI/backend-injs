from rest_framework import serializers
from apps.finance.models import FeeType, StudentFee, PaymentTransaction


class FeeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeType
        fields = '__all__'


class StudentFeeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    matricule = serializers.CharField(source='student.matricule', read_only=True)
    fee_name = serializers.CharField(source='fee_type.name', read_only=True)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = StudentFee
        fields = '__all__'

    def get_photo_url(self, obj):
        user = getattr(obj.student, 'user', None)
        photo = getattr(user, 'photo', None) if user else None
        if photo:
            request = self.context.get('request')
            return request.build_absolute_uri(photo.url) if request else photo.url
        return None


class PaymentTransactionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student_fee.student.user.get_full_name', read_only=True)
    matricule = serializers.CharField(source='student_fee.student.matricule', read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = '__all__'


class PaymentInitSerializer(serializers.Serializer):
    student_fee_id = serializers.UUIDField()
    provider = serializers.ChoiceField(choices=[
        'orange_money', 'mtn_momo', 'moov_money', 'wave', 'visa_card',
    ])
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    phone = serializers.CharField(max_length=20, required=False)
    callback_url = serializers.URLField(required=False)
