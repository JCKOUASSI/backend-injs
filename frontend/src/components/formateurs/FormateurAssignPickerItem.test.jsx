/**
 * Tests de la ligne du sélecteur d'enseignants (LOT 18).
 *
 * Composant pur : nom/spécialité, bouton d'assignation et gating en cas de
 * conflit d'emploi du temps (le message remplace le bouton).
 *
 * NB : le composant attend la prop `formateur` ; or ModuleDetail le câble avec
 * `enseignant` — c'est l'écart §10.12 (la modale plante tant que ce nom de
 * prop n'est pas aligné). Le présent teste le contrat déclaré par le
 * composant ; le test page [écart §10.12] documente la panne de câblage.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import FormateurAssignPickerItem from '@/components/formateurs/FormateurAssignPickerItem'

describe('FormateurAssignPickerItem', () => {
  it('affiche nom, prénom, spécialité et appelle onAssign(id) au clic', () => {
    const onAssign = vi.fn()
    render(
      <FormateurAssignPickerItem
        formateur={{ id: 202, nom: 'Koffi', prenom: 'Ado', specialite: 'LSF' }}
        onAssign={onAssign}
      />,
    )
    expect(screen.getByText('Koffi Ado')).toBeInTheDocument()
    expect(screen.getByText('LSF')).toBeInTheDocument()
    fireEvent.click(screen.getByTitle('Assigner cet enseignant'))
    expect(onAssign).toHaveBeenCalledWith(202)
    expect(onAssign).toHaveBeenCalledTimes(1)
  })

  it('masque le bouton et affiche le conflit quand l’enseignant est occupé', () => {
    render(
      <FormateurAssignPickerItem
        formateur={{ id: 204, nom: 'Bile', prenom: 'Eric', conflit_assignation: 'Déjà en salle B2 à 8h.' }}
        onAssign={() => {}}
      />,
    )
    expect(screen.getByText('Déjà en salle B2 à 8h.')).toBeInTheDocument()
    expect(screen.queryByTitle('Assigner cet enseignant')).not.toBeInTheDocument()
  })

  it('fonctionne sans spécialité renseignée', () => {
    render(
      <FormateurAssignPickerItem
        formateur={{ id: 205, nom: 'Yao', prenom: 'Kouam' }}
        onAssign={() => {}}
      />,
    )
    expect(screen.getByText('Yao Kouam')).toBeInTheDocument()
    expect(screen.getByTitle('Assigner cet enseignant')).toBeInTheDocument()
  })
})
