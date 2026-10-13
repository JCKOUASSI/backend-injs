"""Garde-fou : aucune marque CPFAE / SYGEP ne doit réapparaître dans le code INJS-LMD.

Le test parcourt les sources versionnées (backend, frontend, mobile, CI, scripts)
et échoue si une ligne contient « cpfae » ou « sygep » (insensible à la casse).

Exclusions structurelles : migrations (historique figé), dépendances et sorties
de build, dossier `workspace/` (instantané hors périmètre applicatif).

Exceptions explicites (`AUTORISES`) : chaque entrée est un garde-fou négatif
(il vérifie l'absence de la marque), une archive ou une valeur de production
qu'il n'est pas possible de renommer sans décision d'infrastructure. Toute
nouvelle entrée doit être justifiée ici.
"""

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

RACINE = Path(settings.BASE_DIR).parent
MARQUE = re.compile(r'cpfae|sygep', re.IGNORECASE)

DOSSIERS = (
    'backend', 'frontend/src', 'qr_badge_mobile/lib', 'qr_badge_mobile/test',
    '.github', 'scripts',
)
SUFFIXES = {
    '.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.yml', '.yaml',
    '.json', '.dart', '.sh', '.txt', '.csv',
}
EXCLUS_PARTIES = (
    'migrations', '__pycache__', 'node_modules', '.venv', 'dist',
    'staticfiles', 'workspace',
)

AUTORISES = {
    # Archive réversible du corpus legacy (docstrings et migration elle-même).
    'backend/core/models.py': 'modèle ArchiveDonneeLegacy (documentation de l\'archive)',
    'backend/core/migrations/0002_archive_donnees_cpfae.py': 'migration d\'archivage réversible',
    'backend/core/tests/test_garde_fou_legacy_cpfae.py': 'ce garde-fou',
    # Garde-fous négatifs : vérifient que les rôles / données CPFAE sont refusés.
    'backend/authentication/test_roles_canoniques_contrainte_db.py': 'contrainte CHECK refuse les rôles CPFAE',
    'backend/authentication/test_roles_injs_l4a.py': 'les rôles CPFAE ne sont plus canoniques',
    'backend/authentication/test_garde_fous_comptes.py': 'aucun compte témoin CPFAE',
    'backend/scolarite/tests/test_cours_lmd_rattachement.py': 'absence de rôle CPFAE dans l\'API',
    'backend/presences/test_seances_supervision.py': 'absence de référence CPFAE dans le périmètre',
    'backend/formations/tests/test_referentiel_injs_l6.py': 'fixtures legacy exclues du référentiel INJS',
    'frontend/src/menu/arborescence.test.js': 'garde-fou : entrée CPFAE retirée du menu',
    'frontend/src/pages/Login.jsx': 'commentaire du garde-fou des comptes démo',
    'frontend/src/pages/Login.test.jsx': 'garde-fou : aucune plaquette démo CPFAE',
    'qr_badge_mobile/test/user_facing_error_test.dart': 'garde-fou : pas de domaine legacy dans les erreurs',
    # Domaines de production : changement d'infrastructure soumis à décision.
    '.github/workflows/docker-hub-main.yml': 'domaine de production (décision d\'infrastructure en attente)',
    'qr_badge_mobile/test/session_provider_heartbeat_test.dart': 'domaine de production de l\'API mobile',
    'qr_badge_mobile/lib/utils/guarded_logout.dart': 'message mobile : vérifier le libellé',
}


def _fichiers_versionnes():
    for dossier in DOSSIERS:
        racine = RACINE / dossier
        if not racine.is_dir():
            continue
        for chemin in racine.rglob('*'):
            if not chemin.is_file() or chemin.suffix not in SUFFIXES:
                continue
            relatif = chemin.relative_to(RACINE).as_posix()
            if any(f'/{partie}/' in f'/{relatif}/' for partie in EXCLUS_PARTIES):
                continue
            yield relatif


class GardeFouLegacyCpfaeTests(SimpleTestCase):
    def test_aucune_marque_cpfae_sygep_hors_exceptions(self):
        violations = []
        for relatif in sorted(_fichiers_versionnes()):
            if relatif in AUTORISES:
                continue
            texte = (RACINE / relatif).read_text(encoding='utf-8', errors='ignore')
            for numero, ligne in enumerate(texte.splitlines(), start=1):
                if MARQUE.search(ligne):
                    violations.append(f'{relatif}:{numero}: {ligne.strip()[:120]}')
        self.assertEqual(
            violations, [],
            'Marque CPFAE/SYGEP réintroduite (ajouter une exception justifiée si légitime) :\n'
            + '\n'.join(violations[:50]),
        )

    def test_exceptions_pointent_vers_des_fichiers_existants(self):
        manquants = [p for p in AUTORISES if not (RACINE / p).is_file()]
        self.assertEqual(manquants, [], 'Exceptions obsolètes à retirer de AUTORISES')
