import { useEffect, useMemo, useState } from 'react'
import PageHeader from '../../components/common/PageHeader'
import ExportButtons from '../../components/common/ExportButtons'
import Modal from '../../components/common/Modal'
import PaginationBar from '../../components/common/PaginationBar'
import { useFetch } from '../../hooks/useFetch'
import { useToast } from '../../context/ToastContext'
import { fetchStudentFees, initiatePayment, verifyPayment } from '../../api/finance'
import { StatusBadge } from '../../utils/statusBadge'
import { translateStatus, mediaUrl } from '../../utils/labels'

function studentLabel(f) {
  return f.student_name || f.matricule || f.student_matricule || '—'
}

function feeLabel(f) {
  return f.fee_name || f.fee_type_name || f.fee_type || '—'
}

function remaining(f) {
  return Math.max(0, Number(f.amount_due || 0) - Number(f.amount_paid || 0))
}

function initialsFromName(name) {
  return (name || '?')
    .split(/\s+/)
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

export default function AdminFinances() {
  const { showToast } = useToast()
  const { data, loading, error, reload } = useFetch(() => fetchStudentFees({ page_size: 200 }))
  const fees = data?.results || []

  const [busy, setBusy] = useState(null)
  const [confirmFee, setConfirmFee] = useState(null)

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [viewMode, setViewMode] = useState('table')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(15)

  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput.trim().toLowerCase())
      setPage(1)
    }, 300)
    return () => clearTimeout(t)
  }, [searchInput])

  const pending = fees.filter((f) => f.status === 'pending' || f.status === 'partial')
  const paid = fees.filter((f) => f.status === 'paid')
  const totalDue = fees.reduce((a, f) => a + Number(f.amount_due || 0), 0)
  const totalPaid = fees.reduce((a, f) => a + Number(f.amount_paid || 0), 0)

  const filtered = useMemo(() => {
    return fees.filter((f) => {
      if (statusFilter === 'pending' && !(f.status === 'pending' || f.status === 'partial')) return false
      if (statusFilter === 'paid' && f.status !== 'paid') return false
      if (!search) return true
      const hay = [
        studentLabel(f),
        f.matricule,
        f.student_matricule,
        feeLabel(f),
        f.status,
        translateStatus(f.status),
      ].join(' ').toLowerCase()
      return hay.includes(search)
    })
  }, [fees, statusFilter, search])

  const total = filtered.length
  const pageItems = useMemo(() => {
    const start = (page - 1) * pageSize
    return filtered.slice(start, start + pageSize)
  }, [filtered, page, pageSize])

  const rows = filtered.map((f) => [
    studentLabel(f),
    feeLabel(f),
    f.amount_due,
    f.amount_paid,
    translateStatus(f.status),
  ])

  const setStatusAndReset = (value) => {
    setStatusFilter(value)
    setPage(1)
  }

  const askCollect = (fee) => {
    setConfirmFee(fee)
    showToast(
      `Confirmez l'encaissement de ${remaining(fee).toLocaleString()} XOF pour ${studentLabel(fee)}`,
      'info',
    )
  }

  const handleCollect = async () => {
    const fee = confirmFee
    if (!fee) return
    setBusy(fee.id)
    setConfirmFee(null)
    try {
      const tx = await initiatePayment({
        student_fee_id: fee.id,
        provider: 'orange_money',
        amount: remaining(fee),
      })
      await verifyPayment(tx.id)
      showToast('Paiement démo initié et vérifié', 'success')
      reload()
    } catch (err) {
      showToast(err.message || 'Échec encaissement', 'danger')
    } finally {
      setBusy(null)
    }
  }

  if (loading && !data) {
    return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
  }
  if (error) {
    return <div className="alert alert-danger m-4">{error}</div>
  }

  return (
    <>
      <PageHeader
        title="Finances"
        subtitle="Frais étudiants, encaissements et exports comptables"
        action={
          <ExportButtons
            title="Frais étudiants INJS"
            filename="injs_finances"
            headers={['Étudiant', 'Type', 'Dû', 'Payé', 'Statut']}
            rows={rows}
            resourcePath="/finance/student-fees"
          />
        }
      />

      <div className="row g-3 mb-4">
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold text-primary">{totalDue.toLocaleString()}</div>
            <div className="small text-muted">Total dû (XOF)</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold text-success">{totalPaid.toLocaleString()}</div>
            <div className="small text-muted">Total encaissé</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold text-warning">{pending.length}</div>
            <div className="small text-muted">En attente</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{paid.length}</div>
            <div className="small text-muted">Soldés</div>
          </div>
        </div>
      </div>

      <div className="card-injs p-3 mb-3">
        <div className="d-flex flex-wrap gap-2 align-items-center">
          <span className="small text-muted me-1">Statut :</span>
          <button
            type="button"
            className={`btn btn-sm ${statusFilter === '' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => setStatusAndReset('')}
          >
            Tous ({fees.length})
          </button>
          <button
            type="button"
            className={`btn btn-sm ${statusFilter === 'pending' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => setStatusAndReset('pending')}
          >
            En attente <span className="opacity-75">({pending.length})</span>
          </button>
          <button
            type="button"
            className={`btn btn-sm ${statusFilter === 'paid' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => setStatusAndReset('paid')}
          >
            Soldés <span className="opacity-75">({paid.length})</span>
          </button>
        </div>
      </div>

      <div className="card-injs p-3 mb-4">
        <div className="row g-2 align-items-end">
          <div className="col-md-6">
            <label className="form-label small mb-1">Recherche</label>
            <input
              className="form-control"
              placeholder="Étudiant, matricule, type de frais…"
              value={searchInput}
              onChange={(ev) => setSearchInput(ev.target.value)}
            />
          </div>
          <div className="col-md-3">
            <label className="form-label small mb-1">Statut</label>
            <select
              className="form-select"
              value={statusFilter}
              onChange={(ev) => setStatusAndReset(ev.target.value)}
            >
              <option value="">Tous</option>
              <option value="pending">En attente</option>
              <option value="paid">Soldés</option>
            </select>
          </div>
          <div className="col-md-3">
            <label className="form-label small mb-1">Affichage</label>
            <div className="btn-group w-100" role="group">
              <button
                type="button"
                className={`btn btn-sm ${viewMode === 'table' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
                onClick={() => setViewMode('table')}
              >
                Liste
              </button>
              <button
                type="button"
                className={`btn btn-sm ${viewMode === 'cards' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
                onClick={() => setViewMode('cards')}
              >
                Cartes
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="card-injs position-relative rooms-list-shell">
        {loading && (
          <div className="position-absolute top-0 end-0 m-2" style={{ zIndex: 3 }}>
            <div className="spinner-border spinner-border-sm text-primary" />
          </div>
        )}

        <PaginationBar
          page={page}
          pageSize={pageSize}
          total={total}
          disabled={loading}
          pageSizeOptions={[10, 15, 25, 50]}
          onPageChange={setPage}
          onPageSizeChange={(size) => {
            setPageSize(size)
            setPage(1)
          }}
        />

        <div className="rooms-list-body">
          {viewMode === 'table' ? (
            <div className="table-responsive">
              <table className="table table-hover mb-0 align-middle">
                <thead>
                  <tr>
                    <th>Photo</th>
                    <th>Étudiant</th>
                    <th>Type de frais</th>
                    <th>Montant dû</th>
                    <th>Payé</th>
                    <th>Restant</th>
                    <th>Statut</th>
                    <th className="text-end">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((f) => {
                    const photo = mediaUrl(f.photo_url)
                    const initials = initialsFromName(f.student_name)
                    return (
                      <tr key={f.id}>
                        <td>
                          {photo ? (
                            <img src={photo} alt="" className="student-photo-sm" />
                          ) : (
                            <div className="student-photo-sm student-photo-placeholder">{initials}</div>
                          )}
                        </td>
                        <td>
                          <div className="fw-semibold">{f.student_name || '—'}</div>
                          <code className="small">{f.matricule || f.student_matricule || '—'}</code>
                        </td>
                        <td className="small">{feeLabel(f)}</td>
                        <td>{Number(f.amount_due || 0).toLocaleString()} XOF</td>
                        <td>{Number(f.amount_paid || 0).toLocaleString()} XOF</td>
                        <td>{remaining(f).toLocaleString()} XOF</td>
                        <td><StatusBadge statut={f.status} /></td>
                        <td className="text-end">
                          {f.status !== 'paid' && (
                            <button
                              type="button"
                              className="btn btn-sm btn-injs-primary"
                              disabled={busy === f.id}
                              onClick={() => askCollect(f)}
                            >
                              {busy === f.id ? '…' : 'Encaisser'}
                            </button>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                  {!pageItems.length && (
                    <tr>
                      <td colSpan={8} className="text-center text-muted py-4">Aucun frais trouvé</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-3">
              <div className="row g-3">
                {pageItems.map((f) => {
                  const photo = mediaUrl(f.photo_url)
                  const initials = initialsFromName(f.student_name)
                  return (
                    <div key={f.id} className="col-md-6 col-xl-4">
                      <div className="border rounded-3 p-3 h-100">
                        <div className="d-flex justify-content-between align-items-start mb-2">
                          <code className="small">{f.matricule || f.student_matricule || '—'}</code>
                          <StatusBadge statut={f.status} />
                        </div>
                        <div className="d-flex align-items-center gap-2 mb-2">
                          {photo ? (
                            <img src={photo} alt="" className="student-photo-sm" />
                          ) : (
                            <div className="student-photo-sm student-photo-placeholder">{initials}</div>
                          )}
                          <div>
                            <h6 className="fw-bold mb-0">{f.student_name || '—'}</h6>
                            <small className="text-muted">{feeLabel(f)}</small>
                          </div>
                        </div>
                        <div className="small text-muted mb-1">
                          Dû : <strong className="text-dark">{Number(f.amount_due || 0).toLocaleString()} XOF</strong>
                        </div>
                        <div className="small text-muted mb-1">
                          Payé : <strong className="text-dark">{Number(f.amount_paid || 0).toLocaleString()} XOF</strong>
                        </div>
                        <div className="small text-muted mb-3">
                          Restant : <strong className="text-dark">{remaining(f).toLocaleString()} XOF</strong>
                        </div>
                        {f.status !== 'paid' && (
                          <button
                            type="button"
                            className="btn btn-sm btn-injs-primary"
                            disabled={busy === f.id}
                            onClick={() => askCollect(f)}
                          >
                            {busy === f.id ? '…' : 'Encaisser'}
                          </button>
                        )}
                      </div>
                    </div>
                  )
                })}
                {!pageItems.length && (
                  <div className="col-12 text-center text-muted py-4">Aucun frais trouvé</div>
                )}
              </div>
            </div>
          )}
        </div>

        <PaginationBar
          page={page}
          pageSize={pageSize}
          total={total}
          disabled={loading}
          pageSizeOptions={[10, 15, 25, 50]}
          onPageChange={setPage}
          onPageSizeChange={(size) => {
            setPageSize(size)
            setPage(1)
          }}
        />
      </div>

      <Modal
        show={!!confirmFee}
        onClose={() => setConfirmFee(null)}
        title="Confirmer l'encaissement"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setConfirmFee(null)}>Annuler</button>
            <button type="button" className="btn btn-injs-primary" disabled={!!busy} onClick={handleCollect}>
              Confirmer l&apos;encaissement
            </button>
          </>
        }
      >
        {confirmFee && (
          <>
            <p>
              Vous allez encaisser{' '}
              <strong>{remaining(confirmFee).toLocaleString()} XOF</strong>
              {' '}pour{' '}
              <strong>{studentLabel(confirmFee)}</strong>
              {confirmFee.matricule || confirmFee.student_matricule
                ? <> (<code>{confirmFee.matricule || confirmFee.student_matricule}</code>)</>
                : null}
              .
            </p>
            <p className="text-muted small mb-0">
              Type de frais : {feeLabel(confirmFee)} — paiement démo (Orange Money).
            </p>
          </>
        )}
      </Modal>
    </>
  )
}
