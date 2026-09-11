"""Tests de la garde-fou d'hygiène du dépôt P00-02 (check_repo_hygiene)."""
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from parametres.management.commands.check_repo_hygiene import find_violations


class FindViolationsTests(TestCase):
    def test_ensemble_propre(self):
        tracked = [
            "backend/formations/models.py",
            "docs/modeles/modele_formations.csv",
            "docs/modeles/modele_seances.csv",
            "backend/test_import_formations_seances.xlsx",  # fixture synthétique
            "frontend/src/App.jsx",
        ]
        self.assertEqual(find_violations(tracked), [])

    def test_detecte_donnees_nominatives(self):
        tracked = [
            "backend/import_participants.csv",
            "backend/import_formateurs.xlsx",
            "backend/LISTE DES FORMATEURS FAB.numbers",
            "backend/importverif/FAB A4 OPHIR.xlsx",
        ]
        violations = find_violations(tracked)
        self.assertEqual(sorted(violations), sorted(tracked))

    def test_detecte_staticfiles_et_secrets(self):
        tracked = [
            "backend/staticfiles/sw.js",
            "backend/staticfiles/img/logo.png",
            "backend/.env",
            "qr_badge_mobile/assets/app.env",
            "backend/db.sqlite3",
        ]
        violations = find_violations(tracked)
        self.assertEqual(sorted(violations), sorted(tracked))

    def test_modele_en_dehors_de_docs_modeles_est_violation(self):
        tracked = ["backend/modele_formations.csv"]
        self.assertEqual(find_violations(tracked), ["backend/modele_formations.csv"])


class CheckRepoHygieneCommandTests(TestCase):
    def _run(self, tracked):
        out, err = StringIO(), StringIO()
        with mock.patch(
            "parametres.management.commands.check_repo_hygiene.list_tracked_files",
            return_value=tracked,
        ):
            call_command("check_repo_hygiene", stdout=out, stderr=err)
        return out.getvalue(), err.getvalue()

    def test_commande_verte_si_propre(self):
        out, _ = self._run(["backend/formations/models.py", "docs/modeles/modele_seances.csv"])
        self.assertIn("CONFORME", out)

    def test_commande_echoue_si_violation(self):
        with self.assertRaises(SystemExit) as ctx:
            self._run(["backend/import_participants.csv"])
        self.assertEqual(ctx.exception.code, 1)
