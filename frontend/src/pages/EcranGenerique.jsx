import { useLocation } from 'react-router-dom'
import EcranRessource from '../components/generique/EcranRessource'
import EcranDocuments from '../components/generique/EcranDocuments'
import { useMenuAutorise } from '../hooks/useMenuAutorise'
import { ecranParId } from '../menu/ecrans'
import { ARBORESCENCE, PIED_DE_BARRE, aplatir } from '../menu/arborescence'
import { droitRequis } from '../menu/autorisation'

/**
 * Page hôte des **écrans génériques** de la navigation réorganisée.
 *
 * Elle fait trois choses, dans cet ordre :
 *
 * 1. **résout** le descripteur (`src/menu/ecrans.js`) à partir de l'identifiant
 *    porté par la route — une seule source pour le menu et les routes ;
 * 2. **revérifie l'autorisation** pour le chemin courant : une URL saisie à la
 *    main vers une entrée masquée par le menu affiche un refus explicite plutôt
 *    que des données. Cette défense en profondeur côté interface ne remplace
 *    jamais le contrôle serveur (règle S3 : chaque vue DRF garde ses
 *    `permission_classes`, et c'est elle qui décide) ;
 * 3. **rend** l'écran (liste, onglets, indicateurs ou génération de documents).
 */
export default function EcranGenerique({ id }) {
  const ecran = ecranParId(id)
  const location = useLocation()
  const { parChemin, source } = useMenuAutorise()

  if (!ecran) {
    return (
      <div className="alert alert-warning">
        <strong>Écran inconnu.</strong> Aucun descripteur ne correspond à
        l'identifiant <code>{id}</code>.
      </div>
    )
  }

  const entree = parChemin.get(location.pathname)
  if (!entree) {
    // Le droit requis est porté par l'entrée de menu (pas par le descripteur) :
    // on le retrouve dans l'arborescence complète, non filtrée.
    const entreeComplete = aplatir(ARBORESCENCE, PIED_DE_BARRE)
      .find((e) => e.ecran === id)
    const requis = droitRequis(entreeComplete)
    return (
      <div className="card border-warning">
        <div className="card-body">
          <h5 className="card-title">
            <i className="bi bi-shield-exclamation text-warning me-2"></i>
            Accès non autorisé
          </h5>
          <p className="mb-2">
            Cette entrée ne fait pas partie des droits affichés pour votre compte
            (source : <strong>{source === 'CURP' ? 'permissions effectives CURP' : 'capacités projetées'}</strong>).
            Le serveur reste seul juge : si vous pensez disposer de ce droit,
            contactez un administrateur d'habilitation.
          </p>
          {requis.curp.length > 0 && (
            <p className="small text-muted mb-1">
              Permissions CURP requises : {requis.curp.map((c) => <code key={c} className="me-1">{c}</code>)}
            </p>
          )}
          {requis.legacy.length > 0 && (
            <p className="small text-muted mb-0">
              Capacités requises : {requis.legacy.map((c) => <code key={c} className="me-1">{c}</code>)}
            </p>
          )}
        </div>
      </div>
    )
  }

  return (
    <div data-testid={`ecran-${id}`}>
      <div className="d-flex align-items-start justify-content-between mb-3">
        <div>
          <h4 className="mb-1">
            {ecran.icone && <i className={`bi ${ecran.icone} me-2 text-primary`}></i>}
            {ecran.titre}
          </h4>
          {ecran.introduction && (
            <p className="text-muted small mb-0" style={{ maxWidth: '70ch' }}>{ecran.introduction}</p>
          )}
        </div>
        {ecran.fil && <span className="badge text-bg-light border">{ecran.fil}</span>}
      </div>

      {ecran.type === 'documents'
        ? <EcranDocuments ecran={ecran} />
        : <EcranRessource ecran={ecran} cleBase={['ecran-generique', id]} />}
    </div>
  )
}
