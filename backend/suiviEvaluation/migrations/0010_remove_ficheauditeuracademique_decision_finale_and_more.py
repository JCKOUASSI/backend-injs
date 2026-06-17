from django.db import migrations


class Migration(migrations.Migration):
    """
    Drop all academic evaluation tables on production servers that ran the old migration 0004.
    On fresh databases these tables don't exist, so we use IF EXISTS.
    No state changes — these models were never in the current migration state.
    """

    dependencies = [
        ('suiviEvaluation', '0009_delete_quiz_models'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'DROP TABLE IF EXISTS "suiviEvaluation_historiquenotemodification" CASCADE;'
                        'DROP TABLE IF EXISTS "suiviEvaluation_noteepreuve" CASCADE;'
                        'DROP TABLE IF EXISTS "suiviEvaluation_suivimoduleauditeur" CASCADE;'
                        'DROP TABLE IF EXISTS "suiviEvaluation_moyennemodule" CASCADE;'
                        'DROP TABLE IF EXISTS "suiviEvaluation_ficheauditeuracademique_modules_suivis" CASCADE;'
                        'DROP TABLE IF EXISTS "suiviEvaluation_ficheauditeuracademique" CASCADE;'
                        'DROP TABLE IF EXISTS "suiviEvaluation_ficheformateur" CASCADE;'
                        'DROP TABLE IF EXISTS "suiviEvaluation_decisionpedagogique" CASCADE;'
                        'DROP TABLE IF EXISTS "suiviEvaluation_exportrapport" CASCADE;'
                        'DROP TABLE IF EXISTS "suiviEvaluation_parametresevaluation" CASCADE;'
                        'DROP TABLE IF EXISTS "suiviEvaluation_epreuve" CASCADE;'
                        'DROP TABLE IF EXISTS "suiviEvaluation_typeepreuve" CASCADE;'
                    ),
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[],
        ),
    ]
