import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '../services/api'
import { fmtDuration, formatMoney } from '../components/FinanceStatsGrid'
import FinancePageShell, { FinanceNavActions } from '../components/finance/FinancePageShell'
import {
  buildFinanceListSearchParams,
  buildFinanceQuery,
  FINANCE_QUERY_STORAGE_KEY,
  loadFinancePeriod,
  readFinanceStateFromSearchParams,
  saveFinancePeriod,
} from '../utils/financePeriod'
import { usePersistedListQuery } from '../hooks/usePersistedListQuery'
import Pagination from '../components/Pagination'

const maxActivite = (items) => Math.max(...items.map((i) => Number(i.minutes_realisees || 0)), 1)

const SYNTHESE_PAGE_SIZE = 25

const KPI_GROUPS = [
  {
    title: 'Effectifs',
    iconClass: 'finance-kpi-card-icon--people',
    items: [
      { key: 'total_formateurs', label: 'Formateurs', icon: 'bi-person-video3' },
      { key: 'formateurs_actifs', label: 'Actifs', icon: 'bi-person-check' },
      { key: 'formateurs_inactifs', label: 'Inactifs', icon: 'bi-person-dash' },
    ],
  },
  {
    title: 'Séances',
    iconClass: 'finance-kpi-card-icon--sessions',
    items: [
      { key: 'total_sessions', label: 'Séances', icon: 'bi-calendar3' },
      { key: 'sessions_avec_pointage', label: 'Pointées', icon: 'bi-check2-square' },
    ],
  },
  {
    title: 'Temps',
    iconClass: 'finance-kpi-card-icon--time',
    items: [
      { key: 'total_duree_minutes', label: 'Planifié', format: 'duration', icon: 'bi-clock' },
      { key: 'total_duree_realisee_minutes', label: 'Réalisé', format: 'duration', icon: 'bi-clock-history' },
      { key: 'moyenne_heures_realisees_par_formateur', label: 'Moy. h / actif', format: 'hours', icon: 'bi-graph-up' },
    ],
  },
  {
    title: 'Rémunération',
    iconClass: 'finance-kpi-card-icon--money',
    items: [
      { key: 'prix_heure_realisee', label: 'Tarif / h', format: 'money', icon: 'bi-cash-coin' },
      { key: 'moyenne_montant_par_formateur_actif', label: 'Moy. / actif', format: 'money', icon: 'bi-wallet2' },
    ],
  },
]

function formatKpiValue(kpis, item) {
  const v = kpis[item.key]
  if (item.format === 'duration') return fmtDuration(v)
  if (item.format === 'money') return `${formatMoney(v)} FCFA`
  if (item.format === 'hours') return `${v ?? 0} h`
  return v ?? 0
}

function RankMedal({ idx }) {
  if (idx >= 3) return <span className="text-muted">{idx + 1}</span>
  return <span className={`finance-rank-medal finance-rank-medal--${idx + 1}`}>{idx + 1}</span>
}

function EvolutionBadge({ evolution, kpiKey, format }) {
  const ev = evolution?.[kpiKey]
  if (!ev) return null
  const delta = Number(ev.delta || 0)
  const pct = Number(ev.pourcent || 0)
  const up = delta > 0
  const down = delta < 0
  const cls = up ? 'finance-evolution--up' : down ? 'finance-evolution--down' : 'finance-evolution--flat'
  const sign = up ? '+' : ''
  const display = format === 'money'
    ? `${sign}${formatMoney(delta)} F`
    : format === 'duration'
      ? `${sign}${fmtDuration(Math.abs(delta))}`
      : `${sign}${delta}${format === 'pct' ? ' pts' : ''}`
  return (
    <span className={`finance-evolution ${cls}`} title={`vs période précédente (${pct >= 0 ? '+' : ''}${pct} %)`}>
      <i className={`bi bi-arrow-${up ? 'up' : down ? 'down' : 'right'}-short`}></i>
      {display}
    </span>
  )
}

export default function FinanceDashboard() {
  const [searchParams] = useSearchParams()
  const urlFinance = readFinanceStateFromSearchParams(searchParams)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [period, setPeriod] = useState(() => urlFinance?.period ?? loadFinancePeriod())
  const [appliedPeriod, setAppliedPeriod] = useState(() => urlFinance?.period ?? loadFinancePeriod())
  const [rankTab, setRankTab] = useState(() => searchParams.get('rank_tab') || 'realise')
  const [synthesePage, setSynthesePage] = useState(1)

  usePersistedListQuery(
    FINANCE_QUERY_STORAGE_KEY,
    () => buildFinanceListSearchParams(appliedPeriod, {}, { rankTab }),
    [appliedPeriod, rankTab],
  )

  const load = useCallback(async (p) => {
    setLoading(true)
    try {
      const qs = buildFinanceQuery(p).toString()
      const res = await api.get(`/formations/finance/dashboard/${qs ? `?${qs}` : ''}`)
      setData(res.data || null)
      setError('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Impossible de charger le dashboard finance.')
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(appliedPeriod)
  }, [appliedPeriod, load])

  useEffect(() => {
    setSynthesePage(1)
  }, [appliedPeriod])

  const handleApply = () => {
    saveFinancePeriod(period)
    setAppliedPeriod({ ...period })
    setSynthesePage(1)
  }

  const kpis = data?.kpis || {}
  const comparaison = data?.comparaison || null
  const evolution = comparaison?.evolution || null
  const periode = data?.periode || {}
  const activite = Array.isArray(data?.activite_par_mois) ? data.activite_par_mois : []
  const topPlanifie = Array.isArray(data?.top_formateurs) ? data.top_formateurs : []
  const topRealise = Array.isArray(data?.top_temps_realise) ? data.top_temps_realise : []
  const topMontants = Array.isArray(data?.top_montants) ? data.top_montants : []
  const specialites = Array.isArray(data?.repartition_specialites) ? data.repartition_specialites : []
  const synthese = Array.isArray(data?.synthese_formateurs) ? data.synthese_formateurs : []
  const syntheseTotalPages = Math.max(1, Math.ceil(synthese.length / SYNTHESE_PAGE_SIZE))
  const synthesePageSafe = Math.min(synthesePage, syntheseTotalPages)
  const synthesePageRows = useMemo(() => {
    const start = (synthesePageSafe - 1) * SYNTHESE_PAGE_SIZE
    return synthese.slice(start, start + SYNTHESE_PAGE_SIZE)
  }, [synthese, synthesePageSafe])
  const activiteMax = maxActivite(activite)

  const rankConfig = {
    planifie: { rows: topPlanifie, label: 'Temps planifié', fmt: (f) => fmtDuration(f.total_duree_minutes) },
    realise: { rows: topRealise, label: 'Temps réalisé', fmt: (f) => fmtDuration(f.total_duree_realisee_minutes) },
    montants: { rows: topMontants, label: 'Montant', fmt: (f) => `${formatMoney(f.montant_total_realise)} FCFA` },
  }
  const activeRank = rankConfig[rankTab] || rankConfig.realise

  return (
    <FinancePageShell
      title="Dashboard Finance"
      subtitle="Suivi des temps de cours et rémunération des formateurs"
      icon="bi-speedometer2"
      actions={<FinanceNavActions active="dashboard" />}
      period={period}
      onPeriodChange={setPeriod}
      onPeriodApply={handleApply}
      periodApplying={loading}
      periodeInfo={periode}
    >
      {error && <div className="error-message">{error}</div>}

      {loading ? (
        <div className="loading py-5"><div className="spinner"></div></div>
      ) : (
        <>
          <div className="finance-hero-kpis">
            <div className="finance-hero-kpi finance-hero-kpi--money">
              <div className="finance-hero-kpi-label">Masse salariale (période)</div>
              <div className="finance-hero-kpi-value">
                {formatMoney(kpis.total_montant_realise)} FCFA
                <EvolutionBadge evolution={evolution} kpiKey="total_montant_realise" format="money" />
              </div>
              <div className="finance-hero-kpi-sub">
                Tarif {formatMoney(kpis.prix_heure_realisee)} FCFA / h réalisée
                {comparaison && (
                  <span className="ms-2 opacity-75">
                    (préc. {formatMoney(comparaison.kpis?.total_montant_realise)} F)
                  </span>
                )}
              </div>
            </div>
            <div className="finance-hero-kpi finance-hero-kpi--time">
              <div className="finance-hero-kpi-label">Temps réalisé</div>
              <div className="finance-hero-kpi-value">
                {fmtDuration(kpis.total_duree_realisee_minutes)}
                <EvolutionBadge evolution={evolution} kpiKey="total_duree_realisee_minutes" format="duration" />
              </div>
              <div className="finance-hero-kpi-sub">
                Planifié : {fmtDuration(kpis.total_duree_minutes)}
              </div>
            </div>
            <div className="finance-hero-kpi finance-hero-kpi--rate">
              <div className="finance-hero-kpi-label">Taux de réalisation</div>
              <div className="finance-hero-kpi-value">
                {kpis.taux_realisation_global_pct ?? 0}%
                <EvolutionBadge evolution={evolution} kpiKey="taux_realisation_global_pct" format="pct" />
              </div>
              <div className="finance-hero-kpi-sub">
                {kpis.formateurs_actifs || 0} formateur(s) actif(s) sur la période
                {comparaison && (
                  <span className="ms-1 opacity-75">
                    (préc. {comparaison.kpis?.formateurs_actifs ?? 0})
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="finance-kpi-grid">
            {KPI_GROUPS.flatMap((g) =>
              g.items.map((item) => (
                <div className="finance-kpi-card" key={item.key}>
                  <div className={`finance-kpi-card-icon ${g.iconClass}`}>
                    <i className={`bi ${item.icon}`}></i>
                  </div>
                  <div>
                    <div className="finance-kpi-card-value">{formatKpiValue(kpis, item)}</div>
                    <div className="finance-kpi-card-label">{item.label}</div>
                  </div>
                </div>
              ))
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
            {activite.length > 0 && (
              <section className="finance-section">
                <div className="finance-section-header">
                  <h2><i className="bi bi-bar-chart-line"></i>Activité mensuelle</h2>
                </div>
                <div className="finance-section-body">
                  {activite.map((m) => (
                    <div className="finance-chart-row" key={m.mois}>
                      <span className="finance-chart-label">{m.label}</span>
                      <div className="finance-chart-bar-wrap">
                        <div
                          className="finance-chart-bar"
                          style={{ width: `${Math.min(100, (m.minutes_realisees / activiteMax) * 100)}%` }}
                        />
                      </div>
                      <span className="finance-chart-meta">
                        {fmtDuration(m.minutes_realisees)} · {formatMoney(m.montant)} F
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {specialites.length > 0 && (
              <section className="finance-section">
                <div className="finance-section-header">
                  <h2><i className="bi bi-pie-chart"></i>Spécialités</h2>
                </div>
                <div className="finance-section-body" style={{ padding: 0 }}>
                  <div className="finance-table-wrap">
                    <table className="finance-table">
                      <thead>
                        <tr><th>Spécialité</th><th>Formateurs</th></tr>
                      </thead>
                      <tbody>
                        {specialites.map((s) => (
                          <tr key={s.specialite}>
                            <td>{s.specialite}</td>
                            <td><span className="badge-bg-info">{s.count}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </section>
            )}
          </div>

          <section className="finance-section">
            <div className="finance-section-header">
              <h2><i className="bi bi-trophy"></i>Classement formateurs</h2>
            </div>
            <div className="finance-rank-tabs">
              {[
                { id: 'realise', label: 'Temps réalisé', icon: 'bi-clock-history' },
                { id: 'planifie', label: 'Temps planifié', icon: 'bi-clock' },
                { id: 'montants', label: 'Montants', icon: 'bi-cash-stack' },
              ].map((t) => (
                <button
                  key={t.id}
                  type="button"
                  className={`finance-rank-tab${rankTab === t.id ? ' active' : ''}`}
                  onClick={() => setRankTab(t.id)}
                >
                  <i className={`bi ${t.icon} me-1`}></i>{t.label}
                </button>
              ))}
            </div>
            <div className="finance-table-wrap">
              <table className="finance-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Formateur</th>
                    <th>Spécialité</th>
                    <th>Séances</th>
                    <th>{activeRank.label}</th>
                  </tr>
                </thead>
                <tbody>
                  {activeRank.rows.length > 0 ? activeRank.rows.map((f, idx) => (
                    <tr key={f.id}>
                      <td><RankMedal idx={idx} /></td>
                      <td>
                        <strong>{f.prenom} {f.nom}</strong>
                        <div className="text-muted small">{f.numerobadge || '—'}</div>
                      </td>
                      <td className="text-muted small">{f.specialite || '—'}</td>
                      <td><span className="badge-bg-secondary">{f.sessions_count || 0}</span></td>
                      <td><span className="badge-bg-success">{activeRank.fmt(f)}</span></td>
                    </tr>
                  )) : (
                    <tr>
                      <td colSpan="5">
                        <div className="finance-empty">
                          <i className="bi bi-inbox"></i>
                          Aucune donnée sur cette période
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section className="finance-section">
            <div className="finance-section-header">
              <h2><i className="bi bi-table"></i>Synthèse complète</h2>
              <span className="badge-bg-secondary">
                {synthese.length} formateur(s)
                {syntheseTotalPages > 1 && (
                  <> — page {synthesePageSafe} / {syntheseTotalPages}</>
                )}
              </span>
            </div>
            <div className="finance-table-wrap">
              <table className="finance-table">
                <thead>
                  <tr>
                    <th>N°</th>
                    <th>Nom</th>
                    <th>Prénom</th>
                    <th>Spécialité</th>
                    <th>Grade(s)</th>
                    <th>Groupe(s)</th>
                    <th>Mod.</th>
                    <th>Séances</th>
                    <th>Taux</th>
                    <th>Planifié</th>
                    <th>Réalisé</th>
                    <th>Montant</th>
                  </tr>
                </thead>
                <tbody>
                  {synthesePageRows.length > 0 ? synthesePageRows.map((f) => {
                    const st = f.statistiques || {}
                    const taux = st.taux_realisation_pct ?? 0
                    return (
                      <tr key={f.id}>
                        <td><span className="badge-bg-info">{f.numerobadge || '-'}</span></td>
                        <td><strong>{f.nom}</strong></td>
                        <td>{f.prenom}</td>
                        <td className="small text-muted">{f.specialite || '—'}</td>
                        <td className="small">{f.grades || '—'}</td>
                        <td className="small">{f.groupes || '—'}</td>
                        <td>{f.nb_formations ?? 0}</td>
                        <td>{f.sessions_count ?? 0}</td>
                        <td>
                          <div>{taux}%</div>
                          <div className="finance-taux-bar">
                            <div className="finance-taux-bar-fill" style={{ width: `${Math.min(100, taux)}%` }} />
                          </div>
                        </td>
                        <td style={{ whiteSpace: 'nowrap' }}>{fmtDuration(f.total_duree_minutes)}</td>
                        <td style={{ whiteSpace: 'nowrap' }}>{fmtDuration(f.total_duree_realisee_minutes)}</td>
                        <td style={{ whiteSpace: 'nowrap', fontWeight: 700, color: 'var(--fin-green)' }}>
                          {formatMoney(f.montant_total_realise)} F
                        </td>
                      </tr>
                    )
                  }) : (
                    <tr>
                      <td colSpan="12">
                        <div className="finance-empty"><i className="bi bi-inbox"></i>Aucun formateur</div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="finance-section-footer">
              <Pagination
                page={synthesePageSafe}
                totalPages={syntheseTotalPages}
                onPageChange={setSynthesePage}
                totalItems={synthese.length}
                pageSize={SYNTHESE_PAGE_SIZE}
                activeClassName="pagination-num--active pagination-num--finance"
              />
            </div>
          </section>

          {data?.generated_at && (
            <p className="text-muted small text-end">
              Actualisé le {new Date(data.generated_at).toLocaleString('fr-FR')}
            </p>
          )}
        </>
      )}
    </FinancePageShell>
  )
}
