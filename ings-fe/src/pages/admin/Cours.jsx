import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FiBookOpen, FiUserCheck, FiCalendar, FiClock } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import StatCard from '../../components/common/StatCard'
import PaginationBar from '../../components/common/PaginationBar'
import { useFetch } from '../../hooks/useFetch'
import {
  fetchCoursCatalog,
  fetchDepartments,
  fetchPrograms,
  fetchPromotions,
} from '../../api/academics'

const STATUTS = [
  { value: 'non_affecte', label: 'Non affecté' },
  { value: 'affecte', label: 'Affecté' },
  { value: 'planifie', label: 'Planifié' },
]

const COULEUR_STATUT = {
  non_affecte: 'bg-danger',
  affecte: 'bg-warning text-dark',
  planifie: 'bg-success',
}

/** Pastille de statut d'un cours, partagée avec la fiche détaillée. */
export function statusBadge(statut, libelle) {
  return (
    <span className={`badge ${COULEUR_STATUT[statut] || 'bg-secondary'}`}>
      {libelle || statut || '—'}
    </span>
  )
}

const FILTRES_VIDES = {
  search: '',
  department: '',
  program: '',
  promotion: '',
  semester_number: '',
  status: '',
}

export default function AdminCours() {
  const [filtres, setFiltres] = useState(FILTRES_VIDES)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)

  const { data: departements } = useFetch(() => fetchDepartments(), [])
  const { data: programmes } = useFetch(() => fetchPrograms(), [])
  const { data: promotions } = useFetch(() => fetchPromotions(), [])

  const { data, loading, error } = useFetch(
    () => fetchCoursCatalog({
      ...Object.fromEntries(Object.entries(filtres).filter(([, valeur]) => valeur !== '')),
      page,
      page_size: pageSize,
    }),
    [filtres, page, pageSize],
  )

  const lignes = data?.results || []
  const kpis = data?.kpis || {}
  const anneeLabel = data?.filtre?.academic_year_label
  const avertissement = data?.filtre?.warning

  const changerFiltre = (champ, valeur) => {
    setFiltres((precedent) => ({ ...precedent, [champ]: valeur }))
    setPage(1)
  }

  const reinitialiser = () => {
    setFiltres(FILTRES_VIDES)
    setPage(1)
  }

  const listeProgrammes = programmes?.results || []
  const listePromotions = (promotions?.results || []).filter(
    (promo) => !filtres.program || String(promo.program) === filtres.program,
  )

  return (
    <div>
      <PageHeader
        title="Cours (ECUE)"
        subtitle={
          anneeLabel
            ? `Catalogue des ECUE par promotion — année ${anneeLabel}`
            : 'Catalogue des ECUE par promotion'
        }
      />

      {avertissement && <div className="alert alert-warning">{avertissement}</div>}

      <div className="row g-3 mb-4">
        <div className="col-6 col-lg-3">
          <StatCard icon={FiBookOpen} label="Cours au catalogue" value={kpis.offerings ?? 0} color="green" />
        </div>
        <div className="col-6 col-lg-3">
          <StatCard
            icon={FiUserCheck}
            label="Taux d'affectation"
            value={`${kpis.taux_affectation ?? 0} %`}
            color="blue"
          />
        </div>
        <div className="col-6 col-lg-3">
          <StatCard
            icon={FiCalendar}
            label="Taux de planification"
            value={`${kpis.taux_planification ?? 0} %`}
            color="purple"
          />
        </div>
        <div className="col-6 col-lg-3">
          <StatCard
            icon={FiClock}
            label="Volume horaire"
            value={`${kpis.hours_volume ?? 0} h`}
            color="orange"
          />
        </div>
      </div>

      <div className="card-injs p-3 mb-3">
        <div className="row g-2 align-items-end">
          <div className="col-12 col-lg-3">
            <label className="form-label small text-muted mb-1">Recherche</label>
            <input
              type="search"
              className="form-control form-control-sm"
              placeholder="Code, intitulé, enseignant…"
              value={filtres.search}
              onChange={(event) => changerFiltre('search', event.target.value)}
            />
          </div>
          <div className="col-6 col-lg-2">
            <label className="form-label small text-muted mb-1">Département</label>
            <select
              className="form-select form-select-sm"
              value={filtres.department}
              onChange={(event) => changerFiltre('department', event.target.value)}
            >
              <option value="">Tous</option>
              {(departements?.results || []).map((item) => (
                <option key={item.id} value={item.id}>{item.code || item.name}</option>
              ))}
            </select>
          </div>
          <div className="col-6 col-lg-2">
            <label className="form-label small text-muted mb-1">Programme</label>
            <select
              className="form-select form-select-sm"
              value={filtres.program}
              onChange={(event) => {
                changerFiltre('program', event.target.value)
                changerFiltre('promotion', '')
              }}
            >
              <option value="">Tous</option>
              {listeProgrammes.map((item) => (
                <option key={item.id} value={item.id}>{item.code || item.name}</option>
              ))}
            </select>
          </div>
          <div className="col-6 col-lg-2">
            <label className="form-label small text-muted mb-1">Promotion</label>
            <select
              className="form-select form-select-sm"
              value={filtres.promotion}
              onChange={(event) => changerFiltre('promotion', event.target.value)}
            >
              <option value="">Toutes</option>
              {listePromotions.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </div>
          <div className="col-6 col-lg-1">
            <label className="form-label small text-muted mb-1">Semestre</label>
            <select
              className="form-select form-select-sm"
              value={filtres.semester_number}
              onChange={(event) => changerFiltre('semester_number', event.target.value)}
            >
              <option value="">Tous</option>
              {[1, 2, 3, 4, 5, 6].map((numero) => (
                <option key={numero} value={numero}>S{numero}</option>
              ))}
            </select>
          </div>
          <div className="col-6 col-lg-2">
            <label className="form-label small text-muted mb-1">Statut</label>
            <select
              className="form-select form-select-sm"
              value={filtres.status}
              onChange={(event) => changerFiltre('status', event.target.value)}
            >
              <option value="">Tous</option>
              {STATUTS.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="text-end mt-2">
          <button type="button" className="btn btn-sm btn-outline-secondary" onClick={reinitialiser}>
            Réinitialiser
          </button>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      <div className="card-injs p-0">
        {loading ? (
          <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
        ) : lignes.length === 0 ? (
          <div className="text-center text-muted py-5">
            Aucun cours pour ce périmètre.
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th>ECUE</th>
                  <th>Unité d'enseignement</th>
                  <th>Promotion</th>
                  <th>Enseignant</th>
                  <th className="text-end">Volume</th>
                  <th className="text-end">h/sem.</th>
                  <th className="text-end">Étudiants</th>
                  <th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {lignes.map((ligne) => (
                  <tr key={ligne.id}>
                    <td>
                      <Link to={`/admin/cours/${encodeURIComponent(ligne.id)}`} className="fw-semibold">
                        {ligne.course_code}
                      </Link>
                      <div className="small text-muted">{ligne.course_name}</div>
                    </td>
                    <td>
                      <div>{ligne.teaching_unit_code}</div>
                      <div className="small text-muted">S{ligne.semester_number} · {ligne.credits_ects} ECTS</div>
                    </td>
                    <td>
                      <div>{ligne.promotion_name}</div>
                      <div className="small text-muted">{ligne.program_code}</div>
                    </td>
                    <td>
                      {ligne.teacher_name || <span className="text-muted">Non affecté</span>}
                      {ligne.assignments_count > 1 && (
                        <div className="small text-muted">+{ligne.assignments_count - 1} autre(s)</div>
                      )}
                    </td>
                    <td className="text-end">{ligne.hours_total} h</td>
                    <td className="text-end">{ligne.weekly_hours}</td>
                    <td className="text-end">{ligne.students_count}</td>
                    <td>{statusBadge(ligne.status, ligne.status_label)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {data?.count > 0 && (
        <PaginationBar
          className="mt-3"
          page={page}
          pageSize={pageSize}
          total={data.count}
          disabled={loading}
          onPageChange={setPage}
          onPageSizeChange={(taille) => { setPageSize(taille); setPage(1) }}
        />
      )}
    </div>
  )
}
