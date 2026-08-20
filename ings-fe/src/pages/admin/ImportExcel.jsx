import { useRef, useState } from 'react'
import PageHeader from '../../components/common/PageHeader'
import { useToast } from '../../context/ToastContext'
import { importReferentialFile } from '../../api/academics'

const IMPORT_CONFIGS = [
  {
    resource: 'specializations',
    title: 'Spécialisations',
    color: '#0d6efd',
    columns: ['code', 'name', 'track', 'is_tronc_commun', 'description'],
    examples: [
      ['EM', 'Education et motricite', 'BOTH', 'oui', 'Tronc disciplinaire EPS'],
      ['APA', 'Activites physiques adaptees', 'PL', 'non', 'Parcours adaptation'],
    ],
  },
  {
    resource: 'departments',
    title: 'Departements',
    color: '#198754',
    columns: ['institution_code', 'code', 'name', 'description'],
    examples: [
      ['INJS', 'STAPS', 'Sciences et techniques des activites physiques et sportives', 'Departement principal STAPS'],
    ],
  },
  {
    resource: 'programs',
    title: 'Programmes',
    color: '#6f42c1',
    columns: ['department_code', 'code', 'name', 'degree_type', 'track', 'duration_semesters', 'total_credits', 'description', 'is_active'],
    examples: [
      ['STAPS', 'LIC-STAPS-EM', 'Licence STAPS Education et motricite', 'L', 'PC', 6, 180, 'Cycle licence', 'oui'],
    ],
  },
  {
    resource: 'academic_years',
    title: 'Annees academiques',
    color: '#fd7e14',
    columns: ['institution_code', 'label', 'start_date', 'end_date', 'is_current', 'is_archived'],
    examples: [
      ['INJS', '2026-2027', '2026-10-01', '2027-07-31', 'oui', 'non'],
    ],
  },
  {
    resource: 'semesters',
    title: 'Semestres',
    color: '#20c997',
    columns: ['academic_year_label', 'number', 'name', 'start_date', 'end_date', 'is_current'],
    examples: [
      ['2026-2027', 1, 'Semestre 1', '2026-10-01', '2027-01-31', 'oui'],
    ],
  },
  {
    resource: 'promotions',
    title: 'Promotions',
    color: '#dc3545',
    columns: ['program_code', 'name', 'entry_year', 'current_semester', 'is_active'],
    examples: [
      ['LIC-STAPS-EM', 'L1 2026', 2026, 1, 'oui'],
    ],
  },
]

function csvCell(value) {
  const text = value == null ? '' : String(value)
  return /[;"\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

function downloadTemplate(filename, columns, examples = []) {
  const lines = [columns.map(csvCell).join(';')]
  for (const row of examples) {
    lines.push(row.map(csvCell).join(';'))
  }
  const blob = new Blob(['\uFEFF' + lines.join('\n') + '\n'], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

function ImportCard({ config, onImport, loading }) {
  const fileRef = useRef(null)

  const handleImport = () => {
    const file = fileRef.current?.files?.[0]
    onImport(config.resource, file, () => {
      if (fileRef.current) fileRef.current.value = ''
    })
  }

  return (
    <div className="card-injs p-4 h-100">
      <div className="d-flex align-items-center justify-content-between gap-3 mb-3">
        <div>
          <h5 className="fw-bold mb-1">{config.title}</h5>
          <p className="text-muted small mb-0">Import `.xlsx` avec mise a jour automatique si l’element existe deja.</p>
        </div>
        <span className="badge text-white" style={{ backgroundColor: config.color }}>{config.resource}</span>
      </div>

      <div className="mb-3">
        <label className="form-label">Fichier Excel</label>
        <input ref={fileRef} type="file" className="form-control" accept=".xlsx" />
      </div>

      <div className="d-flex flex-wrap gap-2 mb-3">
        <button type="button" className="btn btn-injs-primary btn-sm" disabled={loading} onClick={handleImport}>
          {loading ? 'Import...' : 'Importer'}
        </button>
        <button
          type="button"
          className="btn btn-outline-secondary btn-sm"
          onClick={() => downloadTemplate(`modele_${config.resource}.csv`, config.columns, config.examples)}
        >
          Modele CSV
        </button>
      </div>

      <div>
        <div className="small text-muted mb-2">Colonnes attendues</div>
        <div className="d-flex flex-wrap gap-2">
          {config.columns.map((column) => (
            <span key={column} className="badge bg-light text-dark border">{column}</span>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function AdminImportExcel() {
  const { showToast } = useToast()
  const [loadingResource, setLoadingResource] = useState('')

  const handleImport = async (resource, file, reset) => {
    if (!file) {
      showToast('Veuillez selectionner un fichier .xlsx', 'danger')
      return
    }

    setLoadingResource(resource)
    try {
      const result = await importReferentialFile(resource, file)
      const summary = [`${result.created || 0} cree(s)`, `${result.updated || 0} mis a jour`, `${result.skipped || 0} ignore(s)`]
      if (result.errors?.length) {
        const preview = result.errors.slice(0, 2).join(' | ')
        const suffix = result.errors.length > 2 ? ' ...' : ''
        showToast(`${resource} — ${summary.join(', ')}. ${preview}${suffix}`, 'warning')
      } else {
        showToast(`${resource} — import termine: ${summary.join(', ')}`, 'success')
      }
      reset?.()
    } catch (error) {
      showToast(error.message || "Import impossible", 'danger')
    } finally {
      setLoadingResource('')
    }
  }

  return (
    <>
      <PageHeader
        title="Import Excel"
        subtitle="Chargement guide des referentiels academiques INJS depuis des fichiers Excel distincts"
      />

      <div className="card-injs p-4 mb-4">
        <p className="mb-2">
          Ordre recommande: <strong>Spécialisations</strong> → <strong>Départements</strong> → <strong>Programmes</strong> → <strong>Années académiques</strong> → <strong>Semestres</strong> → <strong>Promotions</strong>.
        </p>
        <p className="mb-0 text-muted small">
          Les liaisons se font par codes métiers: `institution_code`, `department_code`, `program_code` et `academic_year_label`.
          Un élément existant est mis à jour, sinon il est créé.
        </p>
      </div>

      <div className="row g-4">
        {IMPORT_CONFIGS.map((config) => (
          <div key={config.resource} className="col-12 col-xl-6">
            <ImportCard
              config={config}
              onImport={handleImport}
              loading={loadingResource === config.resource}
            />
          </div>
        ))}
      </div>
    </>
  )
}
