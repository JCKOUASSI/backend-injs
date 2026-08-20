/** Module « Emplois du temps » — pilotage complet EPT-INJS. */
import { useCallback, useState } from 'react'
import PageHeader from '@app/components/common/PageHeader'
import useReferentiels from '../../hooks/useReferentiels'
import { Chargement } from '../../components/Badges'
import OngletConflits from './onglets/OngletConflits'
import OngletGeneration from './onglets/OngletGeneration'
import OngletGroupes from './onglets/OngletGroupes'
import OngletPeriodes from './onglets/OngletPeriodes'
import OngletPlanning from './onglets/OngletPlanning'
import OngletProgrammes from './onglets/OngletProgrammes'

const ONGLETS = [
  { id: 'planning', label: 'Planning', composant: OngletPlanning },
  { id: 'programmes', label: 'Programmes', composant: OngletProgrammes },
  { id: 'generation', label: 'Génération', composant: OngletGeneration },
  { id: 'conflits', label: 'Conflits', composant: OngletConflits },
  { id: 'periodes', label: 'Périodes & paramètres', composant: OngletPeriodes },
  { id: 'groupes', label: 'Groupes', composant: OngletGroupes },
]

export default function EmploiDuTemps() {
  const referentiels = useReferentiels()
  const [ongletActif, setOngletActif] = useState('planning')
  const [filtres, setFiltres] = useState({})
  const [version, setVersion] = useState(0)

  const rafraichir = useCallback(() => setVersion((valeur) => valeur + 1), [])

  const Composant = ONGLETS.find((onglet) => onglet.id === ongletActif).composant

  return (
    <div>
      <PageHeader
        title="Emplois du temps"
        subtitle="Périodes de formation, génération automatique, séances, présences et badgeage"
      />

      {referentiels.erreur && <div className="alert alert-danger">{referentiels.erreur}</div>}

      <div className="ept-tabs">
        {ONGLETS.map((onglet) => (
          <button
            key={onglet.id}
            type="button"
            className={`btn btn-sm ${ongletActif === onglet.id ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => setOngletActif(onglet.id)}
          >
            {onglet.label}
          </button>
        ))}
      </div>

      {referentiels.chargement ? (
        <Chargement />
      ) : (
        <Composant
          key={`${ongletActif}-${version}`}
          referentiels={referentiels}
          filtres={filtres}
          onFiltres={setFiltres}
          onRefresh={rafraichir}
        />
      )}
    </div>
  )
}
