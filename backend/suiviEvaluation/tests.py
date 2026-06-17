"""Tests — calculs de moyennes pondérées et décisions pédagogiques."""
from decimal import Decimal
from django.test import TestCase

from formations.models import Formation, Module, Participant
from .models import (
    TypeEpreuve, Epreuve, NoteEpreuve, ParametresEvaluation, DecisionPedagogique,
)
from . import services as services


class MoyenneCalculTest(TestCase):
    def setUp(self):
        self.formation = Formation.objects.create(formation='Cycle Test')
        self.module = Module.objects.create(
            formation=self.formation, intitule='Module A',
            duree_prevue_heures=Decimal('10'),
        )
        self.participant = Participant.objects.create(
            matricule='M001', nom='Doe', prenom='John', grade='A3',
        )
        self.type_examen = TypeEpreuve.objects.create(code='EX', libelle='Examen', ordre=1)
        self.type_devoir = TypeEpreuve.objects.create(code='DV', libelle='Devoir', ordre=2)

    def test_moyenne_ponderee(self):
        # Examen coeff 3 -> 15 ; Devoir coeff 1 -> 11
        ep1 = Epreuve.objects.create(
            type_epreuve=self.type_examen, module=self.module,
            intitule='Examen final', coefficient=Decimal('3'),
        )
        ep2 = Epreuve.objects.create(
            type_epreuve=self.type_devoir, module=self.module,
            intitule='Devoir 1', coefficient=Decimal('1'),
        )
        NoteEpreuve.objects.create(epreuve=ep1, participant=self.participant, note=Decimal('15'))
        NoteEpreuve.objects.create(epreuve=ep2, participant=self.participant, note=Decimal('11'))

        mm = services.calculer_moyenne_module(self.module, self.participant)
        # (15*3 + 11*1) / 4 = 56/4 = 14.0
        self.assertEqual(mm.moyenne, Decimal('14.00'))
        self.assertEqual(mm.nb_epreuves, 2)

    def test_moyenne_generale_et_decision(self):
        ep = Epreuve.objects.create(
            type_epreuve=self.type_examen, module=self.module,
            intitule='Examen', coefficient=Decimal('1'),
        )
        NoteEpreuve.objects.create(epreuve=ep, participant=self.participant, note=Decimal('15'))
        services.calculer_moyenne_module(self.module, self.participant)

        moyenne = services.calculer_moyenne_generale(self.participant, self.formation)
        self.assertEqual(moyenne, Decimal('15.00'))

        # Sans pointages -> 0% de présence -> EXCLUSION (présence < 50%)
        decision = services.calculer_decision(self.participant, self.formation)
        self.assertEqual(decision.decision, DecisionPedagogique.TypeDecision.EXCLUSION)

        # Avec seuil de présence à 0 -> ADMIS, mention Bien (15 >= 14)
        ParametresEvaluation.objects.create(
            formation=self.formation,
            seuil_admission=Decimal('12'),
            seuil_mention_bien=Decimal('14'),
            seuil_mention_tres_bien=Decimal('16'),
            taux_presence_min=Decimal('0'),
        )
        decision = services.calculer_decision(self.participant, self.formation)
        self.assertEqual(decision.decision, DecisionPedagogique.TypeDecision.ADMIS)
        self.assertEqual(decision.mention, DecisionPedagogique.Mention.BIEN)

    def test_parametres_personnalises(self):
        ParametresEvaluation.objects.create(
            formation=self.formation,
            seuil_admission=Decimal('10'),
            taux_presence_min=Decimal('0'),
        )
        params = services._get_parametres(self.formation)
        self.assertEqual(params['seuil_admission'], 10.0)
        self.assertEqual(params['taux_presence_min'], 0.0)
