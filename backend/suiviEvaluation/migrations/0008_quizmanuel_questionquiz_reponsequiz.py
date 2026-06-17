from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('suiviEvaluation', '0007_question_add_section'),
        ('formations', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='quizmanuel',
            name='nb_questions',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='quizmanuel',
            name='seuil_reussite',
            field=models.DecimalField(decimal_places=2, default=60, max_digits=5),
        ),
        migrations.AlterField(
            model_name='quizmanuel',
            name='module',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='quiz_manuels', to='formations.module'),
        ),
        migrations.AlterField(
            model_name='quizmanuel',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='quiz_crees', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterModelOptions(
            name='quizmanuel',
            options={
                'verbose_name': 'Quiz manuel',
                'verbose_name_plural': 'Quiz manuels',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AlterField(
            model_name='questionquiz',
            name='type_question',
            field=models.CharField(choices=[('QCM', 'QCM'), ('VRAI_FAUX', 'Vrai/Faux'), ('TEXTE', 'Texte libre')], default='QCM', max_length=20),
        ),
        migrations.AlterField(
            model_name='questionquiz',
            name='reponse_correcte',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='questionquiz',
            name='options',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name='questionquiz',
            name='points',
            field=models.DecimalField(decimal_places=2, default=1, max_digits=5),
        ),
        migrations.AlterModelOptions(
            name='questionquiz',
            options={
                'verbose_name': 'Question de quiz',
                'verbose_name_plural': 'Questions de quiz',
                'ordering': ['quiz', 'ordre'],
            },
        ),
        migrations.AlterField(
            model_name='reponsequiz',
            name='reussi',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='reponsequiz',
            name='reponses_detail',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterModelOptions(
            name='reponsequiz',
            options={
                'verbose_name': 'Réponse à un quiz',
                'verbose_name_plural': 'Réponses aux quiz',
                'ordering': ['-date_soumission'],
            },
        ),
    ]
