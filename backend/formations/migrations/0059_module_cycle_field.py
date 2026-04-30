# Colonne `cycle` déjà présente sur certaines bases (NOT NULL) sans entrée dans l'historique Django.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('formations', '0058_add_refvague'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE formations_module "
                        "ADD COLUMN IF NOT EXISTS cycle varchar(255) NOT NULL DEFAULT '';"
                    ),
                    reverse_sql=migrations.RunSQL.noop,
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
