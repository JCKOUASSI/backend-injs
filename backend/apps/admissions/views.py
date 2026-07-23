from rest_framework import serializers, viewsets
from django_filters.rest_framework import DjangoFilterBackend
from apps.admissions.models import AdmissionCampaign, PreRegistration


class AdmissionCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionCampaign
        fields = '__all__'


class PreRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreRegistration
        fields = '__all__'


class AdmissionCampaignViewSet(viewsets.ModelViewSet):
    queryset = AdmissionCampaign.objects.all()
    serializer_class = AdmissionCampaignSerializer
    permission_module = 'admissions'


class PreRegistrationViewSet(viewsets.ModelViewSet):
    queryset = PreRegistration.objects.all()
    serializer_class = PreRegistrationSerializer
    permission_module = 'admissions'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['campaign', 'status']
