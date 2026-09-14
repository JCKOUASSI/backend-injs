"""Matrice niveaux (A2), règles de séparation (J5) et correspondance A6.

``NIVEAUX`` retranscrit la matrice « rôle × module » de l'annexe A2. Seuls
les modules pour lesquels le rôle possède un niveau sont écrits ; les
« — » sont absents. Les astérisques et cercles d'A2 (limitation à ses ECUE
ou à son propre dossier) ne sont pas des niveaux : ils résultent du
périmètre par défaut du rôle et des futurs résolveurs de couverture (U4).

``NIVEAUX_EXTRA_PROVISOIRES`` couvre les cinq modules absents des colonnes
d'A2 (courriers, finances des formateurs, exports, paramètres,
référentiels). Ces cases n'existent pas dans le recueil : elles sont
étiquetées « provisoires, à valider à l'atelier J2 » dans le document de
matrice.
"""

# Les quinze modules des colonnes de la matrice A2, dans l'ordre du recueil.
MODULES_A2 = (
    'administration', 'candidatures', 'scolarite', 'pedagogie',
    'enseignants', 'evaluations', 'jurys', 'diplomation', 'finances_etud',
    'stages', 'rh', 'patrimoine', 'edt', 'presences', 'statistiques',
)

NIVEAUX = {
    'ADMIN_SYSTEME': {m: 'N4' for m in MODULES_A2},
    'DIRECTION_GENERALE': {
        'administration': 'N1', 'candidatures': 'N1', 'scolarite': 'N1',
        'pedagogie': 'N1', 'enseignants': 'N1', 'evaluations': 'N1',
        'jurys': 'N1', 'diplomation': 'N3', 'finances_etud': 'N1',
        'stages': 'N1', 'rh': 'N1', 'patrimoine': 'N1', 'edt': 'N1',
        'presences': 'N1', 'statistiques': 'N4',
    },
    'DIRECTION_ETUDES': {
        'administration': 'N1', 'candidatures': 'N1', 'scolarite': 'N3',
        'pedagogie': 'N3', 'enseignants': 'N1', 'evaluations': 'N3',
        'jurys': 'N3', 'diplomation': 'N3', 'stages': 'N1',
        'edt': 'N3', 'presences': 'N1', 'statistiques': 'N3',
    },
    'SCOLARITE': {
        'administration': 'N1', 'candidatures': 'N2', 'scolarite': 'N3',
        'pedagogie': 'N2', 'enseignants': 'N1', 'evaluations': 'N2',
        'jurys': 'N1', 'diplomation': 'N2', 'finances_etud': 'N1',
        'stages': 'N1', 'edt': 'N2', 'presences': 'N2', 'statistiques': 'N1',
    },
    'RESPONSABLE_PEDAGOGIQUE': {
        'candidatures': 'N1', 'scolarite': 'N1', 'pedagogie': 'N3',
        'enseignants': 'N2', 'evaluations': 'N2', 'jurys': 'N2',
        'diplomation': 'N1', 'stages': 'N2', 'edt': 'N3',
        'presences': 'N2', 'statistiques': 'N1',
    },
    'AGENT_CANDIDATURE': {'candidatures': 'N2', 'scolarite': 'N1'},
    'AGENT_CONTROLE_DOSSIERS': {'candidatures': 'N2', 'scolarite': 'N1'},
    'RESPONSABLE_CONCOURS': {
        'candidatures': 'N4', 'scolarite': 'N2', 'pedagogie': 'N1',
        'enseignants': 'N1', 'evaluations': 'N2', 'edt': 'N1',
        'presences': 'N1', 'statistiques': 'N1',
    },
    'AGENT_ADMISSIONS': {
        'candidatures': 'N2', 'scolarite': 'N2', 'pedagogie': 'N1',
        'finances_etud': 'N1',
    },
    'AGENT_INSCRIPTIONS': {
        'candidatures': 'N1', 'scolarite': 'N2', 'pedagogie': 'N1',
        'finances_etud': 'N1',
    },
    'GESTIONNAIRE_ETUDIANTS': {
        'candidatures': 'N1', 'scolarite': 'N2', 'pedagogie': 'N1',
        'evaluations': 'N1', 'diplomation': 'N1', 'finances_etud': 'N1',
        'stages': 'N1', 'edt': 'N1', 'presences': 'N1', 'statistiques': 'N1',
    },
    'RESPONSABLE_FORMATION': {
        'candidatures': 'N1', 'scolarite': 'N1', 'pedagogie': 'N3',
        'enseignants': 'N2', 'evaluations': 'N2', 'jurys': 'N2',
        'diplomation': 'N1', 'stages': 'N2', 'edt': 'N2',
        'presences': 'N1', 'statistiques': 'N1',
    },
    'GESTIONNAIRE_GROUPES': {
        'scolarite': 'N1', 'pedagogie': 'N2', 'enseignants': 'N1',
        'edt': 'N2', 'presences': 'N1',
    },
    'GESTIONNAIRE_COURS': {
        'scolarite': 'N1', 'pedagogie': 'N2', 'enseignants': 'N1',
        'evaluations': 'N1', 'patrimoine': 'N1', 'edt': 'N2',
        'presences': 'N1',
    },
    'GESTIONNAIRE_MAQUETTES': {
        'scolarite': 'N1', 'pedagogie': 'N3', 'enseignants': 'N1',
        'evaluations': 'N1', 'edt': 'N1',
    },
    'ENSEIGNANT': {
        'pedagogie': 'N1', 'enseignants': 'N1', 'evaluations': 'N2',
        'stages': 'N1', 'edt': 'N1', 'presences': 'N2',
    },
    'RESPONSABLE_UE_ECUE': {
        'pedagogie': 'N2', 'enseignants': 'N2', 'evaluations': 'N3',
        'jurys': 'N1', 'stages': 'N1', 'edt': 'N2', 'presences': 'N2',
        'statistiques': 'N1',
    },
    'GESTIONNAIRE_CHARGES': {
        'pedagogie': 'N2', 'enseignants': 'N2', 'diplomation': 'N1',
        'stages': 'N1', 'patrimoine': 'N1', 'edt': 'N2',
        'presences': 'N1', 'statistiques': 'N1',
    },
    'GESTIONNAIRE_NOTES': {
        'scolarite': 'N1', 'pedagogie': 'N1', 'enseignants': 'N1',
        'evaluations': 'N2', 'jurys': 'N1', 'presences': 'N1',
        'statistiques': 'N1',
    },
    'MEMBRE_JURY': {
        'scolarite': 'N1', 'pedagogie': 'N1', 'evaluations': 'N1',
        'jurys': 'N2', 'diplomation': 'N1', 'presences': 'N1',
        'statistiques': 'N1',
    },
    'RESPONSABLE_JURY': {
        'scolarite': 'N1', 'pedagogie': 'N1', 'evaluations': 'N3',
        'jurys': 'N4', 'diplomation': 'N2', 'presences': 'N1',
        'statistiques': 'N1',
    },
    'RESPONSABLE_GRADUATION': {
        'scolarite': 'N1', 'pedagogie': 'N1', 'evaluations': 'N1',
        'jurys': 'N1', 'diplomation': 'N3', 'statistiques': 'N1',
    },
    'RESPONSABLE_DIPLOMATION': {
        'scolarite': 'N1', 'pedagogie': 'N1', 'evaluations': 'N1',
        'jurys': 'N1', 'diplomation': 'N4', 'statistiques': 'N1',
    },
    'GESTIONNAIRE_FINANCES_ETUD': {
        'candidatures': 'N1', 'scolarite': 'N1', 'diplomation': 'N1',
        'finances_etud': 'N2', 'statistiques': 'N1',
    },
    'VALIDATEUR_FINANCIER': {
        'scolarite': 'N1', 'diplomation': 'N1', 'finances_etud': 'N3',
        'patrimoine': 'N1', 'statistiques': 'N1',
    },
    'GESTIONNAIRE_VACATIONS': {
        'pedagogie': 'N1', 'enseignants': 'N2', 'finances_etud': 'N2',
        'rh': 'N1', 'edt': 'N1', 'presences': 'N1', 'statistiques': 'N1',
    },
    'GESTIONNAIRE_STAGES': {
        'scolarite': 'N1', 'pedagogie': 'N1', 'enseignants': 'N1',
        'evaluations': 'N1', 'finances_etud': 'N1', 'stages': 'N2',
        'edt': 'N1', 'presences': 'N1', 'statistiques': 'N1',
    },
    'GESTIONNAIRE_RH': {
        'enseignants': 'N1', 'finances_etud': 'N1', 'rh': 'N3',
        'patrimoine': 'N1', 'edt': 'N1', 'presences': 'N1',
        'statistiques': 'N1',
    },
    'GESTIONNAIRE_PATRIMOINE': {
        'finances_etud': 'N1', 'rh': 'N1', 'patrimoine': 'N2',
        'edt': 'N1', 'statistiques': 'N1',
    },
    'GESTIONNAIRE_ESPACES': {
        'pedagogie': 'N1', 'patrimoine': 'N2', 'edt': 'N2',
        'presences': 'N1', 'statistiques': 'N1',
    },
    'GESTIONNAIRE_COURRIERS': {
        'administration': 'N2', 'scolarite': 'N1', 'diplomation': 'N1',
        'rh': 'N1', 'patrimoine': 'N1',
    },
    'ARCHIVISTE': {m: 'N1' for m in MODULES_A2},
    'ETUDIANT': {
        'scolarite': 'N1', 'pedagogie': 'N1', 'evaluations': 'N1',
        'jurys': 'N0', 'diplomation': 'N1', 'finances_etud': 'N1',
        'stages': 'N1', 'edt': 'N1', 'presences': 'N1',
    },
    'CANDIDAT': {'candidatures': 'N1', 'diplomation': 'N0'},
    'CONSULTATION': {
        'candidatures': 'N0', 'scolarite': 'N0', 'pedagogie': 'N0',
        'enseignants': 'N0', 'evaluations': 'N0', 'diplomation': 'N0',
        'stages': 'N0', 'patrimoine': 'N0', 'edt': 'N0',
        'presences': 'N0', 'statistiques': 'N1',
    },
}

#: Cinq modules absents des colonnes d'A2 — cases PROVISOIRES (atelier J2).
NIVEAUX_EXTRA_PROVISOIRES = {
    'ADMIN_SYSTEME': {
        'administrations': 'N4', 'finances_form': 'N4', 'exports': 'N4',
        'parametres': 'N4', 'referentiels': 'N4',
    },
    'DIRECTION_GENERALE': {
        'administrations': 'N1', 'finances_form': 'N1',
    },
    'DIRECTION_ETUDES': {'administrations': 'N1'},
    'SCOLARITE': {'administrations': 'N1', 'referentiels': 'N2'},
    'RESPONSABLE_PEDAGOGIQUE': {'referentiels': 'N2'},
    'RESPONSABLE_FORMATION': {'referentiels': 'N2'},
    'GESTIONNAIRE_MAQUETTES': {'referentiels': 'N2'},
    'GESTIONNAIRE_COURRIERS': {'administrations': 'N2'},
    'ARCHIVISTE': {'administrations': 'N1'},
    'GESTIONNAIRE_VACATIONS': {'finances_form': 'N2'},
    'VALIDATEUR_FINANCIER': {'finances_form': 'N3'},
    'GESTIONNAIRE_CHARGES': {'finances_form': 'N1'},
}

#: Permissions dont le niveau requis déroge au niveau de leur verbe (actes
#: que seul un niveau administrateur doit obtenir, quel que soit le module).
NIVEAU_PERMISSION_SURCHARGE = {
    'exports.export_sensible.generer': 4,
}

#: Couples d'incompatibilité (séparation des tâches, fiche U3 J5). Chaque
#: couple est rendu réflexif dans les deux sens lors du chargement.
INCOMPATIBILITES = (
    ('GESTIONNAIRE_NOTES', 'RESPONSABLE_JURY'),
    ('AGENT_INSCRIPTIONS', 'GESTIONNAIRE_FINANCES_ETUD'),
    ('GESTIONNAIRE_FINANCES_ETUD', 'VALIDATEUR_FINANCIER'),
    ('AGENT_CANDIDATURE', 'AGENT_CONTROLE_DOSSIERS'),
    ('RESPONSABLE_GRADUATION', 'GESTIONNAIRE_NOTES'),
)

#: Table de correspondance avec les 12 rôles existants (annexe A6). En U3
#: elle est implémentée et testée ; son application aux comptes relève d'U8.
CORRESPONDANCE_LEGACY = {
    'ADMIN': ['ADMIN_SYSTEME'],
    'CHEF_CPFAE_ADMIN': ['ADMIN_SYSTEME', 'DIRECTION_ETUDES'],
    'CPFAE_ADMIN': ['SCOLARITE', 'GESTIONNAIRE_COURS'],
    'DIRECTION': ['DIRECTION_GENERALE'],
    'CHEF_SECRETARIAT': [
        'SCOLARITE', 'AGENT_INSCRIPTIONS', 'AGENT_ADMISSIONS',
        'GESTIONNAIRE_ETUDIANTS',
    ],
    'SECRETARIAT': [
        'AGENT_INSCRIPTIONS', 'AGENT_ADMISSIONS', 'GESTIONNAIRE_ETUDIANTS',
    ],
    'FINANCE': ['GESTIONNAIRE_FINANCES_ETUD', 'GESTIONNAIRE_VACATIONS'],
    'ARCHIVE': ['ARCHIVISTE'],
    'ENCADRANT': ['ENSEIGNANT', 'GESTIONNAIRE_GROUPES'],
    'SUPERVISEUR': ['RESPONSABLE_PEDAGOGIQUE'],
    'FORMATEUR': ['ENSEIGNANT'],
    'AUDITEUR': ['ETUDIANT'],
}
