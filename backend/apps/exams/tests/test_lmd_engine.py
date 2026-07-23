"""Tests du moteur LMD INJS (CC/CT, compensation, mentions)."""
from decimal import Decimal
from django.test import TestCase, override_settings

from apps.exams.services.lmd_engine import (
    compute_mention,
    _ecue_from_cc_ct,
    _validate_ue,
    _validate_semester,
)


class MentionTests(TestCase):
    def test_mentions_officielles(self):
        self.assertEqual(compute_mention(Decimal('16')), 'Très bien')
        self.assertEqual(compute_mention(Decimal('14')), 'Bien')
        self.assertEqual(compute_mention(Decimal('12')), 'Assez bien')
        self.assertEqual(compute_mention(Decimal('10')), 'Passable')
        self.assertEqual(compute_mention(Decimal('9.5')), 'Ajourné')


@override_settings(LMD_CC_WEIGHT=0.4, LMD_CT_WEIGHT=0.6)
class EcueCalculationTests(TestCase):
    def test_cc_ct_40_60(self):
        # CC=8, CT=14 → 8×0.4 + 14×0.6 = 11.6
        result = _ecue_from_cc_ct(Decimal('8'), Decimal('14'))
        self.assertEqual(result, Decimal('11.60'))

    def test_cc_only_fallback(self):
        result = _ecue_from_cc_ct(Decimal('12'), None)
        self.assertEqual(result, Decimal('12.00'))


class UeValidationTests(TestCase):
    def test_validation_directe_tous_ecue_ok(self):
        ecues = [
            {'average': 10.0, 'validated': True},
            {'average': 12.0, 'validated': True},
        ]
        validated, mode = _validate_ue(ecues, Decimal('11'))
        self.assertTrue(validated)
        self.assertEqual(mode, 'direct')

    def test_validation_compensation_ue(self):
        # ECUE 1 = 9 (≥8), ECUE 2 = 12 → moy UE = 10.5
        ecues = [
            {'average': 9.0, 'validated': False},
            {'average': 12.0, 'validated': True},
        ]
        validated, mode = _validate_ue(ecues, Decimal('10.5'))
        self.assertTrue(validated)
        self.assertEqual(mode, 'compensation')

    def test_echec_compensation_ecue_sous_8(self):
        ecues = [
            {'average': 7.5, 'validated': False},
            {'average': 14.0, 'validated': True},
        ]
        validated, mode = _validate_ue(ecues, Decimal('11'))
        self.assertFalse(validated)
        self.assertEqual(mode, 'echec')


class SemesterValidationTests(TestCase):
    def test_validation_directe_toutes_ue(self):
        ues = [{'validated': True, 'average': 11.0}, {'validated': True, 'average': 12.0}]
        validated, mode = _validate_semester(ues, Decimal('11.5'))
        self.assertTrue(validated)
        self.assertEqual(mode, 'direct')

    def test_compensation_semestre_moyenne_ok(self):
        ues = [{'validated': False, 'average': 9.0}, {'validated': True, 'average': 13.0}]
        validated, mode = _validate_semester(ues, Decimal('10.5'))
        self.assertTrue(validated)
        self.assertEqual(mode, 'compensation')

    def test_echec_semestre_moyenne_insuffisante(self):
        ues = [{'validated': False, 'average': 8.0}, {'validated': False, 'average': 9.0}]
        validated, mode = _validate_semester(ues, Decimal('8.5'))
        self.assertFalse(validated)
        self.assertEqual(mode, 'echec')
