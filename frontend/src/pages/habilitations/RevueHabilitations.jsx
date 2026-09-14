/**
 * RevueHabilitations — CONSULTATION en U4. La campagne de revue signée
 * (confirmation/réduction/révocation par responsable, rapports archivés)
 * relève du prompt C5 / unité U7 : les actions sont volontairement absentes.
 */
import { useEffect, useState } from 'react'
import { recupererRevue } from '@/services/habilitations'
import { BadgeSensible, EnChargement } from './partages'
import './habilitations.css'

export default function RevueHabilitations() {
  const [revue, setRevue] = useState(null)

  useEffect(() => { recupererRevue().then(setRevue).catch(() => setRevue(null)) }, [])
  if (!revue) return <EnChargement />

  const groupes = Object.entries(revue.groupes)
  const total = groupes.reduce((n, [, comptes]) => n + comptes.length, 0)

  return (
    <section data-testid="ecran-revue">
      <div className="hab-carte">
        <h2 className="h5">Revue des habilitations</h2>
        <div className="hab-avertissement">
          <i className="bi bi-hourglass-split me-1" />
          {revue.message}
        </div>
        <p className="hab-muted mb-0">{total} compte(s) gouverné(s) réparti(s) par domaine responsable.</p>
      </div>
      {groupes.map(([responsable, comptes]) => (
        <div className="hab-carte" key={responsable}>
          <h3 className="h6">{responsable} <span className="hab-muted">({comptes.length})</span></h3>
          <table className="hab-table">
            <thead><tr><th>Compte</th><th>Nom</th><th>Statut</th><th>Rôles</th></tr></thead>
            <tbody>
              {comptes.map((c) => (
                <tr key={c.compte}>
                  <td>{c.username}</td>
                  <td>{[c.prenoms, c.nom].filter(Boolean).join(' ')}{c.sensible && <BadgeSensible />}</td>
                  <td>{c.statut}</td>
                  <td>{c.roles.join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      {groupes.length === 0 && (
        <div className="hab-carte hab-muted">Aucun compte gouverné pour l'instant.</div>
      )}
    </section>
  )
}
