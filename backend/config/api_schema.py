"""Schéma OpenAPI — ``operationId`` uniques et stables.

``AutoSchema._tokenize_path()`` de drf-spectacular supprime les variables de
chemin (``re.sub(r'\\{[\\w\\-]+\\}', '', path)``). Deux routes qui ne diffèrent
que par la place d'un paramètre produisent donc le même identifiant :

    GET /api/statistiques/rapports/              → api_statistiques_rapports_retrieve
    GET /api/statistiques/rapports/{rapport_id}/ → api_statistiques_rapports_retrieve

drf-spectacular lève alors « operationId ... has collisions ... resolving with
numeral suffixes » et suffixe arbitrairement la seconde opération (``_2``).
Outre l'avertissement, le résultat est fragile : l'identifiant d'une route
dépend de l'ordre d'énumération des routes, et un client OpenAPI généré
(ou un appelant qui référence un ``operationId``) peut changer de cible dès
qu'une route est ajoutée en amont.

Cette classe conserve la convention de drf-spectacular (jetons du chemin +
verbe, tirets normalisés, ``root`` pour la racine, suffixe ``formatted``) mais
conserve la **position** des paramètres de chemin au lieu de les retirer :
l'identifiant redevient unique, déterministe et lisible dans un client généré
(``api_statistiques_rapports_rapport_id_retrieve``).

La position est nécessaire : un simple suffixe ne sépare pas
``/api/formations/{id}/formateurs/`` de ``/api/formations/formateurs/{id}/``,
dont le jeu de paramètres est identique.

Hors périmètre volontaire : le contrat d'API figé (P00-08,
``config/api_contract.py:build_contract``) est indexé par ``"{METHODE} {chemin}"``
et ne capture que ``parameters`` / ``request_keys`` / ``responses``. Les
``operationId`` n'en font pas partie : ce module ne peut donc pas rompre le
snapshot, et ``export_api_contract --check`` reste vert.
"""
import re

from drf_spectacular.openapi import AutoSchema
from drf_spectacular.settings import spectacular_settings

#: Toute suite de caractères non alphanumériques d'un jeton de chemin.
_NON_ALPHA = re.compile(r'[^A-Za-z0-9]+')


class AutoSchemaINJS(AutoSchema):
    """``AutoSchema`` dont l'``operationId`` conserve les paramètres de chemin."""

    def _tokenize_path_avec_parametres(self):
        """Jetons du chemin, paramètres de chemin conservés à leur place.

        Reprend ``AutoSchema._tokenize_path()`` (retrait du préfixe, tirets
        normalisés, jetons vides écartés) sans l'étape qui efface ``{...}``.
        """
        chemin = re.sub(
            pattern=self.path_prefix,
            repl='',
            string=self.path,
            flags=re.IGNORECASE,
        )
        jetons = chemin.rstrip('/').lstrip('/').split('/')
        return [
            # Les accolades des paramètres sont retirées et toute suite de
            # caractères non alphanumériques (tiret, point d'un segment
            # littéral comme ``export.csv``…) est réduite à un tiret bas, pour
            # que l'identifiant reste valide dans un client généré.
            _NON_ALPHA.sub('_', jeton.strip('{}'))
            for jeton in jetons
            if jeton
        ]

    def get_operation_id(self) -> str:
        if self.method == 'GET' and self._is_list_view():
            action = 'list'
        else:
            action = self.method_mapping[self.method.lower()]

        jetons = self._tokenize_path_avec_parametres()
        if not jetons:
            jetons.append('root')

        if re.search(r'<drf_format_suffix\w*:\w+>', self.path_regex):
            jetons.append('formatted')

        if spectacular_settings.OPERATION_ID_METHOD_POSITION == 'PRE':
            return '_'.join([action] + jetons)
        elif spectacular_settings.OPERATION_ID_METHOD_POSITION == 'POST':
            return '_'.join(jetons + [action])
        else:
            assert False, 'Invalid value for OPERATION_ID_METHOD_POSITION. Allowed: PRE, POST'
