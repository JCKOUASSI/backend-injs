"""Tests paiements et finance INJS."""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.core.tests.test_utils import (
    create_finance_user, create_institution_bundle, create_student,
)
from apps.finance.models import FeeType, PaymentTransaction, StudentFee


class PaymentFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        _, _, program, promotion, ay = create_institution_bundle()
        _, self.student = create_student(
            email='payer@test.ci', matricule='PAY001',
            program=program, promotion=promotion,
        )
        self.fee_type = FeeType.objects.create(
            code='INSCRIPTION-TEST', name='Inscription test',
            amount=Decimal('150000'), academic_year=ay, program=program,
        )
        self.student_fee = StudentFee.objects.create(
            student=self.student, fee_type=self.fee_type,
            amount_due=Decimal('150000'),
        )
        self.finance_user = create_finance_user()
        self.client.force_authenticate(user=self.finance_user)

    def test_list_providers(self):
        response = self.client.get(reverse('payment-provider-list'))
        self.assertEqual(response.status_code, 200)
        codes = {p['code'] for p in response.data}
        self.assertIn('orange_money', codes)
        self.assertIn('wave', codes)

    def test_initiate_orange_money_sandbox(self):
        response = self.client.post(reverse('payment-initiate'), {
            'student_fee_id': str(self.student_fee.id),
            'provider': 'orange_money',
            'phone': '0700000000',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'pending')
        self.assertTrue(response.data['reference'].startswith('INJS-'))
        self.assertTrue(response.data['payment_url'])

        tx = PaymentTransaction.objects.get(id=response.data['id'])
        self.assertEqual(tx.provider, 'orange_money')
        self.assertTrue(tx.raw_response.get('sandbox'))

    def test_initiate_unknown_provider(self):
        response = self.client.post(reverse('payment-initiate'), {
            'student_fee_id': str(self.student_fee.id),
            'provider': 'unknown_provider',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_initiate_requires_finance_create(self):
        from apps.accounts.models import User
        from apps.core.tests.test_utils import TEST_PASSWORD
        user = User.objects.create_user(
            email='viewer@test.ci', password=TEST_PASSWORD,
            first_name='View', last_name='Only',
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(reverse('payment-initiate'), {
            'student_fee_id': str(self.student_fee.id),
            'provider': 'wave',
        }, format='json')
        self.assertEqual(response.status_code, 403)

    def test_verify_payment_updates_student_fee(self):
        initiate = self.client.post(reverse('payment-initiate'), {
            'student_fee_id': str(self.student_fee.id),
            'provider': 'wave',
            'amount': '150000',
        }, format='json')
        tx_id = initiate.data['id']
        response = self.client.post(reverse('payment-verify', kwargs={'pk': tx_id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'success')

        self.student_fee.refresh_from_db()
        self.assertEqual(self.student_fee.status, 'paid')
        self.assertEqual(self.student_fee.amount_paid, Decimal('150000'))

    def test_student_fee_balance(self):
        self.assertEqual(self.student_fee.balance, Decimal('150000'))
        self.student_fee.amount_paid = Decimal('50000')
        self.assertEqual(self.student_fee.balance, Decimal('100000'))
