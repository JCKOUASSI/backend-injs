/**
 * constantes.js — Statistiques (INJS-LMD 2026)
 *
 * Constantes et libellés du dashboard Statistiques, extraits de
 * `pages/Statistiques.jsx` (réduction des fichiers géants, garde-fou G.1).
 * Ce module est purement déclaratif : aucune dépendance, aucun effet.
 */
export const C = ['#2277C1','#1565C0','#F5B100','#7B1FA2','#C62828','#00838F','#0F70AB','#AD1457','#0277BD','#4E342E']

export const STATUT_LABELS = {
  TERMINE:'Terminé', EN_COURS:'En cours', FORCE_DFRC:'Forcé DFRC',
  ABSENT_NON_BADGE:'Absent non badgé', HORS_LIGNE_SUSPECT:'Hors ligne suspect',
  SORTIE_AUTO:'Sortie automatique',
}
export const VALIDATION_ROLES = ['ADMIN','DIRECTION','CHEF_CPFAE_ADMIN','CPFAE_ADMIN']

export const RB_VIEWS = [
  { id: 'bilans', label: 'Bilans INJS', icon: 'bi-table' },
  { id: 'workflow', label: 'Rapports périodiques', icon: 'bi-file-earmark-check' },
]

/** Libellés harmonisés des taux pédagogiques (vague 1). */
export const TAUX_PEDAGOGIE = {
  assiduite: {
    label: 'Assiduité séance',
    help: 'Places présentes ÷ places attendues sur les séances terminées du périmètre. Utilisé pour le dashboard, les alertes et l\'historique.',
    color: '#2277C1',
    getValue: (ped) => ped?.taux_presence ?? 0,
  },
  couverture: {
    label: 'Couverture étudiants',
    help: 'Étudiants ayant au moins une présence ÷ étudiants inscrits. Aligné sur la logique des bilans INJS.',
    color: '#1565C0',
    getValue: (ped) => ped?.taux_couverture_auditeurs ?? ped?.taux_achevement ?? 0,
  },
  absence: {
    label: 'Absence séance',
    help: 'Places absentes ÷ places attendues sur les séances terminées du périmètre.',
    color: '#C62828',
    getValue: (ped) => ped?.taux_absence ?? 0,
  },
  evenements: {
    label: 'Événements absence / suspect',
    help: 'Pointages « absent non badgé » ou « hors ligne suspect » rapportés aux inscrits (événements, pas absents notoires).',
    color: '#F5B100',
    getValue: (ped) => ped?.taux_abandon ?? 0,
  },
}
export const KPI_VH_EXEC = {
  label: 'Avancement VH (sessions clôturées)',
  help: 'Heures réalisées ÷ heures prévues, sur les séances clôturées du périmètre filtré.',
}

export const KPI_SESSIONS_COMPT = {
  label: 'Séances comptabilisées',
  help: 'Séances dont la date est atteinte (EDT importé), alignées avec le point journalier et l\'assiduité.',
}

export const KPI_SESSIONS_TOTAL = {
  label: 'Séances totales',
  help: 'Séances planifiées dont la date est dans la période sélectionnée (y compris futures sur l\'intervalle).',
}

export const KPI_PERIOD_SCOPE_HELP =
  'Filtré selon la période : modules ayant au moins une séance dans l\'intervalle. « Toutes les périodes » = cumul global du périmètre.'

/** Définition métier unifiée (dashboard, bilans, FAC, alertes). */
export const AUDITEURS_NOTOIRES = {
  label: 'Absents notoires',
  cardTitle: 'Absents notoires',
  help: 'Inscrit à au moins un module démarré, sans aucune présence enregistrée, ou avec motif notoire renseigné.',
}

/** Onglets accessibles aux comptes secrétariat (point + bilans uniquement). */
export const SECRETARIAT_STATS_TABS = new Set(['point_journalier', 'rapports'])

/** Onglets où le filtre période s'applique aux indicateurs clés. */
export const VH_PERIOD_TABS = new Set(['overview', 'pedagogy', 'admin', 'history', 'alertes'])

/** Sections API chargées par onglet (évite le calcul de tout le dashboard d'un coup). */
export const TAB_SECTIONS = {
  overview: ['kpis', 'pedagogiques', 'admin_operationnel', 'alertes_overview', 'alertes'],
  pedagogy: ['pedagogiques'],
  admin: ['admin_operationnel'],
  history: ['historique', 'pedagogiques', 'admin_operationnel'],
  alertes: ['alertes', 'pedagogiques', 'admin_operationnel'],
  point_journalier: ['admin_operationnel'],
  rapports: ['admin_operationnel'],
}

/** Méta (formations_liste, secretariats_liste, filtre_actif) — chargées via useStatsMeta. */
export const ALERTES_OVERVIEW_CODES = ['taux_presence', 'taux_execution_vh', 'saturation_groupe']

export const PJ_EXPORT_FORMATS = [
  { fmt: 'xlsx', icon: 'bi-file-earmark-excel', label: 'Excel', col: '#0b4489' },
  { fmt: 'pdf',  icon: 'bi-file-earmark-pdf',   label: 'PDF',   col: '#C62828' },
  { fmt: 'docx', icon: 'bi-file-earmark-word',  label: 'Word',  col: '#1565C0' },
]

export const RB_PERIODES = [
  { value: '', label: 'Toutes périodes' },
  { value: 'QUOTIDIEN', label: 'Quotidien' },
  { value: 'HEBDOMADAIRE', label: 'Hebdomadaire' },
  { value: 'MENSUEL', label: 'Mensuel' },
  { value: 'TRIMESTRIEL', label: 'Trimestriel' },
  { value: 'SEMESTRIEL', label: 'Semestriel' },
  { value: 'ANNUEL', label: 'Annuel' },
  { value: 'MI_PARCOURS', label: 'À mi-parcours' },
]

export const RB_DIMENSIONS = [
  { id: 'module', label: 'Par Module', icon: 'bi-book' },
  { id: 'matiere', label: 'Par Matière', icon: 'bi-journals' },
  { id: 'categorie', label: 'Par Catégorie', icon: 'bi-tag' },
  { id: 'formation', label: 'Par Formation', icon: 'bi-journal-bookmark' },
]

export function rbMatiereOptionValue(m) {
  if (m.ref_module_id) return `r:${m.ref_module_id}`
  return `i:${m.intitule}`
}

export function rbParseMatiereKey(key) {
  if (!key) return {}
  if (key.startsWith('r:')) return { ref_module_id: Number(key.slice(2)) }
  if (key.startsWith('i:')) return { matiere_intitule: key.slice(2) }
  return {}
}

/** Niveaux de vigilance des indicateurs surveillés (alertes). */
export const NIVEAU_ALERTE = {
  ok:              { label: 'Conforme',       bg: '#ecf3fd', border: '#80b7f5', color: '#0b478a', icon: 'bi-check-circle-fill' },
  avertissement:   { label: 'Avertissement',  bg: '#fffceb', border: '#fcdf4d', color: '#b47f09', icon: 'bi-exclamation-triangle-fill' },
  critique:        { label: 'Critique',       bg: '#fff1f2', border: '#fca5a5', color: '#b91c1c', icon: 'bi-exclamation-octagon-fill' },
  inactif:         { label: 'Surveillance off', bg: '#f8fafc', border: '#e2e8f0', color: '#64748b', icon: 'bi-pause-circle' },
  non_configure:   { label: 'Non configuré',  bg: '#f1f5f9', border: '#cbd5e1', color: '#475569', icon: 'bi-gear' },
}
