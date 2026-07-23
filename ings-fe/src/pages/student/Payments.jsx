import { useEffect, useMemo, useState } from 'react'
import PageHeader from '../../components/common/PageHeader'
import ExportButtons from '../../components/common/ExportButtons'
import PaginationBar from '../../components/common/PaginationBar'
import { useToast } from '../../context/ToastContext'
import { useFetch } from '../../hooks/useFetch'
import { fetchStudentFees, initiatePayment, verifyPayment } from '../../api/finance'
import { StatusBadge } from '../../utils/statusBadge'
import { translateStatus } from '../../utils/labels'

function feeLabel(f) {
  return f.fee_name || f.fee_type_name || f.fee_type || 'Frais'
}

function remaining(f) {
  return Math.max(0, Number(f.amount_due || 0) - Number(f.amount_paid || 0))
}

export default function StudentPayments() {
  const { showToast } = useToast()
  const { data, loading, error, reload } = useFetch(() => fetchStudentFees())
  const fees = data?.results || []

  const [phone, setPhone] = useState('0700000000')
  const [provider, setProvider] = useState('orange_money')
  const [busy, setBusy] = useState(null)

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [viewMode, setViewMode] = useState('table')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)

  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput.trim().toLowerCase())
      setPage(1)
    }, 300)
    return () => clearTimeout(t)
  }, [searchInput])

  const pending = fees.filter((f) => f.status !== 'paid')
  const paid = fees.filter((f) => f.status === 'paid')
  const totalRemaining = pending.reduce((a, f) => a + remaining(f), 0)

  const filtered = useMemo(() => {
    return fees.filter((f) => {
      if (statusFilter === 'pending' && f.status === 'paid') return false
      if (statusFilter === 'paid' && f.status !== 'paid') return false
      if (!search) return true
      const hay = `${feeLabel(f)} ${f.status || ''} ${translateStatus(f.status)}`.toLowerCase()
      return hay.includes(search)
    })
  }, [fees, statusFilter, search])

  const total = filtered.length
  const pageItems = useMemo(() => {
    const start = (page - 1) * pageSize
    return filtered.slice(start, start + pageSize)
  }, [filtered, page, pageSize])

  const rows = fees.map((f) => [
    feeLabel(f),
    f.amount_due,
    f.amount_paid,
    translateStatus(f.status),
  ])

  const setStatusAndReset = (value) => {
    setStatusFilter(value)
    setPage(1)
  }

  const pay = async (fee) => {
    const amount = remaining(fee)
    showToast(`Confirmation : paiement de ${amount.toLocaleString()} XOF en cours…`, 'info')
    setBusy(fee.id)
    try {
      const tx = await initiatePayment({
        student_fee_id: fee.id,
        provider,
        phone,
        amount,
      })
      await verifyPayment(tx.id)
      showToast('Paiement initié et vérifié (démo)', 'success')
      reload()
    } catch (err) {
      showToast(err.message || 'Paiement impossible', 'danger')
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
        title="Mes paiements"
        subtitle="Frais d'inscription / scolarité — Orange, MTN, Moov, Wave (démo)"
        action={
          <ExportButtons
            title="Mes frais"
            filename="mes_frais"
            headers={['Type', 'Dû', 'Payé', 'Statut']}
            rows={rows}
          />
        }
      />

      <div className="row g-3 mb-4">
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold text-primary">{fees.length}</div>
            <div className="small text-muted">Frais assignés</div>
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
            <div className="fs-4 fw-bold text-success">{paid.length}</div>
            <div className="small text-muted">Soldés</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{totalRemaining.toLocaleString()}</div>
            <div className="small text-muted">Restant (XOF)</div>
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

      <div className="card-injs p-3 mb-3">
        <h6 className="fw-bold mb-3">Paramètres de paiement</h6>
        <div className="row g-3">
          <div className="col-md-4">
            <label className="form-label small mb-1">Opérateur</label>
            <select className="form-select" value={provider} onChange={(e) => setProvider(e.target.value)}>
              <option value="orange_money">Orange Money</option>
              <option value="mtn_momo">MTN MoMo</option>
              <option value="moov_money">Moov Money</option>
              <option value="wave">Wave</option>
            </select>
          </div>
          <div className="col-md-4">
            <label className="form-label small mb-1">Téléphone</label>
            <input className="form-control" value={phone} onChange={(e) => setPhone(e.target.value)} />
          </div>
        </div>
      </div>

      <div className="card-injs p-3 mb-4">
        <div className="row g-2 align-items-end">
          <div className="col-md-6">
            <label className="form-label small mb-1">Recherche</label>
            <input
              className="form-control"
              placeholder="Type de frais, statut…"
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
          pageSizeOptions={[6, 10, 15, 25]}
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
                    <th>Type</th>
                    <th>Dû</th>
                    <th>Payé</th>
                    <th>Restant</th>
                    <th>Statut</th>
                    <th className="text-end">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((f) => (
                    <tr key={f.id}>
                      <td className="fw-semibold">{feeLabel(f)}</td>
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
                            onClick={() => pay(f)}
                          >
                            {busy === f.id ? 'Paiement…' : 'Payer'}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {!pageItems.length && (
                    <tr>
                      <td colSpan={6} className="text-center text-muted py-4">Aucun frais trouvé</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-3">
              <div className="row g-3">
                {pageItems.map((f) => (
                  <div key={f.id} className="col-md-6">
                    <div className="border rounded-3 p-3 h-100">
                      <div className="d-flex justify-content-between align-items-start gap-2 mb-2">
                        <h6 className="fw-bold mb-0">{feeLabel(f)}</h6>
                        <StatusBadge statut={f.status} />
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
                          onClick={() => pay(f)}
                        >
                          {busy === f.id ? 'Paiement…' : 'Payer'}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
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
          pageSizeOptions={[6, 10, 15, 25]}
          onPageChange={setPage}
          onPageSizeChange={(size) => {
            setPageSize(size)
            setPage(1)
          }}
        />
      </div>
    </>
  )
}
