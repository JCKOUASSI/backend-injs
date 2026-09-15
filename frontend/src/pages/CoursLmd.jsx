import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'

/**
 * Cours (LMD) — vue « Enseignement » du modèle fonctionnel 04 : la ligne de
 * cours = affectation pédagogique (ECUE × groupe × enseignant × type) jointe
 * au planning EDT, à l'effectif du groupe et aux séances réalisées (présences
 * du lot C). Lecture seule ; chemin /cours.
 */

const ENDPOINT = '/scolarite/pedagogie/cours/'
const TYPES = [
  { valeur: '', libelle: 'Tous types' },
  { valeur: 'CM', libelle: 'CM' },
  { valeur: 'TD', libelle: 'TD' },
  { valeur: 'TP', libelle: 'TP' },
]
const STATUTS = ['', 'PROPOSEE', 'VALIDEE', 'PLANIFIEE', 'REALISEE']

function ProgressionSeances({ ligne }) {
  const planifiees = ligne.nb_seances_planifiees || 0
  const realisees = ligne.nb_seances_realisees || 0
  if (!planifiees) {
    return <span className="text-muted" title="Aucun créneau EDT rattaché à ce groupe/cycle">planification manquante</span>
  }
  const ratio = Math.min(100, Math.round((realisees / planifiees) * 100))
  return (
    <div style={{ minWidth: 110 }} title={`${realisees} séance(s) réalisée(s) sur ${planifiees} planifiée(s)`}>
      <div className="d-flex justify-content-between">
        <small>{realisees}/{planifiees}</small>
        <small className="text-muted">{ratio}%</small>
      </div>
      <div style={{ background: '#e9ecef', borderRadius: 4, height: 6 }}>
        <div style={{ width: `${ratio}%`, background: ratio >= 100 ? '#2e7d32' : '#1565C0', height: 6, borderRadius: 4 }} />
      </div>
    </div>
  )
}

export default function CoursLmd() {
  const [lignes, setLignes] = useState([])
  const [charge, setCharge] = useState(true)
  const [erreur, setErreur] = useState('')
  const [filtres, setFiltres] = useState({ q: '', type: '', statut: '' })
  const [detail, setDetail] = useState(null)

  const charger = useCallback(async () => {
    setCharge(true)
    setErreur('')
    try {
      const params = new URLSearchParams()
      if (filtres.q.trim()) params.set('q', filtres.q.trim())
      if (filtres.type) params.set('type_enseignement', filtres.type)
      if (filtres.statut) params.set('statut', filtres.statut)
      const res = await api.get(`${ENDPOINT}?${params.toString()}`)
      const donnees = res.data || {}
      const liste = donnees.resultats || (Array.isArray(donnees) ? donnees : [])
      setLignes(liste)
      setDetail((d) => (d ? liste.find((l) => l.id === d.id) || null : null))
    } catch {
      setErreur('Erreur lors du chargement des enseignements.')
    } finally {
      setCharge(false)
    }
  }, [filtres.q, filtres.type, filtres.statut])

  useEffect(() => { charger() }, [charger])

  const stats = useMemo(() => {
    const avecPlanning = lignes.filter((l) => l.nb_seances_planifiees > 0)
    return {
      total: lignes.length,
      sansPlanning: lignes.length - avecPlanning.length,
      effectifTotal: lignes.reduce((acc, l) => acc + (l.effectif || 0), 0),
    }
  }, [lignes])

  const majFiltre = (cle) => (e) => setFiltres((f) => ({ ...f, [cle]: e.target.value }))

  return (
    <div>
      <div className="card">
        <div className="card-body">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
            <div>
              <h6 className="mb-0" style={{ fontWeight: 700 }}>
                <i className="bi bi-journal-bookmark me-2"></i>Cours (LMD)
              </h6>
              <small className="text-muted">
                Année → cycle → niveau → semestre → ECUE → enseignant → groupe → séances (modèle 04) ;
                l’avancement suit les pointages de séance (QR / émargement).
              </small>
            </div>
            <div className="d-flex align-items-center gap-2" style={{ flexWrap: 'wrap' }}>
              <input className="input input-sm" placeholder="Rechercher ECUE, enseignant, groupe…"
                     value={filtres.q} onChange={majFiltre('q')} style={{ maxWidth: 260 }} />
              <select className="input input-sm" value={filtres.type} onChange={majFiltre('type')} style={{ maxWidth: 140 }}>
                {TYPES.map((t) => <option key={t.valeur} value={t.valeur}>{t.libelle}</option>)}
              </select>
              <select className="input input-sm" value={filtres.statut} onChange={majFiltre('statut')} style={{ maxWidth: 160 }}>
                {STATUTS.map((st) => <option key={st} value={st}>{st || 'Tous statuts'}</option>)}
              </select>
            </div>
          </div>
        </div>
      </div>

      {erreur && <div className="error-message">{erreur}</div>}

      <div className="card">
        <div className="card-header-bar">
          <span><i className="bi bi-list-ul me-2"></i>Enseignements de l’année courante</span>
          <span className="d-flex gap-2">
            <span className="badge-bg-secondary">{stats.total} ligne(s)</span>
            {stats.sansPlanning > 0 && (
              <span className="badge-bg-warning" title="Créneaux EDT à publier pour ces groupes">{stats.sansPlanning} sans planning</span>
            )}
            <span className="badge-bg-secondary">{stats.effectifTotal} étudiant(s)</span>
          </span>
        </div>
        <div className="card-body-flush">
          {charge ? (
            <div className="loading"><div className="spinner"></div></div>
          ) : lignes.length === 0 ? (
            <div className="text-center py-5 text-muted">
              <i className="bi bi-journal-x" style={{ fontSize: '2rem' }}></i>
              <p className="mt-2">Aucun enseignement pour ce filtre — chargez les affectations pédagogiques (charge par groupe) et publiez l’EDT.</p>
            </div>
          ) : (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>ECUE</th><th>Type</th><th>Groupe</th><th>Enseignant</th>
                    <th>Planning</th><th>Effectif</th><th>Séances</th><th>Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {lignes.map((l) => (
                    <tr key={l.id}
                        style={{ cursor: 'pointer', background: detail?.id === l.id ? 'rgba(21,101,192,.07)' : undefined }}
                        onClick={() => setDetail(l)}>
                      <td>
                        <code>{l.ecue}</code> <small className="text-muted">{l.ecue_intitule}</small>
                        <br />
                        <small className="text-muted">{l.cycle || 'cycle non rattaché'} · {l.niveau} · {l.semestre}</small>
                      </td>
                      <td><span className="badge-bg-secondary">{l.type_enseignement}</span></td>
                      <td>{l.groupe_nom || <span className="text-muted">—</span>}</td>
                      <td>{l.enseignant || <span className="text-muted">à désigner</span>}</td>
                      <td>
                        {l.planning?.length ? (
                          <small>{l.planning.map((c) => `${c.jour} ${c.horaire}${c.salle ? ` · ${c.salle}` : ''}`).join(' ; ')}</small>
                        ) : <span className="text-muted">—</span>}
                      </td>
                      <td>
                        {l.effectif ?? '—'}
                        {l.capacite_max ? <small className="text-muted">/{l.capacite_max}</small> : null}
                      </td>
                      <td><ProgressionSeances ligne={l} /></td>
                      <td><small>{l.statut}</small></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {detail && (
        <div className="card">
          <div className="card-header-bar">
            <span><i className="bi bi-eye me-2"></i>Détail — {detail.ecue} {detail.ecue_intitule} ({detail.groupe_nom || 'sans groupe'})</span>
            <button className="btn btn-outline-secondary btn-sm" onClick={() => setDetail(null)}>Fermer</button>
          </div>
          <div className="card-body">
            <div className="row">
              <div className="col-md-6">
                <table className="table table-sm mb-0">
                  <tbody>
                    <tr><th className="text-muted">Cursus</th><td>{detail.annee} · {detail.cycle || '—'}{detail.parcours ? ` · ${detail.parcours}` : ''}</td></tr>
                    <tr><th className="text-muted">Position</th><td>{detail.niveau} · {detail.semestre} · {detail.ue}</td></tr>
                    <tr><th className="text-muted">Volume</th><td>{detail.volume_horaire} h — {detail.credits ?? '—'} crédits</td></tr>
                    <tr><th className="text-muted">Enseignant</th><td>{detail.enseignant || 'à désigner'}</td></tr>
                    <tr><th className="text-muted">Dates</th><td>{detail.dates?.debut || '—'} → {detail.dates?.fin || '—'}</td></tr>
                  </tbody>
                </table>
              </div>
              <div className="col-md-6">
                <h6 style={{ fontWeight: 600 }}>Séances planifiées (EDT)</h6>
                {!detail.planning?.length && <div className="text-muted small">Aucun créneau publié pour ce groupe/cycle.</div>}
                <ul className="list-unstyled mb-2">
                  {(detail.planning || []).map((c) => (
                    <li key={`${c.id}-${c.jour}`} className="mb-1 d-flex align-items-center gap-2" style={{ flexWrap: 'wrap' }}>
                      <span className="badge-bg-secondary">{c.jour} {c.horaire}</span>
                      <small className="text-muted">{c.salle || 'salle à préciser'} · {c.nature} · {c.semaines}</small>
                      <Link className="btn btn-outline-secondary btn-sm" to={`/edt/presences?seance=${c.id}`}>
                        <i className="bi bi-check2-square me-1"></i>Présences
                      </Link>
                    </li>
                  ))}
                </ul>
                <ProgressionSeances ligne={detail} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
