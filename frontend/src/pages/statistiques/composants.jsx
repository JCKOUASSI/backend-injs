/**
 * composants.jsx — Statistiques (INJS-LMD 2026)
 *
 * Petits composants partagés du dashboard Statistiques (cartes, KPI, barres
 * de taux, tendances), extraits de `pages/Statistiques.jsx` (réduction des
 * fichiers géants, garde-fou G.1). Présentationnels : aucun appel réseau.
 */
import { Empty, formatMoisLabel } from './graphiques'

export function MonthTrendChart({ data, valueKey = 'total', color = '#2277C1', height = 160, unit = '' }) {
  if (!data?.length) return <Empty />
  const max = Math.max(...data.map(d => d[valueKey] || 0), 1)
  const barW = 28
  const gap = 10
  const padL = 36
  const w = padL + data.length * (barW + gap) + 16
  const gridSteps = 4

  return (
    <div style={{ overflowX: 'auto' }}>
      <svg width={Math.max(w, 360)} height={height + 44} style={{ display: 'block' }}>
        {[...Array(gridSteps + 1)].map((_, i) => {
          const y = 8 + (i / gridSteps) * (height - 16)
          const val = Math.round(max - (i / gridSteps) * max)
          return (
            <g key={i}>
              <line x1={padL - 4} y1={y} x2={w - 8} y2={y} stroke="#e2e8f0" strokeWidth={1} />
              <text x={padL - 8} y={y + 3} textAnchor="end" fontSize={8} fill="#94a3b8">{val}</text>
            </g>
          )
        })}
        {data.map((d, i) => {
          const v = d[valueKey] || 0
          const bH = v > 0 ? Math.max(6, Math.round((v / max) * (height - 20))) : 0
          const x = padL + i * (barW + gap)
          const y = height - bH
          const hasData = v > 0
          return (
            <g key={i}>
              <rect
                x={x} y={y} width={barW} height={bH || 2} rx={4}
                fill={hasData ? color : '#e2e8f0'}
                opacity={hasData ? 0.88 : 0.5}
              />
              {hasData && (
                <text x={x + barW / 2} y={y - 4} textAnchor="middle" fontSize={9} fill="#1e293b" fontWeight={600}>
                  {v}{unit}
                </text>
              )}
              <text x={x + barW / 2} y={height + 16} textAnchor="middle" fontSize={8} fill="#64748b">
                {formatMoisLabel(d.mois)}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

/** Barres empilées présents / absents par mois */
export function StackedPresenceChart({ data, height = 160 }) {
  if (!data?.length) return <Empty label="Aucun pointage sur la période" />
  const max = Math.max(...data.map(d => (d.presents || 0) + (d.absents || 0)), 1)
  const barW = 28
  const gap = 10
  const padL = 36
  const w = padL + data.length * (barW + gap) + 16

  return (
    <div>
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.5rem', fontSize: '0.75rem' }}>
        <span><span style={{ display: 'inline-block', width: 10, height: 10, background: '#2277C1', borderRadius: 2, marginRight: 4 }} />Présents</span>
        <span><span style={{ display: 'inline-block', width: 10, height: 10, background: '#C62828', borderRadius: 2, marginRight: 4 }} />Absents</span>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <svg width={Math.max(w, 360)} height={height + 44} style={{ display: 'block' }}>
          {data.map((d, i) => {
            const pres = d.presents || 0
            const abs = d.absents || 0
            const total = pres + abs
            const presH = total ? Math.round((pres / max) * (height - 20)) : 0
            const absH = total ? Math.round((abs / max) * (height - 20)) : 0
            const x = padL + i * (barW + gap)
            const baseY = height
            return (
              <g key={i}>
                {total === 0 ? (
                  <rect x={x} y={baseY - 2} width={barW} height={2} rx={2} fill="#e2e8f0" />
                ) : (
                  <>
                    {absH > 0 && (
                      <rect x={x} y={baseY - absH - presH} width={barW} height={absH} rx={absH && !presH ? 4 : 0} fill="#C62828" opacity={0.85} />
                    )}
                    {presH > 0 && (
                      <rect x={x} y={baseY - presH} width={barW} height={presH} rx={4} fill="#2277C1" opacity={0.88} />
                    )}
                    <text x={x + barW / 2} y={baseY - presH - absH - 4} textAnchor="middle" fontSize={8} fill="#64748b">{total}</text>
                  </>
                )}
                <text x={x + barW / 2} y={height + 16} textAnchor="middle" fontSize={8} fill="#64748b">
                  {formatMoisLabel(d.mois)}
                </text>
              </g>
            )
          })}
        </svg>
      </div>
    </div>
  )
}

export function TauxBar({ value, small }) {
  const col = value>=70 ? '#2277C1' : value>=40 ? '#F5B100' : '#C62828'
  return (
    <div style={{display:'flex',alignItems:'center',gap:'0.4rem'}}>
      <div style={{flex:1,background:'#f1f5f9',borderRadius:4,height:small?6:9,overflow:'hidden',minWidth:50}}>
        <div style={{width:`${value}%`,height:'100%',background:col,borderRadius:4}}/>
      </div>
      <b style={{fontSize:'0.8rem',color:col,minWidth:38}}>{value}%</b>
    </div>
  )
}

// ── KPI Card ──────────────────────────────────────────────────────────────────

// ── Chart Card ────────────────────────────────────────────────────────────────
export function Card({ title, icon, children, col }) {
  return (
    <div style={{background:'#fff',borderRadius:12,padding:'1.1rem 1.3rem',boxShadow:'0 1px 4px rgba(0,0,0,0.07)',gridColumn:col}}>
      <h4 style={{fontSize:'0.85rem',fontWeight:700,color:'#1e293b',marginBottom:'0.85rem',display:'flex',alignItems:'center',gap:'0.35rem'}}>
        <i className={`bi ${icon}`} style={{color:'var(--navy)'}}/>
        {title}
      </h4>
      {children}
    </div>
  )
}

export function Kpi({ icon, label, value, color, sub, help }) {
  return (
    <div style={{background:'#fff',borderRadius:12,padding:'1.1rem 1.3rem',display:'flex',alignItems:'center',gap:'0.9rem',boxShadow:'0 1px 4px rgba(0,0,0,0.07)',borderLeft:`4px solid ${color}`}}>
      <div style={{width:42,height:42,borderRadius:'50%',background:color+'1a',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0}}>
        <i className={`bi ${icon}`} style={{fontSize:'1.2rem',color}}/>
      </div>
      <div>
        <div style={{fontSize:'1.55rem',fontWeight:800,color:'#1e293b',lineHeight:1}}>{value??'—'}</div>
        <div style={{fontSize:'0.77rem',color:'#64748b',marginTop:'0.15rem',display:'flex',alignItems:'center',gap:'0.25rem'}}>
          {label}
          {help && (
            <i className="bi bi-info-circle" title={help} style={{fontSize:'0.72rem',color:'#94a3b8',cursor:'help'}}/>
          )}
        </div>
        {sub && <div style={{fontSize:'0.72rem',color:'#94a3b8'}}>{sub}</div>}
      </div>
    </div>
  )
}
