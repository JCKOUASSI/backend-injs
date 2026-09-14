"""Les rôles métier de l'annexe A1 (35 lignes, dont 32 rôles internes et 3
destinataires du service).

Chaque entrée porte, dans l'ordre des champs : code stable, libellé, domaine,
niveau par défaut, périmètre par défaut, application Django requise ('' =
toujours disponible), caractère sensible, canal imposé ('' = les deux),
ordre d'affichage, description en français courant.

Le recueil titre « 33 rôles » mais le tableau A1 contient 35 lignes : les
trois dernières (Étudiant, Candidat, Consultation) sont des *destinataires
du service*. Elles sont chargées par sécurité additive (note de conception
U3, §2).
"""

# (code, libellé, domaine, niveau, périmètre, module, sensible, canal, ordre, description)
ROLES = [
    # ── ADMINISTRATION ──────────────────────────────────────────────
    ('ADMIN_SYSTEME', 'Administrateur système', 'ADMINISTRATION', 'N4',
     'INJS_ENTIER', '', True, '', 10,
     "Gère l'ensemble des comptes, rôles et paramètres de la plateforme, "
     "sans intervenir sur les décisions métier (notes, jurys, finances)."),
    ('DIRECTION_GENERALE', 'Direction générale', 'ADMINISTRATION', 'N4',
     'INJS_ENTIER', '', True, '', 20,
     "Pilote l'institut : consultation générale, décision sur la diplomation "
     "et les statistiques, aucun acte de saisie courante."),
    ('DIRECTION_ETUDES', 'Direction des études', 'ADMINISTRATION', 'N4',
     'INJS_ENTIER', '', True, '', 30,
     "Valide l'organisation des études : scolarité, pédagogie, évaluations, "
     "jurys et emplois du temps."),
    ('SCOLARITE', 'Scolarité', 'ADMINISTRATION', 'N3',
     'SECRETARIAT', 'scolarite', False, '', 40,
     "Coordonne les inscriptions, les dossiers étudiants et le suivi de "
     "scolarité au sein d'un secrétariat."),
    ('RESPONSABLE_PEDAGOGIQUE', 'Responsable pédagogique', 'ADMINISTRATION',
     'N3', 'FORMATION', 'scolarite', False, '', 50,
     "Organise la pédagogie d'une formation : maquettes, équipes, évaluations "
     "et emploi du temps, sans valider les jurys."),
    # ── CANDIDATURES ────────────────────────────────────────────────
    ('AGENT_CANDIDATURE', 'Agent de candidature', 'CANDIDATURES', 'N2',
     'INJS_ENTIER', 'admissions', False, '', 60,
     "Saisit et instruit les dossiers de candidature et les pièces reçues."),
    ('AGENT_CONTROLE_DOSSIERS', 'Agent de contrôle des dossiers',
     'CANDIDATURES', 'N2', 'INJS_ENTIER', 'admissions', False, '', 70,
     "Contrôle la conformité et l'éligibilité des dossiers ; ce rôle est "
     "incompatible avec la saisie des candidatures (séparation des tâches)."),
    ('RESPONSABLE_CONCOURS', 'Responsable concours et sélection',
     'CANDIDATURES', 'N3', 'INJS_ENTIER', 'admissions', True, '', 80,
     "Organise les concours, épreuves et surveillances, puis arrête et publie "
     "les classements."),
    # ── SCOLARITÉ ───────────────────────────────────────────────────
    ('AGENT_ADMISSIONS', 'Agent admissions', 'SCOLARITE', 'N2',
     'SECRETARIAT', 'admissions', False, '', 90,
     "Traite les admissions des candidats retenus et leur passage en "
     "inscription."),
    ('AGENT_INSCRIPTIONS', 'Agent inscriptions', 'SCOLARITE', 'N2',
     'SECRETARIAT', 'scolarite', False, '', 100,
     "Réalise les inscriptions administratives et pédagogiques, et les "
     "affectations de groupes."),
    ('GESTIONNAIRE_ETUDIANTS', 'Gestionnaire étudiants', 'SCOLARITE', 'N2',
     'SECRETARIAT', 'scolarite', False, '', 110,
     "Tient à jour les dossiers étudiants, inscriptions, transferts et suivis "
     "au fil de l'année."),
    # ── PÉDAGOGIE ────────────────────────────────────────────────────
    ('RESPONSABLE_FORMATION', 'Responsable de formation', 'PEDAGOGIE', 'N3',
     'FORMATION', 'scolarite', False, '', 120,
     "Pilote une offre de formation : maquettes, équipes enseignantes et "
     "calendrier, en lien avec les entreprises de stage."),
    ('GESTIONNAIRE_GROUPES', 'Gestionnaire des groupes', 'PEDAGOGIE', 'N2',
     'FORMATION', 'scolarite', False, '', 130,
     "Construit et ajuste les groupes pédagogiques et leurs affectations."),
    ('GESTIONNAIRE_COURS', 'Gestionnaire des cours', 'PEDAGOGIE', 'N2',
     'FORMATION', 'scolarite', False, '', 140,
     "Renseigne les cours, volumes horaires et leur planification."),
    ('GESTIONNAIRE_MAQUETTES', 'Gestionnaire des maquettes', 'PEDAGOGIE', 'N3',
     'FORMATION', 'scolarite', False, '', 150,
     "Élabore et fait valider les maquettes, UE, ECUE et crédits ECTS."),
    # ── ENSEIGNANTS ──────────────────────────────────────────────────
    ('ENSEIGNANT', 'Enseignant', 'ENSEIGNANTS', 'N2',
     'MODULE_ECUE', 'scolarite', False, 'MOBILE', 160,
     "Intervient sur ses ECUE, groupes et séances : saisie des notes et "
     "présences qui le concernent."),
    ('RESPONSABLE_UE_ECUE', 'Responsable UE / ECUE', 'ENSEIGNANTS', 'N3',
     'MODULE_ECUE', 'scolarite', False, '', 170,
     "Coordonne une UE ou une ECUE : équipe, notes, délibérations et "
     "affectations pédagogiques."),
    ('GESTIONNAIRE_CHARGES', 'Gestionnaire des charges enseignantes',
     'ENSEIGNANTS', 'N2', 'FORMATION', 'scolarite', False, '', 180,
     "Prépare les charges et vacations des enseignants, en lien avec la "
     "rémunération des formateurs."),
    # ── ÉVALUATIONS ──────────────────────────────────────────────────
    ('GESTIONNAIRE_NOTES', 'Gestionnaire des notes', 'EVALUATIONS', 'N2',
     'FORMATION', 'suiviEvaluation', False, '', 190,
     "Saisit et corrige les notes et moyennes ; ne participe pas aux jurys "
     "(incompatibilité de séparation des tâches)."),
    ('MEMBRE_JURY', 'Membre de jury', 'EVALUATIONS', 'N2',
     'FORMATION', 'jurys', False, '', 200,
     "Participe aux délibérations d'un jury et signe les propositions "
     "collectives."),
    ('RESPONSABLE_JURY', 'Responsable de jury', 'EVALUATIONS', 'N4',
     'FORMATION', 'jurys', True, '', 210,
     "Préside le jury, arrête les délibérations et signe les procès-verbaux "
     "et résultats."),
    # ── DIPLÔMATION ──────────────────────────────────────────────────
    ('RESPONSABLE_GRADUATION', 'Responsable graduation', 'DIPLOMATION', 'N3',
     'INJS_ENTIER', 'graduation', True, '', 220,
     "Organise les cérémonies et dossiers de graduation et atteste les "
     "parcours arrivant à terme."),
    ('RESPONSABLE_DIPLOMATION', 'Responsable diplômation', 'DIPLOMATION', 'N4',
     'INJS_ENTIER', 'graduation', True, '', 230,
     "Valide, édite et, le cas échéant, révoque les diplômes et tient les "
     "registres réglementaires."),
    # ── FINANCE ──────────────────────────────────────────────────────
    ('GESTIONNAIRE_FINANCES_ETUD', 'Gestionnaire finances étudiantes',
     'FINANCE', 'N2', 'INJS_ENTIER', 'finances_etudiantes', True, '', 240,
     "Saisit les frais, factures, paiements et quittances des étudiants ; ne "
     "valide pas les encaissements (rôle séparé)."),
    ('VALIDATEUR_FINANCIER', 'Validateur financier', 'FINANCE', 'N3',
     'INJS_ENTIER', 'finances_etudiantes', True, '', 250,
     "Valide les paiements, remboursements et écritures financières ; ne "
     "saisit pas les encaissements (séparation des tâches)."),
    ('GESTIONNAIRE_VACATIONS', 'Gestionnaire vacations formateurs',
     'FINANCE', 'N2', 'INJS_ENTIER', 'formations', True, '', 260,
     "Prépare les états de vacation et la rémunération des formateurs et "
     "vacataires."),
    # ── STAGES ───────────────────────────────────────────────────────
    ('GESTIONNAIRE_STAGES', 'Gestionnaire des stages', 'STAGES', 'N2',
     'FORMATION', 'stages', False, '', 270,
     "Gère les organismes d'accueil, tuteurs, conventions et attestations de "
     "stage."),
    # ── RESSOURCES HUMAINES ──────────────────────────────────────────
    ('GESTIONNAIRE_RH', 'Gestionnaire ressources humaines', 'RH', 'N3',
     'INJS_ENTIER', 'ressources_humaines', True, '', 280,
     "Tient les dossiers des agents, services, fonctions, affectations et "
     "documents RH."),
    # ── PATRIMOINE ───────────────────────────────────────────────────
    ('GESTIONNAIRE_PATRIMOINE', 'Gestionnaire du patrimoine', 'PATRIMOINE',
     'N2', 'SITE', 'patrimoine', False, '', 290,
     "Gère les équipements, véhicules, inventaires, maintenance et mouvements "
     "de biens."),
    ('GESTIONNAIRE_ESPACES', 'Gestionnaire des espaces', 'PATRIMOINE', 'N2',
     'SITE', 'patrimoine', False, '', 300,
     "Gère les salles et leurs réservations, en lien avec les emplois du "
     "temps."),
    # ── ADMINISTRATION GÉNÉRALE ──────────────────────────────────────
    ('GESTIONNAIRE_COURRIERS', 'Gestionnaire courriers et documents',
     'ADMINISTRATION_GENERALE', 'N2', 'SERVICE', 'administrations', False,
     '', 310,
     "Enregistre et suit les courriers, documents officiels, réunions et "
     "missions."),
    ('ARCHIVISTE', 'Archiviste', 'ADMINISTRATION_GENERALE', 'N2',
     'INJS_ENTIER', '', False, '', 320,
     "Consulte et archive les dossiers de tous les services, sans droit de "
     "modification."),
    # ── DESTINATAIRES DU SERVICE (usagers, pas des rôles d'administration)
    ('ETUDIANT', 'Étudiant / auditeur', 'DESTINATAIRES', 'N1',
     'PROPRE_COMPTE', 'presences', False, 'MOBILE', 330,
     "Accède uniquement à son propre dossier, ses notes, émargements et "
     "justificatifs via l'application mobile."),
    ('CANDIDAT', 'Candidat', 'DESTINATAIRES', 'N0',
     'PROPRE_COMPTE', 'admissions', False, '', 340,
     "Dépose et suit sa propre candidature et ses pièces, sans voir les "
     "autres dossiers."),
    ('CONSULTATION', 'Consultation restreinte', 'DESTINATAIRES', 'N1',
     'INJS_ENTIER', '', False, '', 350,
     "Compte de lecture très restreinte, sans aucune action de modification, "
     "pour un besoin ponctuel de consultation."),
]

# Index rapide par code.
ROLES_PAR_CODE = {ligne[0]: ligne for ligne in ROLES}

#: Les onze rôles sensibles (colonne « Sens. » de l'annexe A1) — rappel
#: explicite, déduit aussi du fanion ``sensible`` des lignes ci-dessus.
ROLES_SENSIBLES = tuple(
    ligne[0] for ligne in ROLES if ligne[6]
)
