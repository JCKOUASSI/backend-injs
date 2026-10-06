/** Dashboard habilitations — vue d'ensemble (couche IMPACT, additive).
 *
 * Tous les indicateurs proviennent de l'endpoint /api/habilitations/dashboard/
 * (calculés côté Django depuis les données CURP réelles) : rien n'est inventé
 * ni recalculé côté frontend. Les tuiles ne cliquent QUE vers les routes
 * qui existent déjà dans la console.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { dashboardHabilitations, messageErreur } from '@/services/habilitations'
import { EnChargement } from './partages'
import './habilitations.css'

function Tuile({ libelle, valeur, vers, testid }) {
  const corps = (
    <div className="hab-carte text-center h-100" data-testid={testid}>
      <div className="hab-tuile-valeur">{valeur}</div>
      <div className="hab-muted">{libelle}</div>
    </div>
  )
  return vers
    ? <Link to={vers} className="hab-lien-tuile">{corps}</Link>
    : corps
}

export default function Dashboard() {
  const [donnees, setDonnees] = useState(null)
  const [erreur, setErreur] = useState('')

  useEffect(() => {
    dashboardHabilitations()
      .then(setDonnees)
      .catch((e) => setErreur(messageErreur(e, 'Dashboard indisponible.')))
  }, [])

  if (erreur) {
    return (
      <section data-testid="ecran-dashboard-hab">
        <div className="hab-carte hab-avertissement" data-testid="dashboard-erreur">
          {erreur}
        </div>
      </section>
    )
  }
  if (!donnees) {
    return (
      <section data-testid="ecran-dashboard-hab">
        <EnChargement message="Chargement du dashboard…" />
      </section>
    )
  }

  const lignesModule = donnees.permissions.par_module
  const maxModule = Math.max(1, ...lignesModule.map((l) => l.total))

  return (
    <section data-testid="ecran-dashboard-hab">
      <div className="hab-carte">
        <h2 className="h5">
          <i className="bi bi-speedometer2 me-2" />Dashboard des habilitations
        </h2>
        <p className="hab-muted mb-0">
          Vue d'ensemble dérivée des données CURP réelles. Date de référence :{' '}
          {donnees.date_reference}.
        </p>
      </div>

      <div className="hab-grille">
        <Tuile libelle="Comptes" valeur={donnees.comptes.total} vers="/administration/comptes" testid="dash-comptes" />
        <Tuile libelle="Comptes actifs" valeur={donnees.comptes.actifs} testid="dash-comptes-actifs" />
        <Tuile libelle="Rôles" valeur={donnees.roles.total} vers="/administration/comptes/roles" testid="dash-roles" />
        <Tuile libelle="Rôles sensibles" valeur={donnees.roles.sensibles} vers="/administration/comptes/roles" testid="dash-roles-sensibles" />
        <Tuile libelle="Permissions" valeur={donnees.permissions.total} vers="/administration/comptes/permissions" testid="dash-permissions" />
        <Tuile libelle="Permissions sensibles" valeur={donnees.permissions.sensibles} vers="/administration/comptes/permissions" testid="dash-permissions-sensibles" />
        <Tuile libelle="Comptes privilégiés" valeur={donnees.comptes_privileges} testid="dash-privileges" />
        <Tuile libelle="Dérogations actives" valeur={donnees.derogations.octrois + donnees.derogations.retraits} vers="/administration/comptes/derogations" testid="dash-derogations" />
        <Tuile libelle="Délégations actives" valeur={donnees.delegations.actives} vers="/administration/comptes/delegations" testid="dash-delegations" />
        <Tuile libelle="Provisionnement en attente" valeur={donnees.provisionnement.propositions_en_attente} vers="/administration/comptes/provisionnement" testid="dash-provisionnement" />
      </div>

      <div className="hab-carte">
        <h4 className="h6">Répartition des permissions par module</h4>
        <div data-testid="dash-par-module">
          {lignesModule.map((ligne) => (
            <div key={ligne.module} className="hab-barre-ligne">
              <span className="hab-barre-libelle">{ligne.module}</span>
              <span className="hab-barre-piste">
                <span
                  className="hab-barre"
                  style={{ width: `${Math.round((ligne.total / maxModule) * 100)}%` }}
                />
              </span>
              <span className="hab-barre-total">{ligne.total}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="hab-carte">
        <h4 className="h6">Dernières actions d'administration</h4>
        {donnees.dernieres_actions.length === 0 ? (
          <p className="hab-muted" data-testid="dash-journal-vide">
            Aucune action enregistrée.
          </p>
        ) : (
          <table className="hab-table" data-testid="dash-journal">
            <thead>
              <tr><th>#</th><th>Date</th><th>Action</th><th>Acteur</th><th>Objet</th></tr>
            </thead>
            <tbody>
              {donnees.dernieres_actions.map((e) => (
                <tr key={e.numero}>
                  <td>{e.numero}</td>
                  <td>{e.horodatage.replace('T', ' ').slice(0, 19)}</td>
                  <td>{e.type_libelle}</td>
                  <td>{e.acteur || '—'}</td>
                  <td>{e.objet_libelle || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  )
}
