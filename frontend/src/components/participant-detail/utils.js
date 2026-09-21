/**
 * utils.js — modale de détail d'un participant (INJS-LMD 2026)
 *
 * Constantes et fonctions pures de la modale : libellés de mentions et de
 * décisions, mise en forme des durées, construction du brouillon de saisie,
 * synthèse de formation. Extraites de `ParticipantDetailModal.jsx`
 * (réduction des fichiers géants, garde-fou G.1).
 *
 * Aucune dépendance : ni React, ni API, ni contexte.
 */

export const PARTICIPANT_DETAIL_TABS = [
  { id: 'statistiques', label: 'Statistiques', icon: 'bi-graph-up' },
  { id: 'identite', label: 'Identité', icon: 'bi-person-badge' },
  { id: 'modules', label: 'Modules', icon: 'bi-journal-bookmark' },
  { id: 'notes', label: 'Notes', icon: 'bi-pencil-square' },
  { id: 'seances', label: 'Séances', icon: 'bi-clock-history' },
]

export const MENTION_LABELS = {
  TRES_BIEN: 'Très bien',
  BIEN: 'Bien',
  ASSEZ_BIEN: 'Assez bien',
  PASSABLE: 'Passable',
  INSUFFISANT: 'Insuffisant',
  '': '—',
}

export const DECISION_LABELS = {
  ADMIS: 'Admis',
  AJOURNE: 'Ajourné',
  EXCLUSION: 'Exclusion',
  EN_ATTENTE: 'En attente',
}

export const DECISION_COLORS = {
  ADMIS: { background: '#e8eff5', color: '#093f70' },
  AJOURNE: { background: '#fff8e0', color: '#e69700' },
  EXCLUSION: { background: '#ffebee', color: '#b71c1c' },
  EN_ATTENTE: { background: '#f5f5f5', color: '#616161' },
}

export const DEFAULT_CRITERES = { seuil_admission: 12, taux_presence_min: 80 }

export function mentionFromMoyenne(moyenne) {
  const n = parseFloat(moyenne)
  if (isNaN(n)) return ''
  if (n >= 16) return 'TRES_BIEN'
  if (n >= 14) return 'BIEN'
  if (n >= 12) return 'ASSEZ_BIEN'
  if (n >= 10) return 'PASSABLE'
  return 'INSUFFISANT'
}

export function formatHeuresModule(heures) {
  const h = parseFloat(heures)
  if (isNaN(h) || h <= 0) return null
  return Number.isInteger(h) ? `${h}h` : `${Math.round(h * 10) / 10}h`
}

export function moduleMetaParts(m) {
  return [
    m.grade && { icon: 'bi-people', label: m.grade },
    m.groupe && { icon: 'bi-people-fill', label: `Groupe ${m.groupe}` },
    m.vague && { icon: 'bi-layers', label: m.vague },
    m.site && { icon: 'bi-building', label: m.site },
  ].filter(Boolean)
}

export function buildDraftFromRow(row) {
  return {
    moyenne: row?.moyenne != null ? String(row.moyenne) : '',
  }
}

export function mapNotesFicheToState(data) {
  const results = {}
  for (const m of data.modules || []) {
    const row = {
      moyenne: m.moyenne,
      heures_presence: m.heures_presence,
      heures_prevues: m.heures_prevues,
      taux_presence: m.taux_presence,
      admissible: m.admissible,
      mention: m.mention,
    }
    results[m.module_id] = {
      colonneId: m.colonne_id ?? null,
      row,
      draft: buildDraftFromRow(row),
      dirty: false,
    }
  }
  const decisions = {}
  for (const f of data.formations || []) {
    decisions[f.formation_id] = {
      decision: f.decision,
      criteres: f.criteres || DEFAULT_CRITERES,
    }
  }
  return { moduleNotes: results, formationDecisions: decisions }
}

export function computeFormationSummary(formationModules, moduleNotes, criteres = DEFAULT_CRITERES) {
  let somme = 0
  let totalPoids = 0
  let totalPresence = 0
  let totalPrevu = 0

  formationModules.forEach((m) => {
    const d = moduleNotes[m.id]
    const moyenne = parseFloat(d?.draft?.moyenne ?? d?.row?.moyenne)
    const poids = parseFloat(m.duree_prevue_heures) || 1
    if (!isNaN(moyenne)) {
      somme += moyenne * poids
      totalPoids += poids
    }
    const hp = parseFloat(d?.row?.heures_presence)
    const hprev = parseFloat(d?.row?.heures_prevues ?? m.duree_prevue_heures)
    if (!isNaN(hp)) totalPresence += hp
    if (!isNaN(hprev) && hprev > 0) totalPrevu += hprev
  })

  const moyenneGenerale = totalPoids > 0 ? Math.round((somme / totalPoids) * 100) / 100 : null
  const tauxPresence = totalPrevu > 0 ? Math.round((totalPresence / totalPrevu) * 10000) / 100 : null

  const seuilNote = criteres?.seuil_admission ?? DEFAULT_CRITERES.seuil_admission
  const seuilTaux = criteres?.taux_presence_min ?? DEFAULT_CRITERES.taux_presence_min
  let decision = 'EN_ATTENTE'
  if (moyenneGenerale != null && tauxPresence != null) {
    if (moyenneGenerale >= seuilNote && tauxPresence >= seuilTaux) decision = 'ADMIS'
    else if (moyenneGenerale < 8 || tauxPresence < 50) decision = 'EXCLUSION'
    else decision = 'AJOURNE'
  }

  return {
    moyenneGenerale,
    tauxPresence,
    totalPresence: Math.round(totalPresence * 100) / 100,
    totalPrevu: Math.round(totalPrevu * 100) / 100,
    decision,
    mention: moyenneGenerale != null ? mentionFromMoyenne(moyenneGenerale) : '',
  }
}
