/** FicheCompte — identité, rôles, dérogations, délégations, journal. */
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { recupererCompte, changerStatutCompte, messageErreur } from '@/services/habilitations'
import { useToast } from '@/context/ToastContext'
import { BadgeCanal, BadgeSensible, BadgeStatut, EnChargement } from './partages'
import MotifModal from './MotifModal'
import './habilitations.css'

const TRANSITIONS = [
  { transition: 'suspendre', label: 'Suspendre', variant: 'danger' },
  { transition: 'desactiver', label: 'Désactiver', variant: 'danger' },
  { transition: 'verrouiller', label: 'Verrouiller', variant: 'danger' },
  { transition: 'activer', label: 'Réactiver / activer', variant: 'success' },
]

function Section({ titre, valeur, enfants }) {
  return (
    <div className="hab-carte">
      <h3 className="h6">{titre}</h3>
      {valeur ? <p className="hab-muted mb-0">{valeur}</p> : enfants}
    </div>
  )
}

export default function FicheCompte() {
  const { id } = useParams()
  const { showToast } = useToast()
  const [compte, setCompte] = useState(null)
  const [erreur, setErreur] = useState('')
  const [action, setAction] = useState(null)

  const charger = () => recupererCompte(id).then(setCompte).catch((e) => setErreur(messageErreur(e)))
  // Rechargement uniquement au changement d'identifiant de compte.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { charger() }, [id])

  const confirmer = async (motif) => {
    try {
      await changerStatutCompte(id, action.transition, motif)
      showToast('Statut mis à jour.', 'success')
      setAction(null)
      charger()
    } catch (e) {
      showToast(messageErreur(e), 'error')
    }
  }

  if (erreur) return <p className="text-danger">{erreur}</p>
  if (!compte) return <EnChargement message="Chargement du compte…" />
  const p = compte.personne || {}

  return (
    <section data-testid="fiche-compte">
      <div className="hab-carte d-flex justify-content-between align-items-start">
        <div>
          <h2 className="h5 mb-1">
            {p.prenoms} {p.nom} <BadgeStatut statut={compte.statut} />
            {compte.nb_roles_sensibles > 0 && <BadgeSensible />}
          </h2>
          <div className="hab-muted">{compte.username} · {compte.email} · <BadgeCanal canal={compte.canal} /></div>
          <div className="hab-muted">Rôle d'accès actuel (provisoire) : {compte.role_legacy}</div>
          {p.matricule && <div className="hab-muted">Matricule personne : {p.matricule}{p.service ? ` · ${p.service}` : ''}</div>}
        </div>
        <div>
          <Link className="btn btn-success btn-sm" to={`/administration/comptes/${id}/modifier`}>
            <i className="bi bi-pencil-square me-1" />Modifier les droits
          </Link>
        </div>
      </div>

      <Section titre={`Rôles et périmètres actifs (${compte.roles_actifs.length})`}>
        <table className="hab-table">
          <thead><tr><th>Rôle</th><th>Niveau</th><th>Sensible</th><th>Périmètres</th><th>Validé</th></tr></thead>
          <tbody>
            {compte.roles_actifs.map((r) => (
              <tr key={r.id}>
                <td>{r.role_libelle} <code className="small">{r.role}</code></td>
                <td>{r.niveau}</td>
                <td>{r.sensible ? <BadgeSensible avecLabel={false} /> : '—'}</td>
                <td>{(r.perimetres || []).map((x) => x.libelle || x.reference_lisible).join(', ') || '—'}</td>
                <td>{r.validee ? 'Oui' : 'Non'}</td>
              </tr>
            ))}
            {compte.roles_actifs.length === 0 && <tr><td colSpan="5" className="hab-muted">Aucun rôle actif.</td></tr>}
          </tbody>
        </table>
        {compte.roles_inactifs?.length > 0 && (
          <details className="mt-2">
            <summary className="hab-muted">Rôles passés / révoqués ({compte.roles_inactifs.length})</summary>
            <ul className="small mb-0">{compte.roles_inactifs.map((r) => <li key={r.id}>{r.role} — {r.statut}</li>)}</ul>
          </details>
        )}
      </Section>

      <Section titre={`Dérogations (${compte.derogations?.length || 0})`}>
        {compte.derogations?.length ? (
          <ul className="mb-0">
            {compte.derogations.map((d) => (
              <li key={d.id}>{d.sens === 'OCTROI' ? 'Octroi' : 'Retrait'} de <code>{d.permission}</code> — {d.statut}</li>
            ))}
          </ul>
        ) : <p className="hab-muted mb-0">Aucune dérogation.</p>}
      </Section>

      <Section titre={`Délégations (${(compte.delegations_recues?.length || 0)})`}>
        {compte.delegations_recues?.length ? (
          <ul className="mb-0">
            {compte.delegations_recues.map((d) => (
              <li key={d.id}>De {d.delegant} jusqu'au {d.date_fin} — {d.statut}</li>
            ))}
          </ul>
        ) : <p className="hab-muted mb-0">Aucune délégation reçue.</p>}
      </Section>

      <Section titre="Chronologie (journal)">
        {compte.journal?.length ? (
          <table className="hab-table">
            <thead><tr><th>Date</th><th>Événement</th><th>Motif</th></tr></thead>
            <tbody>
              {compte.journal.map((e) => (
                <tr key={e.numero}><td>{e.horodatage.slice(0, 16).replace('T', ' ')}</td><td>{e.type_libelle}</td><td>{e.motif}</td></tr>
              ))}
            </tbody>
          </table>
        ) : <p className="hab-muted mb-0">Aucun événement.</p>}
      </Section>

      <div className="hab-carte">
        <h3 className="h6">Actions sur le statut</h3>
        {TRANSITIONS.map((t) => (
          <button key={t.transition} className={`btn btn-sm btn-${t.variant === 'danger' ? 'outline-danger' : 'outline-success'} me-2`}
                  data-testid={`action-${t.transition}`}
                  onClick={() => setAction(t)}>{t.label}</button>
        ))}
      </div>

      {action && (
        <MotifModal
          titre={action.label}
          action={`${action.label} le compte ${compte.username}`}
          consequences="Cette action est tracée au journal immuable ; elle peut empêcher la connexion."
          variant={action.variant}
          onConfirmer={confirmer}
          onAnnuler={() => setAction(null)}
        />
      )}
    </section>
  )
}
