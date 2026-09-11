"""Garde-fou d'hygiène du dépôt (P00-02).

Vérifie qu'aucune donnée nominative, qu'aucun classeur d'import réel et qu'aucun
artefact de build (staticfiles) n'est suivi par Git. Les modèles vides d'import
sont autorisés uniquement dans ``docs/modeles/`` et les fixtures synthétiques de
tests (``test_*.xlsx``) sont autorisées dans les applications.

La commande sort en code 1 dès qu'une violation est détectée (elle est branchée
dans la CI, job Backend, avant les tests).
"""
from __future__ import annotations

import fnmatch
import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand

# Dossier unique autorisé pour les modèles d'import versionnés.
MODELS_DIR = "docs/modeles/"
# Fichiers de données interdits partout, sauf exceptions ci-dessous.
DATA_PATTERNS = ("*.xlsx", "*.xls", "*.csv", "*.numbers")
FORBIDDEN_NAMES = (".env",)
FORBIDDEN_SUFFIXES = (".sqlite3",)
FORBIDDEN_PATH_PARTS = ("staticfiles/", "importverif/", "assets/app.env")


def _is_synthetic_test_fixture(path: str) -> bool:
    """Fixture de test générée et non nominative (ex: backend/test_*.xlsx)."""
    name = path.rsplit("/", 1)[-1]
    return name.startswith("test_") and name.endswith((".xlsx", ".xls", ".csv"))


def find_violations(tracked_files):
    """Renvoie la liste des chemins suivis qui violent les règles d'hygiène.

    Pur (pas d'E/S) pour être testable directement.
    """
    violations = []
    for raw in tracked_files:
        path = raw.strip().replace("\\", "/")
        if not path:
            continue
        name = path.rsplit("/", 1)[-1]

        if any(part in path for part in FORBIDDEN_PATH_PARTS):
            violations.append(path)
            continue
        if name in FORBIDDEN_NAMES or path.endswith(FORBIDDEN_SUFFIXES):
            violations.append(path)
            continue
        if any(fnmatch.fnmatch(name, pat) for pat in DATA_PATTERNS):
            if path.startswith(MODELS_DIR):
                continue
            if _is_synthetic_test_fixture(path):
                continue
            violations.append(path)
    return sorted(set(violations))


def list_tracked_files():
    """Liste les fichiers suivis par Git à la racine du dépôt (chemins rel. dépôt)."""
    # settings.BASE_DIR pointe vers backend/ ; la racine du dépôt est le parent.
    repo_root = str(settings.BASE_DIR.parent)
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


class Command(BaseCommand):
    help = "Échoue si un fichier nominatif, un classeur d'import ou staticfiles/ est suivi par Git."

    def handle(self, *args, **options):
        try:
            tracked = list_tracked_files()
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            raise SystemExit(f"Impossible de lister les fichiers suivis par Git : {exc}")

        violations = find_violations(tracked)
        if violations:
            self.stderr.write(
                self.style.ERROR(
                    f"Hygiène du dépôt NON CONFORME — {len(violations)} fichier(s) interdit(s) suivi(s) :"
                )
            )
            for path in violations:
                self.stderr.write(f"  - {path}")
            self.stderr.write(
                "\nSortez-les du suivi avec 'git rm --cached <fichier>' (sans les supprimer "
                "du disque) ; les modèles vides vont dans docs/modeles/."
            )
            raise SystemExit(1)

        self.stdout.write(
            self.style.SUCCESS(
                f"Hygiène du dépôt CONFORME — {len(tracked)} fichiers suivis vérifiés, "
                "aucune donnée nominative ni artefact de build versionné."
            )
        )
