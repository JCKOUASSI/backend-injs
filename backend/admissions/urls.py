from django.urls import path

from . import api_views

urlpatterns = [
    path('candidats/',                        api_views.candidat_list,           name='admissions-candidat-list'),
    path('candidats/<int:pk>/',               api_views.candidat_detail,         name='admissions-candidat-detail'),

    path('candidatures/',                     api_views.candidature_list,        name='admissions-candidature-list'),
    path('candidatures/stats/',               api_views.candidature_stats,       name='admissions-candidature-stats'),
    path('candidatures/<int:pk>/',            api_views.candidature_detail,      name='admissions-candidature-detail'),
    path('candidatures/<int:pk>/transition/', api_views.candidature_transition,  name='admissions-candidature-transition'),
    path('candidatures/<int:pk>/pieces/',     api_views.candidature_pieces,      name='admissions-candidature-pieces'),

    path('admissions/',                       api_views.admission_list,          name='admissions-admission-list'),
    path('admissions/stats/',                 api_views.admission_stats,         name='admissions-admission-stats'),
    path('admissions/<int:pk>/',              api_views.admission_detail,        name='admissions-admission-detail'),
    path('admissions/<int:pk>/decision/',     api_views.admission_decision,      name='admissions-admission-decision'),
    path('admissions/<int:pk>/annuler/',      api_views.admission_annuler,       name='admissions-admission-annuler'),

    path('pieces/<int:piece_id>/deposer/',    api_views.piece_deposer,           name='admissions-piece-deposer'),
    path('pieces/<int:piece_id>/verifier/',   api_views.piece_verifier,          name='admissions-piece-verifier'),
    path('pieces/<int:piece_id>/fichier/',    api_views.piece_telecharger,       name='admissions-piece-fichier'),

    path('ref/<str:ressource>/',              api_views.referentiel_list,        name='admissions-ref-list'),
    path('ref/<str:ressource>/<int:pk>/',     api_views.referentiel_detail,      name='admissions-ref-detail'),
]
