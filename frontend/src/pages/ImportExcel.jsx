import { useState, useRef } from 'react'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

function downloadTemplate(filename, columns) {
  const csv = columns.join(';') + '\n'
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

function ImportCard({ type, title, icon, color, columns, onImport, loading }) {
  const fileRef = useRef()

  const handleClick = () => {
    const file = fileRef.current?.files[0]
    if (!file) { onImport(type, null); return }
    onImport(type, file, () => { if (fileRef.current) fileRef.current.value = '' })
  }

  return (
    <div className="card">
      <div className="import-card-header" style={{ background: color }}>
        <i className={`bi ${icon} me-2`}></i>{title}
      </div>
      <div className="card-body">
        <div className="form-group">
          <label className="form-label fw-semibold">Fichier Excel (.xlsx)</label>
          <input type="file" className="form-control" accept=".xlsx,.xls" ref={fileRef} />
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button onClick={handleClick} className="btn btn-dfrc btn-sm" disabled={loading}>
            <i className="bi bi-upload me-1"></i>{loading ? 'Import...' : 'Importer'}
          </button>
          <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => downloadTemplate(`modele_${type}.csv`, columns)}>
            <i className="bi bi-download me-1"></i>Modèle CSV
          </button>
        </div>
        <div className="mt-3">
          <small className="text-muted fw-semibold">Colonnes attendues :</small>
          <div className="mt-2" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
            {columns.map((col) => (
              <span key={col} className="badge-bg-secondary" style={{ fontSize: '0.7rem' }}>{col}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function EdtFileInput({ onImport, loading }) {
  const fileRef = useRef()
  const handleClick = () => {
    const file = fileRef.current?.files[0]
    if (!file) { onImport('emploi_du_temps', null); return }
    onImport('emploi_du_temps', file, () => { if (fileRef.current) fileRef.current.value = '' })
  }
  return (
    <div className="form-group">
      <label className="form-label fw-semibold">Fichier Excel (.xlsx)</label>
      <input type="file" className="form-control" accept=".xlsx,.xls" ref={fileRef} />
      <div style={{ marginTop: '0.5rem' }}>
        <button onClick={handleClick} className="btn btn-dfrc btn-sm" disabled={loading}
          style={{ background: '#7B1FA2', borderColor: '#7B1FA2' }}>
          <i className="bi bi-upload me-1"></i>{loading ? 'Import...' : "Importer l'emploi du temps"}
        </button>
      </div>
    </div>
  )
}

function SeanceFileInput({ onImport, loading }) {
  const fileRef = useRef()
  const handleClick = () => {
    const file = fileRef.current?.files[0]
    if (!file) { onImport('seances', null); return }
    onImport('seances', file, () => { if (fileRef.current) fileRef.current.value = '' })
  }
  return (
    <div className="form-group">
      <label className="form-label fw-semibold">Fichier Excel (.xlsx)</label>
      <input type="file" className="form-control" accept=".xlsx,.xls" ref={fileRef} />
      <div style={{ marginTop: '0.5rem' }}>
        <button onClick={handleClick} className="btn btn-dfrc btn-sm" disabled={loading}
          style={{ background: '#5C6BC0', borderColor: '#5C6BC0' }}>
          <i className="bi bi-upload me-1"></i>{loading ? 'Import...' : 'Importer les séances'}
        </button>
      </div>
    </div>
  )
}

export default function ImportExcel() {
  const { user } = useAuth()
  const { showToast } = useToast()
  const [loading, setLoading] = useState(false)

  if (!['CHEF_SECRETARIAT', 'SECRETARIAT', 'ADMIN', 'CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN'].includes(user?.role)) {
    return (
      <div className="card">
        <div className="card-body text-center text-muted py-5">
          <i className="bi bi-lock" style={{ fontSize: '2rem' }}></i>
          <p className="mt-2 fw-semibold">Accès réservé au Secrétariat / CPFAE Admin</p>
        </div>
      </div>
    )
  }

  const handleImport = async (type, file, resetFile) => {
    if (!file) { showToast('Veuillez sélectionner un fichier', 'error'); return }

    setLoading(true)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('type', type)

    try {
      const response = await api.post('/formations/import-excel/', formData)
      const data = response.data
      const typeLabels = { formations: 'Cours', participants: 'Auditeurs', formateurs: 'Formateurs', seances: 'Séances', emploi_du_temps: 'Emploi du temps' }
      const label = typeLabels[type] || type

      if (data.errors?.length > 0) {
        showToast(`${label} — Import avec ${data.errors.length} erreur(s). ${data.created || 0} créé(s).`, 'error')
      } else {
        const parts = []
        if (data.created > 0) parts.push(`${data.created} créé(s)`)
        if (data.updated > 0) parts.push(`${data.updated} mis à jour`)
        const msg = parts.length > 0 ? parts.join(', ') : 'Aucun élément traité'
        showToast(`${label} — Import réussi ! ${msg}`, 'success')
      }
      if (resetFile) resetFile()
    } catch (err) {
      showToast(err.response?.data?.error || err.response?.data?.detail || "Erreur lors de l'import", 'error')
    } finally { setLoading(false) }
  }

  return (
    <div>
      <div className="card">
        <div className="card-body">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div className="stat-icon bg-warning"><i className="bi bi-info-circle-fill"></i></div>
            <div>
              <strong>Comment importer des données ?</strong>
              <p className="text-muted mb-0" style={{ fontSize: '0.85rem' }}>
                Préparez un fichier Excel (.xlsx) avec les colonnes attendues pour chaque type de données, puis cliquez sur "Importer".
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <ImportCard type="formations" title="Cours" icon="bi-mortarboard" color="var(--ci-green-dark)"
          columns={['N°', 'Formation', 'Module (titre)', 'Site', 'Date début', 'Date fin', 'Volume horaire (h)', 'Catégorie', 'Grade', 'Groupe', 'Vague']}
          onImport={handleImport} loading={loading} />
        <ImportCard type="participants" title="Auditeurs" icon="bi-people" color="var(--ci-blue)"
          columns={["N° d'inscription", 'Nom', 'Prénoms', 'Genre', 'Date de naissance', 'Lieu de naissance', 'E-mail', 'Téléphone 1', 'Téléphone 2', 'Type concours', 'Libellé concours', 'Catégorie', 'Grade', 'Groupe', 'Grade-Groupe', 'Vague', 'Site', 'Salle', 'Formation(s)']}
          onImport={handleImport} loading={loading} />
        <ImportCard type="formateurs" title="Formateurs" icon="bi-person-video3" color="var(--ci-orange)"
          columns={['Numéro', 'Nom', 'Prénom', 'E-mail', 'Téléphone', 'Spécialité', 'Organisation']}
          onImport={handleImport} loading={loading} />

        {/* Séances — 4ème carte dans la grille */}
        <div className="card">
          <div className="import-card-header" style={{ background: '#5C6BC0' }}>
            <i className="bi bi-calendar3 me-2"></i>Séances
          </div>
          <div className="card-body">
            <SeanceFileInput onImport={handleImport} loading={loading} />
            <button type="button" className="btn btn-outline-secondary btn-sm mt-1"
              onClick={() => downloadTemplate('modele_seances.csv',
                ['module_titre', 'date_journee', 'numero', 'intitule', 'heure_debut', 'heure_fin']
              )}>
              <i className="bi bi-download me-1"></i>Modèle CSV
            </button>
            <div className="mt-3">
              <small className="text-muted fw-semibold">Colonnes attendues :</small>
              <div className="mt-1" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                {['module_titre', 'date_journee', 'numero', 'intitule', 'heure_debut', 'heure_fin'].map(col => (
                  <span key={col} className="badge-bg-secondary" style={{ fontSize: '0.7rem' }}>{col}</span>
                ))}
              </div>
              <div className="mt-2" style={{ background: '#f0f4ff', borderRadius: 6, padding: '0.4rem 0.6rem' }}>
                <small><i className="bi bi-info-circle me-1"></i>date: JJ/MM/AAAA · heure: HH:MM · numero: 1,2,3…</small>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
