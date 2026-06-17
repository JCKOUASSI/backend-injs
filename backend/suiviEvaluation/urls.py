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

    # ═══════════════ Évaluation académique — Notes / Moyennes / Décisions ═══════════════
    # ── Types d'épreuves ──
    path('types-epreuves/', views.type_epreuve_list_create, name='eval-type-epreuve-list'),
    path('types-epreuves/<int:pk>/', views.type_epreuve_detail, name='eval-type-epreuve-detail'),

    # ── Épreuves ──
    path('epreuves/', views.epreuve_list_create, name='eval-epreuve-list'),
    path('epreuves/<int:pk>/', views.epreuve_detail, name='eval-epreuve-detail'),

    # ── Notes d'épreuves ──
    path('epreuves/<int:epreuve_pk>/notes/', views.notes_epreuve_list, name='eval-notes-epreuve-list'),
    path('epreuves/<int:epreuve_pk>/notes/bulk/', views.notes_epreuve_bulk_save, name='eval-notes-epreuve-bulk'),
    path('notes-epreuves/<int:pk>/', views.note_epreuve_detail, name='eval-note-epreuve-detail'),
    path('notes-epreuves/<int:note_pk>/historique/', views.historique_note, name='eval-note-historique'),

    # ── Paramètres d'évaluation ──
    path('formations/<int:formation_pk>/parametres/', views.parametres_evaluation, name='eval-parametres'),

    # ── Moyennes ──
    path('modules/<int:module_pk>/moyennes/', views.moyennes_module, name='eval-moyennes-module'),
    path('modules/<int:module_pk>/moyennes/recalculer/', views.recalculer_moyennes_module, name='eval-moyennes-recalculer'),

    # ── Décisions pédagogiques ──
    path('formations/<int:formation_pk>/decisions/', views.decisions_formation, name='eval-decisions-formation'),
    path('formations/<int:formation_pk>/decisions/recalculer/', views.recalculer_decisions_formation, name='eval-decisions-recalculer'),
    path('decisions/<int:pk>/', views.decision_detail, name='eval-decision-detail'),

    # ── Fiches auditeur ──
    path('auditeurs/<int:participant_pk>/formations/<int:formation_pk>/fiche/', views.fiche_auditeur, name='eval-fiche-auditeur'),
    path('auditeurs/<int:participant_pk>/formations/<int:formation_pk>/fiche/export/pdf/', views.export_fiche_auditeur_pdf, name='eval-fiche-auditeur-export-pdf'),
    path('auditeurs/<int:participant_pk>/formations/<int:formation_pk>/fiche/export/xlsx/', views.export_fiche_auditeur_excel, name='eval-fiche-auditeur-export-xlsx'),
    path('ma-fiche/', views.ma_fiche_auditeur, name='eval-ma-fiche'),
    path('formations/<int:formation_pk>/fiches/generer/', views.generer_fiches_formation, name='eval-fiches-generer'),

    # ── Fiches formateur ──
    path('formateurs/<int:formateur_pk>/modules/<int:module_pk>/fiche/', views.fiche_formateur, name='eval-fiche-formateur'),
    path('formateurs/<int:formateur_pk>/modules/<int:module_pk>/fiche/export/pdf/', views.export_fiche_formateur_pdf, name='eval-fiche-formateur-export-pdf'),
    path('formateurs/<int:formateur_pk>/modules/<int:module_pk>/fiche/export/xlsx/', views.export_fiche_formateur_excel, name='eval-fiche-formateur-export-xlsx'),
    path('modules/<int:module_pk>/fiches-formateur/', views.fiches_formateur_module, name='eval-fiches-formateur-module'),

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
