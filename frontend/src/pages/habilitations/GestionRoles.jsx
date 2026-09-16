/** GestionRoles — consultation du référentiel, description et titulaires. */
import { useEffect, useState } from 'react'
import { listerRolesCurp, recupererRole } from '@/services/habilitations'
import { libelleDomaine } from '@/utils/habilitations'
import { BadgeSensible, BadgeCanal, EnChargement } from './partages'
import './habilitations.css'

export default function GestionRoles() {
  const [roles, setRoles] = useState([])
  const [chargement, setChargement] = useState(true)
  const [detail, setDetail] = useState(null)
  const [filtre, setFiltre] = useState('')

  useEffect(() => { listerRolesCurp().then((r) => { setRoles(r); setChargement(false) }) }, [])

  const ouvrir = async (code) => {
    setDetail(await recupererRole(code))
  }
  const rolesFiltres = roles.filter((r) =>
    !filtre || `${r.code} ${r.libelle} ${r.domaine}`.toLowerCase().includes(filtre.toLowerCase()))

  if (chargement) return <EnChargement />
  return (
    <section data-testid="ecran-roles">
      <div className="hab-carte">
        <h2 className="h5">Référentiel des rôles ({roles.length})</h2>
        <p className="hab-muted">Rôles métier du recueil (annexe A1). Les rôles sensibles sont signalés en rouge.</p>
        <input className="form-control mb-2" placeholder="Filtrer par code, libellé ou domaine…"
               data-testid="filtre-roles" value={filtre}
               onChange={(e) => setFiltre(e.target.value)} />
        <div style={{ maxHeight: 620, overflow: 'auto' }}>
          <table className="hab-table">
            <thead><tr><th>Code</th><th>Libellé</th><th>Domaine</th><th>Niv.</th><th>Permissions</th><th>Disponible</th></tr></thead>
            <tbody>
              {rolesFiltres.map((r) => (
                <tr key={r.code} style={{ cursor: 'pointer' }} onClick={() => ouvrir(r.code)}
                    data-testid={`ligne-role-${r.code}`}>
                  <td><code>{r.code}</code>{r.sensible && <BadgeSensible avecLabel={false} />}</td>
                  <td>{r.libelle} <BadgeCanal canal={r.canal_impose} /></td>
                  <td>{libelleDomaine(r.domaine)}</td>
                  <td>{r.niveau_defaut}</td>
                  <td>{r.permissions_count}</td>
                  <td>{r.disponible ? 'Oui' : <span className="text-danger">Module absent</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {detail && (
        <div className="hab-carte" data-testid="detail-role">
          <h3 className="h6">{detail.libelle} <code>{detail.code}</code></h3>
          <p>{detail.description}</p>
          <div className="hab-muted">Domaine : {libelleDomaine(detail.domaine)} · Périmètre par défaut : {detail.perimetre_defaut}</div>
          {detail.incompatible_avec.length > 0 && (
            <div className="hab-avertissement">
              Incompatible avec : {detail.incompatible_avec.join(', ')}
            </div>
          )}
          <h4 className="h6 mt-2">Comptes titulaires ({detail.comptes_titulaires.length})</h4>
          {detail.comptes_titulaires.length === 0 ? <p className="hab-muted">Aucun titulaire pour l'instant.</p> : (
            <ul className="mb-0">
              {detail.comptes_titulaires.map((c) => (
                <li key={c.compte}>{c.prenoms} {c.nom} ({c.username}) — {c.statut}</li>
              ))}
            </ul>
          )}
          <button className="btn btn-secondary btn-sm mt-2" onClick={() => setDetail(null)}>Fermer</button>
        </div>
      )}
    </section>
  )
}
