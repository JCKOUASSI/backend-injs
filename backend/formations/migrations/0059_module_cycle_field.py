# Colonne `cycle` déjà présente sur certaines bases (NOT NULL) sans entrée dans l'historique Django.

from django.db import migrations, models


def add_cycle_column(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor == 'postgresql':
        # ADD COLUMN IF NOT EXISTS : idiome PostgreSQL pour les bases où la
        # colonne existe déjà sans entrée dans l'historique Django.
        with connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE formations_module "
                "ADD COLUMN IF NOT EXISTS cycle varchar(255) NOT NULL DEFAULT '';"
            )
        return
    # Autres moteurs (SQLite en dev local) : ajout standard de la colonne.
    Module = apps.get_model('formations', 'Module')
    field = models.CharField(
        blank=True,
        default='',
        help_text='Libellé du cycle de formation (ex. même valeur que Formation.formation)',
        max_length=255,
    )
    field.set_attributes_from_name('cycle')
    schema_editor.add_field(Module, field)


class Migration(migrations.Migration):

    dependencies = [
        ('formations', '0058_add_refvague'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_cycle_column,
                    migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='module',
                    name='cycle',
                    field=models.CharField(
                        blank=True,
                        default='',
                        help_text='Libellé du cycle de formation (ex. même valeur que Formation.formation)',
                        max_length=255,
                    ),
                ),
            ],
        ),
    ]
