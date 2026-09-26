"""Lot L4b — verrouillage du RBAC INJS-LMD au niveau de la base.

La contrainte applicative (`User.Role.choices`) n'est pas une contrainte SQL :
PostgreSQL accepterait encore d'écrire `CPFAE_ADMIN` dans
`authentication_user.role` par un script, un import ou une requête directe.
Ce lot ajoute une contrainte `CHECK` qui rend cette écriture impossible.

Sémantique retenue :
- les **12 rôles canoniques** sont acceptés ;
- toute autre valeur est refusée (`CPFAE_ADMIN`, `CHEF_CPFAE_ADMIN`,
  `UNKNOWN_ROLE`, chaîne vide…).

**Pourquoi un `RunSQL` et non `AddConstraint` ?**
Sur SQLite (utilisé par les tests), Django traduit `AddConstraint` en
reconstruction complète de table : `CREATE TABLE new__… ; INSERT … SELECT ;
DROP TABLE ; ALTER … RENAME`. C'est un `DROP TABLE` déguisé, interdit par la
consigne et inacceptable sur `authentication_user`. Ici on émet directement
`ALTER TABLE … ADD CONSTRAINT`, qui reste un simple DDL sur toutes les bases.

La migration **échoue proprement** (`MigrationError`) si une valeur inattendue
est découverte : elle ne supprime ni ne réécrit jamais une ligne existante.
"""

from django.db import migrations, models

# Les 12 rôles canoniques INJS-LMD. La liste est figée : ajouter un rôle
# exige un arbitrage métier explicite, pas une édition opportuniste de cette
# migration (qui est déjà appliquée).
ROLES_CANONIQUES = (
    'ADMIN',
    'DIRECTION',
    'CHEF_INJS_ADMIN',
    'INJS_ADMIN',
    'CHEF_SECRETARIAT',
    'SECRETARIAT',
    'FINANCE',
    'ARCHIVE',
    'ENCADRANT',
    'SUPERVISEUR',
    'FORMATEUR',
    'AUDITEUR',
)

NOM_CONTRAINTE = 'auth_user_role_canonique_l4b'

# Même liste que ROLES_CANONIQUES, injectée dans le DDL. On écrit les valeurs
# en dur pour que le SQL reste lisible dans l'historique des migrations.
_VALEURS_SQL = ", ".join(f"'{r}'" for r in ROLES_CANONIQUES)

AJOUTER_CONTRAINTE = (
    'ALTER TABLE "authentication_user" '
    f'ADD CONSTRAINT "{NOM_CONTRAINTE}" '
    f'CHECK ("role" IN ({_VALEURS_SQL}))'
)
RETOURNER_CONTRAINTE = (
    'ALTER TABLE "authentication_user" '
    f'DROP CONSTRAINT IF EXISTS "{NOM_CONTRAINTE}"'
)


def verifier_donnees(apps, schema_editor):
    """Refuse d'appliquer la contrainte si des données sont hors nomenclature.

    On échoue ici plutôt que de « réparer » silencieusement : supprimer ou
    réécrire un compte n'est jamais acceptable dans une migration.
    """
    User = apps.get_model('authentication', 'User')
    hors = (
        User.objects.exclude(role__in=ROLES_CANONIQUES)
        .values_list('role', flat=True)
        .distinct()
    )
    hors = [r for r in hors if r not in (None, '')]
    if hors:
        raise migrations.exceptions.MigrationError(
            'Lot L4b : des comptes portent un rôle hors nomenclature canonique '
            f'INJS-LMD : {sorted(hors)!r}. Corriger ces comptes manuellement '
            'avant de rejouer la migration — aucune donnée ne sera modifiée '
            'automatiquement.'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0023_converger_groupes_roles_injs'),
    ]

    operations = [
        migrations.RunPython(verifier_donnees, migrations.RunPython.noop),
        migrations.RunSQL(
            sql=AJOUTER_CONTRAINTE,
            reverse_sql=RETOURNER_CONTRAINTE,
        ),
    ]