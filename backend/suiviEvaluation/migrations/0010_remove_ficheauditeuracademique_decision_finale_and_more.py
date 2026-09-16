from django.db import migrations


LEGACY_TABLES = [
    'suiviEvaluation_historiquenotemodification',
    'suiviEvaluation_noteepreuve',
    'suiviEvaluation_suivimoduleauditeur',
    'suiviEvaluation_moyennemodule',
    'suiviEvaluation_ficheauditeuracademique_modules_suivis',
    'suiviEvaluation_ficheauditeuracademique',
    'suiviEvaluation_ficheformateur',
    'suiviEvaluation_decisionpedagogique',
    'suiviEvaluation_exportrapport',
    'suiviEvaluation_parametresevaluation',
    'suiviEvaluation_epreuve',
    'suiviEvaluation_typeepreuve',
]


def drop_legacy_tables(apps, schema_editor):
    # CASCADE est du syntaxe PostgreSQL ; SQLite ne le connaît pas.
    suffix = ' CASCADE' if schema_editor.connection.vendor == 'postgresql' else ''
    with schema_editor.connection.cursor() as cursor:
        for table in LEGACY_TABLES:
            cursor.execute(f'DROP TABLE IF EXISTS "{table}"{suffix}')


class Migration(migrations.Migration):
    """
    Supprime les tables d'évaluation académique legacy (migration 0004) sur les
    bases qui les ont encore, et nettoie l'état Django (modèles absents de models.py).
    """

    dependencies = [
        ('suiviEvaluation', '0009_delete_quiz_models'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(drop_legacy_tables, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.DeleteModel(name='HistoriqueNoteModification'),
                migrations.DeleteModel(name='NoteEpreuve'),
                migrations.DeleteModel(name='MoyenneModule'),
                migrations.DeleteModel(name='SuiviModuleAuditeur'),
                migrations.DeleteModel(name='FicheAuditeurAcademique'),
                migrations.DeleteModel(name='FicheFormateur'),
                migrations.DeleteModel(name='ExportRapport'),
                migrations.DeleteModel(name='ParametresEvaluation'),
                migrations.DeleteModel(name='DecisionPedagogique'),
                migrations.DeleteModel(name='Epreuve'),
                migrations.DeleteModel(name='TypeEpreuve'),
            ],
        ),
    ]
