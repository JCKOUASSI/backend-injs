import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import api from '../../services/api'
import { useToast } from '../../context/ToastContext'
import { FinanceStatsGrid, FinanceModulesList, fmtHeures, formatMoney } from '../FinanceStatsGrid'
import Pagination from '../Pagination'
import { useClientPagination, TABLE_PAGE_SIZE } from '../../hooks/useClientPagination'

const FINANCE_DETAIL_TABS = [
  { id: 'statistiques', label: 'Statistiques', icon: 'bi-graph-up' },
  { id: 'identite', label: 'Identité', icon: 'bi-person-badge' },
  { id: 'modules', label: 'Modules', icon: 'bi-journal-bookmark' },
  { id: 'seances', label: 'Séances', icon: 'bi-clock-history' },
  { id: 'paie', label: 'Fiche de paie', icon: 'bi-cash-coin' },
]

export default function FinanceDetailModal({
  financeDetail,
  financeDetailLoading,
  financeDetailTab,
  setFinanceDetailTab,
  onClose,
  formatDuration,
  formatDate,
  exportFinanceSummary,
  exportAfficherMontants = true,
  onExportMontantsChange,
  financeStatsForGrid,
  canEditSensitive = false,
  canViewSensitive = false,
  onSensitiveSaved,
}) {
  const { showToast } = useToast()
  const [sensitive, setSensitive] = useState({ numero_piece_identite: '', numero_compte_bancaire: '' })
  const [savingSensitive, setSavingSensitive] = useState(false)

  useEffect(() => {
    if (financeDetail) {
      setSensitive({
        numero_piece_identite: financeDetail.numero_piece_identite || '',
        numero_compte_bancaire: financeDetail.numero_compte_bancaire || '',
      })
    }
  }, [
    financeDetail?.id,
    financeDetail?.numero_piece_identite,
    financeDetail?.numero_compte_bancaire,
  ])

  const saveSensitive = async () => {
    if (!financeDetail?.id || !canEditSensitive) return
    setSavingSensitive(true)
    try {
      const res = await api.patch(`/formations/formateurs/${financeDetail.id}/donnees-sensibles/`, sensitive)
      showToast('Coordonnées bancaires enregistrées')
      onSensitiveSaved?.(res.data)
    } catch (err) {
      showToast(err.response?.data?.detail || 'Erreur lors de la sauvegarde', 'error')
    } finally {
      setSavingSensitive(false)
    }
  }
  const sessions = financeDetail?.sessions ?? []
  const {
    page: sessionsPage,
    setPage: setSessionsPage,
    totalPages: sessionsTotalPages,
    totalItems: sessionsTotalItems,
    pageItems: sessionsPageRows,
    pageSize: sessionsPageSize,
  } = useClientPagination(sessions, TABLE_PAGE_SIZE, [financeDetail?.id, financeDetailTab])

  if (!financeDetail) return null

  const financePaginationProps = {
    page: sessionsPage,
    totalPages: sessionsTotalPages,
    onPageChange: setSessionsPage,
    totalItems: sessionsTotalItems,
    pageSize: sessionsPageSize,
    activeClassName: 'pagination-num--active pagination-num--finance',
  }

  return (
    <div className="modal-overlay finance-modal" onClick={onClose}>
      <div
        className="modal-content"
        style={{ width: 'min(96vw, 1100px)', maxWidth: '1100px', maxHeight: '92vh', display: 'flex', flexDirection: 'column' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h5>
            <i className="bi bi-person-video3 me-2"></i>
            {financeDetail.prenom} {financeDetail.nom}
            {financeDetail.numerobadge && (
              <small className="ms-2 opacity-75">({financeDetail.numerobadge})</small>
            )}
          </h5>
          <button type="button" className="btn-close" disabled={financeDetailLoading} onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body" style={{ overflowY: 'auto', flex: 1, padding: '1rem 1.25rem' }}>
          {financeDetailLoading ? (
            <div className="loading py-5"><div className="spinner"></div></div>
          ) : (
            <>
              <ul className="finance-detail-tabs" role="tablist">
                {FINANCE_DETAIL_TABS.map((tab) => (
                  <li key={tab.id} role="presentation">
                    <button
                      type="button"
                      className={`finance-detail-tab${financeDetailTab === tab.id ? ' active' : ''}`}
                      onClick={() => setFinanceDetailTab(tab.id)}
                    >
                      <i className={`bi ${tab.icon}`}></i>
                      <span>{tab.label}</span>
                    </button>
                  </li>
                ))}
              </ul>

              <div className="finance-modal-summary">
                <span><i className="bi bi-clock"></i>Planifié <strong>{formatDuration(financeDetail.total_duree_minutes)}</strong></span>
                <span><i className="bi bi-clock-history"></i>Réalisé <strong>{formatDuration(financeDetail.total_duree_realisee_minutes)}</strong></span>
                <span><i className="bi bi-percent"></i>Taux <strong>{financeDetail.statistiques?.taux_realisation_pct ?? 0}%</strong></span>
                <span><i className="bi bi-cash-stack"></i>À verser <strong>{formatMoney(financeDetail.montant_total_realise)} FCFA</strong></span>
              </div>

              {financeDetailTab === 'statistiques' && (
                <FinanceStatsGrid
                  stats={financeStatsForGrid(financeDetail)}
                  montant={financeDetail.montant_total_realise}
                />
              )}

              {financeDetailTab === 'identite' && (
                <div className="grid-2">
                  <div><small className="text-muted">N° Badge</small><div><span className="badge-bg-info">{financeDetail.numerobadge || '-'}</span></div></div>
                  <div><small className="text-muted">Nom</small><div><strong>{financeDetail.nom || '-'}</strong></div></div>
                  <div><small className="text-muted">Prénom</small><div><strong>{financeDetail.prenom || '-'}</strong></div></div>
                  <div><small className="text-muted">Spécialité</small><div>{financeDetail.specialite || '-'}</div></div>
                  <div><small className="text-muted">Grade(s)</small><div>{financeDetail.grades || '-'}</div></div>
                  <div><small className="text-muted">Groupe(s)</small><div>{financeDetail.groupes || '-'}</div></div>
                  <div><small className="text-muted">E-mail</small><div>{financeDetail.email || '-'}</div></div>
                  <div><small className="text-muted">Téléphone</small><div>{financeDetail.telephone || '-'}</div></div>
                  <div><small className="text-muted">Organisation</small><div>{financeDetail.organisation || '-'}</div></div>
                  <div><small className="text-muted">Modules (période)</small><div><span className="badge-bg-success">{financeDetail.nb_formations ?? 0}</span></div></div>
                  <div style={{ gridColumn: '1 / -1' }}>
                    <small className="text-muted">Secrétariat(s)</small>
                    <div>
                      {Array.isArray(financeDetail.secretariats_noms) && financeDetail.secretariats_noms.length > 0
                        ? financeDetail.secretariats_noms.join(', ')
                        : '-'}
                    </div>
                  </div>
                  {financeDetail.created_at && (
                    <div><small className="text-muted">Enregistré le</small><div>{formatDate(financeDetail.created_at)}</div></div>
                  )}
                  {canViewSensitive && (
                    <>
                      <div style={{ gridColumn: '1 / -1' }}>
                        <hr className="my-2" />
                        <small className="text-muted fw-semibold">Données confidentielles (finance)</small>
                      </div>
                      <div>
                        <small className="text-muted">N° pièce d&apos;identité</small>
                        {canEditSensitive ? (
                          <input
                            type="text"
                            className="form-control form-control-sm mt-1"
                            value={sensitive.numero_piece_identite}
                            onChange={(e) => setSensitive((s) => ({ ...s, numero_piece_identite: e.target.value }))}
                            disabled={savingSensitive}
                          />
                        ) : (
                          <div>{financeDetail.numero_piece_identite || '-'}</div>
                        )}
                      </div>
                      <div>
                        <small className="text-muted">N° compte bancaire</small>
                        {canEditSensitive ? (
                          <input
                            type="text"
                            className="form-control form-control-sm mt-1"
                            value={sensitive.numero_compte_bancaire}
                            onChange={(e) => setSensitive((s) => ({ ...s, numero_compte_bancaire: e.target.value }))}
                            disabled={savingSensitive}
                          />
                        ) : (
                          <div>{financeDetail.numero_compte_bancaire || '-'}</div>
                        )}
                      </div>
                      {canEditSensitive && (
                        <div style={{ gridColumn: '1 / -1' }}>
                          <button
                            type="button"
                            className="btn btn-dfrc btn-sm"
                            disabled={savingSensitive}
                            onClick={saveSensitive}
                          >
                            {savingSensitive ? 'Enregistrement…' : 'Enregistrer les données bancaires'}
                          </button>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {financeDetailTab === 'modules' && (
                <FinanceModulesList modules={financeDetail.modules} formatDuration={formatDuration} />
              )}

              {financeDetailTab === 'seances' && (
                <>
                  {Array.isArray(financeDetail.sessions) && financeDetail.sessions.length > 0 ? (
                    <>
                      <div className="finance-table-wrap">
                        <table className="finance-table">
                          <thead>
                            <tr>
                              <th>Date</th>
                              <th>Séance</th>
                              <th>Module</th>
                              <th>Formation</th>
                              <th>Grade</th>
                              <th>Groupe</th>
                              <th>Planifié</th>
                              <th>Réalisé</th>
                              <th>Taux</th>
                              <th>Pointage</th>
                            </tr>
                          </thead>
                          <tbody>
                            {sessionsPageRows.map((s) => (
                              <tr key={s.session_id}>
                                <td>{s.date_journee || '—'}</td>
                                <td>{s.intitule || `Session ${s.numero ?? ''}`}</td>
                                <td>{s.module_intitule || '—'}</td>
                                <td>{s.formation_intitule || '—'}</td>
                                <td>{s.grade || '—'}</td>
                                <td>{s.groupe || '—'}</td>
                                <td>{formatDuration(s.duree_minutes)}</td>
                                <td>{formatDuration(s.duree_realisee_minutes)}</td>
                                <td>{s.taux_realisation_pct ?? 0}%</td>
                                <td>
                                  {s.a_pointage
                                    ? <span className="badge-bg-success">Oui</span>
                                    : <span className="badge-bg-secondary">Non</span>}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <div className="finance-section-footer">
                      <Pagination {...financePaginationProps} />
                    </div>
                    </>
                  ) : (
                    <div className="finance-empty"><i className="bi bi-calendar-x"></i>Aucune séance sur cette période</div>
                  )}
                </>
              )}

              {financeDetailTab === 'paie' && (
                <>
                  <div className="finance-paie-hero">
                    <div className="grid-2">
                      <div>
                        <small className="text-muted">Tarif horaire</small>
                        <div style={{ fontWeight: 600 }}>
                          {financeDetail.tarifs_variables
                            ? 'Variable (selon la formation)'
                            : `${formatMoney(financeDetail.prix_heure_realisee ?? 0)} FCFA / h`}
                        </div>
                      </div>
                      <div>
                        <small className="text-muted">Temps réalisé</small>
                        <div style={{ fontWeight: 600 }}>
                          {formatDuration(financeDetail.total_duree_realisee_minutes)}
                          <span className="text-muted small ms-1">
                            ({fmtHeures(financeDetail.total_duree_realisee_heures)} h)
                          </span>
                        </div>
                      </div>
                      <div style={{ gridColumn: '1 / -1' }}>
                        <small className="text-muted">Montant total à verser</small>
                        <div className="finance-paie-total">{formatMoney(financeDetail.montant_total_realise ?? 0)} FCFA</div>
                      </div>
                    </div>
                  </div>

                  {!financeDetail.tarifs_variables && (financeDetail.prix_heure_realisee ?? 0) <= 0 && (
                    <div className="alert alert-warning py-2 small">
                      <i className="bi bi-exclamation-triangle me-1"></i>
                      Tarif non défini — <Link to="/finance-parametrage">Paramétrage Finance</Link>
                    </div>
                  )}

                  {Array.isArray(financeDetail.sessions) && financeDetail.sessions.length > 0 ? (
                    <>
                      <div className="finance-table-wrap">
                        <table className="finance-table">
                          <thead>
                            <tr>
                              <th>Date</th>
                              <th>Séance</th>
                              <th>Module</th>
                              <th>Réalisé</th>
                              <th style={{ textAlign: 'right' }}>Montant</th>
                            </tr>
                          </thead>
                          <tbody>
                            {sessionsPageRows.map((s) => (
                              <tr key={s.session_id}>
                                <td>{s.date_journee || '—'}</td>
                                <td>{s.intitule || `Session ${s.numero ?? ''}`}</td>
                                <td>{s.module_intitule || '—'}</td>
                                <td>{formatDuration(s.duree_realisee_minutes)}</td>
                                <td style={{ textAlign: 'right', fontWeight: 600 }}>{formatMoney(s.montant_realise ?? 0)} F</td>
                              </tr>
                            ))}
                          </tbody>
                          <tfoot>
                            <tr style={{ background: '#f0fdf4' }}>
                              <td colSpan="4" style={{ textAlign: 'right', fontWeight: 700 }}>Total</td>
                              <td style={{ textAlign: 'right', fontWeight: 800, color: 'var(--fin-green)' }}>
                                {formatMoney(financeDetail.montant_total_realise ?? 0)} FCFA
                              </td>
                            </tr>
                          </tfoot>
                        </table>
                      </div>
                      <div className="finance-section-footer">
                        <Pagination {...financePaginationProps} />
                      </div>
                    </>
                  ) : (
                    <div className="finance-empty"><i className="bi bi-cash"></i>Aucune donnée de paie</div>
                  )}
                </>
              )}
            </>
          )}
        </div>

        <div className="modal-footer">
          {!financeDetailLoading && (
            <div className="d-flex flex-wrap align-items-center gap-3 me-auto">
              <label className="form-check mb-0 small" style={{ cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  className="form-check-input me-1"
                  checked={exportAfficherMontants}
                  onChange={(e) => onExportMontantsChange?.(e.target.checked)}
                />
                Afficher les montants sur l&apos;export
              </label>
              <div className="btn-group">
                <button
                  type="button"
                  className="btn btn-outline-success btn-sm"
                  onClick={() => exportFinanceSummary(financeDetail, 'excel', exportAfficherMontants)}
                >
                  <i className="bi bi-file-earmark-spreadsheet me-1"></i>Excel
                </button>
                <button
                  type="button"
                  className="btn btn-outline-danger btn-sm"
                  onClick={() => exportFinanceSummary(financeDetail, 'pdf', exportAfficherMontants)}
                >
                  <i className="bi bi-file-earmark-pdf me-1"></i>PDF
                </button>
              </div>
            </div>
          )}
          <button type="button" className="btn btn-secondary" disabled={financeDetailLoading} onClick={onClose}>Fermer</button>
        </div>
      </div>
    </div>
  )
}
