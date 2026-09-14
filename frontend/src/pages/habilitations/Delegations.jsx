/** Delegations — création bornée, suivi et fin anticipée (U4). */
import { useEffect, useState } from 'react'
import {
  listerComptes, listerRolesCurp, listerDelegations, creerDelegation,
  terminerDelegation, messageErreur,
} from '@/services/habilitations'
import { useToast } from '@/context/ToastContext'
import { EnChargement } from './partages'
import MotifModal from './MotifModal'
import './habilitations.css'

const formVide = { delegant: '', delegataire: '', roles: [], date_fin: '', motif: '' }

export default function Delegations() {
  const { showToast } = useToast()
  const [comptes, setComptes] = useState([])
  const [roles, setRoles] = useState([])
  const [donnees, setDonnees] = useState(null)
  const [form, setForm] = useState(formVide)
  const [aTerminer, setATerminer] = useState(null)

  const charger = () => listerDelegations({ page_size: 200 }).then(setDonnees)
  useEffect(() => {
    listerComptes({ page_size: 500 }).then((d) => setComptes(d.results || []))
    listerRolesCurp().then(setRoles)
    charger()
  }, [])

  const maj = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const creer = async (e) => {
    e.preventDefault()
    if (form.delegant === form.delegataire) {
      showToast('Le délégant et le délégataire doivent être distincts.', 'error')
      return
    }
    try {
      await creerDelegation({
        delegant: Number(form.delegant), delegataire: Number(form.delegataire),
        roles: form.roles, date_fin: form.date_fin, motif: form.motif,
      })
      showToast('Délégation proposée.', 'success')
      setForm(formVide)
      charger()
    } catch (erreur) {
      showToast(messageErreur(erreur), 'error')
    }
  }
  const confirmerFin = async (motif) => {
    await terminerDelegation(aTerminer.id, motif)
    showToast('Délégation terminée.', 'success')
    setATerminer(null)
    charger()
  }

  if (!donnees) return <EnChargement />
  return (
    <section data-testid="ecran-delegations">
      <div className="hab-carte">
        <h2 className="h5">Délégations temporaires</h2>
        <p className="hab-muted">
          Toute délégation est bornée dans le temps. Le contrôle « on ne délègue que ce que l'on
          détient » et l'interdiction de re-délégation sont appliqués à l'unité U5.
        </p>
        <form className="row g-2" onSubmit={creer} data-testid="form-delegation">
          <div className="col-md-3">
            <label className="form-label">Délégant</label>
            <select className="form-select" required value={form.delegant} onChange={(e) => maj('delegant', e.target.value)}>
              <option value="">Compte…</option>
              {comptes.map((c) => <option key={c.id} value={c.id}>{c.username}</option>)}
            </select>
          </div>
          <div className="col-md-3">
            <label className="form-label">Délégataire</label>
            <select className="form-select" required value={form.delegataire} onChange={(e) => maj('delegataire', e.target.value)}>
              <option value="">Compte…</option>
              {comptes.map((c) => <option key={c.id} value={c.id}>{c.username}</option>)}
            </select>
          </div>
          <div className="col-md-3">
            <label className="form-label">Date de fin</label>
            <input type="date" className="form-control" required value={form.date_fin}
                   onChange={(e) => maj('date_fin', e.target.value)} />
          </div>
          <div className="col-md-3">
            <label className="form-label">Motif</label>
            <input className="form-control" required value={form.motif}
                   onChange={(e) => maj('motif', e.target.value)} />
          </div>
          <div className="col-12">
            <label className="form-label">Rôles délégués</label>
            <select multiple className="form-select" style={{ minHeight: 90 }}
                    onChange={(e) => maj('roles', Array.from(e.target.selectedOptions, (o) => o.value))}>
              {roles.map((r) => <option key={r.code} value={r.code}>{r.libelle}</option>)}
            </select>
          </div>
          <div className="col-12"><button className="btn btn-success btn-sm" data-testid="bouton-creer-delegation">Proposer la délégation</button></div>
        </form>
      </div>
      <div className="hab-carte">
        <table className="hab-table">
          <thead><tr><th>Délégant</th><th>Délégataire</th><th>Rôles</th><th>Fin</th><th>Statut</th><th></th></tr></thead>
          <tbody>
            {donnees.results.map((d) => (
              <tr key={d.id}>
                <td>{d.delegant}</td>
                <td>{d.delegataire}</td>
                <td>{(d.roles || []).join(', ') || '—'}</td>
                <td>{d.date_fin}</td>
                <td>{d.statut}</td>
                <td>{['PROPOSEE', 'ACTIVE'].includes(d.statut) && (
                  <button className="btn btn-sm btn-outline-danger" onClick={() => setATerminer(d)}>Terminer</button>)}</td>
              </tr>
            ))}
            {donnees.results.length === 0 && <tr><td colSpan="6" className="hab-muted text-center py-3">Aucune délégation.</td></tr>}
          </tbody>
        </table>
      </div>
      {aTerminer && (
        <MotifModal titre="Terminer la délégation" action={`Mettre fin à la délégation ${aTerminer.delegant} → ${aTerminer.delegataire}`}
                    consequences="Le délégataire perd dès l'enregistrement les droits correspondants."
                    onConfirmer={confirmerFin} onAnnuler={() => setATerminer(null)} />
      )}
    </section>
  )
}
