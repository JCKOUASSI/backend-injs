"""Garde-fous des ``operationId`` du schéma OpenAPI.

``AutoSchema._tokenize_path()`` de drf-spectacular retire les variables de
chemin, si bien que deux routes ne différant que par leur paramètre
recevaient le même ``operationId`` (39 collisions relevées sur ce dépôt) ;
drf-spectacular les départageait alors par un suffixe numérique dépendant de
l'ordre d'énumération des routes. Un client OpenAPI généré pouvait donc
changer de cible dès l'ajout d'une route en amont.

``config.api_schema.AutoSchemaINJS`` réinjecte les paramètres de chemin à leur
place. Ces tests figent le résultat sur le schéma **réel** de l'API, pas sur
un exemple : absence de suffixe numérique instable, unicité, validité
syntaxique, et présence effective du paramètre dans l'identifiant de la route
de détail.

Le contrat d'API figé (P00-08) est indépendant : ``build_contract`` indexe par
``"{METHODE} {chemin}"`` et ne capture pas les ``operationId``.
"""
import re

from django.test import SimpleTestCase

from config.api_contract import generate_schema

#: Un ``operationId`` doit rester un identifiant exploitable en génération de
#: client (ni accolade, ni tiret, ni point).
IDENTIFIANT_VALIDE = re.compile(r'[A-Za-z0-9_]+')


def _operationids():
    """Liste des (chemin, méthode, operationId) du schéma réel de l'API."""
    resultat = []
    for chemin, methodes in (generate_schema().get('paths') or {}).items():
        for methode, operation in methodes.items():
            if not isinstance(operation, dict):
                continue
            if 'operationId' not in operation:
                continue
            resultat.append((chemin, methode.upper(), operation['operationId']))
    return resultat


class OperationIdTests(SimpleTestCase):
    """Le schéma complet ne doit plus produire d'``operationId`` ambigu."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Une seule génération pour tous les tests de la classe (≈ 10 s).
        cls.operations = _operationids()

    def test_le_schema_expose_des_operations(self):
        # Garde le test honnête : si l'extraction ne trouve rien, les
        # assertions suivantes passeraient à vide.
        self.assertGreater(len(self.operations), 500)

    def test_les_operationid_sont_uniques(self):
        # Invariant maintenu : drf-spectacular résout déjà les collisions par
        # un suffixe numérique, donc le schéma par défaut était unique aussi.
        # Ce qui distingue le correctif, c'est le test suivant (stabilité).
        identifiants = [oid for _, _, oid in self.operations]
        doublons = sorted({
            oid for oid in identifiants
            if identifiants.count(oid) > 1
        })
        self.assertEqual([], doublons)

    def test_aucun_operationid_ne_repose_sur_un_suffixe_numerique(self):
        """Cœur du défaut : le suffixe ``_2`` dépend de l'ordre des routes.

        drf-spectacular départage deux ``operationId`` identiques en ajoutant
        ``_2``, ``_3``… dans l'ordre d'énumération. Ajouter une route en amont
        suffit alors à déplacer le suffixe et à faire pointer un client généré
        vers une autre opération. Aucun identifiant ne doit en dépendre.
        """
        instables = sorted({
            oid for _, _, oid in self.operations
            if re.search(r'_\d+$', oid)
        })
        self.assertEqual([], instables)

    def test_les_operationid_sont_des_identifiants_valides(self):
        invalides = sorted({
            oid for _, _, oid in self.operations
            if not IDENTIFIANT_VALIDE.fullmatch(oid)
        })
        self.assertEqual([], invalides)

    def test_la_route_de_detail_porte_son_parametre_de_chemin(self):
        """Cas déclencheur : ``/api/statistiques/rapports/`` vs ``…/{rapport_id}/``."""
        par_chemin = {
            (chemin, methode): oid
            for chemin, methode, oid in self.operations
        }
        self.assertEqual(
            'api_statistiques_rapports_retrieve',
            par_chemin[('/api/statistiques/rapports/', 'GET')],
        )
        self.assertEqual(
            'api_statistiques_rapports_rapport_id_retrieve',
            par_chemin[('/api/statistiques/rapports/{rapport_id}/', 'GET')],
        )

    def test_la_position_du_parametre_est_conservee(self):
        """Un suffixe ne suffirait pas : ces deux routes ont les mêmes paramètres."""
        par_chemin = {
            (chemin, methode): oid
            for chemin, methode, oid in self.operations
        }
        self.assertEqual(
            'api_formations_id_formateurs_retrieve',
            par_chemin[('/api/formations/{id}/formateurs/', 'GET')],
        )
        self.assertEqual(
            'api_formations_formateurs_id_retrieve',
            par_chemin[('/api/formations/formateurs/{id}/', 'GET')],
        )

    def test_un_segment_litterel_est_normalise(self):
        """``export.csv`` ne doit pas introduire de point dans l'identifiant."""
        identifiants = {oid for _, _, oid in self.operations}
        self.assertIn('api_edts_emplois_id_export_csv_retrieve', identifiants)
