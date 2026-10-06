/** CataloguePermissions — catalogue humain des permissions CURP
 * (module.ressource.action, criticité, rôles, impact).
 *
 * Additive : consomme l'API existante GET /api/habilitations/permissions/
 * (pagination serveur) et ouvre la vue d'impact de chaque permission
 * (?code=…). Aucune logique métier dupliquée.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listerPermissions } from '@/services/habilitations'
import { EnChargement } from './partages'
import SensibleBadge from './SensibleBadge'
import './habilitations.css'

export default function CataloguePermissions() {
  const [page, setPage] = useState(1)
  const [donnees, setDonnees] = useState(null)
  const [filtre, setFiltre] = useState('')
  const [erreur, setErreur] = useState('')

  useEffect(() => {
    listerPermissions(page)
      .then(setDonnees)
      .catch((e) => setErreur(
        e?.response?.data?.detail || 'Catalogue des permissions indisponible.'
      ))
  }, [page])

  if (erreur) {
    return (
      <section data-testid="ecran-catalogue-permissions">
        <div className="hab-carte hab-avertissement" data-testid="catalogue-erreur">
          {erreur}
        </div>
      </section>
    )
  }
  if (!donnees) {
    return (
      <section data-testid="ecran-catalogue-permissions">
        <EnChargement message="Chargement du catalogue…" />
      </section>
    )
  }

  const lignes = donnees.results.filter((p) =>
    !filtre || `${p.code} ${p.libelle} ${p.module}`
      .toLowerCase().includes(filtre.toLowerCase()))

  return (
    <section data-testid="ecran-catalogue-permissions">
      <div className="hab-carte">
        <h2 className="h5">
          <i className="bi bi-list-columns me-2" />Catalogue des permissions
        </h2>
        <p className="hab-muted">
          Décomposition humaine <code>module.ressource.action</code> du
          référentiel CURP. La criticité provient du référentiel chargé ; le
          lien d'impact ouvre la vue « qui est concerné » de chaque permission.
        </p>
        <input
          className="form-control mb-2"
          placeholder="Filtrer la page affichée par code, libellé ou module…"
          data-testid="catalogue-filtre"
          value={filtre}
          onChange={(e) => setFiltre(e.target.value)}
        />
        <table className="hab-table" data-testid="catalogue-table">
          <thead>
            <tr><th>Code</th><th>Libellé</th><th>Module</th><th>Sensibilité</th><th>Impact</th></tr>
          </thead>
          <tbody>
            {lignes.map((p) => (
              <tr key={p.code} data-testid={`catalogue-ligne-${p.code}`}>
                <td><code>{p.code}</code></td>
                <td>{p.libelle}</td>
                <td>{p.module}</td>
                <td>
                  <SensibleBadge type="permission" niveau={p.criticite} />
                  {p.necessite_motif && (
                    <span className="hab-muted ms-1" title="Motif obligatoire">
                      <i className="bi bi-chat-left-text" />
                    </span>
                  )}
                </td>
                <td>
                  <Link
                    className="hab-lien-impact"
                    title={`Impact de la permission ${p.code}`}
                    data-testid={`catalogue-impact-${p.code}`}
                    to={`/administration/comptes/impact-permission?code=${encodeURIComponent(p.code)}`}
                  >
                    <i className="bi bi-crosshair" aria-hidden="true" />
                  </Link>
                </td>
              </tr>
            ))}
            {lignes.length === 0 && (
              <tr><td colSpan="5" className="hab-muted">Aucune permission sur cette page ne correspond au filtre.</td></tr>
            )}
          </tbody>
        </table>
        <div className="d-flex justify-content-between align-items-center mt-2">
          <span className="hab-muted" data-testid="catalogue-total">
            {donnees.count} permissions au total — page {page} sur{' '}
            {Math.max(1, Math.ceil(donnees.count / 50))}
          </span>
          <div>
            <button className="btn btn-sm btn-outline-secondary me-1"
                    data-testid="catalogue-precedente"
                    disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Précédente
            </button>
            <button className="btn btn-sm btn-outline-secondary"
                    data-testid="catalogue-suivante"
                    disabled={page * 50 >= donnees.count}
                    onClick={() => setPage((p) => p + 1)}>
              Suivante
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}
