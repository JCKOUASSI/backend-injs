from django.urls import path

from . import (
    api_views,
    edt_export,
    groupes_api,
    inscription_api,
    passerelle_api,
    pedagogie_api,
)

urlpatterns = [
    path('annee-courante/',                       api_views.annee_courante,          name='scolarite-annee-courante'),

    path('etudiants/',                            inscription_api.etudiant_list,     name='scolarite-etudiant-list'),
    path('etudiants/<int:pk>/',                   inscription_api.etudiant_detail,   name='scolarite-etudiant-detail'),

    path('inscriptions/',                         inscription_api.inscription_list,  name='scolarite-inscription-list'),
    path('inscriptions/stats/',                   inscription_api.inscription_stats, name='scolarite-inscription-stats'),
    path('inscriptions/depuis-admission/',        inscription_api.inscrire_depuis_admission,
                                                                                     name='scolarite-inscription-depuis-admission'),
    path('inscriptions/<int:pk>/',                inscription_api.inscription_detail, name='scolarite-inscription-detail'),
    path('inscriptions/<int:pk>/transition/',     inscription_api.inscription_transition,
                                                                                     name='scolarite-inscription-transition'),

    path('inscriptions/<int:pk>/pedagogie/',      pedagogie_api.inscription_pedagogique_list,
                                                                                     name='scolarite-pedagogie-list'),
    path('inscriptions/<int:pk>/pedagogie/generer/', pedagogie_api.inscription_pedagogique_generer,
                                                                                     name='scolarite-pedagogie-generer'),
    path('inscriptions/<int:pk>/pedagogie/ajouter/', pedagogie_api.inscription_pedagogique_ajouter,
                                                                                     name='scolarite-pedagogie-ajouter'),
    path('pedagogie/<int:ligne_id>/',             pedagogie_api.inscription_pedagogique_detail,
                                                                                     name='scolarite-pedagogie-detail'),

    path('inscriptions/<int:pk>/affectations/',   groupes_api.inscription_affectations,
                                                                                     name='scolarite-affectations'),
    path('inscriptions/<int:pk>/retirer-groupe/', groupes_api.inscription_retirer_groupe,
                                                                                     name='scolarite-retirer-groupe'),
    path('inscriptions/<int:pk>/passerelle/analyser/', passerelle_api.passerelle_analyser,
                                                                                     name='scolarite-passerelle-analyser'),
    path('inscriptions/<int:pk>/passerelle/',     passerelle_api.passerelle_synchroniser,
                                                                                     name='scolarite-passerelle'),
    path('passerelle/lot/',                       passerelle_api.passerelle_lot,     name='scolarite-passerelle-lot'),

    path('groupes/effectifs/',                    groupes_api.groupe_effectifs,      name='scolarite-groupe-effectifs'),
    path('groupes/repartition/',                  groupes_api.repartition_automatique,
                                                                                     name='scolarite-groupe-repartition'),
    path('reinscriptions/',                       groupes_api.reinscrire,            name='scolarite-reinscription'),
    path('etudiants/<int:pk>/evenements/',        groupes_api.etudiant_evenements,   name='scolarite-etudiant-evenements'),

    # Contrat de données en lecture seule pour l'application d'emploi du temps.
    path('edt/',                                  edt_export.contrat,                name='scolarite-edt-contrat'),
    path('edt/groupes/',                          edt_export.groupes,                name='scolarite-edt-groupes'),
    path('edt/enseignements/',                    edt_export.enseignements,          name='scolarite-edt-enseignements'),
    path('edt/etudiants/',                        edt_export.etudiants,              name='scolarite-edt-etudiants'),

    path('maquettes/',                            api_views.maquette_list,           name='scolarite-maquette-list'),
    path('maquettes/<int:pk>/',                   api_views.maquette_detail,         name='scolarite-maquette-detail'),
    path('maquettes/<int:pk>/semestres/<int:semestre_id>/ecues/',
         api_views.maquette_ecues_semestre,                                          name='scolarite-maquette-ecues'),

    path('ref/<str:ressource>/',                  api_views.referentiel_list,        name='scolarite-ref-list'),
    path('ref/<str:ressource>/<int:pk>/',         api_views.referentiel_detail,      name='scolarite-ref-detail'),
]
