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
        migrations.CreateModel(
            name='QuizManuel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titre', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('chapitre', models.CharField(blank=True, default='', max_length=255)),
                ('categories', models.JSONField(blank=True, default=list)),
                ('grades', models.JSONField(blank=True, default=list)),
                ('nb_questions', models.PositiveSmallIntegerField(default=0)),
                ('seuil_reussite', models.DecimalField(decimal_places=2, default=60, max_digits=5)),
                ('duree_max_minutes', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('actif', models.BooleanField(default=True)),
                ('date_ouverture', models.DateTimeField(blank=True, null=True)),
                ('date_fermeture', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='quiz_crees', to=settings.AUTH_USER_MODEL)),
                ('module', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='quiz_manuels', to='formations.module')),
            ],
            options={
                'verbose_name': 'Quiz manuel',
                'verbose_name_plural': 'Quiz manuels',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='QuestionQuiz',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.TextField()),
                ('type_question', models.CharField(choices=[('QCM', 'QCM'), ('VRAI_FAUX', 'Vrai/Faux'), ('TEXTE', 'Texte libre')], default='QCM', max_length=20)),
                ('reponse_correcte', models.TextField(blank=True, default='')),
                ('options', models.JSONField(blank=True, default=list)),
                ('points', models.DecimalField(decimal_places=2, default=1, max_digits=5)),
                ('ordre', models.PositiveSmallIntegerField(default=1)),
                ('quiz', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='suiviEvaluation.quizmanuel')),
            ],
            options={
                'verbose_name': 'Question de quiz',
                'verbose_name_plural': 'Questions de quiz',
                'ordering': ['quiz', 'ordre'],
            },
        ),
        migrations.CreateModel(
            name='ReponseQuiz',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_soumission', models.DateTimeField(auto_now_add=True)),
                ('score', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('reussi', models.BooleanField(default=False)),
                ('temps_pris_minutes', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('reponses_detail', models.JSONField(blank=True, default=dict)),
                ('participant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reponses_quiz', to='formations.participant')),
                ('quiz', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reponses', to='suiviEvaluation.quizmanuel')),
            ],
            options={
                'verbose_name': 'Réponse à un quiz',
                'verbose_name_plural': 'Réponses aux quiz',
                'ordering': ['-date_soumission'],
                'unique_together': {('quiz', 'participant')},
            },
        ),
    ]
