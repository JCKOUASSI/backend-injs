/** Pastilles de statut et jauges de couverture du module EPT-INJS. */

export function StatutBadge({ statut, label }) {
  if (!statut) return <span className="text-muted">—</span>
  return <span className={`ept-badge ept-badge-${statut}`}>{label || statut}</span>
}

export function Jauge({ valeur = 0, largeur = 90 }) {
  const borne = Math.max(0, Math.min(100, Number(valeur) || 0))
  const variante = borne >= 100 ? 'is-complet' : borne < 50 ? 'is-faible' : ''
  return (
    <div className="d-flex align-items-center gap-2">
      <div className="ept-jauge" style={{ width: largeur }}>
        <div className={`ept-jauge-valeur ${variante}`} style={{ width: `${borne}%` }} />
      </div>
      <span className="small text-muted">{borne} %</span>
    </div>
  )
}

export function Kpi({ valeur, label, suffixe }) {
  return (
    <div className="ept-kpi">
      <div className="ept-kpi-value">
        {valeur}
        {suffixe && <span className="fs-6 fw-normal text-muted ms-1">{suffixe}</span>}
      </div>
      <div className="ept-kpi-label">{label}</div>
    </div>
  )
}

export function EtatVide({ message, action }) {
  return (
    <div className="text-center text-muted py-5">
      <p className="mb-3">{message}</p>
      {action}
    </div>
  )
}

export function Chargement() {
  return (
    <div className="text-center py-5">
      <div className="spinner-border text-primary" role="status">
        <span className="visually-hidden">Chargement…</span>
      </div>
    </div>
  )
}
