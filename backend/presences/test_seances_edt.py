"""Lot C — présence par QR sur séances LMD (EDT) + émargement manuel à motif.

Couvre le cycle complet du modèle 08 appliqué à l'EDT : génération du jeton,
scan (entrée puis sortie, fenêtre, groupe), émargement de masse (badger tout le
monde), motif obligatoire sur correction de badge, et clôture automatique.
Les durées planifiées sont ancrées sur l'heure courante pour que la fenêtre de
scan soit ouverte pendant l'exécution des tests (auciune fragilité temporelle).
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from authentication.models import User
from edts.models import AffectationCreneau, CreneauTemplate, EmploiDuTemps
from formations.models import Participant, QRToken, RefFormation
from presences import seances_edt_services as service
from presences.models import AuditLog, Pointage
from scolarite.models import (
    AffectationGroupe, AnneeAcademique, DossierEtudiant, Groupe,
    InscriptionAdministrative, Niveau, StatutEtudiant,
)

JOURS = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI', 'DIMANCHE']


def _fenetre_temporelle():
    """Créneau centré sur maintenant : ouvert 08:00 locales ± tolérances."""
    now = timezone.localtime().replace(second=0, microsecond=0)
    debut = now - timedelta(minutes=5)
    fin = now + timedelta(minutes=55)
    return debut, fin


class SeanceEdtFixtureMixin:
    @classmethod
    def setUpTestData(cls):
        today = timezone.localdate()
        cls.date_seance = today
        debut, fin = _fenetre_temporelle()
        cls.annee = AnneeAcademique.objects.create(
            libelle='2026-2027', date_debut=today - timedelta(weeks=3),
            date_fin=today + timedelta(weeks=40), courante=True,
        )
        cls.enseignant = User.objects.create_user(username='ens-edt', password='x', role='ENCADRANT')
        cls.admin = User.objects.create_user(username='admin-edt', password='x', role='ADMIN')
        cls.secretaire = User.objects.create_user(username='sec-edt', password='x', role='SECRETARIAT')
        cls.template = CreneauTemplate.objects.create(
            jour=JOURS[today.weekday()], heure_debut=debut.time(), heure_fin=fin.time(),
        )
        cls.edt = EmploiDuTemps.objects.create(
            annee_academique=cls.annee, population_type='ANNEE', population_id=0,
            statut='PUBLIE', semaine_debut=1, semaine_fin=10, rentree=cls.annee.date_debut,
            cree_par=cls.admin,
        )
        cls.niveau = Niveau.objects.create(code='L1', libelle='Licence 1', ordre=1)
        cls.ref_formation = RefFormation.objects.create(intitule='LICENCE PRO — TEST EDT')
        cls.groupe = Groupe.objects.create(annee_academique=cls.annee, niveau=cls.niveau,
                                           ref_formation=cls.ref_formation,
                                           nom='L1-G1', capacite_max=10)
        cls.affectation = AffectationCreneau.objects.create(
            emploi_du_temps=cls.edt, creneau_template=cls.template,
            semaine_debut=1, semaine_fin=10, groupe=cls.groupe,
            enseignant_id=cls.enseignant.id, enseignant_nom='Awa Traoré', salle_nom='Amphi 1',
            intitule='Physique appliquée',
        )
        cls.statut_actif = StatutEtudiant.objects.create(code='ACTIF', libelle='Actif')
        cls.auditeurs = []
        cls.participants = []
        for i in range(3):
            user = User.objects.create_user(username=f'etu{i}', password='x', role='AUDITEUR')
            # La synchro de profil peut créer la fiche auditeur d'office ; on la
            # réutilise plutôt que de heurter l'unicité user↔participant.
            participant = Participant.objects.filter(user=user).first()
            if participant is None:
                participant = Participant.objects.create(
                    matricule=f'MAT{i:03d}', nom=f'Nom{i}', prenom=f'Prenom{i}', user=user,
                )
            dossier = DossierEtudiant.objects.create(
                participant=participant, statut=cls.statut_actif,
            )
            inscription = InscriptionAdministrative.objects.create(
                etudiant=dossier, annee_academique=cls.annee, niveau=cls.niveau,
                ref_formation=cls.ref_formation,
                statut=InscriptionAdministrative.Statut.VALIDEE, statut_etudiant=cls.statut_actif,
            )
            AffectationGroupe.objects.create(groupe=cls.groupe, inscription=inscription,
                                             active=True)
            cls.auditeurs.append(user)
            cls.participants.append(participant)


class SeanceDuJourTests(SeanceEdtFixtureMixin, TestCase):
    def test_la_seance_apparait_aujourdhui(self):
        seances = service.seances_du_jour(self.admin, self.date_seance)
        self.assertEqual([s['id'] for s in seances], [self.affectation.pk])
        seance = seances[0]
        self.assertEqual(seance['salle'], 'Amphi 1')
        self.assertEqual(seance['groupe_libelle'], 'L1-G1')
        self.assertTrue(seance['peut_gerer'])

    def test_l_encadrant_voit_seulement_ses_seances(self):
        seances = service.seances_du_jour(self.enseignant, self.date_seance)
        self.assertEqual(len(seances), 1)
        autre = User.objects.create_user(username='autre', password='x', role='ENCADRANT')
        self.assertEqual(service.seances_du_jour(autre, self.date_seance), [])

    def test_pas_de_seance_hors_plage_de_semaines(self):
        AffectationCreneau.objects.filter(pk=self.affectation.pk).update(
            semaine_debut=99, semaine_fin=100)
        self.assertEqual(service.seances_du_jour(self.admin, self.date_seance), [])


class QrSeanceTests(SeanceEdtFixtureMixin, TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_generation_puis_lecture(self):
        self.client.force_authenticate(self.enseignant)
        reponse = self.client.post(f'/api/presences/seances-edt/{self.affectation.pk}/qr/')
        self.assertEqual(reponse.status_code, 201, reponse.data)
        token = reponse.data['token']
        self.assertTrue(QRToken.objects.filter(token=token, seance_edt=self.affectation).exists())
        reponse = self.client.get(f'/api/presences/seances-edt/{self.affectation.pk}/qr/')
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.data['token'], token)

    def test_un_seul_jeton_actif_par_seance(self):
        self.client.force_authenticate(self.enseignant)
        p1 = self.client.post(f'/api/presences/seances-edt/{self.affectation.pk}/qr/').data['token']
        p2 = self.client.post(f'/api/presences/seances-edt/{self.affectation.pk}/qr/').data['token']
        self.assertNotEqual(p1, p2)
        self.assertFalse(QRToken.objects.get(token=p1).actif)
        self.assertTrue(QRToken.objects.get(token=p2).actif)

    def test_generation_interdite_aux_auditeurs(self):
        self.client.force_authenticate(self.auditeurs[0])
        reponse = self.client.post(f'/api/presences/seances-edt/{self.affectation.pk}/qr/')
        self.assertEqual(reponse.status_code, 403)


class ScanSeanceTests(SeanceEdtFixtureMixin, TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.enseignant)
        self.token = self.client.post(
            f'/api/presences/seances-edt/{self.affectation.pk}/qr/').data['token']

    def _scan(self, user, device='post-test'):
        self.client.force_authenticate(user)
        return self.client.post('/api/presences/seances-edt/scan/',
                                {'token_qr': self.token, 'device_id': device}, format='json')

    def test_entree_puis_sortie(self):
        entree = self._scan(self.auditeurs[0])
        self.assertEqual(entree.status_code, 201, entree.data)
        self.assertEqual(entree.data['action'], 'ENTREE')
        self.assertEqual(entree.data['statut_assiduite'], Pointage.StatutAssiduite.PRESENT)
        sortie = self._scan(self.auditeurs[0])
        self.assertEqual(sortie.status_code, 200, sortie.data)
        self.assertEqual(sortie.data['action'], 'SORTIE')
        pointage = Pointage.objects.get(pk=entree.data['pointage_id'])
        self.assertIsNotNone(pointage.timestamp_sortie)
        self.assertGreater(pointage.timestamp_sortie, pointage.timestamp_entree)
        self.assertEqual(pointage.statut, Pointage.Statut.TERMINE)
        self.assertGreaterEqual(pointage.duree_presence_minutes, 0)

    def test_double_complet_refuse(self):
        self._scan(self.auditeurs[0])
        self._scan(self.auditeurs[0])
        reponse = self._scan(self.auditeurs[0])
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(reponse.data['code'], 'ALREADY_SCANNED')

    def test_hors_groupe_refuse(self):
        autre_user = User.objects.create_user(username='claqued', password='x', role='AUDITEUR')
        if not Participant.objects.filter(user=autre_user).exists():
            Participant.objects.create(matricule='MAT-H', nom='Dehors', prenom='Sans',
                                       user=autre_user)
        reponse = self._scan(autre_user)
        self.assertEqual(reponse.status_code, 403)
        self.assertEqual(reponse.data['code'], 'NOT_IN_LIST')

    def test_dispositif_obligatoire(self):
        reponse = self._scan(self.auditeurs[1], device='')
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(reponse.data['code'], 'DEVICE_REQUIRED')

    def test_token_inconnu(self):
        import uuid
        self.client.force_authenticate(self.auditeurs[2])
        reponse = self.client.post('/api/presences/seances-edt/scan/',
                                   {'token_qr': str(uuid.uuid4()), 'device_id': 'd'}, format='json')
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(reponse.data['code'], 'INVALID_TOKEN')

    def test_scan_trace_le_journal(self):
        self._scan(self.auditeurs[0])
        self.assertTrue(AuditLog.objects.filter(
            action=AuditLog.Action.SCAN_SECURE_ENTREE, extra__canal='EDT_LMD').exists())


class EmargementManuelTests(SeanceEdtFixtureMixin, TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.enseignant)
        self.url = f'/api/presences/seances-edt/{self.affectation.pk}/emargement/'

    def _post(self, entries, **extra):
        return self.client.post(self.url, {'entries': entries, **extra}, format='json')

    def test_emargement_de_masse_initial(self):
        entries = [{'participant': p.pk, 'statut': 'PRESENT'} for p in self.participants[:2]]
        entries.append({'participant': self.participants[2].pk, 'statut': 'ABSENT'})
        reponse = self._post(entries)
        self.assertEqual(reponse.status_code, 201, reponse.data)
        self.assertEqual(Pointage.objects.filter(seance_edt=self.affectation).count(), 3)
        absent = Pointage.objects.get(participant=self.participants[2])
        self.assertEqual(absent.statut_assiduite, Pointage.StatutAssiduite.ABSENT)
        self.assertEqual(absent.duree_presence_minutes, 0)

    def test_motif_obligatoire_pour_corriger_un_badge(self):
        self._post([{'participant': self.participants[0].pk, 'statut': 'PRESENT'}])
        reponse = self._post([{'participant': self.participants[0].pk, 'statut': 'ABSENT'}])
        self.assertEqual(reponse.status_code, 400)
        self.assertIn('motif', reponse.data['detail'].lower())
        reponse = self._post([{'participant': self.participants[0].pk, 'statut': 'ABSENT',
                               'motif': 'Maladie constatée par l’enseignant.'}])
        self.assertEqual(reponse.status_code, 201, reponse.data)
        pointage = Pointage.objects.get(participant=self.participants[0], seance_edt=self.affectation)
        self.assertEqual(pointage.statut_assiduite, Pointage.StatutAssiduite.ABSENT)
        entree = AuditLog.objects.filter(
            action__in=[AuditLog.Action.FORCE_ENTREE, AuditLog.Action.FORCE_SORTIE],
            extra__motif='Maladie constatée par l’enseignant.').exists()
        self.assertTrue(entree)

    def test_hors_groupe_refuse(self):
        orphelin = Participant.objects.create(matricule='MAT-X', nom='Hors', prenom='Groupe')
        reponse = self._post([{'participant': orphelin.pk, 'statut': 'PRESENT'}])
        self.assertEqual(reponse.status_code, 403)
        self.assertEqual(reponse.data['code'], 'NOT_IN_GROUP')

    def test_secretaire_peut_emarger(self):
        self.client.force_authenticate(self.secretaire)
        reponse = self._post([{'participant': self.participants[0].pk, 'statut': 'RETARD',
                               'motif': 'Retard déclaré.'}])
        self.assertEqual(reponse.status_code, 201, reponse.data)

    def test_auditeur_refuse(self):
        self.client.force_authenticate(self.auditeurs[0])
        reponse = self._post([{'participant': self.participants[0].pk, 'statut': 'PRESENT'}])
        self.assertEqual(reponse.status_code, 403)

    def test_liste_nominative(self):
        self.client.force_authenticate(self.enseignant)
        reponse = self.client.get(f'/api/presences/seances-edt/{self.affectation.pk}/presences/')
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.data['effectif'], 3)
        self.assertEqual(reponse.data['presents'], 0)


class AutoCloreTests(SeanceEdtFixtureMixin, TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.enseignant)

    def test_cloture_referme_les_ouverts_et_marque_absents(self):
        debut, _ = service.horodatages(self.affectation, self.date_seance)
        Pointage.objects.create(
            participant=self.participants[0], seance_edt=self.affectation,
            date_journee=self.date_seance, timestamp_entree=debut,
            statut=Pointage.Statut.EN_COURS,
        )
        QRToken.objects.create(seance_edt=self.affectation, actif=True,
                               expire_at=timezone.now() + timedelta(hours=2))
        reponse = self.client.post(f'/api/presences/seances-edt/{self.affectation.pk}/autoclore/')
        self.assertEqual(reponse.status_code, 200, reponse.data)
        donnees = reponse.data
        self.assertEqual(donnees['pointages_clotures'], 1)
        self.assertEqual(donnees['absents_marques'], 2)
        pointage = Pointage.objects.get(participant=self.participants[0])
        self.assertEqual(pointage.statut, Pointage.Statut.SORTIE_AUTO)
        self.assertFalse(QRToken.objects.filter(actif=True).exists())
        self.assertTrue(AuditLog.objects.filter(
            action=AuditLog.Action.AUTO_EXIT, extra__source='AUTOCLOTURE').exists())
