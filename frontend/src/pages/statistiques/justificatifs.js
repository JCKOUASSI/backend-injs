/**
 * justificatifs.js — Statistiques (INJS-LMD 2026)
 *
 * Normalisation des justificatifs d'absence notoire, partagée entre les
 * bilans INJS et le bilan FAC. Extrait de `pages/Statistiques.jsx`.
 */

export function normalizeJustificatifs(value) {
  if (!value) return ''
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.filter(Boolean).map(j => `• ${j}`).join('\n')
  return ''
}
