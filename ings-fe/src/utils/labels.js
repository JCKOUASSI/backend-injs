/** Libellés FR pour codes API affichés dans l'UI. */

const STATUS_FR = {
  // Finances
  paid: 'Payé',
  pending: 'En attente',
  partial: 'Partiel',
  overdue: 'En retard',
  cancelled: 'Annulé',
  canceled: 'Annulé',
  failed: 'Échoué',
  success: 'Réussi',
  completed: 'Terminé',

  // Étudiants / admissions
  active: 'Actif',
  inactive: 'Inactif',
  suspended: 'Suspendu',
  graduated: 'Diplômé',
  withdrawn: 'Retiré',
  submitted: 'Soumis',
  approved: 'Approuvé',
  rejected: 'Rejeté',
  under_review: 'En instruction',
  draft: 'Brouillon',

  // Examens / délibérations
  open: 'Ouverte',
  closed: 'Fermée',
  validated: 'Validée',
  published: 'Publiée',
  running: 'En cours',
  scheduled: 'Planifiée',

  // Notes
  valid: 'Validé',
  invalid: 'Non validé',
  pass: 'Réussi',
  fail: 'Échec',

  // Salles / infrastructures
  available: 'Disponible',
  maintenance: 'En maintenance',
  reserved: 'Réservée',

  // Réservations / tickets
  pending: 'En attente',
  approved: 'Approuvée',
  rejected: 'Refusée',
  in_progress: 'En cours',
  resolved: 'Résolu',
  in_use: 'En service',
  retired: 'Réformé',
}

const SESSION_TYPE_FR = {
  normal: 'Normale',
  retake: 'Rattrapage',
  special: 'Spéciale',
}

const DELIB_ACTION_FR = {
  run: 'lancement',
  validate: 'validation',
  publish: 'publication',
}

export function translateStatus(value) {
  if (value == null || value === '' || value === '—') return '—'
  const key = String(value).trim().toLowerCase()
  return STATUS_FR[key] || String(value)
}

export function translateSessionType(value) {
  if (value == null || value === '') return '—'
  const key = String(value).trim().toLowerCase()
  return SESSION_TYPE_FR[key] || String(value)
}

export function translateDelibAction(action) {
  return DELIB_ACTION_FR[action] || action
}

export function mediaUrl(url) {
  if (!url) return null
  if (url.startsWith('blob:') || url.startsWith('data:')) return url
  // Réécrire les URLs absolues du serveur API vers le proxy Vite /media
  try {
    if (url.startsWith('http')) {
      const u = new URL(url)
      if (u.pathname.startsWith('/media')) return u.pathname + u.search
    }
  } catch {
    // ignore
  }
  if (url.startsWith('/')) return url
  return `/${url}`
}
