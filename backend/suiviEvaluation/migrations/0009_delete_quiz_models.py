from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('suiviEvaluation', '0008_quizmanuel_questionquiz_reponsequiz'),
    ]

    operations = [
        migrations.DeleteModel(name='ReponseQuiz'),
        migrations.DeleteModel(name='QuestionQuiz'),
        migrations.DeleteModel(name='QuizManuel'),
    ]
