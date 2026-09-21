/**
 * alertes.jsx — Statistiques (INJS-LMD 2026)
 *
 * Widgets et panneaux de l'onglet « Alertes » du dashboard Statistiques,
 * extraits de `pages/Statistiques.jsx` (réduction des fichiers géants,
 * garde-fou G.1). Présentationnels : les données arrivent par props, aucun
 * appel réseau n'est fait ici.
 *
 * API publique du module : IndicateurSurveillanceCard, AlertesOverviewBandeau, buildAlertesSidebarEntries, AlertesEnsemblePanel, AlertesWidgetDetailPanel, AlertesStyles.
 * Les autres composants (NiveauBadge, SeuilGauge, widgets de synthèse,
 * alertes déclenchées et seuils) ne servent qu'en interne.
 */
import {
  ALERTES_OVERVIEW_CODES,
  AUDITEURS_NOTOIRES,
  NIVEAU_ALERTE,
} from './constantes'
import { Empty } from './graphiques'
import { Card } from './composants'
import {
  AuditeursNotoiresKpiStrip,
  AuditeursNotoiresPanel,
} from '../../components/AuditeursNotoiresPanel'

function NiveauBadge({ niveau, pulse = false }) {
  const n = NIVEAU_ALERTE[niveau] || NIVEAU_ALERTE.non_configure
  return (
    <span className={pulse ? 'stats-alerte-pulse' : undefined} style={{
      display:'inline-flex', alignItems:'center', gap:'0.3rem',
      fontSize:'0.72rem', fontWeight:700, padding:'0.2rem 0.55rem', borderRadius:20,
      background:n.bg, border:`1px solid ${n.border}`, color:n.color,
    }}>
      <i className={`bi ${n.icon}`}/>{n.label}
    </span>
  )
}

function SeuilGauge({ valeur, seuilAvert, seuilCrit, inverse, unite, echelleMax, niveau }) {
  const max = echelleMax || Math.max(valeur, seuilCrit * 1.25, seuilAvert * 1.25, 100)
  const pct = Math.min(100, Math.max(0, (valeur / max) * 100))
  const posAvert = Math.min(100, (seuilAvert / max) * 100)
  const posCrit = Math.min(100, (seuilCrit / max) * 100)

  const fillColor = niveau === 'critique' ? '#C62828'
    : niveau === 'avertissement' ? '#F5B100'
    : niveau === 'ok' ? '#2277C1' : '#94a3b8'

  const gradStops = inverse
    ? `#2277C1 0%, #2277C1 ${posAvert}%, #FCDF4D ${posAvert}%, #FCDF4D ${posCrit}%, #FCA5A5 ${posCrit}%, #FCA5A5 100%`
    : `#FCA5A5 0%, #FCA5A5 ${posCrit}%, #FCDF4D ${posCrit}%, #FCDF4D ${posAvert}%, #2277C1 ${posAvert}%, #2277C1 100%`

  return (
    <div style={{marginTop:'0.65rem'}}>
      <div style={{position:'relative', height:12, borderRadius:8, background:`linear-gradient(90deg, ${gradStops})`, opacity:0.45}}/>
      <div style={{position:'relative', height:12, marginTop:-12, borderRadius:8, overflow:'hidden'}}>
        <div className="stats-gauge-fill" style={{
          width:`${pct}%`, height:'100%',
          background: fillColor, borderRadius:8, opacity:0.92,
          boxShadow: niveau === 'critique' ? '0 0 8px rgba(198,40,40,0.45)' : 'none',
        }}/>
      </div>
      <div style={{position:'relative', height:18, marginTop:-15}}>
        <div className="stats-gauge-cursor" style={{
          position:'absolute', left:`calc(${pct}% - 6px)`, top:0,
          width:0, height:0,
          borderLeft:'6px solid transparent', borderRight:'6px solid transparent',
          borderBottom:`10px solid ${fillColor}`,
          filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.2))',
        }}/>
      </div>
      <div style={{display:'flex', justifyContent:'space-between', fontSize:'0.68rem', color:'#94a3b8', marginTop:'0.15rem'}}>
        <span>0{unite}</span>
        <span>⚠ {seuilAvert}{unite}</span>
        <span>🔴 {seuilCrit}{unite}</span>
        <span>{max}{unite}</span>
      </div>
    </div>
  )
}

export function IndicateurSurveillanceCard({ ind }) {
  const n = NIVEAU_ALERTE[ind.niveau] || NIVEAU_ALERTE.non_configure
  const pulse = ind.niveau === 'critique'
  return (
    <div className={`stats-ind-card${pulse ? ' stats-ind-critique' : ''}`} style={{
      background:'#fff', borderRadius:12, padding:'1rem',
      border:`1px solid ${n.border}`,
      boxShadow: pulse ? '0 4px 18px rgba(198,40,40,0.12)' : '0 2px 8px rgba(0,0,0,0.06)',
      transition:'transform 0.2s ease, box-shadow 0.2s ease',
    }}>
      <div style={{display:'flex', alignItems:'flex-start', gap:'0.75rem', marginBottom:'0.5rem'}}>
        <div style={{
          width:44, height:44, borderRadius:12, flexShrink:0,
          background:`${ind.couleur}18`, color:ind.couleur,
          display:'flex', alignItems:'center', justifyContent:'center', fontSize:'1.25rem',
        }}>
          <i className={`bi ${ind.icone}`}/>
        </div>
        <div style={{flex:1, minWidth:0}}>
          <div style={{display:'flex', alignItems:'center', gap:'0.4rem', flexWrap:'wrap', marginBottom:'0.2rem'}}>
            <span style={{fontWeight:700, color:'#1e293b', fontSize:'0.88rem'}}>{ind.libelle}</span>
            <NiveauBadge niveau={ind.niveau} pulse={pulse}/>
          </div>
          <p style={{margin:0, fontSize:'0.73rem', color:'#64748b', lineHeight:1.45}}>{ind.aide}</p>
        </div>
      </div>
      <div style={{display:'flex', alignItems:'baseline', gap:'0.35rem', marginBottom:'0.15rem'}}>
        <span style={{fontSize:'2rem', fontWeight:800, color:n.color, lineHeight:1}}>
          {ind.valeur}{ind.unite}
        </span>
        <span style={{fontSize:'0.75rem', color:'#94a3b8'}}>valeur actuelle</span>
      </div>
      {ind.configure && ind.actif ? (
        <SeuilGauge
          valeur={ind.valeur}
          seuilAvert={ind.seuil_avertissement}
          seuilCrit={ind.seuil_critique}
          inverse={ind.inverse}
          unite={ind.unite}
          echelleMax={ind.echelle_max}
          niveau={ind.niveau}
        />
      ) : (
        <div style={{
          marginTop:'0.5rem', padding:'0.55rem 0.65rem', borderRadius:8,
          background:'#f8fafc', fontSize:'0.75rem', color:'#64748b',
        }}>
          {!ind.configure
            ? 'Seuil non configuré — initialisez les seuils INJS pour activer la surveillance.'
            : 'Surveillance désactivée pour cet indicateur.'}
        </div>
      )}
    </div>
  )
}

export function AlertesOverviewBandeau({ items }) {
  const actives = (items || []).filter(
    a => ALERTES_OVERVIEW_CODES.includes(a.indicateur)
      && (a.niveau === 'critique' || a.niveau === 'avertissement'),
  )
  if (!actives.length) return null

  return (
    <div style={{ marginBottom: '1rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
      {actives.map((a) => (
        <div
          key={a.indicateur}
          className={a.niveau === 'critique' ? 'stats-alerte-pulse' : undefined}
          style={{
            background: a.niveau === 'critique' ? '#fff3f3' : '#fffceb',
            border: `1px solid ${a.niveau === 'critique' ? '#fca5a5' : '#fcdf4d'}`,
            borderRadius: 8,
            padding: '0.5rem 0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.82rem',
          }}
        >
          <i
            className={`bi ${a.niveau === 'critique' ? 'bi-exclamation-octagon-fill' : 'bi-exclamation-triangle-fill'}`}
            style={{ color: a.niveau === 'critique' ? '#C62828' : '#F5B100', fontSize: '1rem' }}
          />
          <b style={{ color: '#1e293b' }}>{a.libelle}</b>
          <span style={{ color: '#64748b' }}>: {a.valeur}{a.unite}</span>
          <span style={{ color: '#94a3b8', marginLeft: 'auto' }}>
            Seuil {a.niveau === 'critique' ? 'critique' : 'avertissement'} : {a.seuil_critique}{a.unite}
          </span>
        </div>
      ))}
    </div>
  )
}

export function buildAlertesSidebarEntries(alertesMeta, alertesList) {
  const syn = alertesMeta?.synthese || {}
  const nbDecl = alertesList?.length ?? 0
  const indicateurs = alertesMeta?.indicateurs || []

  const sections = [
    {
      id: 'synthese', group: 'sections', tag: 'SYN', tagColor: '#2277C1', label: 'Synthèse & guide',
      icon: 'bi-shield-check', sub: `${syn.ok ?? 0} ok · ${syn.avertissement ?? 0} avert. · ${syn.critique ?? 0} crit.`,
    },
    {
      id: 'indicateurs-grid', group: 'sections', tag: 'GRD', tagColor: '#1565C0', label: 'Grille indicateurs',
      icon: 'bi-grid-3x3', sub: `${indicateurs.length} carte${indicateurs.length > 1 ? 's' : ''} de surveillance`,
    },
    {
      id: 'declenchees', group: 'sections', tag: 'ALT', tagColor: nbDecl ? '#C62828' : '#2277C1', label: 'Alertes déclenchées',
      icon: 'bi-bell-fill', sub: nbDecl ? `${nbDecl} alerte${nbDecl > 1 ? 's' : ''} active${nbDecl > 1 ? 's' : ''}` : 'Tout conforme',
    },
    {
      id: 'seuils', group: 'sections', tag: 'CFG', tagColor: '#7B1FA2', label: 'Configuration seuils',
      icon: 'bi-sliders', sub: alertesMeta?.seuils_vides ? 'Seuils à initialiser' : 'Modifier les paliers',
    },
  ]

  const parInd = indicateurs.map(ind => {
    const n = NIVEAU_ALERTE[ind.niveau] || NIVEAU_ALERTE.non_configure
    return {
      id: `ind-${ind.indicateur}`,
      group: 'indicateurs',
      tag: 'IND',
      tagColor: n.color,
      label: ind.libelle,
      icon: ind.icone || 'bi-speedometer2',
      sub: `${ind.valeur}${ind.unite} · ${n.label}`,
      indicateur: ind,
    }
  })

  return [...sections, ...parInd]
}

function AlertesSyntheseWidget({
  alertesMeta, showGuideAlertes, setShowGuideAlertes, formationId, secretariatId,
}) {
  return (
    <div style={{
      background: 'linear-gradient(135deg, #e8eef6 0%, #d4deec 50%, #f4f7fb 100%)',
      border: '1px solid #e2e8f0', borderRadius: 12, padding: '1rem 1.15rem', marginBottom: '1rem',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 800, color: '#1e293b' }}>
            <i className="bi bi-shield-check me-2" style={{ color: 'var(--navy)' }}/>
            Surveillance des indicateurs
          </h3>
          <p style={{ margin: '0.35rem 0 0', fontSize: '0.78rem', color: '#64748b', maxWidth: 560 }}>
            Les alertes comparent les KPIs en temps réel aux seuils INJS.
            {(formationId || secretariatId)
              ? ' Filtre actif appliqué aux valeurs ci-dessous.'
              : ' Vue globale — utilisez les filtres formation / secrétariat pour affiner.'}
          </p>
        </div>
        <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => setShowGuideAlertes(v => !v)}>
          <i className={`bi ${showGuideAlertes ? 'bi-chevron-up' : 'bi-chevron-down'} me-1`}/>
          {showGuideAlertes ? 'Masquer le guide' : 'Comment lire les alertes ?'}
        </button>
      </div>

      {showGuideAlertes && (
        <div style={{
          marginTop: '0.85rem', display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.5rem',
        }}>
          {[
            { icon: 'bi-check-circle-fill', col: '#2277C1', titre: 'Conforme', texte: 'La valeur respecte les seuils définis.' },
            { icon: 'bi-exclamation-triangle-fill', col: '#F5B100', titre: 'Avertissement', texte: 'Seuil d\'attention atteint — surveiller la tendance.' },
            { icon: 'bi-exclamation-octagon-fill', col: '#C62828', titre: 'Critique', texte: 'Action corrective recommandée rapidement.' },
            { icon: 'bi-sliders', col: '#1565C0', titre: 'Seuils', texte: '⚠ = premier palier · 🔴 = palier critique.' },
          ].map((g, i) => (
            <div key={i} style={{
              background: 'rgba(255,255,255,0.75)', borderRadius: 8, padding: '0.55rem 0.65rem',
              border: '1px solid rgba(255,255,255,0.9)',
            }}>
              <div style={{ fontWeight: 700, fontSize: '0.78rem', color: g.col, marginBottom: '0.15rem' }}>
                <i className={`bi ${g.icon} me-1`}/>{g.titre}
              </div>
              <div style={{ fontSize: '0.72rem', color: '#64748b' }}>{g.texte}</div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.85rem' }}>
        {[
          { key: 'ok', label: 'Conformes', col: '#2277C1', bg: '#ecf3fd' },
          { key: 'avertissement', label: 'Avertissements', col: '#F5B100', bg: '#fffceb' },
          { key: 'critique', label: 'Critiques', col: '#C62828', bg: '#fff1f2' },
        ].map(p => (
          <div key={p.key} className="stats-synthese-pill" style={{
            flex: '1 1 120px', minWidth: 110, textAlign: 'center', padding: '0.55rem 0.75rem',
            borderRadius: 10, background: p.bg, border: `1px solid ${p.col}33`,
          }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: p.col, lineHeight: 1 }}>
              {alertesMeta.synthese?.[p.key] ?? 0}
            </div>
            <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '0.15rem' }}>{p.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function AlertesDeclencheesWidget({ alertes }) {
  return (
    <div style={{ background: '#fff', borderRadius: 12, padding: '1.1rem', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
      <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#1e293b', marginBottom: '0.8rem' }}>
        <i className="bi bi-bell-fill me-1" style={{ color: '#F5B100' }}/>
        Alertes déclenchées
        {alertes?.length > 0 && (
          <span style={{
            marginLeft: '0.4rem', fontSize: '0.72rem', background: '#C62828', color: '#fff',
            borderRadius: 12, padding: '0.1rem 0.45rem', fontWeight: 700,
          }}>{alertes.length}</span>
        )}
      </h4>
      {!alertes?.length ? (
        <div style={{
          textAlign: 'center', padding: '2rem 1rem',
          borderRadius: 10, border: '1px solid #bbd7f7',
          background: 'linear-gradient(180deg, #f0f6fd 0%, #fff 100%)',
        }}>
          <div style={{
            width: 64, height: 64, margin: '0 auto 0.65rem', borderRadius: '50%',
            background: '#2277C118', display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <i className="bi bi-check-lg" style={{ fontSize: '2rem', color: '#2277C1' }}/>
          </div>
          <div style={{ fontWeight: 700, color: '#0b478a', fontSize: '0.88rem', marginBottom: '0.25rem' }}>
            Tout est conforme
          </div>
          <div style={{ fontSize: '0.78rem', color: '#64748b' }}>
            Aucune alerte active pour le périmètre sélectionné.
          </div>
        </div>
      ) : alertes.map((a, i) => (
        <div key={i} className={a.niveau === 'critique' ? 'stats-alerte-pulse' : undefined} style={{
          background: a.niveau === 'critique' ? '#fff1f2' : '#fffceb',
          border: `1px solid ${a.niveau === 'critique' ? '#fca5a5' : '#fcdf4d'}`,
          borderRadius: 10, padding: '0.75rem 0.9rem', marginBottom: '0.5rem',
          borderLeft: `4px solid ${a.niveau === 'critique' ? '#C62828' : '#F5B100'}`,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.35rem' }}>
            <i className={`bi ${a.niveau === 'critique' ? 'bi-exclamation-octagon-fill' : 'bi-exclamation-triangle-fill'}`}
              style={{ color: a.niveau === 'critique' ? '#C62828' : '#F5B100', fontSize: '1.1rem' }}/>
            <b style={{ fontSize: '0.85rem', color: '#1e293b', flex: 1 }}>{a.libelle}</b>
            <NiveauBadge niveau={a.niveau}/>
          </div>
          <div style={{ fontSize: '0.78rem', color: '#64748b', display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
            <span>Valeur : <b style={{ color: '#1e293b', fontSize: '0.95rem' }}>{a.valeur}{a.unite}</b></span>
            <span>Seuil ⚠ : {a.seuil_avertissement}{a.unite}</span>
            <span>Seuil 🔴 : {a.seuil_critique}{a.unite}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

function AlertesSeuilsWidget({
  alertesMeta, seuils, seuilsForm, editSeuils, setEditSeuils, setSeuilsForm,
  canValidate, initSeuilsDefaut, initSeuilsLoading, saveSeuils,
}) {
  return (
    <div style={{ background: '#fff', borderRadius: 12, padding: '1.1rem', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem', flexWrap: 'wrap', gap: '0.4rem' }}>
        <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#1e293b', margin: 0 }}>
          <i className="bi bi-sliders me-1" style={{ color: '#1565C0' }}/>
          Configuration des seuils
        </h4>
        <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
          {canValidate && alertesMeta.seuils_vides && (
            <button className="btn btn-sm btn-outline-success" onClick={initSeuilsDefaut} disabled={initSeuilsLoading}>
              <i className="bi bi-magic me-1"/>Init. INJS
            </button>
          )}
          {canValidate && !editSeuils && seuils.length > 0 && (
            <button className="btn btn-sm btn-outline-primary" onClick={() => setEditSeuils(true)}>
              <i className="bi bi-pencil me-1"/>Modifier
            </button>
          )}
        </div>
      </div>

      {seuils.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '1.5rem', color: '#64748b', fontSize: '0.82rem' }}>
          <i className="bi bi-gear-wide-connected" style={{ fontSize: '1.8rem', display: 'block', marginBottom: '0.5rem', color: '#94a3b8' }}/>
          Configurez les seuils pour personnaliser les alertes automatiques.
        </div>
      ) : editSeuils ? (
        <>
          {seuilsForm.map((s, i) => (
            <div key={s.indicateur || s.id} style={{
              borderBottom: '1px solid #f1f5f9', paddingBottom: '0.75rem', marginBottom: '0.75rem',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.35rem' }}>
                <i className={`bi ${s.icone || 'bi-speedometer2'}`} style={{ color: '#1565C0' }}/>
                <p style={{ fontWeight: 600, color: '#334155', fontSize: '0.82rem', margin: 0, flex: 1 }}>{s.libelle}</p>
                <label style={{ fontSize: '0.72rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                  <input type="checkbox" checked={seuilsForm[i].actif !== false}
                    onChange={e => setSeuilsForm(f => f.map((x, j) => j === i ? { ...x, actif: e.target.checked } : x))}/>
                  Actif
                </label>
              </div>
              {s.aide && <p style={{ fontSize: '0.7rem', color: '#94a3b8', margin: '0 0 0.4rem' }}>{s.aide}</p>}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem' }}>
                <div>
                  <label style={{ fontSize: '0.72rem', color: '#F5B100', fontWeight: 600 }}>⚠ Avertissement</label>
                  <input type="number" className="form-control form-control-sm"
                    value={seuilsForm[i].seuil_avertissement}
                    onChange={e => setSeuilsForm(f => f.map((x, j) => j === i ? { ...x, seuil_avertissement: parseFloat(e.target.value) } : x))}/>
                </div>
                <div>
                  <label style={{ fontSize: '0.72rem', color: '#C62828', fontWeight: 600 }}>🔴 Critique</label>
                  <input type="number" className="form-control form-control-sm"
                    value={seuilsForm[i].seuil_critique}
                    onChange={e => setSeuilsForm(f => f.map((x, j) => j === i ? { ...x, seuil_critique: parseFloat(e.target.value) } : x))}/>
                </div>
              </div>
            </div>
          ))}
          <div style={{ display: 'flex', gap: '0.4rem' }}>
            <button className="btn btn-sm" style={{ background: 'var(--navy)', color: '#fff', border: 'none' }} onClick={saveSeuils}>
              <i className="bi bi-check-lg me-1"/>Enregistrer
            </button>
            <button className="btn btn-sm btn-outline-secondary" onClick={() => { setEditSeuils(false); setSeuilsForm(seuils.map(s => ({ ...s }))) }}>
              Annuler
            </button>
          </div>
        </>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
                <th style={{ padding: '0.4rem 0.6rem', color: '#64748b', fontWeight: 600, textAlign: 'left' }}>Indicateur</th>
                <th style={{ padding: '0.4rem 0.6rem', color: '#F5B100', fontWeight: 600, textAlign: 'center' }}>⚠</th>
                <th style={{ padding: '0.4rem 0.6rem', color: '#C62828', fontWeight: 600, textAlign: 'center' }}>🔴</th>
                <th style={{ padding: '0.4rem 0.6rem', color: '#64748b', fontWeight: 600, textAlign: 'center' }}>Actif</th>
              </tr>
            </thead>
            <tbody>
              {seuils.map((s) => {
                const ind = alertesMeta.indicateurs?.find(x => x.indicateur === s.indicateur)
                return (
                  <tr key={s.id || s.indicateur} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '0.45rem 0.6rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                        <i className={`bi ${s.icone || 'bi-speedometer2'}`} style={{ color: '#64748b' }}/>
                        <span style={{ color: '#334155', fontWeight: 500 }}>{s.libelle}</span>
                        {ind && <NiveauBadge niveau={ind.niveau}/>}
                      </div>
                    </td>
                    <td style={{ textAlign: 'center', padding: '0.45rem 0.6rem', color: '#F5B100', fontWeight: 700 }}>{s.seuil_avertissement}</td>
                    <td style={{ textAlign: 'center', padding: '0.45rem 0.6rem', color: '#C62828', fontWeight: 700 }}>{s.seuil_critique}</td>
                    <td style={{ textAlign: 'center', padding: '0.45rem 0.6rem' }}>
                      {s.actif
                        ? <i className="bi bi-check-circle-fill" style={{ color: '#2277C1' }}/>
                        : <i className="bi bi-dash-circle" style={{ color: '#94a3b8' }}/>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export function AlertesEnsemblePanel(props) {
  const { alertesMeta, onSelectWidget, auditeursNotoires, ...rest } = props
  return (
    <div style={{
      background: '#fff', borderRadius: 10, boxShadow: '0 1px 4px rgba(0,0,0,0.07)',
      overflow: 'hidden', minWidth: 0,
    }}>
      <div style={{
        padding: '0.85rem 1rem', background: 'linear-gradient(135deg, #e8eef6 0%, #f4f7fb 100%)',
        borderBottom: '1px solid #e2e8f0', position: 'sticky', top: 0, zIndex: 2,
      }}>
        <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 800, color: '#1e293b' }}>
          <i className="bi bi-bell me-2" style={{ color: '#F5B100' }}/>
          Alertes — tous les widgets
        </h3>
        <p style={{ margin: '0.35rem 0 0', fontSize: '0.78rem', color: '#64748b' }}>
          Synthèse, cartes de surveillance, alertes actives et configuration des seuils.
        </p>
      </div>
      <div style={{ maxHeight: '62vh', overflowY: 'auto', padding: '1rem' }}>
        <AuditeursNotoiresKpiStrip data={auditeursNotoires}/>
        <div onClick={onSelectWidget ? () => onSelectWidget('synthese') : undefined} role={onSelectWidget ? 'button' : undefined} style={{ cursor: onSelectWidget ? 'pointer' : undefined }}>
          <AlertesSyntheseWidget alertesMeta={alertesMeta} {...rest}/>
        </div>

        {alertesMeta.indicateurs?.length > 0 ? (
          <div
            onClick={onSelectWidget ? () => onSelectWidget('indicateurs-grid') : undefined}
            role={onSelectWidget ? 'button' : undefined}
            style={{ cursor: onSelectWidget ? 'pointer' : undefined, marginBottom: '1rem' }}
          >
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '0.85rem',
            }}>
              {alertesMeta.indicateurs.map(ind => (
                <div
                  key={ind.indicateur}
                  onClick={onSelectWidget ? (e) => { e.stopPropagation(); onSelectWidget(`ind-${ind.indicateur}`) } : undefined}
                  role={onSelectWidget ? 'button' : undefined}
                >
                  <IndicateurSurveillanceCard ind={ind}/>
                </div>
              ))}
            </div>
          </div>
        ) : alertesMeta.seuils_vides ? (
          <div style={{
            textAlign: 'center', padding: '2rem 1rem', marginBottom: '1rem',
            background: '#fff', borderRadius: 12, border: '2px dashed #cbd5e1',
          }}>
            <i className="bi bi-sliders2" style={{ fontSize: '2.5rem', color: '#94a3b8', display: 'block', marginBottom: '0.65rem' }}/>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#334155', marginBottom: '0.35rem' }}>
              Aucun seuil configuré
            </h4>
            <p style={{ fontSize: '0.82rem', color: '#64748b', maxWidth: 420, margin: '0 auto 1rem' }}>
              Initialisez les seuils INJS pour activer la surveillance des 6 indicateurs clés.
            </p>
            {rest.canValidate && (
              <button className="btn btn-sm" style={{ background: 'var(--navy)', color: '#fff', border: 'none' }}
                onClick={rest.initSeuilsDefaut} disabled={rest.initSeuilsLoading}>
                {rest.initSeuilsLoading
                  ? <><span className="spinner-border spinner-border-sm me-1"/>Initialisation…</>
                  : <><i className="bi bi-magic me-1"/>Initialiser les seuils INJS</>}
              </button>
            )}
          </div>
        ) : null}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '1rem' }}>
          <div onClick={onSelectWidget ? () => onSelectWidget('declenchees') : undefined} role={onSelectWidget ? 'button' : undefined}>
            <AlertesDeclencheesWidget alertes={rest.alertes}/>
          </div>
          <div onClick={onSelectWidget ? () => onSelectWidget('seuils') : undefined} role={onSelectWidget ? 'button' : undefined}>
            <AlertesSeuilsWidget alertesMeta={alertesMeta} {...rest}/>
          </div>
        </div>

        <div style={{ marginTop: '1rem' }}>
          <Card title={AUDITEURS_NOTOIRES.cardTitle} icon="bi-person-x-fill" col="1/-1">
            <AuditeursNotoiresPanel data={auditeursNotoires} maxHeight={280} compact/>
          </Card>
        </div>
      </div>
    </div>
  )
}

export function AlertesWidgetDetailPanel({ entry, onGoSeuils, auditeursNotoires, ...props }) {
  const { alertesMeta, alertes, seuils, ...rest } = props

  if (entry.id === 'synthese') {
    return (
      <div style={{ background: '#fff', borderRadius: 10, boxShadow: '0 1px 4px rgba(0,0,0,0.07)', padding: '1rem', minWidth: 0 }}>
        <AlertesSyntheseWidget alertesMeta={alertesMeta} {...rest}/>
      </div>
    )
  }

  if (entry.id === 'indicateurs-grid') {
    return (
      <div style={{ background: '#fff', borderRadius: 10, boxShadow: '0 1px 4px rgba(0,0,0,0.07)', padding: '1rem', minWidth: 0 }}>
        <h3 style={{ margin: '0 0 1rem', fontSize: '0.95rem', fontWeight: 800, color: '#1e293b' }}>
          <i className="bi bi-grid-3x3 me-2" style={{ color: '#1565C0' }}/>
          Grille des indicateurs
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '0.85rem' }}>
          {alertesMeta.indicateurs?.map(ind => (
            <IndicateurSurveillanceCard key={ind.indicateur} ind={ind}/>
          ))}
        </div>
      </div>
    )
  }

  if (entry.id === 'declenchees') {
    return (
      <div style={{ background: '#fff', borderRadius: 10, boxShadow: '0 1px 4px rgba(0,0,0,0.07)', padding: '1rem', minWidth: 0 }}>
        <AuditeursNotoiresKpiStrip data={auditeursNotoires}/>
        <AlertesDeclencheesWidget alertes={alertes}/>
      </div>
    )
  }

  if (entry.id === 'seuils') {
    return <AlertesSeuilsWidget alertesMeta={alertesMeta} seuils={seuils} {...rest}/>
  }

  if (entry.id?.startsWith('ind-') && entry.indicateur) {
    const ind = entry.indicateur
    const seuilRow = seuils?.find(s => s.indicateur === ind.indicateur)
    return (
      <div style={{ background: '#fff', borderRadius: 10, boxShadow: '0 1px 4px rgba(0,0,0,0.07)', padding: '1rem', minWidth: 0 }}>
        <IndicateurSurveillanceCard ind={ind}/>
        {seuilRow && (
          <div style={{ marginTop: '1rem', padding: '0.75rem', background: '#f8fafc', borderRadius: 8, fontSize: '0.8rem' }}>
            <b style={{ color: '#334155' }}>Seuils configurés :</b>{' '}
            ⚠ {seuilRow.seuil_avertissement}{ind.unite} · 🔴 {seuilRow.seuil_critique}{ind.unite}
            {onGoSeuils && (
              <button type="button" className="btn btn-sm btn-link" style={{ fontSize: '0.78rem' }} onClick={onGoSeuils}>
                Modifier tous les seuils
              </button>
            )}
          </div>
        )}
      </div>
    )
  }

  return <Empty label="Widget non disponible"/>
}

export function AlertesStyles() {
  return (
    <style>{`
      @keyframes statsPulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(198,40,40,0.35); }
        50% { box-shadow: 0 0 0 6px rgba(198,40,40,0); }
      }
      @keyframes statsGaugeGrow {
        from { width: 0; }
      }
      @keyframes statsFadeUp {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
      }
      .stats-alerte-pulse { animation: statsPulse 2s ease-in-out infinite; }
      .stats-gauge-fill { animation: statsGaugeGrow 0.8s ease-out; }
      .stats-ind-card { animation: statsFadeUp 0.45s ease-out both; }
      .stats-ind-critique { animation: statsFadeUp 0.45s ease-out both, statsPulse 2.5s ease-in-out infinite; }
      .stats-ind-card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.08); }
      .stats-synthese-pill { transition: transform 0.15s ease; }
      .stats-synthese-pill:hover { transform: scale(1.04); }
    `}</style>
  )
}
