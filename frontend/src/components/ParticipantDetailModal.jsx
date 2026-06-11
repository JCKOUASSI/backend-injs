import { useState } from 'react'
import { formatDate } from '../utils/dates'

const PARTICIPANT_DETAIL_TABS = [
  { id: 'statistiques', label: 'Statistiques', icon: 'bi-graph-up' },
  { id: 'identite', label: 'Identité', icon: 'bi-person-badge' },
  { id: 'modules', label: 'Modules', icon: 'bi-journal-bookmark' },
  { id: 'seances', label: 'Séances', icon: 'bi-clock-history' },
]

export default function ParticipantDetailModal({
  participant,
  modules,
  pointages,
  stats,
  onClose,
  loading,
}) {
  const [activeTab, setActiveTab] = useState('statistiques')

  if (!participant) return null

  const sexeLabel = (s) => ({ MASCULIN: 'Masculin', FEMININ: 'Féminin' }[s] || '-')
  const sexeBadge = (s) => s === 'MASCULIN' ? 'badge-bg-info' : s === 'FEMININ' ? 'badge-bg-warning' : ''

  // Grouper les séances par formation/module
  const sessionsByModule = pointages?.reduce((acc, pt) => {
    const key = `${pt.formation_id || 'none'}-${pt.module_intitule || 'none'}`
    if (!acc[key]) {
      acc[key] = {
        formation_titre: pt.formation_titre || 'Formation',
        module_intitule: pt.module_intitule || '',
        sessions: []
      }
    }
    acc[key].sessions.push(pt)
    return acc
  }, {}) || {}

  const sessionsByModuleList = Object.values(sessionsByModule).sort((a, b) => {
    return a.formation_titre.localeCompare(b.formation_titre)
  })

  return (
    <div className="modal-overlay finance-modal" onClick={onClose}>
      <div
        className="modal-content"
        style={{ width: 'min(96vw, 1100px)', maxWidth: '1100px', maxHeight: '92vh', display: 'flex', flexDirection: 'column' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h5>
            <i className="bi bi-person-badge me-2"></i>
            {participant.nom} {participant.prenom}
            {participant.matricule && (
              <small className="ms-2 opacity-75">({participant.matricule})</small>
            )}
          </h5>
          <button type="button" className="btn-close" disabled={loading} onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body" style={{ overflowY: 'auto', flex: 1, padding: '1rem 1.25rem' }}>
          {loading ? (
            <div className="loading py-5"><div className="spinner"></div></div>
          ) : (
            <>
              <ul className="finance-detail-tabs" role="tablist">
                {PARTICIPANT_DETAIL_TABS.map((tab) => (
                  <li key={tab.id} role="presentation">
                    <button
                      type="button"
                      className={`finance-detail-tab${activeTab === tab.id ? ' active' : ''}`}
                      onClick={() => setActiveTab(tab.id)}
                    >
                      <i className={`bi ${tab.icon}`}></i>
                      <span>{tab.label}</span>
                    </button>
                  </li>
                ))}
              </ul>

              <div className="finance-modal-summary">
                <span><i className="bi bi-journal-bookmark"></i>Modules <strong>{modules?.length ?? 0}</strong></span>
                <span><i className="bi bi-check-circle"></i>Présences <strong>{stats?.terminees ?? 0}</strong></span>
                <span><i className="bi bi-clock-history"></i>Temps total <strong>{Math.round((stats?.total_minutes ?? 0) / 60 * 10) / 10}h</strong></span>
                <span><i className="bi bi-hourglass-split"></i>En cours <strong>{stats?.en_cours ?? 0}</strong></span>
                {stats?.a_verifier > 0 && (
                  <span className="text-danger"><i className="bi bi-exclamation-triangle"></i>À vérifier <strong>{stats.a_verifier}</strong></span>
                )}
              </div>

              {activeTab === 'statistiques' && (
                <div className="grid-2">
                  <div className="card" style={{ padding: '1rem' }}>
                    <h6 className="text-muted mb-3"><i className="bi bi-graph-up me-2"></i>Vue d'ensemble</h6>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                      <div style={{ textAlign: 'center', padding: '1rem', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                        <div style={{ fontSize: '2rem', fontWeight: 600, color: 'var(--primary)' }}>{stats?.terminees ?? 0}</div>
                        <small className="text-muted">Présences terminées</small>
                      </div>
                      <div style={{ textAlign: 'center', padding: '1rem', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                        <div style={{ fontSize: '2rem', fontWeight: 600, color: 'var(--warning)' }}>{stats?.en_cours ?? 0}</div>
                        <small className="text-muted">En cours</small>
                      </div>
                      <div style={{ textAlign: 'center', padding: '1rem', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                        <div style={{ fontSize: '2rem', fontWeight: 600, color: 'var(--success)' }}>{Math.round((stats?.total_minutes ?? 0) / 60 * 10) / 10}h</div>
                        <small className="text-muted">Temps total</small>
                      </div>
                      <div style={{ textAlign: 'center', padding: '1rem', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                        <div style={{ fontSize: '2rem', fontWeight: 600, color: 'var(--info)' }}>{modules?.length ?? 0}</div>
                        <small className="text-muted">Modules</small>
                      </div>
                    </div>
                  </div>
                  
                  <div className="card" style={{ padding: '1rem' }}>
                    <h6 className="text-muted mb-3"><i className="bi bi-building me-2"></i>Répartition par formation</h6>
                    {stats?.formations_count > 0 ? (
                      <div>
                        <div className="mb-2"><strong>{stats.formations_count}</strong> formation(s) suivie(s)</div>
                        <div className="mb-2"><strong>{stats.modules_count}</strong> module(s) inscrit(s)</div>
                        {stats.a_verifier > 0 && (
                          <div className="alert alert-warning py-2 small">
                            <i className="bi bi-exclamation-triangle me-1"></i>
                            {stats.a_verifier} pointage(s) nécessitent une vérification
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-muted">Aucune donnée disponible</div>
                    )}
                  </div>
                </div>
              )}

              {activeTab === 'identite' && (
                <div className="grid-2">
                  <div><small className="text-muted">N° d'inscription</small><div><span className="badge-bg-info">{participant.matricule || '-'}</span></div></div>
                  <div><small className="text-muted">Nom</small><div><strong>{participant.nom || '-'}</strong></div></div>
                  <div><small className="text-muted">Prénom</small><div><strong>{participant.prenom || '-'}</strong></div></div>
                  <div><small className="text-muted">Genre</small><div>{participant.sexe ? <span className={sexeBadge(participant.sexe)}>{sexeLabel(participant.sexe)}</span> : '-'}</div></div>
                  <div><small className="text-muted">Date de naissance</small><div>{formatDate(participant.date_naissance)}</div></div>
                  <div><small className="text-muted">Lieu de naissance</small><div>{participant.lieu_naissance || '-'}</div></div>
                  <div><small className="text-muted">E-mail</small><div>{participant.email || '-'}</div></div>
                  <div><small className="text-muted">Téléphone</small><div>{participant.telephone || '-'}</div></div>
                  <div><small className="text-muted">Téléphone 2</small><div>{participant.telephone2 || '-'}</div></div>
                  <div><small className="text-muted">Type concours</small><div>{participant.type_concours || '-'}</div></div>
                  <div><small className="text-muted">Libellé concours</small><div>{participant.libelle_concours || '-'}</div></div>
                  <div><small className="text-muted">Catégorie</small><div>{participant.categorie || '-'}</div></div>
                  <div><small className="text-muted">Grade</small><div>{participant.grade || '-'}</div></div>
                  <div><small className="text-muted">Groupe</small><div>{participant.groupe || '-'}</div></div>
                  <div><small className="text-muted">Grade-Groupe</small><div>{participant.grade_groupe || '-'}</div></div>
                  <div><small className="text-muted">Vague</small><div>{participant.vague || '-'}</div></div>
                  <div><small className="text-muted">Site</small><div>{participant.site || '-'}</div></div>
                  <div><small className="text-muted">Salle</small><div>{participant.salle || '-'}</div></div>
                  <div style={{ gridColumn: '1 / -1' }}><small className="text-muted">Secrétariat</small><div>{participant.secretariat_nom || '-'}</div></div>
                </div>
              )}

              {activeTab === 'modules' && (
                <>
                  {modules?.length === 0 ? (
                    <div className="finance-empty"><i className="bi bi-journal-bookmark"></i>Aucun module inscrit</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                      {modules.map((m) => (
                        <div key={m.id} className="card" style={{ padding: '0.9rem' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                            <div>
                              <strong>{m.module}</strong>
                              {m.formation && <span className="text-muted" style={{ fontSize: '0.85rem' }}> — {m.formation}</span>}
                              <div className="text-muted" style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>
                                {(m.grade || m.groupe) && <span className="me-2"><i className="bi bi-people me-1"></i>{[m.grade, m.groupe].filter(Boolean).join(' / ')}</span>}
                                {m.vague && <span className="me-2"><i className="bi bi-layers me-1"></i>{m.vague}</span>}
                                {(m.site) && <span className="me-2"><i className="bi bi-building me-1"></i>{m.site}</span>}
                              </div>
                              <div className="text-muted" style={{ fontSize: '0.8rem', marginTop: '0.15rem' }}>
                                {m.date_debut && <span><i className="bi bi-calendar3 me-1"></i>{formatDate(m.date_debut)} → {m.date_fin ? formatDate(m.date_fin) : '?'}</span>}
                              </div>
                            </div>
                            <span className={`badge ${{ 'PLANIFIEE': 'badge-planifiee', 'EN_COURS': 'badge-en-cours', 'TERMINEE': 'badge-terminee', 'SUSPENDUE': 'badge-suspendue' }[m.statut] || 'badge-info'}`}>
                              {{ 'PLANIFIEE': 'Planifiée', 'EN_COURS': 'En cours', 'TERMINEE': 'Terminée', 'SUSPENDUE': 'Suspendue' }[m.statut] || m.statut}
                            </span>
                          </div>
                          <div style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}>
                            <span className="text-muted">Durée prévue : <strong>{m.duree_prevue_heures}h</strong></span>
                            {m.inscrit_le && <span className="text-muted ms-2">| Inscrit le {formatDate(m.inscrit_le)}</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}

              {activeTab === 'seances' && (
                <>
                  {pointages?.length === 0 ? (
                    <div className="finance-empty"><i className="bi bi-clock-history"></i>Aucun badgeage enregistré</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                      {sessionsByModuleList.map((group) => (
                        <div key={`${group.formation_titre}-${group.module_intitule}`} className="card" style={{ padding: '1rem' }}>
                          <h6 style={{ marginBottom: '0.75rem', paddingBottom: '0.5rem', borderBottom: '1px solid var(--border)' }}>
                            <i className="bi bi-journal-bookmark me-2"></i>
                            {group.formation_titre}
                            {group.module_intitule && <span className="text-muted"> — {group.module_intitule}</span>}
                          </h6>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            {group.sessions.map((pt) => (
                              <div key={pt.id} style={{ 
                                background: 'var(--bg-secondary)', 
                                borderRadius: '6px', 
                                padding: '0.75rem',
                                borderLeft: `4px solid ${pt.statut === 'TERMINE' ? 'var(--success)' : pt.statut === 'EN_COURS' ? 'var(--warning)' : 'var(--secondary)'}`,
                              }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                                  <div>
                                    <div style={{ fontWeight: 500 }}>
                                      <i className="bi bi-calendar3 me-1"></i>
                                      {pt.date_journee}
                                      {pt.temps_cours?.heure_debut_prevue && (
                                        <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
                                          <i className="bi bi-clock me-1"></i>
                                          {pt.temps_cours.heure_debut_prevue?.substring(0, 5)} → {pt.temps_cours.heure_fin_prevue?.substring(0, 5)}
                                        </span>
                                      )}
                                    </div>
                                    <div style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>
                                      {pt.seance_intitule && <span className="me-2">{pt.seance_intitule}</span>}
                                      {pt.seance_numero && <span className="text-muted">(Séance {pt.seance_numero})</span>}
                                    </div>
                                  </div>
                                  <span className={`badge ${pt.statut === 'TERMINE' ? 'badge-bg-success' : pt.statut === 'EN_COURS' ? 'badge-bg-warning' : 'badge-bg-secondary'}`}>
                                    {pt.statut_label || pt.statut}
                                  </span>
                                </div>
                                
                                <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.5rem', flexWrap: 'wrap', fontSize: '0.8rem' }}>
                                  <span>
                                    <i className="bi bi-arrow-right-circle me-1 text-success"></i>
                                    Entrée : {pt.timestamp_entree ? new Date(pt.timestamp_entree).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : '-'}
                                  </span>
                                  <span>
                                    <i className="bi bi-arrow-left-circle me-1 text-danger"></i>
                                    Sortie : {pt.timestamp_sortie ? new Date(pt.timestamp_sortie).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : '-'}
                                  </span>
                                  {pt.duree_presence_minutes > 0 && (
                                    <span>
                                      <i className="bi bi-stopwatch me-1 text-info"></i>
                                      Durée : <strong>{Math.round(pt.duree_presence_minutes)} min</strong>
                                    </span>
                                  )}
                                </div>

                                {/* Détails techniques du badgeage */}
                                <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem', flexWrap: 'wrap', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                  {pt.device_id && (
                                    <span title={`Appareil: ${pt.device_id}`}>
                                      <i className="bi bi-phone me-1"></i>
                                      {pt.device_id.substring(0, 12)}...
                                    </span>
                                  )}
                                  {pt.geolocalisation && (
                                    <span title={`Lat: ${pt.geolocalisation.latitude}, Lng: ${pt.geolocalisation.longitude}`}>
                                      <i className="bi bi-geo-alt me-1 text-primary"></i>
                                      📍 {pt.geolocalisation.precision_m ? `±${Math.round(pt.geolocalisation.precision_m)}m` : ''}
                                    </span>
                                  )}
                                  {pt.appareil?.batterie_pct !== undefined && (
                                    <span title={`Batterie: ${pt.appareil.batterie_pct}%${pt.appareil.en_charge ? ' (en charge)' : ''}`}>
                                      <i className={`bi bi-battery-${pt.appareil.batterie_pct > 50 ? 'full' : pt.appareil.batterie_pct > 25 ? 'half' : 'low'} me-1`}></i>
                                      {pt.appareil.batterie_pct}%
                                    </span>
                                  )}
                                  {pt.last_heartbeat_at && (
                                    <span title={`Dernier heartbeat: ${new Date(pt.last_heartbeat_at).toLocaleString('fr-FR')}`}>
                                      <i className="bi bi-activity me-1"></i>
                                      {new Date(pt.last_heartbeat_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                                    </span>
                                  )}
                                  {pt.sorties_geofence_count > 0 && (
                                    <span className="text-danger" title={`Sorties du périmètre: ${pt.sorties_geofence_count}`}>
                                      <i className="bi bi-exclamation-triangle me-1"></i>
                                      {pt.sorties_geofence_count} sortie(s) geofence
                                    </span>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" disabled={loading} onClick={onClose}>Fermer</button>
        </div>
      </div>
    </div>
  )
}
