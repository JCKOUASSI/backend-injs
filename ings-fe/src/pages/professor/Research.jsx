import PageHeader from '../../components/common/PageHeader'

export default function ProfResearch() {
  return (
    <>
      <PageHeader title="Projets de recherche" subtitle="Centre de Médecine du Sport — Laboratoires INJS/UFHB" />
      <div className="card-injs p-4">
        <h6>Projets en cours</h6>
        <ul className="mt-3">
          <li>Physiologie de l'effort chez le sportif ivoirien de haut niveau</li>
          <li>Biomécanique du geste sportif — Plateforme INJS</li>
          <li>Approche par compétences en EPS — Évaluation longitudinale</li>
        </ul>
      </div>
    </>
  )
}
