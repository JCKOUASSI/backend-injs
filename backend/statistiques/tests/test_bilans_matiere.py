"""Tests bilans — dimension matière (agrégation tous groupes)."""
from django.test import TestCase

from formations.models import Formation, Module, ModuleParticipant, Participant, RefModule
from statistiques.bilans import compute_bilans, compute_bilan_effectifs_matiere


class BilansMatiereTest(TestCase):
    def test_deontologie_aggregates_all_groups(self):
        formation = Formation.objects.create(formation='Formation en Administration de Base')
        ref = RefModule.objects.create(intitule='DEONTOLOGIE')

        for g in ('GROUPE 9', 'GROUPE 10', 'GROUPE 11'):
            mod = Module.objects.create(
                formation=formation,
                ref_module=ref,
                intitule='DEONTOLOGIE',
                grade='A4',
                groupe=g,
            )
            for i in range(3):
                p = Participant.objects.create(
                    matricule=f'MAT-{g}-{i}',
                    nom=f'Auditeur{i}',
                    prenom='Test',
                    categorie='A',
                    sexe=Participant.Sexe.MASCULIN,
                )
                ModuleParticipant.objects.create(module=mod, participant=p)

        data = compute_bilans(
            annee=2026,
            formation_id=formation.id,
            dimension='matiere',
        )
        deonto = [b for b in data['bilans'] if b['libelle'].upper() == 'DEONTOLOGIE']
        self.assertEqual(len(deonto), 1)
        self.assertEqual(deonto[0]['nb_groupes'], 3)
        self.assertEqual(deonto[0]['inscrits'], 9)

        tableau = compute_bilan_effectifs_matiere(
            formation.id,
            ref_module_id=ref.id,
            annee=2026,
        )
        self.assertEqual(tableau['type'], 'effectifs_matiere')
        self.assertEqual(tableau['effectifs_auditeurs'], 9)
        self.assertEqual(tableau['nb_groupes'], 3)
