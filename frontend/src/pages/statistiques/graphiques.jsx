/**
 * graphiques.jsx — Statistiques (INJS-LMD 2026)
 *
 * Primitives graphiques SVG natives du dashboard Statistiques, extraites de
 * `pages/Statistiques.jsx` (réduction des fichiers géants, garde-fou G.1).
 * Composants purement présentationnels : aucune donnée, aucun appel réseau.
 */
import { C } from './constantes'

export function Empty({ label = 'Aucune donnée' }) {
  return (
    <div style={{textAlign:'center',padding:'1.5rem',color:'#94a3b8',fontSize:'0.82rem'}}>
      <i className="bi bi-bar-chart" style={{fontSize:'1.8rem',display:'block',marginBottom:'0.4rem'}} />
      {label}
    </div>
  )
}

export function Donut({ data, labelKey, valueKey, size = 150 }) {
  if (!data?.length) return <Empty />
  const total = data.reduce((s,d) => s+d[valueKey], 0)
  if (!total) return <Empty />
  const r = size/2 - 18, cx = size/2, cy = size/2
  let a = -Math.PI/2
  const slices = data.map((d,i) => {
    const ang = (d[valueKey]/total)*2*Math.PI
    const x1 = cx+r*Math.cos(a), y1 = cy+r*Math.sin(a)
    a += ang
    return { ...d, x1, y1, x2: cx+r*Math.cos(a), y2: cy+r*Math.sin(a), large: ang>Math.PI?1:0, color: C[i%C.length] }
  })
  return (
    <div style={{display:'flex',alignItems:'center',gap:'1rem',flexWrap:'wrap'}}>
      <svg width={size} height={size} style={{flexShrink:0}}>
        {slices.map((s,i) => (
          <path key={i} d={`M${cx} ${cy} L${s.x1} ${s.y1} A${r} ${r} 0 ${s.large} 1 ${s.x2} ${s.y2}Z`}
            fill={s.color} opacity={0.88} stroke="#fff" strokeWidth={2}/>
        ))}
        <circle cx={cx} cy={cy} r={r*0.55} fill="#fff"/>
        <text x={cx} y={cy+5} textAnchor="middle" fontSize={13} fontWeight={700} fill="#1e293b">{total}</text>
      </svg>
      <ul style={{listStyle:'none',padding:0,margin:0,fontSize:'0.76rem',maxWidth:220}}>
        {slices.map((s,i) => (
          <li key={i} style={{display:'flex',alignItems:'center',gap:'0.35rem',marginBottom:'0.25rem'}}>
            <span style={{width:9,height:9,borderRadius:'50%',background:s.color,flexShrink:0,display:'inline-block'}}/>
            <span style={{color:'#475569',flex:1}}>{s[labelKey]}</span>
            <b style={{color:'#1e293b'}}>{s[valueKey]}</b>
            <span style={{color:'#94a3b8',fontSize:'0.7rem'}}>({Math.round(s[valueKey]/total*100)}%)</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function Bars({ data, labelKey, valueKey, color='#2277C1', height=150 }) {
  if (!data?.length) return <Empty />
  const max = Math.max(...data.map(d=>d[valueKey]),1)
  const barW = Math.max(18, Math.min(44, Math.floor(520/data.length)-8))
  const w = data.length*(barW+8)+32
  return (
    <div style={{overflowX:'auto'}}>
      <svg width={Math.max(w,260)} height={height+48} style={{display:'block'}}>
        {data.map((d,i) => {
          const bH = Math.max(4, Math.round((d[valueKey]/max)*height))
          const x = 16+i*(barW+8), y = height-bH+4
          return (
            <g key={i}>
              <rect x={x} y={y} width={barW} height={bH} rx={4} fill={color} opacity={0.85}/>
              <text x={x+barW/2} y={y-3} textAnchor="middle" fontSize={10} fill="#1e293b" fontWeight={600}>{d[valueKey]}</text>
              <text x={x+barW/2} y={height+18} textAnchor="middle" fontSize={9} fill="#64748b">
                {String(d[labelKey]).slice(0,9)}{String(d[labelKey]).length>9?'…':''}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

export function HBars({ data, labelKey, valueKey }) {
  if (!data?.length) return <Empty />
  const max = Math.max(...data.map(d=>d[valueKey]),1)
  return (
    <div style={{display:'flex',flexDirection:'column',gap:'0.55rem'}}>
      {data.map((d,i) => (
        <div key={i}>
          <div style={{display:'flex',justifyContent:'space-between',fontSize:'0.79rem',marginBottom:'0.18rem'}}>
            <span style={{color:'#334155',fontWeight:500}}>{d[labelKey]}</span>
            <b style={{color:C[i%C.length]}}>{d[valueKey]}</b>
          </div>
          <div style={{background:'#f1f5f9',borderRadius:6,height:9,overflow:'hidden'}}>
            <div style={{width:`${Math.round(d[valueKey]/max*100)}%`,height:'100%',background:C[i%C.length],borderRadius:6,transition:'width 0.5s ease'}}/>
          </div>
        </div>
      ))}
    </div>
  )
}

export function formatMoisLabel(cle) {
  if (!cle) return ''
  const [y, m] = String(cle).split('-').map(Number)
  const noms = ['janv.','févr.','mars','avr.','mai','juin','juil.','août','sept.','oct.','nov.','déc.']
  return `${noms[(m || 1) - 1]} ${String(y || '').slice(-2)}`
}

export function formatMoisLabelLong(cle) {
  if (!cle) return ''
  const [y, m] = String(cle).split('-').map(Number)
  const noms = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
  return `${noms[(m || 1) - 1]} ${y}`
}

export function TrendBadge({ pct }) {
  if (pct == null) return <span style={{fontSize:'0.72rem',color:'#94a3b8'}}>—</span>
  const up = pct >= 0
  return (
    <span style={{
      fontSize:'0.72rem',fontWeight:700,
      color: up ? '#2277C1' : '#C62828',
      background: (up ? '#2277C1' : '#C62828') + '14',
      borderRadius:20,padding:'0.12rem 0.45rem',
    }}>
      {up ? '▲' : '▼'} {Math.abs(pct)}%
    </span>
  )
}
