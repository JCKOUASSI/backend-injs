export const INSTITUTION = {
  name: 'Institut National de la Jeunesse et des Sports',
  shortName: 'INJS',
  ufr: 'UFR STAPS-JL',
  university: 'Université Félix Houphouët-Boigny',
  city: 'Abidjan',
  country: "Côte d'Ivoire",
  academicYear: '2025-2026',
  motto: 'Union - Discipline - Travail',
}

export const GRADES_LMD = [
  { id: 'licence', label: 'Licence', duree: '3 ans', credits: 180, niveaux: ['L1', 'L2', 'L3'] },
  { id: 'master', label: 'Master', duree: '2 ans', credits: 120, niveaux: ['M1', 'M2'] },
  { id: 'doctorat', label: 'Doctorat', duree: '3 ans', credits: 180, niveaux: ['D1', 'D2', 'D3'] },
]

export const SPECIALITES_STAPS = [
  { id: 'em', code: 'EM', label: 'Éducation et Motricité', color: '#3349A1' },
  { id: 'es', code: 'ES', label: 'Entraînement Sportif', color: '#4A5FBD' },
  { id: 'ms', code: 'MS', label: 'Management du Sport', color: '#283D85' },
  { id: 'apa', code: 'APA', label: 'Activités Physiques Adaptées et Santé', color: '#5B6FC7' },
]

export const SEMESTRES = [
  { id: 1, label: 'S1', niveau: 'L1', credits: 30, type: 'Tronc commun' },
  { id: 2, label: 'S2', niveau: 'L1', credits: 30, type: 'Tronc commun' },
  { id: 3, label: 'S3', niveau: 'L2', credits: 30, type: 'Tronc commun' },
  { id: 4, label: 'S4', niveau: 'L2', credits: 30, type: 'Spécialité' },
  { id: 5, label: 'S5', niveau: 'L3', credits: 30, type: 'Spécialité' },
  { id: 6, label: 'S6', niveau: 'L3', credits: 30, type: 'Stage professionnel' },
]

export const UE_SEMESTRE_1 = [
  { code: 'SVS8101', label: 'Sciences de la Vie et de la Santé appliquées aux APS', credits: 6, ecue: ['Anatomie du système musculo-squelettique', 'Physiologie et APS'] },
  { code: 'CIS8101', label: 'Aspects institutionnels des systèmes sportifs', credits: 4, ecue: ['Histoire du sport et de l\'EPS', 'Connaissances institutionnelles et législatives'] },
  { code: 'SCG8101', label: 'Sports collectifs de grandes surfaces', credits: 6, ecue: ['Football : Fondamentaux', 'Rugby : Fondamentaux'] },
  { code: 'SEC8101', label: 'Sports d\'expression corporelle 1', credits: 4, ecue: ['Gymnastique : Fondamentaux'] },
  { code: 'SPA8101', label: 'Sports athlétiques 1', credits: 4, ecue: ['Athlétisme : Fondamentaux'] },
  { code: 'SIV8101', label: 'Intervention en APS', credits: 4, ecue: ['Concepts de base en intervention', 'Pratique des APS au primaire'] },
  { code: 'TCO8101', label: 'Techniques de communication écrite et orale 1', credits: 2, ecue: ['Anglais : communication orale'] },
]

export const STATS_ADMIN = {
  totalEtudiants: 1542,
  totalProfesseurs: 87,
  totalUE: 156,
  tauxReussite: 78.5,
  inscriptions2025: 4800,
  admisConcours: 420,
}

export const ETUDIANTS_MOCK = [
  { id: 'ETU2024001', nom: 'Koné', prenom: 'Aminata', niveau: 'L2', specialite: 'EM', semestre: 4, credits: 90, moyenne: 12.45, statut: 'Actif' },
  { id: 'ETU2024002', nom: 'Traoré', prenom: 'Ibrahim', niveau: 'L1', specialite: 'Tronc commun', semestre: 2, credits: 30, moyenne: 11.20, statut: 'Actif' },
  { id: 'ETU2024003', nom: 'Diallo', prenom: 'Fatou', niveau: 'L3', specialite: 'ES', semestre: 6, credits: 150, moyenne: 13.80, statut: 'Actif' },
  { id: 'ETU2024004', nom: 'Bamba', prenom: 'Seydou', niveau: 'L2', specialite: 'MS', semestre: 4, credits: 90, moyenne: 10.95, statut: 'Actif' },
  { id: 'ETU2024005', nom: 'Coulibaly', prenom: 'Mariam', niveau: 'L2', specialite: 'APA', semestre: 4, credits: 90, moyenne: 14.10, statut: 'Actif' },
  { id: 'ETU2023012', nom: 'Yao', prenom: 'Christian', niveau: 'M1', specialite: 'STAPS', semestre: 7, credits: 210, moyenne: 13.25, statut: 'Actif' },
]

export const PROFESSEURS_MOCK = [
  { id: 'PRF001', nom: 'Seri Bialli', grade: 'Professeur Titulaire', ue: 'Sciences de la Vie', email: 'seribialliv@gmail.com', tel: '07 76 19 91' },
  { id: 'PRF002', nom: 'Tako Antoine', grade: 'Professeur Titulaire', ue: 'Biologie du Vieillissement', email: 'antoine.tako@gmail.com', tel: '07 93 89 24' },
  { id: 'PRF003', nom: 'Da Cyrille', grade: 'Professeur', ue: 'Physiologie et APS', email: 'da.cyrille@ufhb.ci', tel: '07 12 34 56' },
  { id: 'PRF004', nom: 'Baha Bi', grade: 'Professeur', ue: 'Sociologie des APS', email: 'baha.bi@ufhb.ci', tel: '05 67 89 01' },
  { id: 'PRF005', nom: 'Kouamé', grade: 'Professeur', ue: 'Méthodologie de la recherche', email: 'kouame@ufhb.ci', tel: '01 23 45 67' },
]

export const NOTES_ETUDIANT = [
  { ue: 'MEV8114', label: 'Mesure et évaluation des APS', cc: 14, ct: 12, moyenne: 12.8, statut: 'Validé', credits: 3 },
  { ue: 'ESC8114', label: 'Enseignement sports collectifs petites surfaces', cc: 13, ct: 15, moyenne: 14.2, statut: 'Validé', credits: 6 },
  { ue: 'ESE8114', label: 'Enseignement sports d\'expression corporelle', cc: 11, ct: 10, moyenne: 10.4, statut: 'Validé', credits: 4 },
  { ue: 'INF8114', label: 'Informatique - Bureautique', cc: 16, ct: 14, moyenne: 14.8, statut: 'Validé', credits: 2 },
]

export const EMPLOI_DU_TEMPS = [
  { jour: 'Lundi', heure: '08:00-10:00', ue: 'ESC8114', matiere: 'Pédagogie du handball', salle: 'Gymnase A', type: 'TP' },
  { jour: 'Lundi', heure: '10:15-12:15', ue: 'MEV8114', matiere: 'Mesure et évaluation en APS', salle: 'Amphi INJS', type: 'CM' },
  { jour: 'Mardi', heure: '08:00-10:00', ue: 'ESE8114', matiere: 'Pédagogie gymnastique', salle: 'Gymnase B', type: 'TP' },
  { jour: 'Mercredi', heure: '14:00-16:00', ue: 'PSC8114', matiere: 'Pédagogie du football', salle: 'Terrain synthétique', type: 'TP' },
  { jour: 'Jeudi', heure: '08:00-10:00', ue: 'INF8114', matiere: 'Bureautique', salle: 'Salle Info 2', type: 'TD' },
  { jour: 'Vendredi', heure: '10:15-12:15', ue: 'ESA8114', matiere: 'Pédagogie athlétisme', salle: 'Stade INJS', type: 'TP' },
]

export const STAGES = [
  { type: 'Découverte', semestre: 4, lieu: 'École primaire Cocody', duree: '75h', statut: 'En cours', superviseur: 'M. Amidou C.' },
  { type: 'Initiation', semestre: 5, lieu: 'Lycée moderne Abidjan', duree: '75h', statut: 'À venir', superviseur: '—' },
  { type: 'Responsabilité', semestre: 6, lieu: 'Collège municipal Yopougon', duree: '375h', statut: 'À venir', superviseur: '—' },
]

export const EVENEMENTS = [
  { date: '15 Jan 2026', titre: 'Rentrée académique 2025-2026', type: 'Institutionnel' },
  { date: '28 Fév 2026', titre: 'Examens partiels S2', type: 'Académique' },
  { date: '10 Mar 2026', titre: 'Séminaire CONFEJES - Formation régionale', type: 'Partenariat' },
  { date: '05 Avr 2026', titre: 'Concours d\'entrée INJS 2026', type: 'Admission' },
]

export const DEPARTEMENTS = [
  { code: 'STAPS-BIO', label: 'Biologie appliquée aux APS', responsable: 'Pr Ivan Zunon-K' },
  { code: 'STAPS-SHS', label: 'Sciences Humaines et Sociales appliquées aux APS', responsable: 'Pr Baha Bi' },
  { code: 'STAPS-INT', label: 'Sciences de l\'intervention', responsable: 'Amidou C.' },
  { code: 'STASE-ANIM', label: 'Sciences de l\'Animation pour le développement', responsable: 'Dr Comoé' },
  { code: 'STASE-EDU', label: 'Sciences Humaines appliquées à l\'éducation permanente', responsable: 'Dr Edi' },
  { code: 'STASE-LOIS', label: 'Sciences du Loisir', responsable: 'Dr Ayékoé' },
]

// ——— Comptes plateforme & permissions (UI prête pour le backend) ———

export const PERMISSION_MODULES = [
  {
    id: 'etudiants',
    label: 'Étudiants',
    permissions: [
      { key: 'students.read', label: 'Consulter les dossiers étudiants' },
      { key: 'students.write', label: 'Créer / modifier les inscriptions' },
      { key: 'students.archive', label: 'Archiver un dossier étudiant' },
    ],
  },
  {
    id: 'professeurs',
    label: 'Professeurs',
    permissions: [
      { key: 'professors.read', label: 'Consulter les professeurs' },
      { key: 'professors.write', label: 'Gérer les fiches enseignants' },
    ],
  },
  {
    id: 'pedagogie',
    label: 'Pédagogie LMD',
    permissions: [
      { key: 'formations.read', label: 'Consulter formations & UE' },
      { key: 'formations.write', label: 'Modifier formations, UE et ECUE' },
      { key: 'grades.read', label: 'Consulter les notes' },
      { key: 'grades.write', label: 'Saisir et valider les notes' },
      { key: 'internships.manage', label: 'Gérer les stages' },
    ],
  },
  {
    id: 'administration',
    label: 'Administration',
    permissions: [
      { key: 'events.manage', label: 'Gérer les événements' },
      { key: 'finances.read', label: 'Consulter les finances' },
      { key: 'finances.write', label: 'Modifier les finances' },
      { key: 'reports.export', label: 'Exporter les rapports' },
      { key: 'settings.manage', label: 'Accéder aux paramètres système' },
      { key: 'users.manage', label: 'Gérer les utilisateurs et rôles' },
    ],
  },
]

export const ROLES_SYSTEME = [
  {
    id: 'admin',
    label: 'Administration',
    description: 'Accès complet à la plateforme',
    isSystem: true,
    permissions: ['*'],
  },
  {
    id: 'professeur',
    label: 'Professeur',
    description: 'Enseignement, évaluations et suivi pédagogique',
    isSystem: true,
    permissions: [
      'students.read',
      'formations.read',
      'grades.read',
      'grades.write',
      'internships.manage',
    ],
  },
  {
    id: 'etudiant',
    label: 'Étudiant',
    description: 'Consultation du parcours personnel',
    isSystem: true,
    permissions: ['formations.read', 'grades.read'],
  },
  {
    id: 'secretaire',
    label: 'Secrétariat pédagogique',
    description: 'Inscriptions, dossiers et suivi administratif',
    isSystem: false,
    permissions: [
      'students.read',
      'students.write',
      'professors.read',
      'formations.read',
      'events.manage',
      'reports.export',
    ],
  },
]

export const UTILISATEURS_MOCK = [
  {
    id: 'USR001',
    prenom: 'Jean-Marc',
    nom: 'Kouassi',
    email: 'admin@injs.ci',
    role: 'admin',
    statut: 'Actif',
    lastLogin: '28/06/2026 14:32',
    linkedId: null,
    linkedType: null,
  },
  {
    id: 'USR002',
    prenom: 'Seri',
    nom: 'Bialli',
    email: 'seribialliv@gmail.com',
    role: 'professeur',
    statut: 'Actif',
    lastLogin: '30/06/2026 09:15',
    linkedId: 'PRF001',
    linkedType: 'professeur',
  },
  {
    id: 'USR003',
    prenom: 'Aminata',
    nom: 'Koné',
    email: 'etudiant@injs.ci',
    role: 'etudiant',
    statut: 'Actif',
    lastLogin: '01/07/2026 08:42',
    linkedId: 'ETU2024001',
    linkedType: 'etudiant',
  },
  {
    id: 'USR004',
    prenom: 'Adjoua',
    nom: 'N\'Guessan',
    email: 'secretaire@injs.ci',
    role: 'secretaire',
    statut: 'Actif',
    lastLogin: '29/06/2026 16:20',
    linkedId: null,
    linkedType: null,
  },
  {
    id: 'USR005',
    prenom: 'Tako',
    nom: 'Antoine',
    email: 'antoine.tako@gmail.com',
    role: 'professeur',
    statut: 'Inactif',
    lastLogin: '12/03/2026 11:00',
    linkedId: 'PRF002',
    linkedType: 'professeur',
  },
]
