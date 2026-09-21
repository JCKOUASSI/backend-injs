/**
 * bilan-fac.jsx — Statistiques (INJS-LMD 2026)
 *
 * Bilan FAC : tableaux de synthèse (point global, VH par grade, absents
 * notoires, modules) et leur panneau à sous-onglets. Extrait de
 * `pages/Statistiques.jsx` (réduction des fichiers géants, garde-fou G.1).
 *
 * API publique du module : BilanFACPanel. Les tableaux et les constantes de
 * style (FAC_TH*, FAC_TD*, fmtVH, fmtTauxPct, FAC_SOUS_ONGLETS) ne servent
 * qu'en interne.
 */
import { useEffect, useState } from 'react'
import { Empty } from './graphiques'
import { PJ_EXPORT_FORMATS } from './constantes'
import { normalizeJustificatifs } from './justificatifs'

const FAC_SOUS_ONGLETS = [
  { id: 'point_global',    label: 'Point global',       icon: 'bi-table' },
  { id: 'vh_par_groupe',   label: 'Volume horaire',     icon: 'bi-clock-history' },
  { id: 'absents',         label: 'Absents notoires',   icon: 'bi-person-x-fill' },
  { id: 'modules',         label: 'État des modules',   icon: 'bi-check2-square' },
]

export function fmtVH(n) {
  if (n == null) return '—'
  const v = Number(n)
  return v === Math.round(v) ? String(Math.round(v)) : v.toFixed(2)
}

export function fmtTauxPct(n, decimals = 2) {
  if (n == null) return '—'
  return `${Number(n).toFixed(decimals).replace('.', ',')} %`
}

const FAC_TH = {
  padding: '0.4rem 0.35rem',
  border: '1px solid #000',
  fontWeight: 700,
  fontSize: '0.6rem',
  textAlign: 'center',
  verticalAlign: 'middle',
  lineHeight: 1.2,
  background: '#FCEFD6',
  whiteSpace: 'normal',
}
const FAC_TH_DARK = { ...FAC_TH, background: '#F4CF84' }
const FAC_TH_YELLOW = { ...FAC_TH, background: '#EDB131', color: '#fff' }
const FAC_TD = {
  padding: '0.45rem 0.35rem',
  border: '1px solid #000',
  textAlign: 'center',
  verticalAlign: 'middle',
  fontSize: '0.75rem',
  fontWeight: 700,
  background: '#FFFDF5',
}
const FAC_TD_BLUE = { ...FAC_TD, background: '#DDEBF7' }
const FAC_TD_YELLOW = { ...FAC_TD, background: '#FFE566' }
const FAC_TD_BLUE_SOFT = { ...FAC_TD, background: '#DAE7EF' }
const FAC_TD_RED = { ...FAC_TD, background: '#FCEFD6' }
const FAC_TD_TEXT = { ...FAC_TD, textAlign: 'left', fontWeight: 500, fontSize: '0.7rem' }

function BilanFACPointGlobalTable({ data, onMetaChange }) {
  const lignesRaw = data?.lignes || []
  const totaux = data?.totaux || {}

  const [justifByGrade, setJustifByGrade] = useState({})
  const [difficultesByGrade, setDifficultesByGrade] = useState({})

  const updateJustif = (grade, text) => {
    setJustifByGrade(prev => ({ ...prev, [grade]: text }))
  }

  const updateDifficultes = (grade, text) => {
    setDifficultesByGrade(prev => ({ ...prev, [grade]: text }))
  }

  useEffect(() => {
    setJustifByGrade({})
    setDifficultesByGrade({})
  }, [data?.formation_id, data?.annee, data?.date_generation])

  useEffect(() => {
    onMetaChange?.({ justificatifs: justifByGrade, difficultes: difficultesByGrade })
  }, [justifByGrade, difficultesByGrade, onMetaChange])

  // Agréger les lignes par grade (évite les doublons)
  const lignesMap = new Map()
  for (const l of lignesRaw) {
    const grade = l.grade?.trim()
    if (!grade) continue
    if (!lignesMap.has(grade)) {
      lignesMap.set(grade, { ...l, grade })
    } else {
      const existing = lignesMap.get(grade)
      // Sommer les valeurs numériques. L'effectif auditeurs est cumulé à part
      // (ci-dessous) : sa valeur courante sert de poids aux moyennes, donc le
      // sommer ici (via une clé) fausserait les poids en comptant la nouvelle
      // ligne deux fois.
      const sumKeys = ['effectif_secretariat', 'nb_encadrants', 'nb_groupes',
        'absents_notoires', 'groupes_termines', 'vh_total', 'vh_epuise']
      for (const k of sumKeys) {
        existing[k] = (existing[k] || 0) + (l[k] || 0)
      }
      // Moyenne pondérée pour les taux ; n1 = effectif déjà cumulé, n2 =
      // effectif de la ligne fusionnée. Le cumul de l'effectif est posé APRÈS
      // lecture des poids (§10.15, corrigé au LOT 44 : la clé erronée
      // 'effectif_étudiants' laissait l'effectif figé à la première ligne).
      const n1 = existing.effectif_auditeurs || 0
      const n2 = l.effectif_auditeurs || 0
      const total = n1 + n2
      existing.effectif_auditeurs = total
      if (total > 0) {
        const w1 = n1 / total
        const w2 = n2 / total
        existing.taux_participation = (existing.taux_participation || 0) * w1 + (l.taux_participation || 0) * w2
        existing.taux_absents_notoires = (existing.taux_absents_notoires || 0) * w1 + (l.taux_absents_notoires || 0) * w2
        existing.taux_presence_cours = (existing.taux_presence_cours || 0) * w1 + (l.taux_presence_cours || 0) * w2
        existing.taux_absence_cours = (existing.taux_absence_cours || 0) * w1 + (l.taux_absence_cours || 0) * w2
        existing.taux_exec_vh = (existing.taux_exec_vh || 0) * w1 + (l.taux_exec_vh || 0) * w2
      }
      // Fusionner les justificatifs (legacy liste → ignorée, champ libre côté UI)
      existing.justificatifs = existing.justificatifs || ''
    }
  }
  const lignes = Array.from(lignesMap.values()).sort((a, b) => a.grade.localeCompare(b.grade))

  const pctStr = (n) => {
    if (n == null) return '—'
    const v = Number(n)
    if (v <= 1 && v >= 0 && String(n).indexOf('.') > -1) return `${(v * 100).toFixed(2).replace('.', ',')} %`
    return `${v.toFixed(2).replace('.', ',')} %`
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'collapse', minWidth: 1400, fontSize: '0.62rem', width: '100%' }}>
        <thead>
          <tr>
            <th style={{ ...FAC_TH, minWidth: 80 }}>CATÉGORIE / GRADE</th>
            <th style={FAC_TH}>EFFECTIF DES MEMBRES DE SECRÉTARIAT</th>
            <th style={FAC_TH}>EFFECTIF DES ENCADREURS</th>
            <th style={FAC_TH}>NOMBRE DE GROUPES</th>
            <th style={{ ...FAC_TH_DARK, minWidth: 60 }}>EFFECTIF TOTAL DES AUDITEURS</th>
            <th style={FAC_TH}>EFFECTIF TOTAL DES AUDITEURS ABSENTS NOTOIRES</th>
            <th style={FAC_TH}>GROUPES AYANT TERMINÉ LA FORMATION</th>
            <th style={{ ...FAC_TH, minWidth: 120 }}>JUSTIFICATIFS DES ABSENCES NOTOIRES</th>
            <th style={FAC_TH}>TAUX DE PARTICIPATION</th>
            <th style={FAC_TH}>TAUX DES AUDITEURS ABSENTS NOTOIRES</th>
            <th style={{ ...FAC_TH_YELLOW, minWidth: 55 }}>TOTAL VOLUME HORAIRE</th>
            <th style={{ ...FAC_TH_YELLOW, minWidth: 55 }}>TOTAL VOLUME HORAIRE ÉPUISÉ</th>
            <th style={{ ...FAC_TH_YELLOW }}>TAUX D&apos;EXÉCUTION DU VOLUME HORAIRE</th>
            <th style={{ ...FAC_TH, background: '#BDD7EE' }}>TAUX DE PRÉSENCE AUX COURS</th>
            <th style={{ ...FAC_TH, background: '#F8E0AD' }}>TAUX D&apos;ABSENCE AUX COURS</th>
            <th style={{ ...FAC_TH, minWidth: 140 }}>DIFFICULTÉS RENCONTRÉES</th>
          </tr>
        </thead>
        <tbody>
          {lignes.map((l, i) => (
            <tr key={l.grade || i}>
              <td style={{ ...FAC_TD, fontWeight: 800, background: '#FCEFD6' }}>
                {l.grade}
              </td>
              <td style={FAC_TD}>{l.effectif_secretariat ?? '—'}</td>
              <td style={FAC_TD}>{l.nb_encadrants ?? '—'}</td>
              <td style={FAC_TD}>{l.nb_groupes ?? '—'}</td>
              <td style={{ ...FAC_TD_BLUE, fontWeight: 800 }}>{l.effectif_auditeurs ?? '—'}</td>
              <td style={FAC_TD}>{l.absents_notoires ?? '—'}</td>
              <td style={FAC_TD_BLUE_SOFT}>{l.groupes_termines ?? '—'}</td>
              <td style={{ ...FAC_TD_TEXT, verticalAlign: 'top', padding: '0.35rem' }}>
                <textarea
                  className="form-control form-control-sm"
                  value={justifByGrade[l.grade] ?? normalizeJustificatifs(l.justificatifs)}
                  onChange={e => updateJustif(l.grade, e.target.value)}
                  placeholder="Justificatifs (saisie libre)…"
                  rows={4}
                  style={{
                    width: '100%',
                    minWidth: 110,
                    fontSize: '0.68rem',
                    lineHeight: 1.45,
                    resize: 'vertical',
                    border: '1px solid #cbd5e1',
                  }}
                />
              </td>
              <td style={FAC_TD_BLUE}>{pctStr(l.taux_participation)}</td>
              <td style={FAC_TD_RED}>{pctStr(l.taux_absents_notoires)}</td>
              <td style={{ ...FAC_TD, background: '#FCEFD6', fontWeight: 800 }}>{fmtVH(l.vh_total)}</td>
              <td style={{ ...FAC_TD, background: '#FCEFD6', fontWeight: 800 }}>{fmtVH(l.vh_epuise)}</td>
              <td style={{ ...FAC_TD, background: '#FCEFD6' }}>{pctStr(l.taux_exec_vh)}</td>
              <td style={{ ...FAC_TD, background: '#BDD7EE' }}>{pctStr(l.taux_presence_cours)}</td>
              <td style={{ ...FAC_TD, background: '#F8E0AD' }}>{pctStr(l.taux_absence_cours)}</td>
              <td style={{ ...FAC_TD_TEXT, verticalAlign: 'top', padding: '0.35rem' }}>
                <textarea
                  className="form-control form-control-sm"
                  value={difficultesByGrade[l.grade] ?? (l.difficultes || '')}
                  onChange={e => updateDifficultes(l.grade, e.target.value)}
                  placeholder="Difficultés rencontrées (saisie libre)…"
                  rows={4}
                  style={{
                    width: '100%',
                    minWidth: 120,
                    fontSize: '0.68rem',
                    lineHeight: 1.45,
                    resize: 'vertical',
                    border: '1px solid #cbd5e1',
                    color: '#C62828',
                  }}
                />
              </td>
            </tr>
          ))}
          {/* Ligne TOTAL */}
          <tr>
            <td style={{ ...FAC_TD_YELLOW, fontWeight: 800, textAlign: 'left' }}>TOTAL</td>
            <td style={FAC_TD_YELLOW}>{totaux.effectif_secretariat ?? '—'}</td>
            <td style={FAC_TD_YELLOW}>{totaux.nb_encadrants ?? '—'}</td>
            <td style={FAC_TD_YELLOW}>{totaux.nb_groupes ?? '—'}</td>
            <td style={{ ...FAC_TD_YELLOW, fontWeight: 800 }}>{totaux.effectif_auditeurs ?? '—'}</td>
            <td style={FAC_TD_YELLOW}>{totaux.absents_notoires ?? '—'}</td>
            <td style={FAC_TD_YELLOW}>{totaux.groupes_termines ?? '—'}</td>
            <td style={FAC_TD_YELLOW}>—</td>
            <td style={FAC_TD_YELLOW}>—</td>
            <td style={FAC_TD_YELLOW}>—</td>
            <td style={{ ...FAC_TD_YELLOW, fontWeight: 800 }}>{fmtVH(totaux.vh_total)}</td>
            <td style={{ ...FAC_TD_YELLOW, fontWeight: 800 }}>{fmtVH(totaux.vh_epuise)}</td>
            <td style={FAC_TD_YELLOW}>{pctStr(totaux.taux_exec_vh)}</td>
            <td style={FAC_TD_YELLOW}>—</td>
            <td style={FAC_TD_YELLOW}>—</td>
            <td style={FAC_TD_YELLOW}>—</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

function BilanFACVHParGradeTable({ vhParGrade }) {
  if (!vhParGrade?.length) return <Empty label="Aucune donnée de volume horaire"/>

  const VH_ROWS = [
    { key: 'vh_prevu',      label: 'VOLUME HORAIRE DU CYCLE DE FORMATION', style: FAC_TD },
    { key: 'vh_epuise',     label: 'VOLUME HORAIRE ÉPUISÉ',                style: FAC_TD },
    { key: 'taux_execution',label: "TAUX D'EXÉCUTION (%)",                 style: FAC_TD_BLUE_SOFT },
    { key: 'vh_restant',    label: 'VOLUME HORAIRE RESTANT',               style: FAC_TD },
    { key: 'taux_restant',  label: 'TAUX DU VOLUME HORAIRE RESTANT (%)',   style: FAC_TD_RED },
  ]

  return (
    <div>
      {vhParGrade.map(gradeBlock => {
        // Agréger les groupes identiques (sommer les VH)
        const groupesRaw = gradeBlock.groupes || []
        const groupesMap = new Map()
        for (const g of groupesRaw) {
          const grpName = (g.groupe || '').trim()
          if (!grpName) continue
          if (!groupesMap.has(grpName)) {
            groupesMap.set(grpName, { ...g, groupe: grpName })
          } else {
            const existing = groupesMap.get(grpName)
            existing.vh_prevu = (existing.vh_prevu || 0) + (g.vh_prevu || 0)
            existing.vh_epuise = (existing.vh_epuise || 0) + (g.vh_epuise || 0)
            existing.vh_restant = (existing.vh_restant || 0) + (g.vh_restant || 0)
          }
        }
        const groupes = Array.from(groupesMap.values()).sort((a, b) =>
          a.groupe.localeCompare(b.groupe, undefined, { numeric: true })
        )
        const recap = gradeBlock.recap || {}
        return (
          <div key={gradeBlock.grade} style={{ marginBottom: '2rem' }}>
            <div style={{
              fontWeight: 800, fontSize: '0.82rem', color: '#1e293b',
              marginBottom: '0.5rem', padding: '0.3rem 0.6rem',
              background: '#FCEFD6', borderRadius: 6, display: 'inline-block',
            }}>
              Grade {gradeBlock.grade}
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ borderCollapse: 'collapse', minWidth: 300, fontSize: '0.72rem' }}>
                <thead>
                  <tr>
                    <th style={{ ...FAC_TH, minWidth: 220, textAlign: 'left' }}>GROUPES</th>
                    {groupes.map(g => (
                      <th key={g.groupe} style={{ ...FAC_TH, minWidth: 55 }}>{g.groupe}</th>
                    ))}
                    <th style={{ ...FAC_TH_DARK, minWidth: 80 }}>RÉCAPITULATIF</th>
                  </tr>
                </thead>
                <tbody>
                  {VH_ROWS.map(row => (
                    <tr key={row.key}>
                      <td style={{ ...FAC_TD, textAlign: 'left', fontWeight: 600, background: '#FFF6CC' }}>
                        {row.label}
                      </td>
                      {groupes.map(g => {
                        const val = g[row.key]
                        const isRate = row.key.startsWith('taux')
                        return (
                          <td key={g.groupe} style={row.style}>
                            {isRate ? fmtTauxPct(val) : fmtVH(val)}
                          </td>
                        )
                      })}
                      <td style={{ ...FAC_TD_YELLOW, fontWeight: 800 }}>
                        {row.key.startsWith('taux') ? fmtTauxPct(recap[row.key]) : fmtVH(recap[row.key])}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )
      })}

      {/* Récapitulatif global */}
      {vhParGrade.length > 1 && (
        <div style={{ marginTop: '1rem' }}>
          <div style={{
            fontWeight: 800, fontSize: '0.82rem', color: '#fff',
            background: '#EDB131', borderRadius: 6, padding: '0.3rem 0.6rem',
            display: 'inline-block', marginBottom: '0.5rem',
          }}>
            RÉCAPITULATIF GLOBAL
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ borderCollapse: 'collapse', minWidth: 600, fontSize: '0.72rem' }}>
              <thead>
                <tr>
                  <th style={{ ...FAC_TH, textAlign: 'left', minWidth: 100 }}>CATÉGORIE</th>
                  <th style={FAC_TH}>VH CYCLE</th>
                  <th style={FAC_TH}>VH ÉPUISÉ</th>
                  <th style={FAC_TH}>TAUX D&apos;EXÉCUTION</th>
                  <th style={FAC_TH}>VH RESTANT</th>
                  <th style={FAC_TH}>TAUX VH RESTANT</th>
                </tr>
              </thead>
              <tbody>
                {vhParGrade.map(gb => (
                  <tr key={gb.grade}>
                    <td style={{ ...FAC_TD, textAlign: 'left', fontWeight: 700, background: '#FCEFD6' }}>
                      Grade {gb.grade}
                    </td>
                    <td style={FAC_TD}>{fmtVH(gb.recap.vh_prevu)}</td>
                    <td style={FAC_TD}>{fmtVH(gb.recap.vh_epuise)}</td>
                    <td style={FAC_TD_BLUE_SOFT}>{fmtTauxPct(gb.recap.taux_execution)}</td>
                    <td style={FAC_TD}>{fmtVH(gb.recap.vh_restant)}</td>
                    <td style={FAC_TD_RED}>{fmtTauxPct(gb.recap.taux_restant)}</td>
                  </tr>
                ))}
                <tr>
                  <td style={{ ...FAC_TD_YELLOW, fontWeight: 800, textAlign: 'left' }}>TOTAL</td>
                  <td style={{ ...FAC_TD_YELLOW, fontWeight: 800 }}>
                    {fmtVH(vhParGrade.reduce((s, g) => s + (g.recap.vh_prevu || 0), 0))}
                  </td>
                  <td style={{ ...FAC_TD_YELLOW, fontWeight: 800 }}>
                    {fmtVH(vhParGrade.reduce((s, g) => s + (g.recap.vh_epuise || 0), 0))}
                  </td>
                  <td style={FAC_TD_YELLOW}>
                    {(() => {
                      const tot = vhParGrade.reduce((s, g) => s + (g.recap.vh_prevu || 0), 0)
                      const epu = vhParGrade.reduce((s, g) => s + (g.recap.vh_epuise || 0), 0)
                      return tot ? fmtTauxPct(epu / tot * 100) : '—'
                    })()}
                  </td>
                  <td style={FAC_TD_YELLOW}>
                    {fmtVH(vhParGrade.reduce((s, g) => s + (g.recap.vh_restant || 0), 0))}
                  </td>
                  <td style={FAC_TD_YELLOW}>—</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function BilanFACAbsentsNotoiresTable({ absents }) {
  if (!absents?.length) return (
    <div style={{ textAlign: 'center', padding: '2rem', color: '#2277C1', fontSize: '0.85rem' }}>
      <i className="bi bi-check-circle" style={{ fontSize: '2rem', display: 'block', marginBottom: '0.5rem' }}/>
      Aucun absent notoire enregistré.
    </div>
  )

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'collapse', minWidth: 900, fontSize: '0.73rem', width: '100%' }}>
        <thead>
          <tr>
            <th style={{ ...FAC_TH, minWidth: 35 }}>N°</th>
            <th style={{ ...FAC_TH, minWidth: 130 }}>N° CONCOURS (MATRICULE)</th>
            <th style={{ ...FAC_TH, minWidth: 100 }}>NOM</th>
            <th style={{ ...FAC_TH, minWidth: 120 }}>PRÉNOMS</th>
            <th style={{ ...FAC_TH, minWidth: 160 }}>LIBELLÉ DU CONCOURS</th>
            <th style={{ ...FAC_TH, minWidth: 100 }}>CONTACTS</th>
            <th style={{ ...FAC_TH, minWidth: 70 }}>GRADE / GROUPE</th>
            <th style={{ ...FAC_TH, minWidth: 160 }}>OBSERVATIONS</th>
          </tr>
        </thead>
        <tbody>
          {absents.map((a, i) => (
            <tr key={a.matricule || i} style={{ background: i % 2 === 0 ? '#FFFDF5' : '#FFF9EC' }}>
              <td style={{ ...FAC_TD, fontWeight: 800 }}>{a.numero}</td>
              <td style={{ ...FAC_TD, fontFamily: 'monospace', fontSize: '0.68rem' }}>{a.matricule}</td>
              <td style={{ ...FAC_TD, textAlign: 'left', fontWeight: 700 }}>{a.nom}</td>
              <td style={{ ...FAC_TD, textAlign: 'left' }}>{a.prenom}</td>
              <td style={{ ...FAC_TD, textAlign: 'left', fontSize: '0.67rem' }}>{a.libelle_concours || '—'}</td>
              <td style={{ ...FAC_TD, fontFamily: 'monospace', fontSize: '0.68rem' }}>{a.contacts || '—'}</td>
              <td style={{ ...FAC_TD, fontWeight: 800 }}>
                {a.grade && a.groupe ? `${a.grade} / ${a.groupe}` : a.grade || a.groupe || '—'}
              </td>
              <td style={{ ...FAC_TD_TEXT, color: a.observations ? '#C62828' : '#94a3b8' }}>
                {a.observations || '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '0.5rem', textAlign: 'right' }}>
        {absents.length} absent{absents.length > 1 ? 's' : ''} notoire{absents.length > 1 ? 's' : ''}
      </div>
    </div>
  )
}

function BilanFACModulesTable({ modules }) {
  if (!modules?.length) return <Empty label="Aucun module trouvé"/>

  const grades = [...new Set(modules.map(m => m.grade).filter(Boolean))].sort()

  const STATUT_STYLE = {
    TERMINEE:  { bg: '#DAE7EF', color: '#1063c5', label: 'Terminé' },
    EN_COURS:  { bg: '#DDEBF7', color: '#1565C0', label: 'En cours' },
    PLANIFIEE: { bg: '#FFF6CC', color: '#F5B100', label: 'Planifié' },
    SUSPENDUE: { bg: '#FCEFD6', color: '#C62828', label: 'Suspendu' },
  }

  return (
    <div>
      {grades.map(grade => {
        const mods = modules.filter(m => m.grade === grade)
        return (
          <div key={grade} style={{ marginBottom: '2rem' }}>
            <div style={{
              fontWeight: 800, fontSize: '0.82rem', color: '#1e293b',
              marginBottom: '0.5rem', padding: '0.3rem 0.6rem',
              background: '#FCEFD6', borderRadius: 6, display: 'inline-block',
            }}>
              Grade {grade}
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ borderCollapse: 'collapse', minWidth: 400, fontSize: '0.72rem', width: '100%' }}>
                <thead>
                  <tr>
                    <th style={{ ...FAC_TH, textAlign: 'left', minWidth: 200 }}>MODULE</th>
                    <th style={FAC_TH}>GROUPE</th>
                    <th style={FAC_TH}>VH PRÉVU (h)</th>
                    <th style={FAC_TH}>VH RESTANT (h)</th>
                    <th style={FAC_TH}>DATE DÉBUT</th>
                    <th style={FAC_TH}>DATE FIN</th>
                    <th style={FAC_TH}>STATUT</th>
                  </tr>
                </thead>
                <tbody>
                  {mods.map((m, i) => {
                    const st = STATUT_STYLE[m.statut] || STATUT_STYLE.PLANIFIEE
                    return (
                      <tr key={m.id} style={{ background: i % 2 === 0 ? '#FFFDF5' : '#fff' }}>
                        <td style={{ ...FAC_TD, textAlign: 'left', fontWeight: 600, fontSize: '0.7rem' }}>{m.intitule}</td>
                        <td style={FAC_TD}>{m.groupe || '—'}</td>
                        <td style={FAC_TD}>{m.vh_prevu ? fmtVH(m.vh_prevu) : '—'}</td>
                        <td style={FAC_TD}>{m.vh_restant ? fmtVH(m.vh_restant) : '—'}</td>
                        <td style={FAC_TD}>{m.date_debut || '—'}</td>
                        <td style={FAC_TD}>{m.date_fin || '—'}</td>
                        <td style={{ ...FAC_TD, background: st.bg, color: st.color }}>
                          {st.label}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function BilanFACPanel({ data, sousOnglet, onChangeSousOnglet, onMetaChange, onExport, exportingFac }) {
  return (
    <div>
      {/* En-tête */}
      <div style={{
        background: 'linear-gradient(135deg,#FFFBF0 0%,#FEF7E2 100%)',
        borderRadius: 8, padding: '0.85rem 1rem', marginBottom: '1rem',
        border: '1px solid #FEE8AA',
      }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', gap: '0.75rem' }}>
          <div style={{ flex: '1 1 240px' }}>
            <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 800, color: '#1e293b' }}>
              <i className="bi bi-file-earmark-bar-graph me-2" style={{ color: '#EDB131' }}/>
              {data.titre}
            </h3>
            <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.4rem', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                <i className="bi bi-calendar3 me-1"/>{data.annee}
              </span>
              <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                <i className="bi bi-card-list me-1"/>Grades : {(data.grades || []).join(', ') || '—'}
              </span>
              <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                <i className="bi bi-person-x me-1"/>Absents notoires : {data.absents_notoires?.length ?? 0}
              </span>
              <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                <i className="bi bi-printer me-1"/>Généré le {data.date_generation}
              </span>
            </div>
          </div>
          {onExport && (
            <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', alignItems: 'center' }}>
              {PJ_EXPORT_FORMATS.map(({ fmt, icon, label, col }) => (
                <button
                  key={`fac-${fmt}`}
                  type="button"
                  className="btn btn-sm"
                  disabled={!!exportingFac}
                  style={{
                    background: col, color: '#fff', border: 'none', minWidth: 88,
                    opacity: exportingFac ? 0.65 : 1,
                  }}
                  onClick={() => onExport(fmt)}
                  title={`Exporter le bilan FAC (${label})`}
                >
                  {exportingFac === fmt ? (
                    <span className="spinner-border spinner-border-sm"/>
                  ) : (
                    <><i className={`bi ${icon} me-1`}/>{label}</>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Sous-onglets */}
      <div style={{ display: 'flex', gap: '0.3rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        {FAC_SOUS_ONGLETS.map(so => (
          <button
            key={so.id}
            type="button"
            onClick={() => onChangeSousOnglet(so.id)}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
              padding: '0.4rem 0.8rem', borderRadius: 7, cursor: 'pointer',
              fontSize: '0.79rem', fontWeight: 600,
              border: sousOnglet === so.id ? '2px solid #EDB131' : '1px solid #e2e8f0',
              background: sousOnglet === so.id ? '#FFFBF0' : '#fff',
              color: sousOnglet === so.id ? '#C8891B' : '#64748b',
            }}
          >
            <i className={`bi ${so.icon}`}/>{so.label}
          </button>
        ))}
      </div>

      {/* Contenu selon sous-onglet */}
      <div style={{
        background: '#fff', borderRadius: 8, boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
        border: '1px solid #f1f5f9', padding: '1rem',
      }}>
        {sousOnglet === 'point_global' && (
          <>
            <h4 style={{
              textAlign: 'center', fontWeight: 700, fontSize: '0.82rem',
              textDecoration: 'underline', textTransform: 'uppercase',
              marginBottom: '1rem', color: '#1e293b',
            }}>
              POINT GLOBAL — {data.formation}
            </h4>
            <BilanFACPointGlobalTable data={data.point_global} onMetaChange={onMetaChange} />
          </>
        )}

        {sousOnglet === 'vh_par_groupe' && (
          <>
            <h4 style={{
              textAlign: 'center', fontWeight: 700, fontSize: '0.82rem',
              textDecoration: 'underline', textTransform: 'uppercase',
              marginBottom: '1rem', color: '#1e293b',
            }}>
              TABLEAU MENSUEL RÉCAPITULANT L&apos;ÉVOLUTION DES HORAIRES DE COURS — {data.formation}
            </h4>
            <BilanFACVHParGradeTable vhParGrade={data.vh_par_grade} />
          </>
        )}

        {sousOnglet === 'absents' && (
          <>
            <h4 style={{
              textAlign: 'center', fontWeight: 700, fontSize: '0.82rem',
              textDecoration: 'underline', textTransform: 'uppercase',
              marginBottom: '1rem', color: '#1e293b',
            }}>
              ÉTAT DES AUDITEURS ABSENTS NOTOIRES — {data.formation}
            </h4>
            <BilanFACAbsentsNotoiresTable absents={data.absents_notoires} />
          </>
        )}

        {sousOnglet === 'modules' && (
          <>
            <h4 style={{
              textAlign: 'center', fontWeight: 700, fontSize: '0.82rem',
              textDecoration: 'underline', textTransform: 'uppercase',
              marginBottom: '1rem', color: '#1e293b',
            }}>
              ÉTAT D&apos;AVANCEMENT DES MODULES — {data.formation}
            </h4>
            <BilanFACModulesTable modules={data.modules_statuts} />
          </>
        )}
      </div>
    </div>
  )
}
