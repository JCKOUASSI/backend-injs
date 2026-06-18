"""Tests appariement stable post-migration 0076."""

from datetime import date, datetime, timezone as dt_timezone

from django.test import TestCase
from django.utils import timezone

from formations.audit_recovery import (
    _parse_explicit_mapping,
    apply_session_recovery,
    match_deleted_modules_to_survivors,
)
from formations.models import Formation, Module, SessionModule


class AuditRecoveryMatchingTest(TestCase):
    """Scénario DEONTOLOGIE : 4 doublons supprimés, survivants proches en id."""

    def setUp(self):
        self.formation = Formation.objects.create(formation='Test DEONTO')
        self.d15 = date(2026, 6, 15)
        self.d16 = date(2026, 6, 16)
        self.d17 = date(2026, 6, 17)

        def mod(pk, groupe):
            return Module.objects.create(
                pk=pk,
                formation=self.formation,
                intitule='DEONTOLOGIE',
                grade='G',
                groupe=groupe,
                vague='V1',
            )

        self.surv_327 = mod(327, 'GROUPE 18')
        self.surv_336 = mod(336, 'GROUPE 17')
        self.surv_363 = mod(363, 'GROUPE 20')
        self.surv_372 = mod(372, 'GROUPE 19')
        # Bruit : id proche mais mauvais EDT
        self.surv_392 = mod(392, 'GROUPE 25')

        for mod in (self.surv_327, self.surv_336, self.surv_363, self.surv_372):
            for day in (self.d15, self.d16, self.d17):
                SessionModule.objects.create(module=mod, date_journee=day, numero=2)

        # #372 a déjà les horaires (survivant du doublon #312)
        stop_312 = timezone.make_aware(datetime(2026, 6, 15, 17, 25, 54))
        start_312 = timezone.make_aware(datetime(2026, 6, 15, 13, 5, 32))
        s372 = SessionModule.objects.get(module=self.surv_372, date_journee=self.d15, numero=2)
        s372.demarree_le = start_312
        s372.terminee_le = stop_312
        s372.save()

        def audit_events(stop15, stop16=None, stop17=None):
            start = timezone.make_aware(datetime(2026, 6, 15, 13, 5, 32))
            events = {
                1: {
                    'date_journee': self.d15,
                    'numero': 2,
                    'start': start,
                    'stop': stop15,
                },
                2: {
                    'date_journee': self.d16,
                    'numero': 2,
                    'start': timezone.make_aware(datetime(2026, 6, 16, 13, 6, 0)),
                    'stop': stop16 or timezone.make_aware(datetime(2026, 6, 16, 18, 0, 0)),
                },
            }
            if stop17:
                events[3] = {
                    'date_journee': self.d17,
                    'numero': 2,
                    'start': timezone.make_aware(datetime(2026, 6, 17, 13, 3, 0)),
                    'stop': stop17,
                }
            return events

        self.deleted = {
            321: audit_events(timezone.make_aware(datetime(2026, 6, 15, 17, 23, 38))),
            312: audit_events(timezone.make_aware(datetime(2026, 6, 15, 17, 25, 54))),
            330: audit_events(timezone.make_aware(datetime(2026, 6, 15, 17, 31, 8))),
            357: audit_events(timezone.make_aware(datetime(2026, 6, 15, 17, 35, 18))),
        }
        self.meta = {
            mid: {'formation_id': self.formation.id, 'intitule': 'DEONTOLOGIE'}
            for mid in self.deleted
        }

    def test_auto_match_dedup_0076(self):
        mapping = match_deleted_modules_to_survivors(self.deleted, self.meta)
        self.assertEqual(mapping[312].id, 372)
        self.assertEqual(mapping[321].id, 327)
        self.assertEqual(mapping[330].id, 336)
        self.assertEqual(mapping[357].id, 363)

    def test_explicit_mapping_override(self):
        explicit = _parse_explicit_mapping('321:327,312:372,330:336,357:363')
        mapping = match_deleted_modules_to_survivors(
            self.deleted, self.meta, explicit_mapping=explicit,
        )
        self.assertEqual({k: v.id for k, v in mapping.items()}, explicit)

    def test_apply_recovery_on_empty_survivor(self):
        mapping = match_deleted_modules_to_survivors(self.deleted, self.meta)
        stats = apply_session_recovery(
            mapping[321], self.deleted[321], dry_run=True,
        )
        self.assertEqual(stats['updated'], 2)
        self.assertEqual(stats['missing'], 0)

