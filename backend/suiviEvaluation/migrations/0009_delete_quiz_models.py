from django.db import migrations


QUIZ_TABLES = [
    'suiviEvaluation_reponsequiz',
    'suiviEvaluation_questionquiz',
    'suiviEvaluation_quizmanuel',
]


def drop_quiz_tables(apps, schema_editor):
    # CASCADE est du syntaxe PostgreSQL ; SQLite ne le connaît pas.
    suffix = ' CASCADE' if schema_editor.connection.vendor == 'postgresql' else ''
    with schema_editor.connection.cursor() as cursor:
        for table in QUIZ_TABLES:
            cursor.execute(f'DROP TABLE IF EXISTS "{table}"{suffix}')


class Migration(migrations.Migration):
    """
    Drop quiz tables on production servers that ran the old migration 0004.
    On fresh databases these tables don't exist, so we use IF EXISTS.
    No state changes — these models are not in the current migration state.
    """

    dependencies = [
        ('suiviEvaluation', '0008_quizmanuel_questionquiz_reponsequiz'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(drop_quiz_tables, migrations.RunPython.noop),
            ],
            state_operations=[],
        ),
    ]
