from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('suiviEvaluation', '0005_seed_types_epreuves'),
    ]

    operations = [
        migrations.AddField(
            model_name='quizmanuel',
            name='categories',
            field=models.JSONField(default=list, blank=True, help_text='Liste des catégories autorisées'),
        ),
        migrations.AddField(
            model_name='quizmanuel',
            name='grades',
            field=models.JSONField(default=list, blank=True, help_text='Liste des grades autorisés'),
        ),
    ]
