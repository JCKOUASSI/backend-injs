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
  const [tarifs, setTarifs] = useState([])
  const [exportSettings, setExportSettings] = useState({
    afficher_montants_exports: true,
    export_titre_document: 'ÉTAT FINANCIER FORMATEUR',
    export_entete_ligne1: '',
    export_entete_ligne2: '',
    export_organisme: '',
    export_adresse: '',
    export_reference_prefix: 'EFI',
    export_mention_legale: '',
    export_signataire_nom: '',
    export_signataire_fonction: '',
  })
  const [meta, setMeta] = useState({ updated_at: null, updated_by: null })

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const res = await api.get('/formations/finance/settings/')
        setPrix(String(res.data?.prix_heure_realisee ?? 0))
        setTarifs(
          (res.data?.tarifs_formations ?? []).map((t) => ({
            ...t,
            prix_heure_realisee: t.prix_heure_realisee != null ? String(t.prix_heure_realisee) : '',
          })),
        )
        setExportSettings({
          afficher_montants_exports: res.data?.afficher_montants_exports !== false,
          export_titre_document: res.data?.export_titre_document || 'ÉTAT FINANCIER FORMATEUR',
          export_entete_ligne1: res.data?.export_entete_ligne1 || '',
          export_entete_ligne2: res.data?.export_entete_ligne2 || '',
          export_organisme: res.data?.export_organisme || '',
          export_adresse: res.data?.export_adresse || '',
          export_reference_prefix: res.data?.export_reference_prefix || 'EFI',
          export_mention_legale: res.data?.export_mention_legale || '',
          export_signataire_nom: res.data?.export_signataire_nom || '',
          export_signataire_fonction: res.data?.export_signataire_fonction || '',
        })
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

  const handleTarifChange = (id, value) => {
    setTarifs((prev) =>
      prev.map((t) => (t.id === id ? { ...t, prix_heure_realisee: value } : t)),
    )
  }

  const parsePrix = (raw) => {
    if (raw === '' || raw == null) return null
    const value = Number(String(raw).replace(',', '.'))
    if (Number.isNaN(value) || value < 0) return NaN
    return value
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!canEdit) return

    const defaultPrix = parsePrix(prix)
    if (Number.isNaN(defaultPrix)) {
      showToast('Le tarif par défaut doit être un montant valide (≥ 0) ou vide (0).', 'error')
      return
    }

    const tarifsPayload = []
    for (const t of tarifs) {
      const value = parsePrix(t.prix_heure_realisee)
      if (Number.isNaN(value)) {
        showToast(`Tarif invalide pour « ${t.intitule} ».`, 'error')
        return
      }
      tarifsPayload.push({ id: t.id, prix_heure_realisee: value })
    }

    setSaving(true)
    try {
      const res = await api.patch('/formations/finance/settings/', {
        prix_heure_realisee: defaultPrix ?? 0,
        tarifs_formations: tarifsPayload,
        ...exportSettings,
      })
      setPrix(String(res.data?.prix_heure_realisee ?? defaultPrix))
      setTarifs(
        (res.data?.tarifs_formations ?? []).map((t) => ({
          ...t,
          prix_heure_realisee: t.prix_heure_realisee != null ? String(t.prix_heure_realisee) : '',
        })),
      )
      setMeta({
        updated_at: res.data?.updated_at || null,
        updated_by: res.data?.updated_by || null,
      })
      setExportSettings({
        afficher_montants_exports: res.data?.afficher_montants_exports !== false,
        export_titre_document: res.data?.export_titre_document || 'ÉTAT FINANCIER FORMATEUR',
        export_entete_ligne1: res.data?.export_entete_ligne1 || '',
        export_entete_ligne2: res.data?.export_entete_ligne2 || '',
        export_organisme: res.data?.export_organisme || '',
        export_adresse: res.data?.export_adresse || '',
        export_reference_prefix: res.data?.export_reference_prefix || 'EFI',
        export_mention_legale: res.data?.export_mention_legale || '',
        export_signataire_nom: res.data?.export_signataire_nom || '',
        export_signataire_fonction: res.data?.export_signataire_fonction || '',
      })
      showToast('Paramètres enregistrés')
    } catch (err) {
      showToast(err.response?.data?.detail || 'Erreur lors de la sauvegarde', 'error')
    } finally {
      setSaving(false)
    }
  }

  const setExportField = (key, value) => {
    setExportSettings((prev) => ({ ...prev, [key]: value }))
  }

  const prixNum = Number(prix) || 0
  const tarifsActifs = tarifs.filter((t) => t.actif !== false)
  const tarifsInactifs = tarifs.filter((t) => t.actif === false)

  const renderTarifRow = (t) => {
    const effective = t.prix_heure_realisee !== '' ? Number(t.prix_heure_realisee) : prixNum
    return (
      <tr key={t.id} className={t.actif === false ? 'text-muted' : ''}>
        <td>
          {t.intitule}
          {t.actif === false && (
            <span className="badge bg-secondary ms-2" style={{ fontSize: '0.65rem' }}>Inactif</span>
          )}
        </td>
        <td>
          <div className="input-group input-group-sm">
            <input
              type="number"
              className="form-control"
              min="0"
              step="0.01"
              placeholder={String(prixNum)}
              value={t.prix_heure_realisee}
              onChange={(e) => handleTarifChange(t.id, e.target.value)}
              disabled={!canEdit || saving}
            />
            <span className="input-group-text">FCFA / h</span>
          </div>
        </td>
        <td className="text-muted small">
          {t.prix_heure_realisee === ''
            ? `Défaut (${formatMoney(prixNum)} FCFA / h)`
            : `${formatMoney(effective)} FCFA / h`}
        </td>
      </tr>
    )
  }

  return (
    <FinancePageShell
      title="Paramétrage Finance"
      subtitle="Tarifs horaires appliqués au calcul des fiches de paie"
      icon="bi-sliders"
      actions={<FinanceNavActions active="parametrage" />}
      showPeriodFilter={false}
    >
      {loading ? (
        <div className="loading py-5"><div className="spinner"></div></div>
      ) : (
        <div className="finance-settings-card finance-settings-card-wide">
          <p className="text-muted mb-4" style={{ fontSize: '0.9rem', lineHeight: 1.5 }}>
            Le montant est calculé à partir du <strong>temps réalisé</strong> (badgeage effectif)
            multiplié par le tarif horaire du <strong>cycle de formation</strong> concerné.
            La liste reprend les formations du référentiel et les cycles déjà utilisés dans l&apos;application.
            Définissez un tarif par formation ci-dessous ; le tarif par défaut ne sert que de repli
            si une formation n&apos;a pas de tarif propre.
          </p>

          <form onSubmit={handleSubmit}>
            <div className="form-group mb-4">
              <label className="form-label fw-semibold">
                Tarif par défaut (1 heure réalisée)
                <span className="text-muted fw-normal ms-1">— optionnel</span>
              </label>
              <div className="input-group input-group-lg" style={{ maxWidth: 420 }}>
                <input
                  type="number"
                  className="form-control"
                  min="0"
                  step="0.01"
                  value={prix}
                  onChange={(e) => setPrix(e.target.value)}
                  disabled={!canEdit || saving}
                />
                <span className="input-group-text fw-semibold">FCFA / h</span>
              </div>
              <div className="form-text">
                Repli uniquement pour les formations sans tarif spécifique dans le tableau ci-dessous.
                Si chaque formation a son propre tarif, vous pouvez laisser 0 ou ignorer ce champ.
              </div>
            </div>

            <div className="finance-settings-preview mb-4">
              <div className="mb-2"><i className="bi bi-calculator me-2"></i><strong>Exemple (tarif par défaut)</strong></div>
              <div>10 h réalisées × {formatMoney(prixNum)} FCFA = <strong>{formatMoney(prixNum * 10)} FCFA</strong></div>
              <div className="mt-1 text-muted small">31 min réalisées ≈ {formatMoney((prixNum * 31) / 60)} FCFA</div>
            </div>

            <h6 className="fw-semibold mb-3">
              <i className="bi bi-journal-bookmark me-2"></i>
              Tarifs par formation (référentiel)
            </h6>

            {tarifs.length === 0 ? (
              <p className="text-muted small">Aucune formation dans le référentiel.</p>
            ) : (
              <div className="finance-table-wrap mb-4">
                <table className="finance-table finance-settings-table">
                  <thead>
                    <tr>
                      <th>Formation (cycle)</th>
                      <th style={{ width: 240 }}>Tarif horaire</th>
                      <th style={{ width: 180 }}>Tarif appliqué</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tarifsActifs.map(renderTarifRow)}
                    {tarifsInactifs.map(renderTarifRow)}
                  </tbody>
                </table>
              </div>
            )}

            <hr className="my-4" />

            <h6 className="fw-semibold mb-3">
              <i className="bi bi-file-earmark-text me-2"></i>
              États financiers (exports PDF / Excel)
            </h6>
            <p className="text-muted small mb-3">
              En-têtes, mentions et signataire affichés sur les états financiers formateurs.
              L&apos;option montants peut aussi être modifiée à chaque export.
            </p>

            <div className="form-check form-switch mb-3">
              <input
                type="checkbox"
                className="form-check-input"
                id="afficher_montants_exports"
                checked={exportSettings.afficher_montants_exports}
                onChange={(e) => setExportField('afficher_montants_exports', e.target.checked)}
                disabled={!canEdit || saving}
              />
              <label className="form-check-label" htmlFor="afficher_montants_exports">
                Afficher les montants par défaut sur les exports
              </label>
            </div>

            <div className="row g-3 mb-3">
              <div className="col-md-6">
                <label className="form-label">Titre du document</label>
                <input
                  type="text"
                  className="form-control"
                  value={exportSettings.export_titre_document}
                  onChange={(e) => setExportField('export_titre_document', e.target.value)}
                  disabled={!canEdit || saving}
                />
              </div>
              <div className="col-md-6">
                <label className="form-label">Préfixe référence</label>
                <input
                  type="text"
                  className="form-control"
                  value={exportSettings.export_reference_prefix}
                  onChange={(e) => setExportField('export_reference_prefix', e.target.value)}
                  disabled={!canEdit || saving}
                  placeholder="EFI"
                />
              </div>
              <div className="col-md-6">
                <label className="form-label">En-tête ligne 1</label>
                <input
                  type="text"
                  className="form-control"
                  value={exportSettings.export_entete_ligne1}
                  onChange={(e) => setExportField('export_entete_ligne1', e.target.value)}
                  disabled={!canEdit || saving}
                  placeholder="République de Côte d'Ivoire"
                />
              </div>
              <div className="col-md-6">
                <label className="form-label">En-tête ligne 2</label>
                <input
                  type="text"
                  className="form-control"
                  value={exportSettings.export_entete_ligne2}
                  onChange={(e) => setExportField('export_entete_ligne2', e.target.value)}
                  disabled={!canEdit || saving}
                  placeholder="Ministère / Direction"
                />
              </div>
              <div className="col-md-6">
                <label className="form-label">Organisme</label>
                <input
                  type="text"
                  className="form-control"
                  value={exportSettings.export_organisme}
                  onChange={(e) => setExportField('export_organisme', e.target.value)}
                  disabled={!canEdit || saving}
                  placeholder="CPFAE"
                />
              </div>
              <div className="col-md-6">
                <label className="form-label">Signataire — nom</label>
                <input
                  type="text"
                  className="form-control"
                  value={exportSettings.export_signataire_nom}
                  onChange={(e) => setExportField('export_signataire_nom', e.target.value)}
                  disabled={!canEdit || saving}
                />
              </div>
              <div className="col-12">
                <label className="form-label">Adresse / coordonnées</label>
                <textarea
                  className="form-control"
                  rows={2}
                  value={exportSettings.export_adresse}
                  onChange={(e) => setExportField('export_adresse', e.target.value)}
                  disabled={!canEdit || saving}
                />
              </div>
              <div className="col-md-6">
                <label className="form-label">Signataire — fonction</label>
                <input
                  type="text"
                  className="form-control"
                  value={exportSettings.export_signataire_fonction}
                  onChange={(e) => setExportField('export_signataire_fonction', e.target.value)}
                  disabled={!canEdit || saving}
                />
              </div>
              <div className="col-md-6">
                <label className="form-label">Mention légale (pied de page)</label>
                <textarea
                  className="form-control"
                  rows={2}
                  value={exportSettings.export_mention_legale}
                  onChange={(e) => setExportField('export_mention_legale', e.target.value)}
                  disabled={!canEdit || saving}
                />
              </div>
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
