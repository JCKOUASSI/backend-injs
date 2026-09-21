/**
 * taux-pedagogie.jsx — Statistiques (INJS-LMD 2026)
 *
 * Restitution des taux pédagogiques (assiduité, couverture, absences,
 * événements), en bloc principal ou en grille. Extrait de
 * `pages/Statistiques.jsx` (réduction des fichiers géants, garde-fou G.1).
 */
import { Kpi, TauxBar } from './composants'
import { TAUX_PEDAGOGIE } from './constantes'

export function PedagogieTauxPrincipaux({ ped, auditeursNotoires }) {
  const a = TAUX_PEDAGOGIE.assiduite
  const c = TAUX_PEDAGOGIE.couverture
  const an = auditeursNotoires || ped?.auditeurs_notoires
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: '0.75rem', marginBottom: '0.75rem' }}>
      <Kpi icon="bi-person-check" label={a.label} value={`${a.getValue(ped)}%`} color={a.color} help={a.help}/>
      <Kpi icon="bi-people" label={c.label} value={`${c.getValue(ped)}%`} color={c.color} help={c.help}/>
      {an != null && (
        <Kpi
          icon="bi-person-x-fill"
          label="Absents notoires"
          value={an.total ?? 0}
          color="#C62828"
          sub={`${Number(an.pct || 0).toFixed(1).replace('.', ',')}% des inscrits`}
          help="Inscrit à au moins un module démarré, sans présence enregistrée ou avec motif notoire."
        />
      )}
    </div>
  )
}

export function PedagogieTauxGrille({ ped, withBars = false, grid = false }) {
  const items = [
    TAUX_PEDAGOGIE.assiduite,
    TAUX_PEDAGOGIE.absence,
    TAUX_PEDAGOGIE.evenements,
    TAUX_PEDAGOGIE.couverture,
  ]
  return (
    <div style={{
      display: grid ? 'grid' : 'flex',
      gridTemplateColumns: grid ? 'repeat(2, minmax(0, 1fr))' : undefined,
      gap: grid ? '0.75rem' : '1.25rem',
      flexWrap: grid ? undefined : 'wrap',
      justifyContent: grid ? 'stretch' : 'center',
      padding: withBars || grid ? '0.5rem 0' : 0,
    }}>
      {items.map((t) => (
        <div key={t.label} style={{ textAlign: 'center', minWidth: withBars ? 100 : 80 }} title={t.help}>
          <div style={{ fontSize: withBars ? '2rem' : '1.6rem', fontWeight: 800, color: t.color }}>{t.getValue(ped)}%</div>
          <div style={{ fontSize: withBars ? '0.78rem' : '0.72rem', color: '#64748b', fontWeight: withBars ? 600 : 400, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.2rem' }}>
            {t.label}
            <i className="bi bi-info-circle" style={{ fontSize: '0.68rem', color: '#94a3b8', cursor: 'help' }}/>
          </div>
          {withBars && (
            <div style={{ marginTop: '0.35rem' }}><TauxBar value={t.getValue(ped)} small/></div>
          )}
        </div>
      ))}
    </div>
  )
}
