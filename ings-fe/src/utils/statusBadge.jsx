import { translateStatus } from './labels'

/** Classes badge alignées sur le module Stages (grade-valid / grade-pending / grade-fail). */
export function getStatusBadgeClass(statut) {
  const s = String(statut || '').toLowerCase().trim()

  if (!s || s === '—' || s === '-') return 'grade-pending'

  // Tester les négations AVANT "validé" (sinon "non validé" devient vert)
  if (
    s.includes('non valid') ||
    s.includes('non-valid') ||
    s.includes('ajourn') ||
    s.includes('échec') ||
    s.includes('echec') ||
    s.includes('refus') ||
    s.includes('échou') ||
    s.includes('fail') ||
    s.includes('reject') ||
    s.includes('suspend') ||
    s.includes('absent') ||
    s.includes('overdue') ||
    s.includes('retir')
  ) {
    return 'grade-fail'
  }

  if (
    s.includes('validé') ||
    s.includes('valide') ||
    s.includes('approuv') ||
    s.includes('réussi') ||
    s.includes('reussi') ||
    s.includes('soldé') ||
    s.includes('payé') ||
    s.includes('paid') ||
    s.includes('actif') ||
    s.includes('active') ||
    s.includes('publi') ||
    s.includes('terminé') ||
    s.includes('termine') ||
    s.includes('complété') ||
    s.includes('complete') ||
    s.includes('approv')
  ) {
    return 'grade-valid'
  }

  // En cours, pending, brouillon, etc. → même jaune que Stages
  return 'grade-pending'
}

export function StatusBadge({ statut, className = '', translate = true }) {
  const label = translate ? translateStatus(statut) : (statut || '—')
  return (
    <span className={`grade-badge ${getStatusBadgeClass(statut || label)} ${className}`.trim()}>
      {label}
    </span>
  )
}
