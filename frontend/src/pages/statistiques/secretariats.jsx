/**
 * secretariats.jsx — Statistiques (INJS-LMD 2026)
 *
 * Panneau « Secrétariats » : tableau comparatif et détail d'un secrétariat.
 *
 * Extrait de `pages/Statistiques.jsx` (réduction des fichiers géants,
 * garde-fou G.1). Les données arrivent par props : aucun appel réseau.
 */
import { AuditeursNotoiresPanel } from '../../components/AuditeursNotoiresPanel'
import { fmtHeures } from '../../components/FinanceStatsGrid'
import { Card, Kpi, TauxBar } from './composants'
import { AUDITEURS_NOTOIRES, C, STATUT_LABELS, TAUX_PEDAGOGIE } from './constantes'
import { Bars, Donut, Empty, HBars } from './graphiques'

const SEC_TABLE_HEADERS = [
  'N°', 'Secrétariat', 'Responsable', 'Modules', 'Étudiants', 'Enseignants', 'Séances',
  'Inscrits', 'Présents', 'Assiduité séance', 'Absences', 'Abs. notoires', 'Vol.H. prévu', 'Avancement VH', 'Hommes', 'Femmes', '',
]

export function SecretariatsComparatifTable({ secretariats, onRowClick }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
        <thead>
          <tr style={{ background: '#f8fafc', borderBottom: '2px solid #e2e8f0' }}>
            {SEC_TABLE_HEADERS.map(h => (
              <th
                key={h}
                style={{
                  padding: '0.5rem 0.65rem', color: '#64748b', fontWeight: 600,
                  textAlign: h === 'Secrétariat' || h === 'Responsable' ? 'left' : 'center',
                  whiteSpace: 'nowrap',
                }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {secretariats.map((s, i) => (
            <tr
              key={s.secretariat_id}
              style={{ borderBottom: '1px solid #f1f5f9', cursor: onRowClick ? 'pointer' : undefined }}
              onMouseEnter={onRowClick ? e => { e.currentTarget.style.background = '#e8eef6' } : undefined}
              onMouseLeave={onRowClick ? e => { e.currentTarget.style.background = '' } : undefined}
              onClick={onRowClick ? () => onRowClick(i) : undefined}
            >
              <td style={{ padding: '0.45rem 0.65rem', color: '#94a3b8', textAlign: 'center' }}>{s.numero}</td>
              <td style={{ padding: '0.45rem 0.65rem', color: '#1e293b', fontWeight: 600, whiteSpace: 'nowrap' }}>
                <i className="bi bi-building me-1" style={{ color: C[i % C.length] }}/>
                {s.secretariat}
              </td>
              <td style={{ padding: '0.45rem 0.65rem', color: '#64748b', whiteSpace: 'nowrap' }}>{s.responsable || '—'}</td>
              <td style={{ textAlign: 'center', padding: '0.45rem 0.65rem', color: '#2277C1', fontWeight: 700 }}>{s.nb_modules}</td>
              <td style={{ textAlign: 'center', padding: '0.45rem 0.65rem', color: '#F5B100', fontWeight: 700 }}>{s.nb_participants}</td>
              <td style={{ textAlign: 'center', padding: '0.45rem 0.65rem', color: '#7B1FA2', fontWeight: 700 }}>{s.nb_formateurs}</td>
              <td style={{ textAlign: 'center', padding: '0.45rem 0.65rem', color: '#00838F', fontWeight: 700 }}>{s.nb_sessions}</td>
              <td style={{ textAlign: 'center', padding: '0.45rem 0.65rem', color: '#64748b' }}>{s.nb_inscrits}</td>
              <td style={{ textAlign: 'center', padding: '0.45rem 0.65rem', color: '#2277C1', fontWeight: 600 }}>{s.nb_presents}</td>
              <td style={{ padding: '0.45rem 0.65rem', minWidth: 110 }}><TauxBar value={s.taux_presence} small/></td>
              <td style={{ textAlign: 'center', padding: '0.45rem 0.65rem', color: '#C62828', fontWeight: 600 }}>{s.nb_absences}</td>
              <td style={{ textAlign: 'center', padding: '0.45rem 0.65rem', color: '#C62828', fontWeight: 700 }} title={`${Number(s.pct_auditeurs_notoires || 0).toFixed(1)}% des inscrits`}>
                {s.nb_auditeurs_notoires ?? 0}
              </td>
              <td style={{ textAlign: 'center', padding: '0.45rem 0.65rem', color: '#0F70AB' }}>{fmtHeures(s.vh_prevu)}h</td>
              <td style={{ padding: '0.45rem 0.65rem', minWidth: 80 }}><TauxBar value={s.taux_execution_vh} small/></td>
              <td style={{ textAlign: 'center', padding: '0.45rem 0.65rem', color: '#1565C0' }}>{s.ratio_hf.hommes}</td>
              <td style={{ textAlign: 'center', padding: '0.45rem 0.65rem', color: '#AD1457' }}>{s.ratio_hf.femmes}</td>
              <td style={{ padding: '0.45rem 0.65rem', textAlign: 'center' }}>
                {onRowClick && <i className="bi bi-arrow-right-circle" style={{ color: 'var(--navy)' }} title="Voir le détail"/>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function SecretariatsEnsemblePanel({ secStats, onSelectIndividuel }) {
  const { secretariats } = secStats
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
          <i className="bi bi-building me-2" style={{ color: 'var(--navy)' }}/>
          {secStats.total} secrétariat{secStats.total > 1 ? 's' : ''} — vue d&apos;ensemble
        </h3>
        <p style={{ margin: '0.35rem 0 0', fontSize: '0.78rem', color: '#64748b' }}>
          Comparaison de tous les secrétariats (effectifs, présences, pointages).
          Cliquez sur une ligne ou choisissez un secrétariat dans le panneau de gauche pour le détail.
        </p>
      </div>
      <div style={{ maxHeight: '62vh', overflowY: 'auto', padding: '1rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(160px,1fr))', gap: '0.8rem', marginBottom: '1.2rem' }}>
          <Kpi icon="bi-building" label="Secrétariats" value={secStats.total} color="#1565C0"/>
          <Kpi icon="bi-people" label="Étudiants total" value={secretariats.reduce((s, r) => s + r.nb_participants, 0)} color="#F5B100"/>
          <Kpi icon="bi-book" label="Modules total" value={secretariats.reduce((s, r) => s + r.nb_modules, 0)} color="#2277C1"/>
          <Kpi icon="bi-qr-code-scan" label="Pointages total" value={secretariats.reduce((s, r) => s + r.nb_pointages, 0)} color="#C62828"/>
          <Kpi icon="bi-person-x-fill" label="Absents notoires" value={secStats.auditeurs_notoires?.total ?? secretariats.reduce((s, r) => s + (r.nb_auditeurs_notoires || 0), 0)} color="#C62828"
            sub={secStats.auditeurs_notoires ? `${Number(secStats.auditeurs_notoires.pct || 0).toFixed(1).replace('.', ',')}% des inscrits` : undefined}/>
        </div>

        <div style={{ background: '#fff', borderRadius: 10, border: '1px solid #e2e8f0', overflow: 'hidden', marginBottom: '1.2rem' }}>
          <SecretariatsComparatifTable secretariats={secretariats} onRowClick={onSelectIndividuel}/>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(320px,1fr))', gap: '1rem' }}>
          <Card title="Étudiants par secrétariat" icon="bi-people">
            <HBars data={secretariats.map(s => ({ label: s.secretariat, value: s.nb_participants }))} labelKey="label" valueKey="value"/>
          </Card>
          <Card title="Modules par secrétariat" icon="bi-book">
            <Bars data={secretariats.map(s => ({ label: s.secretariat, value: s.nb_modules }))} labelKey="label" valueKey="value" color="#2277C1"/>
          </Card>
          <Card title={`${TAUX_PEDAGOGIE.assiduite.label} par secrétariat`} icon="bi-percent">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
              {secretariats.map((s, i) => (
                <div key={s.secretariat_id}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.79rem', marginBottom: '0.18rem' }}>
                    <span style={{ color: '#334155', fontWeight: 600 }}>
                      <i className="bi bi-building me-1" style={{ color: C[i % C.length] }}/>
                      {s.secretariat}
                    </span>
                    <span style={{ color: '#64748b' }}>{s.nb_inscrits} inscrits · {s.nb_presents} présents</span>
                  </div>
                  <TauxBar value={s.taux_presence} small/>
                </div>
              ))}
            </div>
          </Card>
          <Card title="Pointages par secrétariat" icon="bi-qr-code-scan">
            <Bars data={secretariats.map(s => ({ label: s.secretariat, value: s.nb_pointages }))} labelKey="label" valueKey="value" color="#C62828"/>
          </Card>
          <Card title="Absences par secrétariat" icon="bi-x-circle">
            <HBars data={secretariats.map(s => ({ label: s.secretariat, value: s.nb_absences }))} labelKey="label" valueKey="value"/>
          </Card>
        </div>

        <div style={{ marginTop: '1rem' }}>
          <Card title={AUDITEURS_NOTOIRES.cardTitle} icon="bi-person-x-fill" col="1/-1">
            <AuditeursNotoiresPanel data={secStats.auditeurs_notoires} maxHeight={360}/>
          </Card>
        </div>
      </div>
    </div>
  )
}

export function SecretariatDetailPanel({ row, detail }) {
  const kpis = detail?.kpis || {}
  const pedagogiques = detail?.pedagogiques || {}
  const adm = detail?.admin_operationnel || {}

  return (
    <div style={{
      background: '#fff', borderRadius: 10, boxShadow: '0 1px 4px rgba(0,0,0,0.07)',
      overflow: 'hidden', minWidth: 0, padding: '1rem',
    }}>
      <div style={{
        padding: '0.65rem 0.85rem', margin: '-1rem -1rem 1rem', background: 'linear-gradient(135deg, #e8eef6 0%, #d4deec 100%)',
        borderBottom: '1px solid #e2e8f0',
      }}>
        <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 800, color: '#1e293b' }}>
          <i className="bi bi-building me-2" style={{ color: '#1565C0' }}/>
          {row?.secretariat || 'Secrétariat'}
        </h3>
        {row?.responsable && (
          <p style={{ margin: '0.25rem 0 0', fontSize: '0.78rem', color: '#64748b' }}>
            Responsable : {row.responsable}
          </p>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(160px,1fr))', gap: '0.8rem', marginBottom: '1.1rem' }}>
        <Kpi icon="bi-book" label="Modules" value={kpis.modules} color="#2277C1"/>
        <Kpi icon="bi-people" label="Étudiants" value={kpis.participants} color="#F5B100"/>
        <Kpi icon="bi-person-video3" label="Enseignants" value={kpis.formateurs} color="#7B1FA2"/>
        <Kpi icon="bi-calendar-event" label="Séances" value={kpis.sessions_total} color="#00838F"/>
        <Kpi icon="bi-qr-code-scan" label="Pointages" value={kpis.pointages} color="#C62828"/>
        <Kpi icon="bi-percent" label={TAUX_PEDAGOGIE.assiduite.label} value={`${pedagogiques.taux_presence}%`} color="#2277C1" help={TAUX_PEDAGOGIE.assiduite.help}/>
        <Kpi icon="bi-percent" label="Taux absence" value={`${pedagogiques.taux_absence}%`} color="#C62828"/>
        <Kpi icon="bi-person-x-fill" label="Absents notoires" value={adm.auditeurs_notoires?.total ?? 0} color="#C62828"
          sub={adm.auditeurs_notoires ? `${Number(adm.auditeurs_notoires.pct || 0).toFixed(1).replace('.', ',')}% des inscrits` : undefined}/>
        <Kpi icon="bi-clock-history" label="Vol. horaire prévu" value={`${fmtHeures(kpis.vh_prevu_heures)}h`} color="#0F70AB"/>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(320px,1fr))', gap: '1rem' }}>
        <Card title="Pointages par statut" icon="bi-pie-chart">
          <Donut data={(adm.pointages_par_statut || []).map(d => ({ ...d, label: STATUT_LABELS[d.statut] || d.statut }))} labelKey="label" valueKey="total"/>
        </Card>
        <Card title="Répartition Hommes / Femmes" icon="bi-gender-ambiguous">
          <Donut data={adm.participants_par_sexe} labelKey="sexe" valueKey="total"/>
        </Card>
        <Card title="Assiduité séance par formation" icon="bi-building">
          {pedagogiques.taux_par_formation?.length
            ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {pedagogiques.taux_par_formation.map((r, i) => (
                  <div key={i}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '0.15rem' }}>
                      <span style={{ color: '#334155', fontWeight: 500, maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.formation}</span>
                      <span style={{ color: '#64748b' }}>{r.inscrits} inscrits</span>
                    </div>
                    <TauxBar value={r.taux} small/>
                  </div>
                ))}
              </div>
            )
            : <Empty label="Aucune formation pour ce secrétariat"/>}
        </Card>
        <Card title="Étudiants par catégorie" icon="bi-bar-chart-steps">
          <HBars data={(adm.participants_par_categorie || []).map(d => ({ ...d, categorie: d.categorie || 'Non rens.' }))} labelKey="categorie" valueKey="total"/>
        </Card>
        <Card title="Taux par grade" icon="bi-award">
          {pedagogiques.taux_par_grade?.length
            ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                {pedagogiques.taux_par_grade.map((r, i) => (
                  <div key={i}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '0.12rem' }}>
                      <b style={{ color: '#334155' }}>{r.grade}</b>
                      <span style={{ color: '#64748b' }}>{r.inscrits} inscrits</span>
                    </div>
                    <TauxBar value={r.taux} small/>
                  </div>
                ))}
              </div>
            )
            : <Empty label="Aucun grade renseigné"/>}
        </Card>
        <Card title="Charge des enseignants" icon="bi-person-video3">
          <HBars data={adm.charge_formateurs} labelKey="nom" valueKey="nb_sessions"/>
        </Card>
      </div>

      <div style={{ marginTop: '1rem' }}>
        <Card title={AUDITEURS_NOTOIRES.cardTitle} icon="bi-person-x-fill" col="1/-1">
          <AuditeursNotoiresPanel data={adm.auditeurs_notoires} maxHeight={360}/>
        </Card>
      </div>
    </div>
  )
}
