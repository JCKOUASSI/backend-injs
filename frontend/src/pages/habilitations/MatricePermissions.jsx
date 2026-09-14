/** MatricePermissions — visualisation croisée rôle × module, filtrable, exportable. */
import { useEffect, useMemo, useState } from 'react'
import { recupererMatrice } from '@/services/habilitations'
import { EnChargement } from './partages'
import './habilitations.css'

function telechargerCsv(lignes, modules) {
  const entetes = ['role', ...modules.map((m) => m.code)]
  const corps = lignes.map((l) => [
    l.code,
    ...modules.map((m) => l.niveaux[m.code]?.niveau || ''),
  ])
  const csv = [entetes, ...corps].map((ligne) => ligne.join(';')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'matrice_habilitations_injs.csv'
  a.click()
  URL.revokeObjectURL(url)
}

export default function MatricePermissions() {
  const [matrice, setMatrice] = useState(null)
  const [filtre, setFiltre] = useState('')
  const [domaine, setDomaine] = useState('')

  useEffect(() => { recupererMatrice().then(setMatrice).catch(() => setMatrice(null)) }, [])

  const domaines = useMemo(
    () => (matrice ? Array.from(new Set(matrice.lignes.map((l) => l.domaine))) : []),
    [matrice],
  )
  const lignes = useMemo(() => {
    if (!matrice) return []
    return matrice.lignes.filter((l) =>
      (!domaine || l.domaine === domaine) &&
      (!filtre || `${l.code} ${l.libelle}`.toLowerCase().includes(filtre.toLowerCase())))
  }, [matrice, filtre, domaine])

  if (!matrice) return <EnChargement message="Chargement de la matrice…" />

  return (
    <section data-testid="ecran-matrice">
      <div className="hab-carte">
        <div className="d-flex justify-content-between align-items-center flex-wrap gap-2">
          <h2 className="h5 mb-0">Matrice rôle × module</h2>
          <button className="btn btn-outline-success btn-sm" data-testid="export-matrice"
                  onClick={() => telechargerCsv(matrice.lignes, matrice.modules)}>
            <i className="bi bi-download me-1" />Exporter (CSV)
          </button>
        </div>
        <p className="hab-muted mt-1 mb-2">
          Les niveaux provisoires (modules hors annexe A2, à valider à l'atelier J2) sont
          signalés par un contour pointillé. N0 lecture très limitée → N4 administration.
        </p>
        <div className="hab-filtres">
          <input className="form-control" placeholder="Rechercher un rôle…" value={filtre}
                 data-testid="filtre-matrice" onChange={(e) => setFiltre(e.target.value)} />
          <select className="form-select" value={domaine} onChange={(e) => setDomaine(e.target.value)}>
            <option value="">Tous domaines</option>
            {domaines.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div style={{ overflow: 'auto', maxHeight: '68vh' }}>
          <table className="hab-matrice">
            <thead>
              <tr>
                <th style={{ position: 'sticky', left: 0, background: '#f4f7fb' }}>Rôle</th>
                {matrice.modules.map((m) => <th key={m.code} title={m.libelle}>{m.code}</th>)}
              </tr>
            </thead>
            <tbody>
              {lignes.map((l) => (
                <tr key={l.code}>
                  <td style={{ position: 'sticky', left: 0, background: '#fff', textAlign: 'left', whiteSpace: 'nowrap' }}>
                    {l.sensible && <i className="bi bi-shield-exclamation text-danger me-1" title="Sensible" />}
                    {l.libelle}
                  </td>
                  {matrice.modules.map((m) => {
                    const case_ = l.niveaux[m.code]
                    if (!case_) return <td key={m.code}>—</td>
                    return (
                      <td key={m.code} className={`hab-niveau-${case_.niveau} ${case_.origine === 'J2' ? 'hab-provisoire' : ''}`}
                          title={case_.origine === 'J2' ? `Provisoire J2 — ${m.libelle}` : m.libelle}>
                        {case_.niveau}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
