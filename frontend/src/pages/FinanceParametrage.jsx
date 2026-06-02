import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import FinancePageShell, { FinanceNavActions } from '../components/finance/FinancePageShell'
import { formatMoney } from '../components/FinanceStatsGrid'
import {
  buildFinanceListSearchParams,
  FINANCE_QUERY_STORAGE_KEY,
  loadFinancePeriod,
  readFinanceStateFromSearchParams,
} from '../utils/financePeriod'
import { usePersistedListQuery } from '../hooks/usePersistedListQuery'

const formatDateTime = (value) => {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '-'
  return d.toLocaleString('fr-FR')
}

export default function FinanceParametrage() {
  const { user } = useAuth()
  const { showToast } = useToast()
  const canEdit = ['FINANCE', 'DIRECTION'].includes(user?.role)
  const [searchParams] = useSearchParams()

  usePersistedListQuery(
    FINANCE_QUERY_STORAGE_KEY,
    () => {
      const fromUrl = readFinanceStateFromSearchParams(searchParams)
      return buildFinanceListSearchParams(fromUrl?.period ?? loadFinancePeriod(), {})
    },
    [searchParams],
  )

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [prix, setPrix] = useState('')
  const [meta, setMeta] = useState({ updated_at: null, updated_by: null })

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const res = await api.get('/formations/finance/settings/')
        setPrix(String(res.data?.prix_heure_realisee ?? 0))
        setMeta({
          updated_at: res.data?.updated_at || null,
          updated_by: res.data?.updated_by || null,
        })
      } catch {
        showToast('Impossible de charger les paramètres finance.', 'error')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [showToast])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!canEdit) return
    const value = Number(String(prix).replace(',', '.'))
    if (Number.isNaN(value) || value < 0) {
      showToast('Saisissez un montant valide (≥ 0).', 'error')
      return
    }
    setSaving(true)
    try {
      const res = await api.patch('/formations/finance/settings/', { prix_heure_realisee: value })
      setPrix(String(res.data?.prix_heure_realisee ?? value))
      setMeta({
        updated_at: res.data?.updated_at || null,
        updated_by: res.data?.updated_by || null,
      })
      showToast('Paramètres enregistrés')
    } catch (err) {
      showToast(err.response?.data?.detail || 'Erreur lors de la sauvegarde', 'error')
    } finally {
      setSaving(false)
    }
  }

  const prixNum = Number(prix) || 0

  return (
    <FinancePageShell
      title="Paramétrage Finance"
      subtitle="Tarif horaire appliqué au calcul des fiches de paie"
      icon="bi-sliders"
      actions={<FinanceNavActions active="parametrage" />}
      showPeriodFilter={false}
    >
      {loading ? (
        <div className="loading py-5"><div className="spinner"></div></div>
      ) : (
        <div className="finance-settings-card">
          <p className="text-muted mb-4" style={{ fontSize: '0.9rem', lineHeight: 1.5 }}>
            Le montant est calculé à partir du <strong>temps réalisé</strong> (badgeage effectif)
            multiplié par ce tarif horaire.
          </p>

          <form onSubmit={handleSubmit}>
            <div className="form-group mb-3">
              <label className="form-label fw-semibold">Prix pour 1 heure réalisée</label>
              <div className="input-group input-group-lg">
                <input
                  type="number"
                  className="form-control"
                  min="0"
                  step="0.01"
                  required
                  value={prix}
                  onChange={(e) => setPrix(e.target.value)}
                  disabled={!canEdit || saving}
                />
                <span className="input-group-text fw-semibold">FCFA / h</span>
              </div>
            </div>

            <div className="finance-settings-preview">
              <div className="mb-2"><i className="bi bi-calculator me-2"></i><strong>Exemple de calcul</strong></div>
              <div>10 h réalisées × {formatMoney(prixNum)} FCFA = <strong>{formatMoney(prixNum * 10)} FCFA</strong></div>
              <div className="mt-1 text-muted small">31 min réalisées ≈ {formatMoney((prixNum * 31) / 60)} FCFA</div>
            </div>

            {(meta.updated_at || meta.updated_by) && (
              <p className="text-muted small mt-3 mb-3">
                <i className="bi bi-clock-history me-1"></i>
                Dernière mise à jour : {formatDateTime(meta.updated_at)}
                {meta.updated_by ? ` par ${meta.updated_by}` : ''}
              </p>
            )}

            {canEdit && (
              <button type="submit" className="btn btn-dfrc mt-2" disabled={saving}>
                {saving ? 'Enregistrement…' : (
                  <><i className="bi bi-check-lg me-1"></i>Enregistrer</>
                )}
              </button>
            )}
          </form>
        </div>
      )}
    </FinancePageShell>
  )
}
