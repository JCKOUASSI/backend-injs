from decimal import Decimal
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
import uuid

from apps.finance.models import FeeType, StudentFee, PaymentTransaction, PaymentProviderConfig
from apps.finance.providers.base import get_provider, PaymentRequest, PROVIDERS
from apps.finance.serializers import (
    FeeTypeSerializer, StudentFeeSerializer, PaymentTransactionSerializer, PaymentInitSerializer,
)
from apps.core.mixins import ExportMixin


class FeeTypeViewSet(viewsets.ModelViewSet):
    queryset = FeeType.objects.select_related('program', 'academic_year').all()
    serializer_class = FeeTypeSerializer
    permission_module = 'finance'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['academic_year', 'program']


class StudentFeeViewSet(ExportMixin, viewsets.ModelViewSet):
    queryset = StudentFee.objects.select_related('student', 'student__user', 'fee_type').all()
    serializer_class = StudentFeeSerializer
    permission_module = 'finance'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['student', 'status', 'fee_type']
    export_headers = ['Matricule', 'Étudiant', 'Frais', 'Dû', 'Payé', 'Statut']
    export_title = 'Frais étudiants INJS'
    export_filename = 'frais_etudiants'

    def get_export_rows(self):
        return [
            [
                f.student.matricule, f.student.user.get_full_name(),
                f.fee_type.name, f.amount_due, f.amount_paid, f.get_status_display(),
            ]
            for f in self.filter_queryset(self.get_queryset())
        ]


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PaymentTransaction.objects.select_related('student_fee', 'student_fee__student').all()
    serializer_class = PaymentTransactionSerializer
    permission_module = 'finance'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'provider', 'student_fee__student']

    @action(detail=False, methods=['post'])
    def initiate(self, request):
        serializer = PaymentInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            student_fee = StudentFee.objects.get(id=data['student_fee_id'])
        except StudentFee.DoesNotExist:
            return Response({'error': 'Frais introuvable'}, status=404)

        provider_code = data['provider']
        if provider_code not in PROVIDERS:
            return Response({'error': f'Provider {provider_code} non supporté'}, status=400)

        reference = f'INJS-{uuid.uuid4().hex[:12].upper()}'
        amount = data.get('amount') or student_fee.balance

        transaction = PaymentTransaction.objects.create(
            reference=reference,
            student_fee=student_fee,
            amount=amount,
            provider=provider_code,
            phone=data.get('phone', ''),
            status='initiated',
        )

        provider = get_provider(provider_code)
        result = provider.initiate_payment(PaymentRequest(
            amount=Decimal(str(amount)),
            currency='XOF',
            reference=reference,
            phone=data.get('phone'),
            email=request.user.email if request.user.is_authenticated else '',
            description=f'{student_fee.fee_type.name} - {student_fee.student.matricule}',
            callback_url=data.get('callback_url', ''),
        ))

        transaction.provider_reference = result.provider_reference
        transaction.payment_url = result.payment_url or ''
        transaction.raw_response = result.raw_response or {}
        transaction.status = 'pending' if result.success else 'failed'
        transaction.save()

        return Response(PaymentTransactionSerializer(transaction).data, status=201)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        transaction = self.get_object()
        provider = get_provider(transaction.provider)
        result = provider.verify_payment(transaction.reference)
        if result.success:
            transaction.status = 'success'
            transaction.completed_at = timezone.now()
            fee = transaction.student_fee
            fee.amount_paid += transaction.amount
            if fee.amount_paid >= fee.amount_due:
                fee.status = 'paid'
            else:
                fee.status = 'partial'
            fee.save()
            transaction.save()
        return Response(PaymentTransactionSerializer(transaction).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def orange_webhook(request):
    provider = get_provider('orange_money')
    result = provider.handle_webhook(request.data)
    _process_webhook(result)
    return Response({'status': 'ok'})


@api_view(['POST'])
@permission_classes([AllowAny])
def mtn_webhook(request):
    provider = get_provider('mtn_momo')
    result = provider.handle_webhook(request.data)
    _process_webhook(result)
    return Response({'status': 'ok'})


@api_view(['POST'])
@permission_classes([AllowAny])
def wave_webhook(request):
    provider = get_provider('wave')
    result = provider.handle_webhook(request.data)
    _process_webhook(result)
    return Response({'status': 'ok'})


def _process_webhook(result):
    if not result.success:
        return
    try:
        tx = PaymentTransaction.objects.get(reference=result.transaction_id)
        tx.status = 'success'
        tx.completed_at = timezone.now()
        tx.save()
        fee = tx.student_fee
        fee.amount_paid += tx.amount
        fee.status = 'paid' if fee.amount_paid >= fee.amount_due else 'partial'
        fee.save()
    except PaymentTransaction.DoesNotExist:
        pass


class PaymentProviderViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PaymentProviderConfig.objects.filter(is_enabled=True)
    permission_module = 'finance'

    def list(self, request):
        providers = [
            {'code': code, 'name': dict(PaymentTransaction.PROVIDERS).get(code, code), 'enabled': True}
            for code in PROVIDERS.keys()
        ]
        return Response(providers)
