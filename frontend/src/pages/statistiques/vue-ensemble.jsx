/**
 * vue-ensemble.jsx — Statistiques (INJS-LMD 2026)
 *
 * Panneau « Vue d'ensemble » : synthèse riche par sections et navigation
 * vers le détail d'une section.
 *
 * Extrait de `pages/Statistiques.jsx` (réduction des fichiers géants,
 * garde-fou G.1). Les données arrivent par props : aucun appel réseau.
 */
import { AuditeursNotoiresPanel } from '../../components/AuditeursNotoiresPanel'
import { fmtHeures } from '../../components/FinanceStatsGrid'
import { AlertesOverviewBandeau, IndicateurSurveillanceCard } from './alertes'
import { Card, Kpi } from './composants'
import { PedagogieTauxGrille, PedagogieTauxPrincipaux } from './taux-pedagogie'
import { ALERTES_OVERVIEW_CODES, AUDITEURS_NOTOIRES, KPI_PERIOD_SCOPE_HELP, KPI_SESSIONS_COMPT, KPI_SESSIONS_TOTAL, KPI_VH_EXEC, TAUX_PEDAGOGIE } from './constantes'
import { Donut, Empty, HBars } from './graphiques'

const OVERVIEW_SECTION_DEFS = [
  { id: 'alertes', tag: 'ALT', tagColor: '#C62828', label: 'Surveillance', icon: 'bi-bell' },
  { id: 'kpis', tag: 'KPI', tagColor: '#1565C0', label: 'Chiffres clés', icon: 'bi-speedometer2' },
  { id: 'pedagogie', tag: 'PED', tagColor: '#2277C1', label: 'Pédagogique', icon: 'bi-mortarboard' },
  { id: 'operationnel', tag: 'OPE', tagColor: '#7B1FA2', label: 'Opérationnel', icon: 'bi-gear' },
]

export function buildOverviewSections(alertesItems) {
  const actives = (alertesItems || []).filter(
    a => ALERTES_OVERVIEW_CODES.includes(a.indicateur)
      && (a.niveau === 'critique' || a.niveau === 'avertissement'),
  )
  const crit = actives.filter(a => a.niveau === 'critique').length
  const avert = actives.filter(a => a.niveau === 'avertissement').length
  const alertesSub = actives.length
    ? `${actives.length} alerte${actives.length > 1 ? 's' : ''} (${crit} crit. · ${avert} avert.)`
    : 'Aucune alerte active'

  return OVERVIEW_SECTION_DEFS.map(def => ({
    ...def,
    sub: def.id === 'alertes' ? alertesSub
      : def.id === 'kpis' ? 'Formations, modules, étudiants, séances…'
      : def.id === 'pedagogie' ? 'Assiduité séance, couverture étudiants, absences'
      : def.id === 'operationnel' ? 'Répartition H/F, charge enseignants, absents notoires'
      : '',
  }))
}

export function VueEnsemblePanel({ kpis, periode, loading, pedagogiques, adm, alertesOverview, onSelectSection, auditeursNotoires }) {
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
          <i className="bi bi-speedometer2 me-2" style={{ color: 'var(--navy)' }}/>
          Vue d&apos;ensemble — synthèse
        </h3>
        <p style={{ margin: '0.35rem 0 0', fontSize: '0.78rem', color: '#64748b' }}>
          Indicateurs clés, surveillance et graphiques opérationnels.
          Choisissez une section à gauche pour le focus détaillé.
        </p>
        {periode?.label && (
          <div className="finance-period-badge" style={{ marginTop: '0.55rem' }}>
            <i className="bi bi-calendar-check"/>
            <div>
              <strong>Données filtrées : {periode.label}</strong>
              {periode.periode_label && (
                <span className="ms-1">— {periode.periode_label}</span>
              )}
            </div>
          </div>
        )}
      </div>
      <div style={{ maxHeight: '62vh', overflowY: 'auto', padding: '1rem', position: 'relative' }}>
        {loading && !kpis && (
          <div style={{
            position: 'absolute', inset: 0, zIndex: 3, background: 'rgba(255,255,255,0.85)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem',
            color: '#64748b', fontSize: '0.85rem',
          }}>
            <div className="spinner"/>Mise à jour des indicateurs…
          </div>
        )}
        <div
          style={{ marginBottom: '1rem', cursor: onSelectSection ? 'pointer' : undefined }}
          onClick={onSelectSection ? () => onSelectSection('alertes') : undefined}
          role={onSelectSection ? 'button' : undefined}
        >
          <AlertesOverviewBandeau items={alertesOverview} />
        </div>

        <div
          style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(175px,1fr))', gap: '0.85rem', marginBottom: '1.2rem' }}
          onClick={onSelectSection ? () => onSelectSection('kpis') : undefined}
          role={onSelectSection ? 'button' : undefined}
        >
          <Kpi icon="bi-journal-bookmark" label="Formations" value={kpis.formations} color="#1565C0" help={KPI_PERIOD_SCOPE_HELP}/>
          <Kpi icon="bi-book" label="Modules" value={kpis.modules} color="#2277C1" help={KPI_PERIOD_SCOPE_HELP}/>
          <Kpi icon="bi-people" label="Étudiants" value={kpis.participants} color="#F5B100" help={KPI_PERIOD_SCOPE_HELP}/>
          <Kpi icon="bi-person-video3" label="Enseignants" value={kpis.formateurs} color="#7B1FA2" help={KPI_PERIOD_SCOPE_HELP}/>
          <Kpi icon="bi-calendar-event" label={KPI_SESSIONS_TOTAL.label} value={kpis.sessions_total} color="#00838F"
            help={KPI_SESSIONS_TOTAL.help}/>
          <Kpi icon="bi-calendar-check" label={KPI_SESSIONS_COMPT.label} value={kpis.sessions_terminees} color="#082961"
            help={KPI_SESSIONS_COMPT.help}/>
          <Kpi icon="bi-clock-history" label="Vol. horaire prévu" value={`${fmtHeures(kpis.vh_prevu_heures)}h`} color="#0F70AB"/>
          <Kpi icon="bi-check2-all" label={KPI_VH_EXEC.label} value={`${kpis.taux_execution_vh}%`}
            color={kpis.taux_execution_vh >= 70 ? '#2277C1' : kpis.taux_execution_vh >= 40 ? '#F5B100' : '#C62828'}
            help={KPI_VH_EXEC.help}/>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '1rem', alignItems: 'start' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div onClick={onSelectSection ? () => onSelectSection('pedagogie') : undefined} role={onSelectSection ? 'button' : undefined} style={{ cursor: onSelectSection ? 'pointer' : undefined }}>
              <Card title="Indicateurs pédagogiques" icon="bi-pie-chart">
                <PedagogieTauxPrincipaux ped={pedagogiques} auditeursNotoires={auditeursNotoires}/>
              </Card>
            </div>
            <div onClick={onSelectSection ? () => onSelectSection('operationnel') : undefined} role={onSelectSection ? 'button' : undefined} style={{ cursor: onSelectSection ? 'pointer' : undefined }}>
              <Card title="Charge des enseignants (top 8)" icon="bi-trophy">
                <HBars data={adm.charge_formateurs} labelKey="nom" valueKey="nb_sessions"/>
              </Card>
            </div>
          </div>

          <div onClick={onSelectSection ? () => onSelectSection('operationnel') : undefined} role={onSelectSection ? 'button' : undefined} style={{ cursor: onSelectSection ? 'pointer' : undefined }}>
            <Card title="Répartition Hommes / Femmes" icon="bi-gender-ambiguous">
              <Donut data={adm.participants_par_sexe} labelKey="sexe" valueKey="total"/>
              <div style={{ marginTop: '1rem', paddingTop: '0.85rem', borderTop: '1px solid #e2e8f0' }}>
                <p style={{ fontSize: '0.72rem', fontWeight: 600, color: '#64748b', marginBottom: '0.65rem', textAlign: 'center' }}>
                  Taux pédagogiques
                </p>
                <PedagogieTauxGrille ped={pedagogiques} grid/>
              </div>
            </Card>
          </div>
        </div>

        <div style={{ marginTop: '1rem' }}>
          <Card title={AUDITEURS_NOTOIRES.cardTitle} icon="bi-person-x-fill" col="1/-1">
            <AuditeursNotoiresPanel data={auditeursNotoires}/>
          </Card>
        </div>
      </div>
    </div>
  )
}

export function VueOverviewDetailPanel({
  sectionId, kpis, periode, pedagogiques, adm, alertesOverview, onGoAlertes, onGoPedagogie, onGoAdmin, auditeursNotoires,
}) {
  const section = OVERVIEW_SECTION_DEFS.find(s => s.id === sectionId)
  const header = (
    <div style={{
      padding: '0.65rem 0.85rem', margin: '-1rem -1rem 1rem',
      background: 'linear-gradient(135deg, #e8eef6 0%, #d4deec 100%)',
      borderBottom: '1px solid #e2e8f0',
    }}>
      <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 800, color: '#1e293b' }}>
        <i className={`bi ${section?.icon || 'bi-speedometer2'} me-2`} style={{ color: section?.tagColor || '#2277C1' }}/>
        {section?.label || sectionId}
      </h3>
      {periode?.label && (
        <p style={{ margin: '0.35rem 0 0', fontSize: '0.75rem', color: '#64748b' }}>
          <i className="bi bi-calendar-check me-1"/>
          {periode.label}{periode.periode_label ? ` — ${periode.periode_label}` : ''}
        </p>
      )}
    </div>
  )

  if (sectionId === 'alertes') {
    const indicateurs = (alertesOverview || []).filter(a => ALERTES_OVERVIEW_CODES.includes(a.indicateur))
    return (
      <div style={{ background: '#fff', borderRadius: 10, boxShadow: '0 1px 4px rgba(0,0,0,0.07)', padding: '1rem', minWidth: 0 }}>
        {header}
        {indicateurs.length ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(300px,1fr))', gap: '0.85rem', marginBottom: '1rem' }}>
            {indicateurs.map((ind, i) => (
              <div key={ind.indicateur} style={{ animationDelay: `${i * 0.05}s` }}>
                <IndicateurSurveillanceCard ind={ind}/>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '1.5rem', color: '#64748b', fontSize: '0.85rem' }}>
            <i className="bi bi-check-circle" style={{ fontSize: '2rem', color: '#2277C1', display: 'block', marginBottom: '0.5rem' }}/>
            Aucune alerte active sur les 3 indicateurs clés.
          </div>
        )}
        {onGoAlertes && (
          <button type="button" className="btn btn-sm btn-outline-success" onClick={onGoAlertes}>
            <i className="bi bi-bell me-1"/>Configurer et voir toutes les alertes
          </button>
        )}
      </div>
    )
  }

  if (sectionId === 'kpis') {
    return (
      <div style={{ background: '#fff', borderRadius: 10, boxShadow: '0 1px 4px rgba(0,0,0,0.07)', padding: '1rem', minWidth: 0 }}>
        {header}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(175px,1fr))', gap: '0.85rem' }}>
          <Kpi icon="bi-journal-bookmark" label="Formations" value={kpis.formations} color="#1565C0" help={KPI_PERIOD_SCOPE_HELP}/>
          <Kpi icon="bi-book" label="Modules" value={kpis.modules} color="#2277C1" help={KPI_PERIOD_SCOPE_HELP}/>
          <Kpi icon="bi-people" label="Étudiants" value={kpis.participants} color="#F5B100" help={KPI_PERIOD_SCOPE_HELP}/>
          <Kpi icon="bi-person-video3" label="Enseignants" value={kpis.formateurs} color="#7B1FA2" help={KPI_PERIOD_SCOPE_HELP}/>
          <Kpi icon="bi-calendar-event" label={KPI_SESSIONS_TOTAL.label} value={kpis.sessions_total} color="#00838F"
            help={KPI_SESSIONS_TOTAL.help}/>
          <Kpi icon="bi-calendar-check" label={KPI_SESSIONS_COMPT.label} value={kpis.sessions_terminees} color="#082961"
            help={KPI_SESSIONS_COMPT.help}/>
          <Kpi icon="bi-clock-history" label="Vol. horaire prévu" value={`${fmtHeures(kpis.vh_prevu_heures)}h`} color="#0F70AB"/>
          <Kpi icon="bi-check2-all" label={KPI_VH_EXEC.label} value={`${kpis.taux_execution_vh}%`}
            color={kpis.taux_execution_vh >= 70 ? '#2277C1' : kpis.taux_execution_vh >= 40 ? '#F5B100' : '#C62828'}
            help={KPI_VH_EXEC.help}/>
        </div>
        <p style={{ margin: '1rem 0 0', fontSize: '0.76rem', color: '#64748b' }}>
          Effectifs et volumes sur le périmètre filtré (séances comptabilisables).
        </p>
      </div>
    )
  }

  if (sectionId === 'pedagogie') {
    const ped = pedagogiques || {}
    return (
      <div style={{ background: '#fff', borderRadius: 10, boxShadow: '0 1px 4px rgba(0,0,0,0.07)', padding: '1rem', minWidth: 0 }}>
        {header}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(140px,1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
          <Kpi icon="bi-person-check" label="Inscrits" value={ped.total_inscrits} color="#1565C0"/>
          <Kpi icon="bi-check-circle" label="Présents" value={ped.total_presents} color="#2277C1"/>
          <Kpi icon="bi-x-circle" label="Absents" value={ped.total_absents} color="#C62828"/>
          <Kpi icon="bi-arrow-right-circle" label="Événements" value={ped.total_abandons} color="#F5B100"
            help={TAUX_PEDAGOGIE.evenements.help}/>
        </div>
        <PedagogieTauxPrincipaux ped={ped} auditeursNotoires={auditeursNotoires}/>
        <Card title="Indicateurs pédagogiques" icon="bi-pie-chart">
          <PedagogieTauxGrille ped={ped} withBars/>
        </Card>
        <Card title={AUDITEURS_NOTOIRES.cardTitle} icon="bi-person-x-fill" col="1/-1">
          <AuditeursNotoiresPanel data={auditeursNotoires} maxHeight={360}/>
        </Card>
        {onGoPedagogie && (
          <button type="button" className="btn btn-sm btn-outline-success mt-2" onClick={onGoPedagogie}>
            <i className="bi bi-mortarboard me-1"/>Ouvrir l&apos;onglet Pédagogique
          </button>
        )}
      </div>
    )
  }

  if (sectionId === 'operationnel') {
    return (
      <div style={{ background: '#fff', borderRadius: 10, boxShadow: '0 1px 4px rgba(0,0,0,0.07)', padding: '1rem', minWidth: 0 }}>
        {header}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(300px,1fr))', gap: '1rem', marginBottom: '1rem' }}>
          <Card title="Répartition Hommes / Femmes" icon="bi-gender-ambiguous">
            <Donut data={adm.participants_par_sexe} labelKey="sexe" valueKey="total"/>
          </Card>
          <Card title="Charge des enseignants (top 8)" icon="bi-trophy" col="1/-1">
            <HBars data={adm.charge_formateurs} labelKey="nom" valueKey="nb_sessions"/>
          </Card>
        </div>
        <Card title={AUDITEURS_NOTOIRES.cardTitle} icon="bi-person-x-fill" col="1/-1">
          <AuditeursNotoiresPanel data={auditeursNotoires} maxHeight={480}/>
        </Card>
        {onGoAdmin && (
          <button type="button" className="btn btn-sm btn-outline-success mt-2" onClick={onGoAdmin}>
            <i className="bi bi-gear me-1"/>Ouvrir l&apos;onglet Administratif
          </button>
        )}
      </div>
    )
  }

  return <Empty label="Section non disponible"/>
}
