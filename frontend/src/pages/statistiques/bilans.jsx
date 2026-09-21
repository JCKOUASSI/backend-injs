/**
 * bilans.jsx — Statistiques (INJS-LMD 2026)
 *
 * Panneau « Bilans INJS » : effectifs par module et détail d'un bilan.
 *
 * Extrait de `pages/Statistiques.jsx` (réduction des fichiers géants,
 * garde-fou G.1). Les données arrivent par props : aucun appel réseau.
 */
import { useEffect, useState } from 'react'
import { RB_DIMENSIONS } from './constantes'
import { Empty } from './graphiques'
import { normalizeJustificatifs } from './justificatifs'

export function BilansEnsemblePanel({ items, bilans, filtres, dimension, onSelectIndividuel }) {
  const dimLabel = RB_DIMENSIONS.find(d => d.id === dimension)?.label || dimension

  const selectBilan = (bilanId) => {
    const idx = (bilans || []).findIndex(b => b.id === bilanId)
    if (idx >= 0) onSelectIndividuel(idx)
  }

  if (!items?.length) {
    return (
      <div style={{
        background: '#fff', borderRadius: 10, padding: '2rem', textAlign: 'center',
        boxShadow: '0 1px 4px rgba(0,0,0,0.07)',
      }}>
        <Empty label="Aucun tableau à afficher pour cette sélection"/>
      </div>
    )
  }

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
          <i className="bi bi-grid-3x3-gap me-2" style={{ color: 'var(--navy)' }}/>
          {items.length} tableau{items.length > 1 ? 'x' : ''} — {dimLabel}
        </h3>
        <p style={{ margin: '0.35rem 0 0', fontSize: '0.78rem', color: '#64748b' }}>
          Vue d&apos;ensemble ({filtres?.annee}{filtres?.periode_label ? ` · ${filtres.periode_label}` : ''}).
          Utilisez le panneau de gauche pour afficher un seul tableau en plein écran.
        </p>
      </div>
      <div style={{ maxHeight: '62vh', overflowY: 'auto', padding: '1rem' }}>
        {items.map((entry, i) => (
          <div
            key={entry.bilan_id}
            id={`rb-tableau-${entry.bilan_id}`}
            style={{
              marginBottom: i < items.length - 1 ? '1.75rem' : 0,
              paddingBottom: i < items.length - 1 ? '1.75rem' : 0,
              borderBottom: i < items.length - 1 ? '2px dashed #e2e8f0' : 'none',
            }}
          >
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
              gap: '0.5rem', marginBottom: '0.65rem', flexWrap: 'wrap',
            }}>
              <div>
                <div style={{ fontWeight: 800, fontSize: '0.88rem', color: '#1e293b' }}>
                  {entry.bilan?.libelle}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{entry.bilan?.sous_titre}</div>
              </div>
              <button
                type="button"
                className="btn btn-sm btn-outline-success"
                style={{ fontSize: '0.72rem', flexShrink: 0 }}
                onClick={() => selectBilan(entry.bilan_id)}
              >
                <i className="bi bi-arrows-fullscreen me-1"/>Plein écran
              </button>
            </div>
            <BilanDetailPanel
              bilan={entry.bilan}
              tableau={entry.tableau}
              filtres={filtres}
            />
          </div>
        ))}
      </div>
    </div>
  )
}

export function BilanEffectifsModuleTable({ data }) {
  const thBase = {
    padding: '0.45rem 0.5rem',
    border: '1px solid #000',
    fontWeight: 700,
    fontSize: '0.72rem',
    textAlign: 'center',
    verticalAlign: 'middle',
    lineHeight: 1.25,
  }
  const tdBase = {
    padding: '0.65rem 0.5rem',
    border: '1px solid #000',
    textAlign: 'center',
    verticalAlign: 'middle',
    fontSize: '0.85rem',
  }
  const Soit = ({ children }) => (
    <div style={{ fontSize: '0.72rem', fontWeight: 400, marginTop: '0.35rem', lineHeight: 1.35 }}>
      <span style={{ textDecoration: 'underline' }}>soit</span> {children}
    </div>
  )

  return (
    <div style={{ overflowX: 'auto' }}>
      <h3 style={{
        textAlign: 'center', fontWeight: 700, fontSize: '0.88rem',
        textDecoration: 'underline', textTransform: 'uppercase',
        margin: '0 0 0.85rem', color: '#1e293b', lineHeight: 1.35,
      }}>
        {data.titre}
      </h3>
      <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 620 }}>
        <thead>
          <tr>
            <th style={{ ...thBase, background: '#FCE7B4' }} rowSpan={2}>
              EFFECTIFS<br/>DES AUDITEURS
            </th>
            <th style={{ ...thBase, background: '#FCE7B4' }} rowSpan={2}>
              EFFECTIFS<br/>PRESENTS
            </th>
            <th style={{ ...thBase, background: '#D9D9D9' }} colSpan={2}>
              EFFECTIFS PRESENTS PAR GENRE
            </th>
            <th style={{ ...thBase, background: '#77BCE7' }} rowSpan={2}>
              ABSENTS
            </th>
          </tr>
          <tr>
            <th style={{ ...thBase, background: '#99CCFF' }}>MASCULIN</th>
            <th style={{ ...thBase, background: '#FFCCFF' }}>FEMININ</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style={tdBase}>
              <div style={{ fontWeight: 700, fontSize: '1rem' }}>{fmtNbFR(data.effectifs_auditeurs)}</div>
              {(data.masculin_inscrits != null || data.feminin_inscrits != null) && (
                <Soit>
                  {fmtNbFR(data.masculin_inscrits ?? 0)} H / {fmtNbFR(data.feminin_inscrits ?? 0)} F inscrits
                </Soit>
              )}
            </td>
            <td style={tdBase}>
              <div style={{ fontWeight: 700, fontSize: '1rem' }}>{fmtNbFR(data.effectifs_presents)}</div>
              <Soit>{fmtPctFR(data.pct_presents_total)}% de l&apos;effectif total</Soit>
            </td>
            <td style={tdBase}>
              <div style={{ fontWeight: 700, fontSize: '1rem' }}>{fmtNbFR(data.masculin)}</div>
              <Soit>{fmtPctFR(data.pct_masculin_presents)}% de l&apos;effectif des présents</Soit>
            </td>
            <td style={tdBase}>
              <div style={{ fontWeight: 700, fontSize: '1rem' }}>{fmtNbFR(data.feminin)}</div>
              <Soit>{fmtPctFR(data.pct_feminin_presents)}% de l&apos;effectif des présents</Soit>
            </td>
            <td style={tdBase}>
              <div style={{ fontWeight: 700, fontSize: '1rem' }}>{fmtNbFR(data.absents)}</div>
              <Soit>{fmtPctFR(data.pct_absents_total)}% de l&apos;effectif total</Soit>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

export function BilanDetailPanel({ bilan, tableau, filtres, justificatifsText, onJustificatifsChange }) {
  const dimLabel = RB_DIMENSIONS.find(d => d.id === bilan.dimension)?.label || bilan.dimension

  if (['module', 'matiere', 'categorie'].includes(bilan.dimension) && !tableau) {
    return (
      <div style={{
        background: '#fff', borderRadius: 10, padding: '2rem', textAlign: 'center',
        boxShadow: '0 1px 4px rgba(0,0,0,0.07)',
      }}>
        <Empty label="Aucune séance comptabilisable sur la période filtrée — aucun tableau d'effectifs."/>
      </div>
    )
  }

  if (bilan.dimension === 'formation' && tableau?.type === 'bilan_periode_formation') {
    return (
      <div style={{ background: '#fff', borderRadius: 10, padding: '1rem', boxShadow: '0 1px 4px rgba(0,0,0,0.07)', minWidth: 0 }}>
        <BilanPeriodeFormationTable
          data={tableau}
          justificatifsText={justificatifsText}
          onJustificatifsChange={onJustificatifsChange}
        />
      </div>
    )
  }

  if (bilan.dimension === 'module' && tableau?.type === 'effectifs_module') {
    return (
      <div style={{ background: '#fff', borderRadius: 10, padding: '1rem', boxShadow: '0 1px 4px rgba(0,0,0,0.07)', minWidth: 0 }}>
        <BilanEffectifsModuleTable data={tableau} />
      </div>
    )
  }

  if (bilan.dimension === 'matiere' && tableau?.type === 'effectifs_matiere') {
    return (
      <div style={{ background: '#fff', borderRadius: 10, padding: '1rem', boxShadow: '0 1px 4px rgba(0,0,0,0.07)', minWidth: 0 }}>
        {tableau.nb_groupes != null && (
          <p style={{ margin: '0 0 0.65rem', fontSize: '0.78rem', color: '#64748b' }}>
            Agrégation de <strong>{tableau.nb_groupes}</strong> groupe{tableau.nb_groupes > 1 ? 's' : ''} —
            étudiants uniques sur tous les groupes.
          </p>
        )}
        <BilanEffectifsModuleTable data={tableau} />
      </div>
    )
  }

  if (bilan.dimension === 'categorie' && tableau?.type === 'effectifs_categorie') {
    return (
      <div style={{ background: '#fff', borderRadius: 10, padding: '1rem', boxShadow: '0 1px 4px rgba(0,0,0,0.07)', minWidth: 0 }}>
        <BilanEffectifsModuleTable data={tableau} />
      </div>
    )
  }

  return (
    <div style={{background:'#fff',borderRadius:10,padding:'1rem',boxShadow:'0 1px 4px rgba(0,0,0,0.07)',minWidth:0}}>
      <div style={{background:'#1565C0',color:'#fff',textAlign:'center',padding:'0.5rem 0.75rem',borderRadius:8,fontWeight:700,fontSize:'0.82rem',marginBottom:'0.75rem'}}>
        BILAN — {dimLabel.toUpperCase()}
      </div>
      <h4 style={{margin:'0 0 0.35rem',fontWeight:800,color:'#1e293b',fontSize:'1rem'}}>{bilan.libelle}</h4>
      <p style={{margin:'0 0 0.75rem',fontSize:'0.78rem',color:'#64748b'}}>{bilan.sous_titre}</p>

      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(140px,1fr))',gap:'0.5rem',marginBottom:'0.85rem'}}>
        {[
          ['Période', bilan.periode_label || 'Toutes périodes'],
          ['Année', bilan.annee],
          ['Catégorie', bilan.categorie || '—'],
          bilan.formation ? ['Formation', bilan.formation] : null,
          bilan.module ? ['Module', bilan.module] : null,
          bilan.inscrits != null ? ['Inscrits', bilan.inscrits] : null,
          filtres?.calendrier ? ['Calendrier prév.', filtres.calendrier] : null,
        ].filter(Boolean).map(([l,v])=>(
          <div key={l} style={{background:'#f8fafc',borderRadius:8,padding:'0.5rem 0.65rem',border:'1px solid #e2e8f0'}}>
            <div style={{fontSize:'0.68rem',color:'#94a3b8',fontWeight:600}}>{l}</div>
            <div style={{fontSize:'0.85rem',fontWeight:700,color:'#1e293b',marginTop:'0.15rem'}}>{v}</div>
          </div>
        ))}
      </div>

      <div style={{
        background:'#fffceb', border:'1px dashed #fcdf4d', borderRadius:10,
        padding:'1.25rem', textAlign:'center',
      }}>
        <i className="bi bi-table" style={{fontSize:'2rem',color:'#F5B100',display:'block',marginBottom:'0.5rem'}}/>
        <p style={{margin:0,fontSize:'0.85rem',fontWeight:700,color:'#92660e'}}>
          Zone tableau bilan
        </p>
        <p style={{margin:'0.35rem 0 0',fontSize:'0.78rem',color:'#64748b',maxWidth:420,marginLeft:'auto',marginRight:'auto'}}>
          Le modèle INJS pour ce bilan ({dimLabel}) sera intégré ici dès validation du format.
          Les filtres sélectionnés ci-dessus s&apos;appliqueront au tableau affiché et aux exports Excel, PDF et Word.
        </p>
      </div>
    </div>
  )
}

export function fmtNbFR(n) {
  return new Intl.NumberFormat('fr-FR').format(n ?? 0)
}

export function fmtPctFR(n) {
  return (n ?? 0).toFixed(2).replace('.', ',')
}

// Exporté pour les tests unitaires de la synchro des justificatifs (§10.7) ;
// le rendu applicatif passe par BilanDetailPanel ci-dessus.
export function BilanPeriodeFormationTable({ data, justificatifsText = '', onJustificatifsChange }) {
  const th = {
    padding: '0.4rem 0.35rem',
    border: '1px solid #000',
    fontWeight: 700,
    fontSize: '0.65rem',
    textAlign: 'center',
    verticalAlign: 'middle',
    lineHeight: 1.2,
    background: '#FCE7B4',
  }
  const thDark = { ...th, background: '#F4CF84' }
  const td = {
    padding: '0.45rem 0.35rem',
    border: '1px solid #000',
    textAlign: 'center',
    verticalAlign: 'middle',
    fontSize: '0.78rem',
    fontWeight: 700,
    background: '#FFFDF5',
  }
  const tdBlue = { ...td, background: '#DDEBF7' }
  const tdTotal = { ...td, background: '#FFE566' }

  const [justifText, setJustifText] = useState(() => (
    justificatifsText || normalizeJustificatifs(data?.justificatifs)
  ))

  useEffect(() => {
    // `data?.justificatifs` est bien une dépendance voulue (écart §10.7 tranché
    // LOT 6) : un justificatif serveur reçu pour une ligne DÉJÀ affichée (mêmes
    // titre/formation/année, ex. rafraîchissement) doit synchroniser le champ.
    // La saisie reste prioritaire : quand le parent porte déjà un texte, le
    // `justificatifsText ||` court-circule la valeur serveur et n'écrase rien.
    setJustifText(justificatifsText || normalizeJustificatifs(data?.justificatifs))
  }, [data?.titre, data?.formation_id, data?.annee, data?.justificatifs, justificatifsText])

  const handleJustifChange = (e) => {
    const next = e.target.value
    setJustifText(next)
    onJustificatifsChange?.(next)
  }

  const Soit = ({ children }) => (
    <div style={{ fontSize: '0.65rem', fontWeight: 600, marginTop: '0.2rem' }}>
      <span style={{ textDecoration: 'underline' }}>Soit</span> {children}
    </div>
  )
  const InscritsCell = ({ t, full = true }) => (
    full ? (
      <>
        <div>{fmtNbFR(t.inscrits_actifs)} / {fmtNbFR(t.inscrits_reference)}</div>
        <Soit>{fmtPctFR(t.pct_inscrits)}%</Soit>
      </>
    ) : (
      <div>{fmtNbFR(t.inscrits_actifs)}</div>
    )
  )
  const AbsentsCell = ({ t, full = true }) => (
    full ? (
      <>
        <div>{fmtNbFR(t.absents_notoires)}</div>
        {t.inscrits_reference > 0 && (
          <Soit>{fmtPctFR(t.pct_absents)}% de l&apos;effectif</Soit>
        )}
      </>
    ) : (
      <div>{String(t.absents_notoires).padStart(2, '0')}</div>
    )
  )

  const firstRowKey = (() => {
    const l = data.lignes[0]
    if (!l) return null
    if (l.multi_grade && l.sous_lignes?.length) return `${l.categorie}-${l.sous_lignes[0].grade}`
    return l.categorie
  })()

  const nbJustifRows = data.lignes.reduce((acc, l) => {
    if (l.multi_grade && l.sous_lignes?.length) return acc + l.sous_lignes.length + 1
    return acc + 1
  }, 0) + 1

  const justificatifsCell = (
    <td rowSpan={nbJustifRows} style={{ ...td, fontWeight: 500, fontSize: '0.72rem', textAlign: 'left', verticalAlign: 'top', minWidth: 160, padding: '0.35rem' }}>
      <textarea
        className="form-control form-control-sm"
        value={justifText}
        onChange={handleJustifChange}
        placeholder={'Saisir les justificatifs…\n• Report de formation\n• Maladie'}
        rows={Math.max(5, nbJustifRows + 1)}
        style={{
          width: '100%',
          minHeight: 120,
          fontSize: '0.72rem',
          lineHeight: 1.45,
          resize: 'vertical',
          border: '1px solid #cbd5e1',
          background: '#fff',
        }}
      />
    </td>
  )

  let justifPlaced = false

  const renderDataRows = () => data.lignes.flatMap((ligne) => {
    const rows = []
    if (ligne.multi_grade && ligne.sous_lignes?.length) {
      ligne.sous_lignes.forEach((sl, idx) => {
        const rowKey = `${ligne.categorie}-${sl.grade}`
        rows.push(
          <tr key={rowKey}>
            {idx === 0 && (
              <td rowSpan={ligne.sous_lignes.length + 1} style={{ ...td, fontSize: '0.9rem' }}>
                {ligne.categorie}
              </td>
            )}
            <td style={td}>{sl.grade}</td>
            <td style={td}>{String(sl.nb_groupes).padStart(2, '0')}</td>
            {idx === 0 && (
              <>
                <td rowSpan={ligne.sous_lignes.length + 1} style={td}>
                  {String(ligne.totaux.nb_encadrants).padStart(2, '0')}
                </td>
                <td rowSpan={ligne.sous_lignes.length + 1} style={td}>
                  {ligne.totaux.effectif_secretariat}
                </td>
              </>
            )}
            <td style={td}><InscritsCell t={sl} full={false} /></td>
            <td style={tdBlue}>{fmtNbFR(sl.auditeurs_listes)}</td>
            <td style={td}><AbsentsCell t={sl} full={false} /></td>
            {rowKey === firstRowKey && !justifPlaced && (justifPlaced = true) && justificatifsCell}
          </tr>,
        )
      })
      rows.push(
        <tr key={`${ligne.categorie}-tot`}>
          <td style={{ ...td, fontStyle: 'italic', color: '#64748b' }}>Σ</td>
          <td style={td}>{String(ligne.totaux.nb_groupes).padStart(2, '0')}</td>
          <td style={td}><InscritsCell t={ligne.totaux} /></td>
          <td style={tdBlue}>{fmtNbFR(ligne.totaux.auditeurs_listes)}</td>
          <td style={td}><AbsentsCell t={ligne.totaux} /></td>
        </tr>,
      )
    } else {
      const t = ligne.totaux
      rows.push(
        <tr key={ligne.categorie}>
          <td colSpan={2} style={td}>{ligne.categorie}</td>
          <td style={td}>{String(t.nb_groupes).padStart(2, '0')}</td>
          <td style={td}>{String(t.nb_encadrants).padStart(2, '0')}</td>
          <td style={td}>{t.effectif_secretariat}</td>
          <td style={td}><InscritsCell t={t} /></td>
          <td style={tdBlue}>{fmtNbFR(t.auditeurs_listes)}</td>
          <td style={td}><AbsentsCell t={t} /></td>
          {ligne.categorie === firstRowKey && !justifPlaced && (justifPlaced = true) && justificatifsCell}
        </tr>,
      )
    }
    return rows
  })

  return (
    <div style={{ overflowX: 'auto' }}>
      <h3 style={{
        textAlign: 'center', fontWeight: 700, fontSize: '0.85rem',
        textDecoration: 'underline', textTransform: 'uppercase',
        margin: '0 0 0.85rem', color: '#1e293b', lineHeight: 1.35,
      }}>
        {data.titre}
      </h3>
      <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 980 }}>
        <thead>
          <tr>
            <th style={th} colSpan={2}>CATEGORIE / GRADE</th>
            <th style={th}>NBRE DE GRPES</th>
            <th style={th}>NBRE D&apos;ENCADRANTS</th>
            <th style={th}>EFFECTIF MEMBRE DE SECRETARIAT</th>
            <th style={thDark}>EFFECTIF DES INSCRITS AU {data.date_inscrits}</th>
            <th style={th}>EFFECTIF DES AUDITEURS SUR LES LISTES DE CLASSES</th>
            <th style={th}>EFFECTIF DES AUDITEURS ABSENTS NOTOIRES</th>
            <th style={th}>JUSTIFICATIFS DES ABSENCES NOTOIRES</th>
          </tr>
        </thead>
        <tbody>
          {renderDataRows()}
          <tr>
            <td colSpan={2} style={tdTotal}>TOTAL</td>
            <td style={tdTotal}>{String(data.total.nb_groupes).padStart(2, '0')}</td>
            <td style={tdTotal}>{String(data.total.nb_encadrants).padStart(2, '0')}</td>
            <td style={tdTotal}>{data.total.effectif_secretariat}</td>
            <td style={tdTotal}><InscritsCell t={data.total} /></td>
            <td style={tdTotal}>{fmtNbFR(data.total.auditeurs_listes)}</td>
            <td style={tdTotal}>{fmtNbFR(data.total.absents_notoires)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}
