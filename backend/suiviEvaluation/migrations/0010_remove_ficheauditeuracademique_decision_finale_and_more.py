from django.db import migrations


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
