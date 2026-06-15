const DEFAULT_FIELD_LABELS = {
  username: 'Identifiant',
  role: 'Rôle',
  password: 'Mot de passe',
  matricule: 'N° matricule',
  email: 'Adresse e-mail',
  secretariat: 'Secrétariat',
  first_name: 'Prénom',
  last_name: 'Nom',
  telephone: 'Téléphone',
  detail: 'Erreur',
  non_field_errors: 'Erreur',
}

/**
 * Formate une réponse d'erreur API DRF en texte lisible pour l'utilisateur.
 */
export function formatApiErrors(data, { fieldLabels = DEFAULT_FIELD_LABELS, fallback = 'Une erreur est survenue.' } = {}) {
  if (!data) return fallback
  if (typeof data === 'string') return data

  if (data.detail != null) {
    const detail = data.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map(String).join('\n')
    return String(detail)
  }

  if (!data || typeof data !== 'object') return fallback

  const lines = Object.entries(data).map(([key, value]) => {
    const label = fieldLabels[key] || key
    const text = Array.isArray(value) ? value.join(', ') : String(value)
    return `${label} : ${text}`
  })

  return lines.length > 0 ? lines.join('\n') : fallback
}
