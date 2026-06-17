from django.urls import path
from . import views

urlpatterns = [
    # ── Questionnaires (superviseurs) ────────────────────────────────
    path('questionnaires/', views.questionnaire_list_create, name='eval-questionnaire-list'),
    path('questionnaires/<int:pk>/', views.questionnaire_detail, name='eval-questionnaire-detail'),
    path('questionnaires/<int:pk>/statut/', views.questionnaire_publier, name='eval-questionnaire-statut'),
    path('questionnaires/<int:pk>/resultats/', views.resultats_questionnaire, name='eval-questionnaire-resultats'),
    path('questionnaires/<int:pk>/analyse/', views.analyse_qualitative, name='eval-questionnaire-analyse'),

    # ── Questions (superviseurs) ──────────────────────────────────────
    path('questionnaires/<int:questionnaire_pk>/questions/', views.question_create, name='eval-question-create'),
    path('questionnaires/<int:questionnaire_pk>/questions/<int:pk>/', views.question_detail, name='eval-question-detail'),

    # ── Résultats par module (superviseurs) ──────────────────────────
    path('modules/<int:module_pk>/resultats/', views.resultats_par_module, name='eval-module-resultats'),

    # ── Auditeurs ─────────────────────────────────────────────────────
    path('mes-questionnaires/', views.questionnaires_disponibles, name='eval-mes-questionnaires'),
    path('soumettre/', views.soumettre_evaluation, name='eval-soumettre'),

    # ── Quiz manuels (gestion) ──
    path('quiz/', views.quiz_list_create, name='eval-quiz-list'),
    path('quiz/<int:pk>/', views.quiz_detail, name='eval-quiz-detail'),
    path('quiz/<int:pk>/resultats/', views.quiz_resultats, name='eval-quiz-resultats'),
    path('quiz/<int:quiz_pk>/questions/', views.quiz_question_create, name='eval-quiz-question-create'),
    path('quiz/<int:quiz_pk>/questions/<int:pk>/', views.quiz_question_detail, name='eval-quiz-question-detail'),

    # ── Quiz manuels (auditeurs) ──
    path('mes-quiz/', views.quiz_disponibles, name='eval-mes-quiz'),
    path('quiz/<int:quiz_pk>/soumettre/', views.quiz_soumettre, name='eval-quiz-soumettre'),
]

