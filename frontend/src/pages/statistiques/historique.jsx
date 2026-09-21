/**
 * historique.jsx — Statistiques (INJS-LMD 2026)
 *
 * Panneau « Historique » : tendances mensuelles et détail d'un mois.
 *
 * Extrait de `pages/Statistiques.jsx` (réduction des fichiers géants,
 * garde-fou G.1). Les données arrivent par props : aucun appel réseau.
 */
import { AuditeursNotoiresKpiStrip, AuditeursNotoiresPanel } from '../../components/AuditeursNotoiresPanel'
import { Card, Kpi, MonthTrendChart, StackedPresenceChart } from './composants'
import { AUDITEURS_NOTOIRES, TAUX_PEDAGOGIE } from './constantes'
import { TrendBadge, formatMoisLabelLong } from './graphiques'

export function HistoriqueEnsemblePanel({ historique, onSelectMois, auditeursNotoires }) {
  const { resume } = historique
  return (
    <div style={{
      background: '#fff', borderRadius: 10, boxShadow: '0 1px 4px rgba(0,0,0,0.07)',
      overflow: 'hidden', minWidth: 0,
    }}>
      <div style={{
        padding: '0.85rem 1rem', background: 'linear-gradient(135deg, #e8eef6 0%, #d4deec 100%)',
        borderBottom: '1px solid #e2e8f0', position: 'sticky', top: 0, zIndex: 2,
      }}>
        <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 800, color: '#1e293b' }}>
          <i className="bi bi-graph-up me-2" style={{ color: 'var(--navy)' }}/>
          Historique — 12 derniers mois
        </h3>
        <p style={{ margin: '0.35rem 0 0', fontSize: '0.78rem', color: '#64748b' }}>
          Vue d&apos;ensemble des tendances (pointages, présences, séances, modules).
          Choisissez un mois dans le panneau de gauche pour le détail mensuel.
        </p>
      </div>
      <div style={{ maxHeight: '62vh', overflowY: 'auto', padding: '1rem' }}>
        {resume && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(180px,1fr))', gap: '0.8rem', marginBottom: '1rem' }}>
            <Kpi icon="bi-qr-code-scan" label="Pointages (12 mois)" value={resume.total_pointages}
              sub={`Moy. ${resume.moy_pointages_mois}/mois actif`} color="#C62828"/>
            <Kpi icon="bi-calendar-event" label="Séances (12 mois)" value={resume.total_sessions}
              sub={resume.sessions_mois_courant != null ? `${resume.sessions_mois_courant} ce mois` : undefined} color="#1565C0"/>
            <Kpi icon="bi-percent" label={`${TAUX_PEDAGOGIE.assiduite.label} moyen`} value={`${resume.moy_taux_presence}%`} color="#2277C1" help={TAUX_PEDAGOGIE.assiduite.help}/>
            <Kpi icon="bi-book" label="Modules actifs" value={resume.modules_actifs_dernier_mois}
              sub="Dernier mois avec séances" color="#7B1FA2"/>
            <Kpi icon="bi-graph-up-arrow" label="Pointages ce mois" value={resume.pointages_mois_courant}
              sub={<TrendBadge pct={resume.variation_pointages_pct}/>} color="#F5B100"/>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(320px,1fr))', gap: '1rem' }}>
          <Card title="Pointages par mois — présents vs absents" icon="bi-people-fill">
            <StackedPresenceChart data={historique.pointages_par_mois}/>
          </Card>
          <Card title="Volume de pointages (12 mois)" icon="bi-graph-up">
            <MonthTrendChart data={historique.pointages_par_mois} valueKey="total" color="#C62828"/>
          </Card>
          <Card title={`${TAUX_PEDAGOGIE.assiduite.label} mensuel`} icon="bi-percent">
            <MonthTrendChart data={historique.taux_presence_par_mois} valueKey="total" color="#2277C1" unit="%"/>
            <p style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '0.5rem', marginBottom: 0 }}>
              Calculé sur présents / (présents + absents) par mois.
            </p>
          </Card>
          <Card title="Séances par mois" icon="bi-calendar-week">
            <MonthTrendChart data={historique.sessions_par_mois} valueKey="total" color="#1565C0"/>
          </Card>
          <Card title="Modules — créations et activité" icon="bi-graph-up-arrow">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <p style={{ fontSize: '0.78rem', fontWeight: 600, color: '#64748b', marginBottom: '0.4rem' }}>Nouveaux modules</p>
                <MonthTrendChart data={historique.modules_par_mois} valueKey="total" color="#2277C1" height={130}/>
              </div>
              <div>
                <p style={{ fontSize: '0.78rem', fontWeight: 600, color: '#64748b', marginBottom: '0.4rem' }}>Modules actifs</p>
                <MonthTrendChart data={historique.modules_par_mois} valueKey="actifs" color="#7B1FA2" height={130}/>
              </div>
            </div>
            <p style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '0.5rem', marginBottom: 0 }}>
              Stock cumulé : <b>{historique.modules_par_mois?.slice(-1)[0]?.cumul ?? '—'}</b> modules.
            </p>
          </Card>
        </div>

        <div style={{ marginTop: '1rem' }}>
          <Card title={AUDITEURS_NOTOIRES.cardTitle} icon="bi-person-x-fill" col="1/-1">
            <AuditeursNotoiresPanel data={auditeursNotoires} maxHeight={320}/>
          </Card>
        </div>

        {onSelectMois && (
          <div style={{ marginTop: '1rem', padding: '0.75rem', background: '#f8fafc', borderRadius: 8, fontSize: '0.76rem', color: '#64748b' }}>
            <i className="bi bi-info-circle me-1"/>
            Cliquez sur un mois à gauche pour afficher les indicateurs détaillés de ce mois.
          </div>
        )}
      </div>
    </div>
  )
}

export function HistoriqueMoisPanel({ historique, monthIndex, auditeursNotoires }) {
  const pt = historique.pointages_par_mois[monthIndex]
  const taux = historique.taux_presence_par_mois[monthIndex]
  const sess = historique.sessions_par_mois[monthIndex]
  const mod = historique.modules_par_mois[monthIndex]
  const prevPt = monthIndex > 0 ? historique.pointages_par_mois[monthIndex - 1] : null
  const varPt = prevPt && prevPt.total > 0
    ? Math.round(((pt.total - prevPt.total) / prevPt.total) * 1000) / 10
    : (pt.total > 0 && !prevPt?.total ? 100 : null)
  const winStart = Math.max(0, monthIndex - 2)
  const windowSlice = (arr) => arr.slice(winStart, monthIndex + 1)

  return (
    <div style={{
      background: '#fff', borderRadius: 10, boxShadow: '0 1px 4px rgba(0,0,0,0.07)',
      overflow: 'hidden', minWidth: 0, padding: '1rem',
    }}>
      <div style={{
        padding: '0.65rem 0.85rem', margin: '-1rem -1rem 1rem',
        background: 'linear-gradient(135deg, #e8eef6 0%, #d4deec 100%)',
        borderBottom: '1px solid #e2e8f0',
      }}>
        <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 800, color: '#1e293b' }}>
          <i className="bi bi-calendar3 me-2" style={{ color: '#1565C0' }}/>
          {formatMoisLabelLong(pt.mois)}
        </h3>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(150px,1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
        <Kpi icon="bi-qr-code-scan" label="Pointages" value={pt.total} color="#C62828"
          sub={varPt != null ? <TrendBadge pct={varPt}/> : undefined}/>
        <Kpi icon="bi-person-check" label="Présents" value={pt.presents ?? 0} color="#2277C1"/>
        <Kpi icon="bi-person-x" label="Absents" value={pt.absents ?? 0} color="#C62828"/>
        <Kpi icon="bi-percent" label={TAUX_PEDAGOGIE.assiduite.label} value={`${Number(taux?.total || 0).toFixed(1)}%`} color="#2277C1" help={TAUX_PEDAGOGIE.assiduite.help}/>
        <Kpi icon="bi-calendar-event" label="Séances" value={sess?.total ?? 0} color="#1565C0"/>
        <Kpi icon="bi-book" label="Modules créés" value={mod?.total ?? 0} color="#7B1FA2"/>
        <Kpi icon="bi-book-half" label="Modules actifs" value={mod?.actifs ?? 0} color="#0F70AB"/>
        <Kpi icon="bi-layers" label="Stock modules" value={mod?.cumul ?? '—'} color="#64748b"/>
      </div>

      <AuditeursNotoiresKpiStrip data={auditeursNotoires}/>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(280px,1fr))', gap: '1rem' }}>
        <Card title="Présents vs absents (ce mois)" icon="bi-people-fill">
          <StackedPresenceChart data={[pt]} height={140}/>
        </Card>
        <Card title={`Contexte — ${windowSlice(historique.pointages_par_mois).length} mois`} icon="bi-graph-up">
          <MonthTrendChart data={windowSlice(historique.pointages_par_mois)} valueKey="total" color="#C62828" height={140}/>
        </Card>
        <Card title={`${TAUX_PEDAGOGIE.assiduite.label} (contexte)`} icon="bi-percent">
          <MonthTrendChart data={windowSlice(historique.taux_presence_par_mois)} valueKey="total" color="#2277C1" unit="%" height={140}/>
        </Card>
        <Card title="Séances (contexte)" icon="bi-calendar-week">
          <MonthTrendChart data={windowSlice(historique.sessions_par_mois)} valueKey="total" color="#1565C0" height={140}/>
        </Card>
      </div>
    </div>
  )
}
