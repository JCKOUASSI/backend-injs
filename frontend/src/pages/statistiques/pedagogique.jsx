/**
 * pedagogique.jsx — Statistiques (INJS-LMD 2026)
 *
 * Panneau « Pédagogique » : synthèse des taux, entrées de sidebar et
 * panneau de détail.
 *
 * Extrait de `pages/Statistiques.jsx` (réduction des fichiers géants,
 * garde-fou G.1). Les données arrivent par props : aucun appel réseau.
 */
import { AuditeursNotoiresPanel, filterAuditeursNotoires } from '../../components/AuditeursNotoiresPanel'
import { Card, Kpi, TauxBar } from './composants'
import { PedagogieTauxPrincipaux } from './taux-pedagogie'
import { AUDITEURS_NOTOIRES, TAUX_PEDAGOGIE } from './constantes'
import { Empty, HBars } from './graphiques'

export function buildPedagogieEntries(ped) {
  if (!ped) return []
  const entries = []
  ;(ped.taux_par_formation || []).forEach(r => {
    entries.push({
      id: `formation-${r.formation_id}`,
      type: 'formation',
      tag: 'FOR',
      tagColor: '#1565C0',
      label: r.formation,
      sub: `${r.inscrits} inscrits · ${Number(r.taux).toFixed(1)}% prés.`,
      row: r,
    })
  })
  ;(ped.taux_par_grade || []).forEach((r, i) => {
    entries.push({
      id: `grade-${i}`,
      type: 'grade',
      tag: 'GRD',
      tagColor: '#7B1FA2',
      label: r.grade,
      sub: `${r.inscrits} inscrits · ${Number(r.taux).toFixed(1)}% prés.`,
      row: r,
    })
  })
  ;(ped.taux_par_secretariat || []).forEach(r => {
    entries.push({
      id: `secretariat-${r.secretariat_id}`,
      type: 'secretariat',
      tag: 'SEC',
      tagColor: '#F5B100',
      label: r.secretariat,
      sub: `${r.inscrits} inscrits · ${Number(r.taux).toFixed(1)}% prés.`,
      row: r,
    })
  })
  return entries
}

export function PedagogiqueEnsemblePanel({ pedagogiques, pedEntries, onSelect, auditeursNotoires }) {
  const ped = pedagogiques || {}
  const an = auditeursNotoires || ped.auditeurs_notoires
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
          <i className="bi bi-mortarboard me-2" style={{ color: 'var(--navy)' }}/>
          Pédagogique — vue d&apos;ensemble
        </h3>
        <p style={{ margin: '0.35rem 0 0', fontSize: '0.78rem', color: '#64748b' }}>
          Synthèse globale et répartitions par formation, grade et secrétariat.
          Sélectionnez un périmètre à gauche pour le détail.
        </p>
      </div>
      <div style={{ maxHeight: '62vh', overflowY: 'auto', padding: '1rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(160px,1fr))', gap: '0.8rem', marginBottom: '1.1rem' }}>
          <Kpi icon="bi-person-check" label="Inscrits" value={ped.total_inscrits} color="#1565C0"/>
          <Kpi icon="bi-check-circle" label="Présents" value={ped.total_presents} color="#2277C1"/>
          <Kpi icon="bi-x-circle" label="Absents" value={ped.total_absents} color="#C62828"/>
          <Kpi icon="bi-arrow-right-circle" label="Événements" value={ped.total_abandons} color="#F5B100"
            help={TAUX_PEDAGOGIE.evenements.help}/>
        </div>
        <PedagogieTauxPrincipaux ped={ped} auditeursNotoires={an}/>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(160px,1fr))', gap: '0.8rem', marginBottom: '1.1rem' }}>
          <Kpi icon="bi-percent" label={TAUX_PEDAGOGIE.absence.label} value={`${TAUX_PEDAGOGIE.absence.getValue(ped)}%`} color={TAUX_PEDAGOGIE.absence.color} help={TAUX_PEDAGOGIE.absence.help}/>
          <Kpi icon="bi-percent" label={TAUX_PEDAGOGIE.evenements.label} value={`${TAUX_PEDAGOGIE.evenements.getValue(ped)}%`} color={TAUX_PEDAGOGIE.evenements.color} help={TAUX_PEDAGOGIE.evenements.help}/>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(320px,1fr))', gap: '1rem' }}>
          <Card title="Assiduité séance par formation" icon="bi-building">
            {ped.taux_par_formation?.length ? (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
                      {['Formation', 'Inscrits', 'Présents', 'Taux'].map(h => (
                        <th key={h} style={{ padding: '0.45rem 0.7rem', color: '#64748b', fontWeight: 600, textAlign: h === 'Formation' ? 'left' : 'center' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {ped.taux_par_formation.map((r) => {
                      const entryId = `formation-${r.formation_id}`
                      return (
                        <tr
                          key={entryId}
                          style={{ borderBottom: '1px solid #f1f5f9', cursor: onSelect ? 'pointer' : undefined }}
                          onClick={onSelect ? () => onSelect(entryId) : undefined}
                          onMouseEnter={onSelect ? e => { e.currentTarget.style.background = '#e8eef6' } : undefined}
                          onMouseLeave={onSelect ? e => { e.currentTarget.style.background = '' } : undefined}
                        >
                          <td style={{ padding: '0.45rem 0.7rem', color: '#1e293b', maxWidth: 260 }}>{r.formation}</td>
                          <td style={{ textAlign: 'center', padding: '0.45rem 0.7rem', color: '#64748b' }}>{r.inscrits}</td>
                          <td style={{ textAlign: 'center', padding: '0.45rem 0.7rem', color: '#2277C1', fontWeight: 600 }}>{r.presents}</td>
                          <td style={{ padding: '0.45rem 0.7rem', minWidth: 140 }}><TauxBar value={r.taux} small/></td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ) : <Empty/>}
          </Card>

          <Card title="Assiduité séance par grade" icon="bi-bar-chart-steps">
            {ped.taux_par_grade?.length ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {ped.taux_par_grade.map((r, i) => (
                  <div
                    key={i}
                    style={{ cursor: onSelect ? 'pointer' : undefined }}
                    onClick={onSelect ? () => onSelect(`grade-${i}`) : undefined}
                    role={onSelect ? 'button' : undefined}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.79rem', marginBottom: '0.15rem' }}>
                      <b style={{ color: '#334155' }}>{r.grade}</b>
                      <span style={{ color: '#64748b' }}>{r.inscrits} inscrits</span>
                    </div>
                    <TauxBar value={r.taux} small/>
                  </div>
                ))}
              </div>
            ) : <Empty label="Aucun grade renseigné"/>}
          </Card>

          <Card title="Étudiants par type de concours" icon="bi-layers">
            <HBars data={ped.par_type_concours} labelKey="type" valueKey="total"/>
          </Card>

          {ped.taux_par_secretariat?.length > 0 && (
            <Card title="Assiduité séance par secrétariat" icon="bi-building">
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
                      {['N°', 'Secrétariat', 'Inscrits', 'Présents', 'Taux'].map(h => (
                        <th key={h} style={{ padding: '0.45rem 0.7rem', color: '#64748b', fontWeight: 600, textAlign: h === 'Secrétariat' ? 'left' : 'center' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {ped.taux_par_secretariat.map(r => {
                      const entryId = `secretariat-${r.secretariat_id}`
                      return (
                        <tr
                          key={entryId}
                          style={{ borderBottom: '1px solid #f1f5f9', cursor: onSelect ? 'pointer' : undefined }}
                          onClick={onSelect ? () => onSelect(entryId) : undefined}
                          onMouseEnter={onSelect ? e => { e.currentTarget.style.background = '#e8eef6' } : undefined}
                          onMouseLeave={onSelect ? e => { e.currentTarget.style.background = '' } : undefined}
                        >
                          <td style={{ padding: '0.45rem 0.7rem', color: '#94a3b8', textAlign: 'center' }}>{r.numero}</td>
                          <td style={{ padding: '0.45rem 0.7rem', color: '#1e293b', fontWeight: 500 }}>{r.secretariat}</td>
                          <td style={{ textAlign: 'center', padding: '0.45rem 0.7rem', color: '#64748b' }}>{r.inscrits}</td>
                          <td style={{ textAlign: 'center', padding: '0.45rem 0.7rem', color: '#2277C1', fontWeight: 600 }}>{r.presents}</td>
                          <td style={{ padding: '0.45rem 0.7rem', minWidth: 130 }}><TauxBar value={r.taux} small/></td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>

        <div style={{ marginTop: '1rem' }}>
          <Card title={AUDITEURS_NOTOIRES.cardTitle} icon="bi-person-x-fill" col="1/-1">
            <AuditeursNotoiresPanel data={an} maxHeight={360}/>
          </Card>
        </div>

        {pedEntries.length > 0 && (
          <p style={{ margin: '1rem 0 0', fontSize: '0.76rem', color: '#64748b' }}>
            <i className="bi bi-info-circle me-1"/>
            {pedEntries.length} périmètres listés à gauche — cliquez sur une ligne pour ouvrir le détail.
          </p>
        )}
      </div>
    </div>
  )
}

export function PedagogiqueDetailPanel({ entry, pedagogiques, onGoSecretariat, auditeursNotoires }) {
  const ped = pedagogiques || {}
  const baseAn = auditeursNotoires || ped.auditeurs_notoires
  const an = entry.type === 'secretariat' && entry.row?.secretariat_id != null
    ? filterAuditeursNotoires(baseAn, { secretariatId: entry.row.secretariat_id })
    : baseAn
  const r = entry.row
  const typeLabel = entry.type === 'formation' ? 'Formation' : entry.type === 'grade' ? 'Grade' : 'Secrétariat'
  const ecart = r.taux != null && ped.taux_presence != null
    ? Math.round((r.taux - ped.taux_presence) * 10) / 10
    : null

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
          <span style={{
            background: `${entry.tagColor}18`, color: entry.tagColor, borderRadius: 4,
            padding: '0.1rem 0.4rem', marginRight: '0.4rem', fontSize: '0.72rem',
          }}>{entry.tag}</span>
          {typeLabel} — {entry.label}
        </h3>
        {entry.type === 'secretariat' && r.numero != null && (
          <p style={{ margin: '0.25rem 0 0', fontSize: '0.78rem', color: '#64748b' }}>N° {r.numero}</p>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(140px,1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
        <Kpi icon="bi-person-check" label="Inscrits" value={r.inscrits} color="#1565C0"/>
        <Kpi icon="bi-check-circle" label="Présents" value={r.presents} color="#2277C1"/>
        <Kpi icon="bi-percent" label={TAUX_PEDAGOGIE.assiduite.label} value={`${Number(r.taux).toFixed(1)}%`} color={TAUX_PEDAGOGIE.assiduite.color} help={TAUX_PEDAGOGIE.assiduite.help}/>
        {ecart != null && (
          <Kpi
            icon="bi-arrow-left-right"
            label="Écart vs global"
            value={`${ecart > 0 ? '+' : ''}${ecart} pt`}
            color={ecart >= 0 ? '#2277C1' : '#C62828'}
            sub={`Moyenne globale : ${ped.taux_presence}% (assiduité séance)`}
          />
        )}
      </div>

      <div style={{ marginBottom: '1rem' }}>
        <p style={{ fontSize: '0.78rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>Assiduité séance du périmètre</p>
        <TauxBar value={r.taux}/>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(280px,1fr))', gap: '1rem' }}>
        <Card title="Contexte global (filtre actif)" icon="bi-speedometer2">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem', fontSize: '0.8rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#64748b' }}>Inscrits (total)</span>
              <b style={{ color: '#1e293b' }}>{ped.total_inscrits}</b>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#64748b' }}>Présents (total)</span>
              <b style={{ color: '#2277C1' }}>{ped.total_presents}</b>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#64748b' }}>{TAUX_PEDAGOGIE.assiduite.label} (global)</span>
              <b style={{ color: '#1e293b' }}>{ped.taux_presence}%</b>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#64748b' }}>Séances terminées</span>
              <b style={{ color: '#1e293b' }}>{ped.nb_seances_terminees ?? '—'}</b>
            </div>
          </div>
        </Card>

        {entry.type === 'formation' && ped.taux_par_grade?.length > 0 && (
          <Card title="Grades liés (aperçu)" icon="bi-bar-chart-steps">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              {ped.taux_par_grade.slice(0, 5).map((g, i) => (
                <div key={i}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '0.1rem' }}>
                    <span style={{ color: '#334155' }}>{g.grade}</span>
                    <span style={{ color: '#64748b' }}>{g.taux}%</span>
                  </div>
                  <TauxBar value={g.taux} small/>
                </div>
              ))}
            </div>
          </Card>
        )}

        {entry.type === 'secretariat' && onGoSecretariat && (
          <Card title="Aller plus loin" icon="bi-building">
            <p style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.65rem' }}>
              Consultez le tableau de bord complet de ce secrétariat (modules, pointages, graphiques).
            </p>
            <button
              type="button"
              className="btn btn-sm"
              style={{ background: 'var(--navy)', color: '#fff', border: 'none' }}
              onClick={() => onGoSecretariat(r.secretariat_id)}
            >
              <i className="bi bi-building me-1"/>Ouvrir l&apos;onglet Secrétariats
            </button>
          </Card>
        )}
      </div>

      <div style={{ marginTop: '1rem' }}>
        <Card title={AUDITEURS_NOTOIRES.cardTitle} icon="bi-person-x-fill" col="1/-1">
          <AuditeursNotoiresPanel data={an} maxHeight={320} compact/>
        </Card>
      </div>
    </div>
  )
}
