/**
 * Statistiques.jsx — SYGEP-CPFAE
 * Dashboard multi-onglets : Vue d'ensemble · Pédagogique · Administratif · Historique · Secrétariats · Rapports · Alertes
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import FinancePeriodFilter from '../components/FinancePeriodFilter'
import { fmtHeures } from '../components/FinanceStatsGrid'
import {
  appendPeriodToSearchParams,
  loadFinancePeriod,
  saveFinancePeriod,
  isPeriodWhollyFuture,
  currentTrimestreParts,
  financePeriodKey,
} from '../utils/financePeriod'
import { isSecretariatScopedRole, lockedSecretariatId } from '../utils/roles'
import { useStatsMeta } from '../hooks/useStatsMeta'
import { PointJournalierTableauCPFAE, pjPct } from '../components/PointJournalierCPFAE'
import { AuditeursNotoiresPanel, AuditeursNotoiresKpiStrip, filterAuditeursNotoires } from '../components/AuditeursNotoiresPanel'
import RapportsWorkflowPanel from '../components/RapportsWorkflowPanel'

// ── Palettes, libellés et constantes — voir ./statistiques/constantes.js ─────
import {
  C,
  STATUT_LABELS,
  VALIDATION_ROLES,
  RB_VIEWS,
  TAUX_PEDAGOGIE,
  KPI_VH_EXEC,
  KPI_SESSIONS_COMPT,
  KPI_SESSIONS_TOTAL,
  KPI_PERIOD_SCOPE_HELP,
  AUDITEURS_NOTOIRES,
  SECRETARIAT_STATS_TABS,
  VH_PERIOD_TABS,
  TAB_SECTIONS,
  ALERTES_OVERVIEW_CODES,
  PJ_EXPORT_FORMATS,
  RB_PERIODES,
  RB_DIMENSIONS,
  rbMatiereOptionValue,
  rbParseMatiereKey,
} from './statistiques/constantes'


// ── Primitives graphiques SVG — voir ./statistiques/graphiques.jsx ───────────
import { Empty, Donut, Bars, HBars, formatMoisLabelLong, TrendBadge } from './statistiques/graphiques'
// ── Cartes, KPI et barres de taux — voir ./statistiques/composants.jsx ─────
import {
  Card,
  Kpi,
  MonthTrendChart,
  StackedPresenceChart,
  TauxBar,
} from './statistiques/composants'
// ── Onglet Alertes — voir ./statistiques/alertes.jsx ────────────────────────
import {
  IndicateurSurveillanceCard,
  AlertesOverviewBandeau,
  buildAlertesSidebarEntries,
  AlertesEnsemblePanel,
  AlertesWidgetDetailPanel,
  AlertesStyles,
} from './statistiques/alertes'
// ── Bilan FAC — voir ./statistiques/bilan-fac.jsx ───────────────────────────
import { BilanFACPanel } from './statistiques/bilan-fac'
import { normalizeJustificatifs } from './statistiques/justificatifs'
import { BilansEnsemblePanel, BilanEffectifsModuleTable, BilanDetailPanel } from './statistiques/bilans'
// Exporté pour les tests unitaires de la synchro des justificatifs (§10.7 LOT 6).
export { BilanPeriodeFormationTable } from './statistiques/bilans'
import { SEC_TABLE_HEADERS, SecretariatsComparatifTable, SecretariatsEnsemblePanel, SecretariatDetailPanel } from './statistiques/secretariats'
import { HistoriqueEnsemblePanel, HistoriqueMoisPanel } from './statistiques/historique'
import { buildPedagogieEntries, PedagogiqueEnsemblePanel, PedagogiqueDetailPanel } from './statistiques/pedagogique'
import { OVERVIEW_SECTION_DEFS, buildOverviewSections, VueEnsemblePanel, VueOverviewDetailPanel } from './statistiques/vue-ensemble'

// ── Composant principal ────────────────────────────────────────────────────────
export default function Statistiques() {
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const isSecretariatScoped = isSecretariatScopedRole(user?.role)
  const isEncadrantScoped = user?.role === 'ENCADRANT'
  const secretariatFilterLocked = isSecretariatScoped
  const userLockedSecretariatId = lockedSecretariatId(user)
  const [onglet, setOnglet] = useState(() => (
    isSecretariatScopedRole(user?.role) ? 'point_journalier' : 'overview'
  ))
  const [data, setData] = useState(null)
  const [loadingInitial, setLoadingInitial] = useState(true)
  const [loadingTab, setLoadingTab] = useState(false)
  const [error, setError] = useState(null)
  const [formationId, setFormationId] = useState('')
  const [secretariatId, setSecretariatId] = useState('')
  const effectiveSecretariatId = userLockedSecretariatId || secretariatId
  const [lastRefresh, setLastRefresh] = useState(null)
  const [vhPeriod, setVhPeriod] = useState(() => loadFinancePeriod())
  const [appliedVhPeriod, setAppliedVhPeriod] = useState(() => loadFinancePeriod())
  const appliedPeriodKey = financePeriodKey(appliedVhPeriod)

  const { data: statsMeta } = useStatsMeta({
    formationId: formationId || undefined,
    secretariatId: effectiveSecretariatId || undefined,
    period: appliedVhPeriod,
  })

  useEffect(() => {
    if (!statsMeta) return
    setData(prev => ({
      ...(prev || {}),
      formations_liste: statsMeta.formations_liste,
      secretariats_liste: statsMeta.secretariats_liste,
      filtre_actif: statsMeta.filtre_actif,
    }))
  }, [statsMeta])

  // Secrétariats — onglet dédié
  const [secStats, setSecStats] = useState(null)
  const [loadingSecStats, setLoadingSecStats] = useState(false)
  const [secSelection, setSecSelection] = useState(null)
  const [secDetail, setSecDetail] = useState(null)
  const [loadingSecDetail, setLoadingSecDetail] = useState(false)

  // Historique — navigation par mois
  const [histSelection, setHistSelection] = useState(null)

  // Pédagogique — navigation par périmètre
  const [pedSelection, setPedSelection] = useState(null)

  // Vue d'ensemble — navigation par section
  const [overviewSelection, setOverviewSelection] = useState(null)

  // Alertes — navigation par widget / indicateur
  const [alertesSelection, setAlertesSelection] = useState(null)

  // Seuils alertes
  const [seuils, setSeuils] = useState([])
  const [editSeuils, setEditSeuils] = useState(false)
  const [seuilsForm, setSeuilsForm] = useState([])
  const [alertesMeta, setAlertesMeta] = useState({ indicateurs: [], synthese: {}, seuils_vides: true })
  const [initSeuilsLoading, setInitSeuilsLoading] = useState(false)
  const [showGuideAlertes, setShowGuideAlertes] = useState(true)

  // Point journalier
  const [pjData, setPjData] = useState(null)
  const [pjAllTableaux, setPjAllTableaux] = useState([])
  const [pjDetail, setPjDetail] = useState(null)
  const [loadingPj, setLoadingPj] = useState(false)
  const [loadingPjDetail, setLoadingPjDetail] = useState(false)
  const [pjAnnee, setPjAnnee] = useState(new Date().getFullYear())
  const [pjMois, setPjMois] = useState('')
  const [pjError, setPjError] = useState(null)
  const [pjCategorie, setPjCategorie] = useState('')
  const [pjFormationId, setPjFormationId] = useState('')
  const [pjSelection, setPjSelection] = useState(null)
  const [exportingPj, setExportingPj] = useState(null)

  // Bilans & Rapports — filtres (entête type Point Journalier)
  const [rbAnnee, setRbAnnee] = useState(new Date().getFullYear())
  const [rbMois, setRbMois] = useState('')
  const [rbCategorie, setRbCategorie] = useState('')
  const [rbModuleId, setRbModuleId] = useState('')
  const [rbMatiereKey, setRbMatiereKey] = useState('')
  const [rbFormationId, setRbFormationId] = useState('')
  const [rbPeriode, setRbPeriode] = useState('')
  const [rbCalendrier, setRbCalendrier] = useState('')
  const [rbDimension, setRbDimension] = useState('module')
  const [rbData, setRbData] = useState(null)
  const [rbAllTableaux, setRbAllTableaux] = useState([])
  const [rbJustificatifsText, setRbJustificatifsText] = useState('')
  const [rbSelection, setRbSelection] = useState(null)
  const [rbDetail, setRbDetail] = useState(null)
  const [loadingRb, setLoadingRb] = useState(false)
  const [loadingRbDetail, setLoadingRbDetail] = useState(false)
  const [exportingRb, setExportingRb] = useState(null)
  const [exportingFac, setExportingFac] = useState(null)
  const [facExportMeta, setFacExportMeta] = useState({ justificatifs: {}, difficultes: {} })

  // Bilan FAC — sous-onglet dans Rapports & Bilans
  const [facFormationId, setFacFormationId] = useState('')
  const [facAnnee, setFacAnnee] = useState(new Date().getFullYear())
  const [facCategorie, setFacCategorie] = useState('')
  const [facData, setFacData] = useState(null)
  const [loadingFac, setLoadingFac] = useState(false)
  const [facSousOnglet, setFacSousOnglet] = useState('point_global')
  const [showFacPanel, setShowFacPanel] = useState(false)
  const [facPerimetre, setFacPerimetre] = useState({ grades: [], groupes: [] })
  const [facGradesSelected, setFacGradesSelected] = useState([])
  const [facGroupesSelected, setFacGroupesSelected] = useState([])
  const [loadingFacPerimetre, setLoadingFacPerimetre] = useState(false)
  const [rbView, setRbView] = useState(() => searchParams.get('rbView') || 'bilans')

  const canValidate = VALIDATION_ROLES.includes(user?.role)
  const prevLoadCtx = useRef({ onglet, formationId, secretariatId, appliedPeriodKey })
  const hasDataRef = useRef(false)
  const fetchSeqRef = useRef(0)

  useEffect(() => {
    if (userLockedSecretariatId) {
      setSecretariatId(userLockedSecretariatId)
    }
  }, [userLockedSecretariatId])

  useEffect(() => {
    const v = searchParams.get('rbView')
    if (v === 'workflow' || v === 'bilans') setRbView(v)
    if (searchParams.get('tab') === 'rapports' || searchParams.get('rbView') === 'workflow') {
      setOnglet('rapports')
    }
  }, [searchParams])

  const setRbViewAndUrl = (view) => {
    setRbView(view)
    const next = new URLSearchParams(searchParams)
    if (view === 'bilans') next.delete('rbView')
    else next.set('rbView', view)
    setSearchParams(next, { replace: true })
  }

  useEffect(() => {
    if (isSecretariatScoped && !SECRETARIAT_STATS_TABS.has(onglet)) {
      setOnglet('point_journalier')
    }
  }, [isSecretariatScoped, onglet])

  const fetchData = useCallback(async (sections, { silent = false, initial = false } = {}) => {
    const tabSections = sections?.length ? sections : (TAB_SECTIONS[onglet] || TAB_SECTIONS.overview)
    const allSections = tabSections
    const seq = ++fetchSeqRef.current
    if (!silent) {
      if (initial) setLoadingInitial(true)
      else setLoadingTab(true)
    }
    setError(null)
    try {
      const params = new URLSearchParams()
      params.set('sections', allSections.join(','))
      if (formationId) params.set('formation_id', formationId)
      if (effectiveSecretariatId) params.set('secretariat_id', effectiveSecretariatId)
      appendPeriodToSearchParams(params, appliedVhPeriod)
      const res = await api.get(`/statistiques/?${params}`)
      if (seq !== fetchSeqRef.current) return
      setData(prev => ({ ...(prev || {}), ...res.data }))
      hasDataRef.current = true
      setLastRefresh(new Date())
    } catch(e) {
      if (seq !== fetchSeqRef.current) return
      if (!silent) setError(e.response?.data?.detail || 'Erreur de chargement.')
    } finally {
      if (seq === fetchSeqRef.current) {
        setLoadingInitial(false)
        setLoadingTab(false)
      }
    }
  }, [formationId, effectiveSecretariatId, onglet, appliedVhPeriod])

  const fetchSecStats = useCallback(async () => {
    setLoadingSecStats(true)
    setSecDetail(null)
    try {
      const params = new URLSearchParams()
      if (formationId) params.set('formation_id', formationId)
      if (effectiveSecretariatId) params.set('secretariat_id', effectiveSecretariatId)
      appendPeriodToSearchParams(params, appliedVhPeriod)
      const qs = params.toString()
      const res = await api.get(`/statistiques/secretariats/${qs ? `?${qs}` : ''}`)
      setSecStats(res.data)
      setSecSelection(prev => {
        if (!res.data.secretariats?.length) return null
        if (prev !== null && prev < res.data.secretariats.length) return prev
        return null
      })
    } catch {
      setSecStats(null)
      setSecSelection(null)
    } finally {
      setLoadingSecStats(false)
    }
  }, [formationId, effectiveSecretariatId, appliedVhPeriod])

  const fetchSecDetail = useCallback(async (secId) => {
    if (!secId) {
      setSecDetail(null)
      return
    }
    setLoadingSecDetail(true)
    try {
      const params = new URLSearchParams({
        secretariat_id: String(secId),
        sections: 'kpis,pedagogiques,admin_operationnel,filtre_actif',
      })
      if (formationId) params.set('formation_id', formationId)
      appendPeriodToSearchParams(params, appliedVhPeriod)
      const res = await api.get(`/statistiques/?${params}`)
      setSecDetail(res.data)
    } catch {
      setSecDetail(null)
    } finally {
      setLoadingSecDetail(false)
    }
  }, [formationId, appliedVhPeriod])

  const fetchSeuils = useCallback(async () => {
    try {
      const params = new URLSearchParams()
      if (formationId) params.set('formation_id', formationId)
      if (effectiveSecretariatId) params.set('secretariat_id', effectiveSecretariatId)
      const res = await api.get(`/statistiques/alertes/seuils/?${params}`)
      const payload = Array.isArray(res.data)
        ? { seuils: res.data, indicateurs: [], synthese: {}, seuils_vides: !res.data.length }
        : res.data
      setSeuils(payload.seuils || [])
      setSeuilsForm((payload.seuils || []).map(s => ({ ...s })))
      setAlertesMeta({
        indicateurs: payload.indicateurs || [],
        synthese: payload.synthese || {},
        seuils_vides: payload.seuils_vides ?? !(payload.seuils || []).length,
      })
    } catch {}
    // Le callback ne lit que effectiveSecretariatId (string), pas secretariatId
    // directement : c'est lui qui figure dans les deps (LOT 6, cf. §10.2).
  }, [formationId, effectiveSecretariatId])

  const initSeuilsDefaut = async () => {
    setInitSeuilsLoading(true)
    try {
      const params = new URLSearchParams()
      if (formationId) params.set('formation_id', formationId)
      if (effectiveSecretariatId) params.set('secretariat_id', effectiveSecretariatId)
      await api.post(`/statistiques/alertes/seuils/?${params}`)
      await fetchSeuils()
      fetchData()
    } catch (e) {
      alert(e.response?.data?.detail || 'Erreur lors de l\'initialisation des seuils.')
    } finally {
      setInitSeuilsLoading(false)
    }
  }

  const fetchPointJournalier = useCallback(async () => {
    setLoadingPj(true)
    setPjDetail(null)
    setPjAllTableaux([])
    setPjError(null)
    try {
      const params = new URLSearchParams({ annee: String(pjAnnee), tous_tableaux: '1' })
      if (pjMois) params.set('mois', pjMois)
      if (pjCategorie) params.set('categorie', pjCategorie)
      if (pjFormationId) params.set('formation_id', pjFormationId)
      if (effectiveSecretariatId) params.set('secretariat_id', effectiveSecretariatId)
      const res = await api.get(`/statistiques/point-journalier/?${params}`)
      setPjData(res.data)
      setPjAllTableaux(res.data.tableaux_complets || [])
      setPjSelection(prev => {
        if (!res.data.tableaux?.length) return null
        if (prev !== null && prev < res.data.tableaux.length) return prev
        return null
      })
    } catch (e) {
      setPjData(null)
      setPjAllTableaux([])
      setPjSelection(null)
      setPjDetail(null)
      setPjError(e.response?.data?.detail || e.message || 'Erreur de chargement.')
    } finally {
      setLoadingPj(false)
    }
    // Le callback ne lit que effectiveSecretariatId (string), pas secretariatId
    // directement : c'est lui qui figure dans les deps (LOT 6, cf. §10.2).
  }, [pjAnnee, pjMois, pjCategorie, pjFormationId, effectiveSecretariatId])

  const fetchPjDetail = useCallback(async (tb) => {
    if (!tb) {
      setPjDetail(null)
      return
    }
    setLoadingPjDetail(true)
    try {
      const params = new URLSearchParams({
        annee: String(pjAnnee),
        detail: '1',
        jour: tb.date,
        formation_id: String(tb.formation_id),
        categorie: tb.categorie || '—',
      })
      if (tb.grade) params.set('grade', tb.grade)
      if (effectiveSecretariatId) params.set('secretariat_id', effectiveSecretariatId)
      const res = await api.get(`/statistiques/point-journalier/?${params}`)
      setPjDetail(res.data.tableau)
    } catch {
      setPjDetail(null)
    } finally {
      setLoadingPjDetail(false)
    }
    // Le callback ne lit que effectiveSecretariatId (string), pas secretariatId
    // directement : c'est lui qui figure dans les deps (LOT 6, cf. §10.2).
  }, [pjAnnee, effectiveSecretariatId])

  const downloadPointJournalier = async (format) => {
    setExportingPj(format)
    try {
      const params = new URLSearchParams({ export: format, annee: String(pjAnnee) })
      if (pjMois) params.set('mois', pjMois)
      if (pjCategorie) params.set('categorie', pjCategorie)
      if (pjFormationId) params.set('formation_id', pjFormationId)
      if (effectiveSecretariatId) params.set('secretariat_id', effectiveSecretariatId)
      if (pjSelection !== null && pjData?.tableaux?.[pjSelection]) {
        const tb = pjData.tableaux[pjSelection]
        params.set('jour', tb.date)
        params.set('formation_id', String(tb.formation_id))
        if (tb.categorie) params.set('categorie', tb.categorie)
        if (tb.grade) params.set('grade', tb.grade)
      }
      const { blob, fileName } = await api.getBlob(`/statistiques/point-journalier-export/?${params}`)
      const ext = format === 'pdf' ? 'pdf' : format === 'docx' ? 'docx' : 'xlsx'
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const moisPart = pjMois ? `_M${pjMois}` : '_annuel'
      a.download = fileName || `POINT_JOURNALIER_${pjAnnee}${moisPart}.${ext}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      const detail = e.response?.data?.detail
      alert(detail || e.message || 'Erreur lors du téléchargement.')
    } finally {
      setExportingPj(null)
    }
  }

  const fetchBilans = useCallback(async () => {
    setLoadingRb(true)
    setRbDetail(null)
    setRbAllTableaux([])
    try {
      const effFormation = rbFormationId || formationId
      const params = new URLSearchParams({
        annee: String(rbAnnee),
        dimension: rbDimension,
        tous_tableaux: '1',
      })
      if (rbMois) params.set('mois', rbMois)
      if (rbCategorie) params.set('categorie', rbCategorie)
      if (rbDimension === 'matiere') {
        const mk = rbParseMatiereKey(rbMatiereKey)
        if (mk.ref_module_id) params.set('ref_module_id', String(mk.ref_module_id))
      } else if (rbModuleId) {
        params.set('module_id', rbModuleId)
      }
      if (effFormation) params.set('formation_id', effFormation)
      if (effectiveSecretariatId) params.set('secretariat_id', effectiveSecretariatId)
      if (rbPeriode) params.set('periode', rbPeriode)
      if (rbCalendrier) params.set('calendrier', rbCalendrier)
      const res = await api.get(`/statistiques/bilans/?${params}`)
      setRbData(res.data)
      setRbAllTableaux(res.data.tableaux_complets || [])
      setRbSelection(prev => {
        if (!res.data.bilans?.length) return null
        if (prev !== null && prev < res.data.bilans.length) return prev
        return null
      })
    } catch {
      setRbData(null)
      setRbAllTableaux([])
      setRbSelection(null)
    } finally {
      setLoadingRb(false)
    }
    // Le callback ne lit que effectiveSecretariatId (string), pas secretariatId
    // directement : c'est lui qui figure dans les deps (LOT 6, cf. §10.2).
  }, [rbAnnee, rbMois, rbCategorie, rbModuleId, rbMatiereKey, rbFormationId, rbPeriode, rbCalendrier, rbDimension, formationId, effectiveSecretariatId])

  const fetchFacPerimetre = useCallback(async () => {
    const effFormation = facFormationId || formationId
    if (!effFormation) {
      setFacPerimetre({ grades: [], groupes: [] })
      setFacGradesSelected([])
      setFacGroupesSelected([])
      return
    }
    setLoadingFacPerimetre(true)
    try {
      const params = new URLSearchParams({ formation_id: effFormation })
      if (facCategorie) params.set('categorie', facCategorie)
      if (effectiveSecretariatId) params.set('secretariat_id', effectiveSecretariatId)
      const res = await api.get(`/statistiques/bilan-fac/perimetre/?${params}`)
      const grades = res.data?.grades || []
      const groupes = res.data?.groupes || []
      setFacPerimetre({ grades, groupes })
      setFacGradesSelected(grades)
      setFacGroupesSelected(groupes.map(g => g.id))
    } catch {
      setFacPerimetre({ grades: [], groupes: [] })
      setFacGradesSelected([])
      setFacGroupesSelected([])
    } finally {
      setLoadingFacPerimetre(false)
    }
  }, [facFormationId, facCategorie, formationId, effectiveSecretariatId])

  useEffect(() => {
    if (!showFacPanel) return
    fetchFacPerimetre()
  }, [showFacPanel, fetchFacPerimetre])

  const facGroupesVisibles = (facPerimetre.groupes || []).filter(
    g => facGradesSelected.includes(g.grade),
  )

  useEffect(() => {
    const visibleIds = new Set(facGroupesVisibles.map(g => g.id))
    setFacGroupesSelected(prev => prev.filter(id => visibleIds.has(id)))
  // eslint-disable-next-line react-hooks/exhaustive-deps -- rechargement intentionnel : la fonction de chargement n’est pas mémoïsée (l’ajouter provoquerait une boucle) ; les dépendances de données présentes pilotent déjà le (re)chargement.
  }, [facGradesSelected.join(','), facPerimetre.groupes.length])

  const fetchBilanFac = useCallback(async () => {
    const effFormation = facFormationId || formationId
    if (!effFormation) return
    if (!facGradesSelected.length) return
    setLoadingFac(true)
    try {
      const params = new URLSearchParams({ formation_id: effFormation, annee: String(facAnnee) })
      if (facCategorie) params.set('categorie', facCategorie)
      if (effectiveSecretariatId) params.set('secretariat_id', effectiveSecretariatId)
      const allGrades = facPerimetre.grades || []
      const allGroupeIds = facGroupesVisibles.map(g => g.id)
      if (facGradesSelected.length < allGrades.length) {
        params.set('grades', facGradesSelected.join(','))
      }
      if (
        allGroupeIds.length > 0
        && facGroupesSelected.length < allGroupeIds.length
      ) {
        params.set('groupes', facGroupesSelected.join(','))
      }
      const res = await api.get(`/statistiques/bilan-fac/?${params}`)
      setFacData(res.data)
    } catch {
      setFacData(null)
    } finally {
      setLoadingFac(false)
    }
  }, [
    facFormationId, facAnnee, facCategorie, formationId, effectiveSecretariatId,
    facGradesSelected, facGroupesSelected, facPerimetre.grades, facGroupesVisibles,
  ])

  const fetchRbDetail = useCallback(async (bilan) => {
    if (!bilan) {
      setRbDetail(null)
      return
    }
    if (bilan.dimension === 'module' && !bilan.module_id) {
      setRbDetail(null)
      return
    }
    if (bilan.dimension === 'formation' && !bilan.formation_id) {
      setRbDetail(null)
      return
    }
    if (bilan.dimension === 'categorie' && (!bilan.categorie || bilan.categorie === '—')) {
      setRbDetail(null)
      return
    }
    if (bilan.dimension === 'matiere' && !bilan.formation_id) {
      setRbDetail(null)
      return
    }
    if (!['module', 'matiere', 'formation', 'categorie'].includes(bilan.dimension)) {
      setRbDetail(null)
      return
    }
    setLoadingRbDetail(true)
    try {
      const effFormation = rbFormationId || formationId
      const params = new URLSearchParams({
        annee: String(rbAnnee),
        detail: '1',
        dimension: bilan.dimension,
      })
      if (bilan.module_id) params.set('module_id', String(bilan.module_id))
      if (bilan.formation_id) params.set('formation_id', String(bilan.formation_id))
      else if (effFormation) params.set('formation_id', effFormation)
      if (bilan.dimension === 'matiere') {
        if (bilan.ref_module_id) params.set('ref_module_id', String(bilan.ref_module_id))
        if (bilan.matiere_intitule) params.set('matiere_intitule', bilan.matiere_intitule)
      }
      if (rbMois) params.set('mois', rbMois)
      const cat = (bilan.categorie && bilan.categorie !== '—') ? bilan.categorie : rbCategorie
      if (cat) params.set('categorie', cat)
      if (effectiveSecretariatId) params.set('secretariat_id', effectiveSecretariatId)
      if (rbPeriode) params.set('periode', rbPeriode)
      if (rbCalendrier) params.set('calendrier', rbCalendrier)
      const res = await api.get(`/statistiques/bilans/?${params}`)
      setRbDetail(res.data.tableau)
    } catch {
      setRbDetail(null)
    } finally {
      setLoadingRbDetail(false)
    }
    // Le callback ne lit que effectiveSecretariatId (string), pas secretariatId
    // directement : c'est lui qui figure dans les deps (LOT 6, cf. §10.2).
  }, [rbAnnee, rbMois, rbCategorie, rbFormationId, rbPeriode, rbCalendrier, formationId, effectiveSecretariatId])

  const downloadBilanExport = async (format) => {
    setExportingRb(format)
    try {
      const effFormation = rbFormationId || formationId
      const params = new URLSearchParams({ export: format, annee: String(rbAnnee), dimension: rbDimension })
      if (rbMois) params.set('mois', rbMois)
      if (rbCategorie) params.set('categorie', rbCategorie)
      if (rbDimension === 'matiere') {
        const mk = rbParseMatiereKey(rbMatiereKey)
        if (mk.ref_module_id) params.set('ref_module_id', String(mk.ref_module_id))
      } else if (rbModuleId) {
        params.set('module_id', rbModuleId)
      }
      if (effFormation) params.set('formation_id', effFormation)
      if (effectiveSecretariatId) params.set('secretariat_id', effectiveSecretariatId)
      if (rbPeriode) params.set('periode', rbPeriode)
      if (rbCalendrier) params.set('calendrier', rbCalendrier)
      const bilan = rbSelection !== null && rbData?.bilans?.[rbSelection] ? rbData.bilans[rbSelection] : null
      if (bilan?.module_id) params.set('module_id', String(bilan.module_id))
      if (bilan?.formation_id) params.set('formation_id', String(bilan.formation_id))
      if (bilan?.ref_module_id) params.set('ref_module_id', String(bilan.ref_module_id))
      if (bilan?.matiere_intitule) params.set('matiere_intitule', bilan.matiere_intitule)
      if (bilan?.categorie && bilan.categorie !== '—') params.set('categorie', bilan.categorie)
      if (rbJustificatifsText.trim()) params.set('justificatifs', rbJustificatifsText.trim())
      const { blob, fileName } = await api.getBlob(`/statistiques/bilans-export/?${params}`)
      const ext = format === 'pdf' ? 'pdf' : format === 'docx' ? 'docx' : 'xlsx'
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = fileName || `BILANS_${rbAnnee}.${ext}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      const detail = e.response?.data?.detail
      alert(detail || e.message || 'Erreur lors du téléchargement.')
    } finally {
      setExportingRb(null)
    }
  }

  const downloadBilanFac = async (format) => {
    const effFormation = facFormationId || formationId
    if (!effFormation || !facData) return
    setExportingFac(format)
    try {
      const params = new URLSearchParams({
        export: format,
        formation_id: effFormation,
        annee: String(facAnnee),
      })
      if (facCategorie) params.set('categorie', facCategorie)
      if (effectiveSecretariatId) params.set('secretariat_id', effectiveSecretariatId)
      const allGrades = facPerimetre.grades || []
      const allGroupeIds = facGroupesVisibles.map(g => g.id)
      if (facGradesSelected.length < allGrades.length) {
        params.set('grades', facGradesSelected.join(','))
      }
      if (allGroupeIds.length > 0 && facGroupesSelected.length < allGroupeIds.length) {
        params.set('groupes', facGroupesSelected.join(','))
      }
      const { justificatifs, difficultes } = facExportMeta
      if (
        Object.keys(justificatifs || {}).length
        || Object.keys(difficultes || {}).length
      ) {
        params.set('meta', JSON.stringify({ justificatifs, difficultes }))
      }
      const { blob, fileName } = await api.getBlob(`/statistiques/bilan-fac-export/?${params}`)
      const ext = format === 'pdf' ? 'pdf' : format === 'docx' ? 'docx' : 'xlsx'
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = fileName || `BILAN_FAC_${facAnnee}.${ext}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      const detail = e.response?.data?.detail
      alert(detail || e.message || 'Erreur lors du téléchargement.')
    } finally {
      setExportingFac(null)
    }
  }

  const handleApplyVhPeriod = useCallback((periodOverride) => {
    const p = periodOverride ?? vhPeriod
    saveFinancePeriod(p)
    setVhPeriod(p)
    setAppliedVhPeriod({ ...p })
    fetchSeqRef.current += 1
    setData(prev => (prev ? {
      ...prev,
      kpis: undefined,
      periode: undefined,
      pedagogiques: undefined,
      admin_operationnel: undefined,
      alertes: undefined,
      alertes_overview: undefined,
    } : prev))
  }, [vhPeriod])

  const handleRefreshAll = () => {
    fetchData(TAB_SECTIONS[onglet] || TAB_SECTIONS.overview)
    if (onglet === 'point_journalier') fetchPointJournalier()
    if (onglet === 'rapports') fetchBilans()
    if (onglet === 'secretariats') fetchSecStats()
    if (onglet === 'alertes') fetchSeuils()
  }

  useEffect(() => {
    const prev = prevLoadCtx.current
    const ongletChanged = prev.onglet !== onglet
    const filtreChanged = prev.formationId !== formationId
      || prev.secretariatId !== secretariatId
      || prev.appliedPeriodKey !== appliedPeriodKey
    prevLoadCtx.current = { onglet, formationId, secretariatId, appliedPeriodKey }

    if (filtreChanged && hasDataRef.current) {
      fetchSeqRef.current += 1
      setData(d => (d ? {
        ...d,
        kpis: undefined,
        periode: undefined,
        pedagogiques: undefined,
        admin_operationnel: undefined,
        alertes: undefined,
        alertes_overview: undefined,
      } : d))
    }

    const sections = TAB_SECTIONS[onglet] || TAB_SECTIONS.overview
    const isFirst = !hasDataRef.current
    fetchData(sections, {
      initial: isFirst,
      silent: !isFirst && ongletChanged && !filtreChanged,
    })
  }, [formationId, secretariatId, onglet, appliedPeriodKey, fetchData])

  useEffect(() => {
    setHistSelection(null)
    setPedSelection(null)
    setOverviewSelection(null)
    setAlertesSelection(null)
  }, [formationId, secretariatId])

  useEffect(() => {
    if (onglet === 'alertes') fetchSeuils()
    if (onglet === 'secretariats') fetchSecStats()
  }, [onglet, appliedPeriodKey, formationId, secretariatId, fetchSeuils, fetchSecStats])

  useEffect(() => {
    if (onglet !== 'secretariats' || secSelection === null || !secStats?.secretariats?.length) return
    fetchSecDetail(secStats.secretariats[secSelection].secretariat_id)
  }, [onglet, secSelection, secStats, fetchSecDetail])

  useEffect(() => {
    if (onglet !== 'secretariats' || !secretariatId || !secStats?.secretariats?.length) return
    const idx = secStats.secretariats.findIndex(s => String(s.secretariat_id) === String(secretariatId))
    if (idx >= 0) setSecSelection(idx)
  }, [onglet, secretariatId, secStats])

  useEffect(() => {
    if (data?.filtre_actif?.scope_locked && data.filtre_actif.secretariat_id) {
      setSecretariatId(String(data.filtre_actif.secretariat_id))
    }
  }, [data?.filtre_actif?.scope_locked, data?.filtre_actif?.secretariat_id])

  useEffect(() => {
    if (onglet !== 'point_journalier') return
    fetchPointJournalier()
  }, [onglet, pjAnnee, pjMois, pjCategorie, pjFormationId, secretariatId, fetchPointJournalier])

  useEffect(() => {
    setRbJustificatifsText('')
  }, [rbSelection, rbAnnee, rbMois, rbFormationId, rbPeriode, rbCalendrier, rbDimension])

  useEffect(() => {
    if (onglet !== 'rapports') return
    fetchBilans()
  }, [onglet, rbAnnee, rbMois, rbCategorie, rbModuleId, rbMatiereKey, rbFormationId, rbPeriode, rbCalendrier, rbDimension, formationId, secretariatId, fetchBilans])

  useEffect(() => {
    if (onglet !== 'rapports' || rbSelection === null || !rbData?.bilans?.length) return
    const bilan = rbData.bilans[rbSelection]
    const cached = rbAllTableaux.find(t => t.bilan_id === bilan.id)
    if (cached?.tableau) {
      setRbDetail(cached.tableau)
      return
    }
    fetchRbDetail(bilan)
  }, [onglet, rbSelection, rbData, rbAllTableaux, fetchRbDetail])

  useEffect(() => {
    if (onglet !== 'point_journalier' || pjSelection === null || !pjData?.tableaux?.length) return
    const meta = pjData.tableaux[pjSelection]
    const cached = pjAllTableaux.find(t => t.tableau_id === meta.id)
    if (cached?.tableau) {
      setPjDetail(cached.tableau)
      return
    }
    fetchPjDetail(meta)
  }, [onglet, pjSelection, pjData, pjAllTableaux, fetchPjDetail])

  const saveSeuils = async () => {
    try {
      const params = new URLSearchParams()
      if (formationId) params.set('formation_id', formationId)
      if (effectiveSecretariatId) params.set('secretariat_id', effectiveSecretariatId)
      await api.put(`/statistiques/alertes/seuils/?${params}`, seuilsForm)
      setEditSeuils(false)
      await fetchSeuils()
      fetchData()
    } catch(e) {
      alert(e.response?.data?.detail || 'Erreur lors de la sauvegarde.')
    }
  }

  // ── Onglets nav ──────────────────────────────────────────────────────────
  const onglets = [
    {id:'overview',      icon:'bi-speedometer2',       label:'Vue d\'ensemble'},
    {id:'pedagogy',      icon:'bi-mortarboard',         label:'Pédagogique'},
    {id:'admin',         icon:'bi-people',               label:'Administratif'},
    {id:'history',       icon:'bi-graph-up',             label:'Historique'},
    {id:'secretariats',  icon:'bi-building',             label:'Secrétariats'},
    {id:'rapports',      icon:'bi-file-earmark-text',    label:'Rapports & Bilans'},
    {id:'point_journalier', icon:'bi-calendar2-check',   label:'Point Journalier'},
    {id:'alertes',       icon:'bi-bell',                 label:'Alertes'},
  ]
  const visibleOnglets = isSecretariatScoped
    ? onglets.filter(o => SECRETARIAT_STATS_TABS.has(o.id))
    : onglets

  if (loadingInitial && !data) return (
    <div style={{display:'flex',alignItems:'center',justifyContent:'center',minHeight:300,gap:'0.75rem',color:'#64748b'}}>
      <div className="spinner"/><span>Chargement des statistiques…</span>
    </div>
  )
  if (error && !data) return (
    <div style={{background:'#fff3f3',border:'1px solid #fca5a5',borderRadius:10,padding:'1.5rem',color:'#C62828',maxWidth:500}}>
      <i className="bi bi-exclamation-triangle me-2"/>{error}
      <br/><button className="btn btn-sm btn-outline-danger" style={{marginTop:'0.75rem'}} onClick={() => fetchData(TAB_SECTIONS[onglet] || TAB_SECTIONS.overview, { initial: true })}>Réessayer</button>
    </div>
  )

  const { kpis, pedagogiques, admin_operationnel: adm, historique, alertes, alertes_overview, formations_liste, secretariats_liste } = data || {}
  const secretariatScopeLabel = (secretariats_liste || []).find(
    s => String(s.id) === String(effectiveSecretariatId),
  )?.nom || user?.secretariat_nom || 'Mon secrétariat'
  const auditeursNotoires = adm?.auditeurs_notoires
    || pedagogiques?.auditeurs_notoires
    || secDetail?.admin_operationnel?.auditeurs_notoires
    || secStats?.auditeurs_notoires
    || null

  const tabLoading = loadingTab && (
    <div style={{display:'flex',alignItems:'center',gap:'0.4rem',fontSize:'0.78rem',color:'#64748b',marginBottom:'0.65rem'}}>
      <div className="spinner" style={{width:14,height:14}}/>Actualisation…
    </div>
  )

  const TabSpinner = ({ label = 'Chargement…' }) => (
    <div style={{display:'flex',alignItems:'center',gap:'0.5rem',color:'#64748b',padding:'2rem',background:'#fff',borderRadius:10,boxShadow:'0 1px 4px rgba(0,0,0,0.07)'}}>
      <div className="spinner"/>{label}
    </div>
  )

  return (
    <div>
      <AlertesStyles />
      {/* ── En-tête ─────────────────────────────────────── */}
      <div style={{display:'flex',alignItems:'flex-start',justifyContent:'space-between',marginBottom:'1.2rem',flexWrap:'wrap',gap:'0.75rem'}}>
        <div>
          <h2 style={{margin:0,fontWeight:800,color:'#1e293b',fontSize:'1.3rem'}}>
            <i className="bi bi-bar-chart-line me-2" style={{color:'var(--navy)'}}/>
            Statistiques & Bilans
          </h2>
          {lastRefresh && (
            <p style={{margin:0,fontSize:'0.73rem',color:'#94a3b8',marginTop:'0.1rem'}}>
              Mis à jour le {lastRefresh.toLocaleString('fr-FR')}
            </p>
          )}
        </div>
        <div style={{display:'flex',gap:'0.5rem',alignItems:'center',flexWrap:'wrap'}}>
          <select
            className="form-select form-select-sm"
            value={formationId}
            onChange={e => { setFormationId(e.target.value) }}
            style={{minWidth:180,maxWidth:240}}
          >
            <option value="">Toutes les formations</option>
            {(formations_liste||[]).map(f => (
              <option key={f.id} value={f.id}>{f.formation}</option>
            ))}
          </select>
          {!secretariatFilterLocked && (
            <select
              className="form-select form-select-sm"
              value={secretariatId}
              onChange={e => { setSecretariatId(e.target.value) }}
              style={{minWidth:170,maxWidth:220}}
              disabled={isEncadrantScoped && (secretariats_liste || []).length <= 1}
            >
              <option value="">Tous les secrétariats</option>
              {(secretariats_liste||[]).map(s => (
                <option key={s.id} value={s.id}>{s.nom}</option>
              ))}
            </select>
          )}
          {secretariatFilterLocked && (secretariats_liste||[]).length > 0 && (
            <span className="badge bg-light text-dark border" style={{fontSize:'0.78rem',padding:'0.45rem 0.65rem'}}>
              <i className="bi bi-building me-1"/>
              {(secretariats_liste||[])[0]?.nom || user?.secretariat_nom || 'Mon secrétariat'}
            </span>
          )}
          {(formationId || (!secretariatFilterLocked && secretariatId)) && (
            <button
              className="btn btn-sm btn-outline-danger"
              onClick={() => {
                setFormationId('')
                if (!secretariatFilterLocked) setSecretariatId('')
              }}
              title="Effacer les filtres"
            >
              <i className="bi bi-x-lg"/>
            </button>
          )}
          <button className="btn btn-sm btn-outline-secondary" onClick={handleRefreshAll} disabled={loadingInitial || loadingTab}>
            <i className="bi bi-arrow-clockwise me-1"/>Actualiser
          </button>
        </div>
      </div>

      {VH_PERIOD_TABS.has(onglet) && (
      <div className="finance-filter-panel" style={{ marginBottom: '1rem' }}>
        <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#64748b', marginBottom: '0.5rem', letterSpacing: '0.04em' }}>
          PÉRIODE — INDICATEURS CLÉS
        </div>
        <div className="finance-filter-panel-inner">
          <FinancePeriodFilter
            period={vhPeriod}
            onChange={setVhPeriod}
            onApply={handleApplyVhPeriod}
            applying={loadingInitial || loadingTab || loadingSecStats}
            embedded
            autoApplyOnSelect
          />
        </div>
        {isPeriodWhollyFuture(appliedVhPeriod) && (
          <div style={{
            marginTop: '0.65rem', padding: '0.55rem 0.75rem', borderRadius: 8,
            background: '#fffceb', border: '1px solid #fcdf4d', color: '#92660e', fontSize: '0.82rem',
          }}>
            <i className="bi bi-info-circle me-1"/>
            Cette période n&apos;a pas encore commencé — indicateurs clés et séances comptabilisables à 0
            (volume horaire et présences inclus).
            {(() => {
              const { annee, q } = currentTrimestreParts()
              return (
                <button
                  type="button"
                  className="btn btn-link btn-sm p-0 ms-1 align-baseline"
                  style={{ fontSize: '0.82rem', verticalAlign: 'baseline' }}
                  onClick={() => {
                    const next = {
                      ...appliedVhPeriod,
                      preset: 'trimestre',
                      trimestreAnnee: annee,
                      trimestreQ: q,
                      trimestre: `${annee}-Q${q}`,
                    }
                    setVhPeriod(next)
                    saveFinancePeriod(next)
                    setAppliedVhPeriod({ ...next })
                  }}
                >
                  Voir le trimestre en cours (T{q})
                </button>
              )
            })()}
          </div>
        )}
        {!isPeriodWhollyFuture(appliedVhPeriod)
          && data?.periode?.filtre_actif
          && data?.kpis?.sessions_terminees === 0
          && appliedVhPeriod?.preset !== 'tout' && (
          <div style={{
            marginTop: '0.65rem', padding: '0.55rem 0.75rem', borderRadius: 8,
            background: '#f8fafc', border: '1px solid #e2e8f0', color: '#64748b', fontSize: '0.82rem',
          }}>
            <i className="bi bi-calendar-x me-1"/>
            Aucune séance comptabilisable sur {data.periode.label || 'cette période'}
            {data.periode.periode_label ? ` (${data.periode.periode_label})` : ''}.
          </div>
        )}
        {data?.periode?.label && (
          <div className="finance-period-badge">
            <i className="bi bi-calendar-check"></i>
            <div>
              <strong>{data.periode.label}</strong>
              {data.periode.periode_label && (
                <span className="ms-1">— {data.periode.periode_label}</span>
              )}
            </div>
          </div>
        )}
      </div>
      )}

      {error && data && (
        <div style={{background:'#fff3f3',border:'1px solid #fca5a5',borderRadius:8,padding:'0.65rem 0.85rem',color:'#C62828',fontSize:'0.82rem',marginBottom:'0.75rem'}}>
          <i className="bi bi-exclamation-triangle me-1"/>{error}
        </div>
      )}

      {tabLoading}

      {/* ── Navigation onglets ─────────────────────────── */}
      <div style={{display:'flex',gap:'0.25rem',marginBottom:'1.2rem',borderBottom:'2px solid #e2e8f0',overflowX:'auto',paddingBottom:0}}>
        {visibleOnglets.map(o => (
          <button key={o.id} onClick={() => setOnglet(o.id)} style={{
            background:'none',border:'none',cursor:'pointer',padding:'0.55rem 0.9rem',
            fontSize:'0.82rem',fontWeight:onglet===o.id?700:500,
            color:onglet===o.id?'#001a33':'#64748b',
            borderBottom:onglet===o.id?'2px solid #001a33':'2px solid transparent',
            marginBottom:'-2px',whiteSpace:'nowrap',display:'flex',alignItems:'center',gap:'0.3rem',
          }}>
            <i className={`bi ${o.icon}`}/>{o.label}
          </button>
        ))}
      </div>

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* Onglet 1 — Vue d'ensemble                                            */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {onglet==='overview' && (() => {
        const overviewSections = buildOverviewSections(alertes_overview || alertes)
        const overviewSection = overviewSelection
          ? overviewSections.find(s => s.id === overviewSelection)
          : null
        return (
        <>
          <div style={{display:'flex',flexWrap:'wrap',gap:'0.5rem',alignItems:'center',marginBottom:'0.75rem'}}>
            <span style={{fontSize:'0.78rem',color:'#64748b'}}>
              Tableau de bord synthétique
              {formationId && <> · <b>{(formations_liste||[]).find(f => String(f.id) === formationId)?.formation}</b></>}
              {secretariatId && <> · <b>{(secretariats_liste||[]).find(s => String(s.id) === secretariatId)?.nom}</b></>}
            </span>
            <div style={{marginLeft:'auto'}}>
              <button className="btn btn-sm btn-outline-secondary" onClick={() => fetchData(TAB_SECTIONS.overview)} disabled={loadingTab}>
                <i className="bi bi-arrow-clockwise me-1"/>Actualiser
              </button>
            </div>
          </div>

          {loadingInitial && !data ? <TabSpinner label="Chargement de la vue d'ensemble…"/> : (
          <div style={{display:'grid',gridTemplateColumns:'minmax(200px,260px) 1fr',gap:'1rem',alignItems:'start',marginBottom:'1.2rem'}}>
            <div style={{background:'#fff',borderRadius:10,boxShadow:'0 1px 4px rgba(0,0,0,0.07)',overflow:'hidden',maxHeight:'70vh',overflowY:'auto'}}>
              <div style={{padding:'0.65rem 0.85rem',background:'#f8fafc',borderBottom:'1px solid #e2e8f0',fontSize:'0.78rem',color:'#64748b',fontWeight:600}}>
                {overviewSections.length} section{overviewSections.length > 1 ? 's' : ''}
              </div>
              <button
                type="button"
                onClick={()=>setOverviewSelection(null)}
                style={{
                  display:'block', width:'100%', textAlign:'left', border:'none', cursor:'pointer',
                  padding:'0.55rem 0.85rem', fontSize:'0.78rem', fontWeight:700,
                  background: overviewSelection === null ? '#e0f2fe' : '#fff',
                  borderBottom:'2px solid #e2e8f0', color: overviewSelection === null ? '#0369a1' : '#475569',
                }}
              >
                <i className="bi bi-grid-3x3-gap me-1"/>
                Tous les indicateurs
              </button>
              {overviewSections.map(section => (
                <button
                  key={section.id}
                  type="button"
                  onClick={()=>setOverviewSelection(section.id)}
                  style={{
                    display:'block', width:'100%', textAlign:'left', border:'none', cursor:'pointer',
                    padding:'0.55rem 0.85rem', fontSize:'0.78rem',
                    background: overviewSelection===section.id ? '#e8eef6' : '#fff',
                    borderBottom:'1px solid #f1f5f9',
                  }}
                >
                  <div style={{fontWeight:700, color:'#1e293b', marginBottom:'0.1rem'}}>
                    <i className={`bi ${section.icon} me-1`} style={{color:section.tagColor}}/>
                    <span style={{
                      background:`${section.tagColor}18`, color:section.tagColor, borderRadius:4,
                      padding:'0.05rem 0.35rem', marginRight:'0.3rem', fontSize:'0.68rem',
                    }}>{section.tag}</span>
                    {section.label}
                  </div>
                  <div style={{color:'#94a3b8', fontSize:'0.72rem'}}>{section.sub}</div>
                </button>
              ))}
            </div>

            {overviewSelection === null ? (
              !kpis ? (
                <TabSpinner label="Mise à jour des indicateurs pour la période sélectionnée…"/>
              ) : (
              <VueEnsemblePanel
                key={appliedPeriodKey}
                kpis={kpis}
                periode={data?.periode}
                loading={loadingTab}
                pedagogiques={pedagogiques}
                adm={adm}
                alertesOverview={alertes_overview || alertes}
                onSelectSection={setOverviewSelection}
                auditeursNotoires={auditeursNotoires}
              />
              )
            ) : overviewSection ? (
              !kpis ? (
                <TabSpinner label="Mise à jour des indicateurs pour la période sélectionnée…"/>
              ) : (
              <div style={{ minWidth: 0 }}>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-secondary mb-2"
                  onClick={()=>setOverviewSelection(null)}
                >
                  <i className="bi bi-grid-3x3-gap me-1"/>Voir tous les indicateurs
                </button>
                <VueOverviewDetailPanel
                  key={appliedPeriodKey}
                  sectionId={overviewSection.id}
                  kpis={kpis}
                  periode={data?.periode}
                  pedagogiques={pedagogiques}
                  adm={adm}
                  alertesOverview={alertes_overview || alertes}
                  onGoAlertes={() => setOnglet('alertes')}
                  onGoPedagogie={() => setOnglet('pedagogy')}
                  onGoAdmin={() => setOnglet('admin')}
                  auditeursNotoires={auditeursNotoires}
                />
              </div>
              )
            ) : (
              <Empty label="Section introuvable"/>
            )}
          </div>
          )}
        </>
        )
      })()}

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* Onglet 2 — Pédagogique                                               */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {onglet==='pedagogy' && (() => {
        const pedEntries = buildPedagogieEntries(pedagogiques)
        const pedEntry = pedSelection ? pedEntries.find(e => e.id === pedSelection) : null
        return (
        <>
          <div style={{display:'flex',flexWrap:'wrap',gap:'0.5rem',alignItems:'center',marginBottom:'0.75rem'}}>
            <span style={{fontSize:'0.78rem',color:'#64748b'}}>
              Indicateurs pédagogiques (assiduité séance, couverture étudiants, absences, événements)
              {formationId && <> · <b>{(formations_liste||[]).find(f => String(f.id) === formationId)?.formation}</b></>}
              {secretariatId && <> · <b>{(secretariats_liste||[]).find(s => String(s.id) === secretariatId)?.nom}</b></>}
            </span>
            <div style={{marginLeft:'auto'}}>
              <button className="btn btn-sm btn-outline-secondary" onClick={() => fetchData(TAB_SECTIONS.pedagogy)} disabled={loadingTab}>
                <i className="bi bi-arrow-clockwise me-1"/>Actualiser
              </button>
            </div>
          </div>

          {!pedagogiques ? <TabSpinner label="Chargement des indicateurs pédagogiques…"/> : (
          <div style={{display:'grid',gridTemplateColumns:'minmax(220px,280px) 1fr',gap:'1rem',alignItems:'start',marginBottom:'1.2rem'}}>
            <div style={{background:'#fff',borderRadius:10,boxShadow:'0 1px 4px rgba(0,0,0,0.07)',overflow:'hidden',maxHeight:'70vh',overflowY:'auto'}}>
              <div style={{padding:'0.65rem 0.85rem',background:'#f8fafc',borderBottom:'1px solid #e2e8f0',fontSize:'0.78rem',color:'#64748b',fontWeight:600}}>
                {pedEntries.length} périmètre{pedEntries.length > 1 ? 's' : ''}
              </div>
              <button
                type="button"
                onClick={()=>setPedSelection(null)}
                style={{
                  display:'block', width:'100%', textAlign:'left', border:'none', cursor:'pointer',
                  padding:'0.55rem 0.85rem', fontSize:'0.78rem', fontWeight:700,
                  background: pedSelection === null ? '#e0f2fe' : '#fff',
                  borderBottom:'2px solid #e2e8f0', color: pedSelection === null ? '#0369a1' : '#475569',
                }}
              >
                <i className="bi bi-grid-3x3-gap me-1"/>
                Tous les indicateurs
              </button>
              {pedEntries.length > 0 && (
                <>
                  {['formation', 'grade', 'secretariat'].map(dim => {
                    const group = pedEntries.filter(e => e.type === dim)
                    if (!group.length) return null
                    const dimLabel = dim === 'formation' ? 'Formations' : dim === 'grade' ? 'Grades' : 'Secrétariats'
                    return (
                      <div key={dim}>
                        <div style={{padding:'0.4rem 0.85rem',fontSize:'0.68rem',fontWeight:700,color:'#94a3b8',background:'#fafbfc',borderBottom:'1px solid #f1f5f9'}}>
                          {dimLabel}
                        </div>
                        {group.map(entry => (
                          <button
                            key={entry.id}
                            type="button"
                            onClick={()=>setPedSelection(entry.id)}
                            style={{
                              display:'block', width:'100%', textAlign:'left', border:'none', cursor:'pointer',
                              padding:'0.55rem 0.85rem', fontSize:'0.78rem',
                              background: pedSelection===entry.id ? '#e8eef6' : '#fff',
                              borderBottom:'1px solid #f1f5f9',
                            }}
                          >
                            <div style={{fontWeight:700, color:'#1e293b', marginBottom:'0.1rem'}}>
                              <span style={{
                                background:`${entry.tagColor}18`, color:entry.tagColor, borderRadius:4,
                                padding:'0.05rem 0.35rem', marginRight:'0.3rem', fontSize:'0.68rem',
                              }}>{entry.tag}</span>
                              <span style={{overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',display:'inline-block',maxWidth:'calc(100% - 2.5rem)',verticalAlign:'bottom'}}>
                                {entry.label}
                              </span>
                            </div>
                            <div style={{color:'#94a3b8', fontSize:'0.72rem'}}>{entry.sub}</div>
                          </button>
                        ))}
                      </div>
                    )
                  })}
                </>
              )}
            </div>

            {pedSelection === null ? (
              <PedagogiqueEnsemblePanel
                pedagogiques={pedagogiques}
                pedEntries={pedEntries}
                onSelect={setPedSelection}
                auditeursNotoires={auditeursNotoires}
              />
            ) : pedEntry ? (
              <div style={{ minWidth: 0 }}>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-secondary mb-2"
                  onClick={()=>setPedSelection(null)}
                >
                  <i className="bi bi-grid-3x3-gap me-1"/>Voir tous les indicateurs
                </button>
                <PedagogiqueDetailPanel
                  entry={pedEntry}
                  pedagogiques={pedagogiques}
                  auditeursNotoires={auditeursNotoires}
                  onGoSecretariat={(id) => {
                    setSecretariatId(String(id))
                    setOnglet('secretariats')
                  }}
                />
              </div>
            ) : (
              <Empty label="Périmètre introuvable"/>
            )}
          </div>
          )}
        </>
        )
      })()}

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* Onglet 3 — Administratif & Opérationnel                              */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {onglet==='admin' && (
        !adm ? <TabSpinner label="Chargement des indicateurs administratifs…"/> : (
        <>
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(165px,1fr))',gap:'0.8rem',marginBottom:'1.1rem'}}>
            <Kpi icon="bi-diagram-3"    label="Groupes actifs"       value={adm.nb_groupes}            color="#1565C0"/>
            <Kpi icon="bi-person-badge" label="Encadrants"           value={adm.nb_encadrants}          color="#7B1FA2"/>
            <Kpi icon="bi-x-square"     label="Séances annulées"     value={adm.nb_seances_annulees}    color="#C62828"/>
            <Kpi icon="bi-calendar-check" label={KPI_SESSIONS_COMPT.label} value={adm.nb_seances_terminees} color="#082961"
              help={KPI_SESSIONS_COMPT.help}/>
            <Kpi icon="bi-person-x-fill" label={AUDITEURS_NOTOIRES.label}
              value={auditeursNotoires?.total ?? adm.nb_absences_notoires ?? 0} color="#C62828"
              sub={auditeursNotoires ? `${Number(auditeursNotoires.pct || 0).toFixed(1).replace('.', ',')}% des inscrits` : undefined}
              help={AUDITEURS_NOTOIRES.help}/>
            <Kpi icon="bi-people-fill"  label="Moy. étudiants/groupe" value={adm.moy_auditeurs_groupe}  color="#00838F"/>
            <Kpi icon="bi-percent"      label="% Hommes"             value={`${adm.ratio_hf?.pct_hommes??0}%`} color="#1565C0"/>
            <Kpi icon="bi-percent"      label="% Femmes"             value={`${adm.ratio_hf?.pct_femmes??0}%`} color="#AD1457"/>
          </div>

          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(320px,1fr))',gap:'1rem'}}>
            <Card title="Répartition Hommes / Femmes" icon="bi-gender-ambiguous">
              <Donut data={adm.participants_par_sexe} labelKey="sexe" valueKey="total"/>
            </Card>

            <Card title="Étudiants par catégorie" icon="bi-bar-chart-steps">
              <HBars data={(adm.participants_par_categorie||[]).map(d=>({...d,categorie:d.categorie||'Non rens.'}))}
                labelKey="categorie" valueKey="total"/>
            </Card>

            <Card title="Étudiants par grade" icon="bi-award">
              <Bars data={(adm.participants_par_grade||[]).map(d=>({...d,grade:d.grade||'—'}))}
                labelKey="grade" valueKey="total" color="#7B1FA2"/>
            </Card>

            <Card title="Étudiants par vague" icon="bi-layers">
              <Bars data={(adm.participants_par_vague||[]).map(d=>({...d,vague:d.vague||'—'}))}
                labelKey="vague" valueKey="total" color="#F5B100"/>
            </Card>

            <Card title="Charge des enseignants" icon="bi-person-video3" col="1/-1">
              <HBars data={adm.charge_enseignants} labelKey="nom" valueKey="nb_sessions"/>
            </Card>
          </div>

          <div style={{ marginTop: '1rem' }}>
            <Card title={AUDITEURS_NOTOIRES.cardTitle} icon="bi-person-x-fill" col="1/-1">
              <AuditeursNotoiresPanel data={auditeursNotoires} maxHeight={420}/>
            </Card>
          </div>
        </>
        )
      )}

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* Onglet 4 — Historique                                                */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {onglet==='history' && (
        <>
          <div style={{display:'flex',flexWrap:'wrap',gap:'0.5rem',alignItems:'center',marginBottom:'0.75rem'}}>
            <span style={{fontSize:'0.78rem',color:'#64748b'}}>
              Période : <b>12 derniers mois</b>
              {formationId && <> · Formation : <b>{(formations_liste||[]).find(f => String(f.id) === formationId)?.formation}</b></>}
              {secretariatId && <> · Secrétariat : <b>{(secretariats_liste||[]).find(s => String(s.id) === secretariatId)?.nom}</b></>}
            </span>
            <div style={{marginLeft:'auto'}}>
              <button className="btn btn-sm btn-outline-secondary" onClick={() => fetchData(TAB_SECTIONS.history)} disabled={loadingTab}>
                <i className="bi bi-arrow-clockwise me-1"/>Actualiser
              </button>
            </div>
          </div>

          {!historique ? <TabSpinner label="Chargement de l'historique…"/> : !historique.pointages_par_mois?.length ? (
            <div style={{background:'#fff',borderRadius:10,padding:'2rem',textAlign:'center',boxShadow:'0 1px 4px rgba(0,0,0,0.07)'}}>
              <Empty label="Aucune donnée historique pour cette sélection"/>
              <p style={{margin:'0.75rem 0 0',fontSize:'0.78rem',color:'#64748b'}}>
                Vérifiez les filtres formation / secrétariat ou l&apos;activité des séances et pointages.
              </p>
            </div>
          ) : (
            <div style={{display:'grid',gridTemplateColumns:'minmax(200px,260px) 1fr',gap:'1rem',alignItems:'start',marginBottom:'1.2rem'}}>
              <div style={{background:'#fff',borderRadius:10,boxShadow:'0 1px 4px rgba(0,0,0,0.07)',overflow:'hidden',maxHeight:'70vh',overflowY:'auto'}}>
                <div style={{padding:'0.65rem 0.85rem',background:'#f8fafc',borderBottom:'1px solid #e2e8f0',fontSize:'0.78rem',color:'#64748b',fontWeight:600}}>
                  {historique.pointages_par_mois.length} mois
                </div>
                <button
                  type="button"
                  onClick={()=>setHistSelection(null)}
                  style={{
                    display:'block', width:'100%', textAlign:'left', border:'none', cursor:'pointer',
                    padding:'0.55rem 0.85rem', fontSize:'0.78rem', fontWeight:700,
                    background: histSelection === null ? '#e0f2fe' : '#fff',
                    borderBottom:'2px solid #e2e8f0', color: histSelection === null ? '#0369a1' : '#475569',
                  }}
                >
                  <i className="bi bi-grid-3x3-gap me-1"/>
                  Tous les mois (12)
                </button>
                {[...historique.pointages_par_mois].reverse().map((pt) => {
                  const i = historique.pointages_par_mois.findIndex(m => m.mois === pt.mois)
                  const taux = historique.taux_presence_par_mois[i]
                  const hasData = (pt.total || 0) > 0 || (pt.presents || 0) + (pt.absents || 0) > 0
                  return (
                    <button
                      key={pt.mois}
                      type="button"
                      onClick={()=>setHistSelection(i)}
                      style={{
                        display:'block', width:'100%', textAlign:'left', border:'none', cursor:'pointer',
                        padding:'0.55rem 0.85rem', fontSize:'0.78rem',
                        background: histSelection===i ? '#e8eef6' : '#fff',
                        borderBottom:'1px solid #f1f5f9',
                        opacity: hasData ? 1 : 0.65,
                      }}
                    >
                      <div style={{fontWeight:700, color:'#1e293b', marginBottom:'0.1rem'}}>
                        <i className="bi bi-calendar3 me-1" style={{color:'#1565C0'}}/>
                        {formatMoisLabelLong(pt.mois)}
                      </div>
                      <div style={{color:'#94a3b8', fontSize:'0.72rem'}}>
                        {pt.total} ptg. · {Number(taux?.total || 0).toFixed(1)}% prés.
                        {!hasData ? ' · sans données' : ''}
                      </div>
                    </button>
                  )
                })}
              </div>

              {histSelection === null ? (
                <HistoriqueEnsemblePanel historique={historique} onSelectMois={setHistSelection} auditeursNotoires={auditeursNotoires} />
              ) : (
                <div style={{ minWidth: 0 }}>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-secondary mb-2"
                    onClick={()=>setHistSelection(null)}
                  >
                    <i className="bi bi-grid-3x3-gap me-1"/>Voir tous les mois
                  </button>
                  <HistoriqueMoisPanel historique={historique} monthIndex={histSelection} auditeursNotoires={auditeursNotoires} />
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* Onglet 5 — Secrétariats                                              */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {onglet==='secretariats' && (
        <>
          <div style={{display:'flex',flexWrap:'wrap',gap:'0.5rem',alignItems:'center',marginBottom:'0.75rem'}}>
            <span style={{fontSize:'0.78rem',color:'#64748b'}}>
              {formationId
                ? <>Filtre formation : <b>{(formations_liste||[]).find(f => String(f.id) === formationId)?.formation || formationId}</b></>
                : 'Toutes les formations'}
            </span>
            <div style={{marginLeft:'auto'}}>
              <button className="btn btn-sm btn-outline-secondary" onClick={fetchSecStats} disabled={loadingSecStats}>
                <i className="bi bi-arrow-clockwise me-1"/>Actualiser
              </button>
            </div>
          </div>

          {loadingSecStats ? (
            <div style={{display:'flex',alignItems:'center',gap:'0.5rem',color:'#64748b',padding:'2rem',marginBottom:'1rem'}}>
              <div className="spinner"/>Chargement de tous les secrétariats…
            </div>
          ) : !secStats?.secretariats?.length ? (
            <div style={{marginBottom:'1.2rem'}}>
              <Empty label="Aucun secrétariat trouvé"/>
            </div>
          ) : (
            <div style={{display:'grid',gridTemplateColumns:'minmax(220px,280px) 1fr',gap:'1rem',alignItems:'start',marginBottom:'1.2rem'}}>
              <div style={{background:'#fff',borderRadius:10,boxShadow:'0 1px 4px rgba(0,0,0,0.07)',overflow:'hidden',maxHeight:'70vh',overflowY:'auto'}}>
                <div style={{padding:'0.65rem 0.85rem',background:'#f8fafc',borderBottom:'1px solid #e2e8f0',fontSize:'0.78rem',color:'#64748b',fontWeight:600}}>
                  {secStats.total} secrétariat{secStats.total > 1 ? 's' : ''}
                </div>
                <button
                  type="button"
                  onClick={()=>{ setSecSelection(null); setSecDetail(null); setSecretariatId('') }}
                  style={{
                    display:'block', width:'100%', textAlign:'left', border:'none', cursor:'pointer',
                    padding:'0.55rem 0.85rem', fontSize:'0.78rem', fontWeight:700,
                    background: secSelection === null ? '#e0f2fe' : '#fff',
                    borderBottom:'2px solid #e2e8f0', color: secSelection === null ? '#0369a1' : '#475569',
                  }}
                >
                  <i className="bi bi-grid-3x3-gap me-1"/>
                  Tous les secrétariats ({secStats.total})
                </button>
                {secStats.secretariats.map((s,i)=>(
                  <button
                    key={s.secretariat_id}
                    type="button"
                    onClick={()=>setSecSelection(i)}
                    style={{
                      display:'block', width:'100%', textAlign:'left', border:'none', cursor:'pointer',
                      padding:'0.55rem 0.85rem', fontSize:'0.78rem',
                      background: secSelection===i ? '#e8eef6' : '#fff',
                      borderBottom:'1px solid #f1f5f9',
                    }}
                  >
                    <div style={{fontWeight:700, color:'#1e293b', marginBottom:'0.1rem'}}>
                      <i className="bi bi-building me-1" style={{color:C[i%C.length]}}/>
                      {s.secretariat}
                    </div>
                    <div style={{color:'#64748b', fontSize:'0.72rem'}}>
                      {s.nb_modules} mod. · {s.nb_inscrits} inscrits · {Number(s.taux_presence).toFixed(1)}% prés.
                      {(s.nb_auditeurs_notoires ?? 0) > 0 && (
                        <> · <span style={{ color: '#C62828' }}>{s.nb_auditeurs_notoires} not.</span></>
                      )}
                    </div>
                  </button>
                ))}
              </div>

              {secSelection === null ? (
                <SecretariatsEnsemblePanel secStats={secStats} onSelectIndividuel={setSecSelection} />
              ) : (
                loadingSecDetail ? (
                  <div style={{display:'flex',alignItems:'center',gap:'0.5rem',color:'#64748b',padding:'2rem',background:'#fff',borderRadius:10,boxShadow:'0 1px 4px rgba(0,0,0,0.07)'}}>
                    <div className="spinner"/>Chargement du détail…
                  </div>
                ) : secDetail ? (
                  <div style={{ minWidth: 0 }}>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-secondary mb-2"
                      onClick={()=>{ setSecSelection(null); setSecDetail(null); setSecretariatId('') }}
                    >
                      <i className="bi bi-grid-3x3-gap me-1"/>Voir tous les secrétariats
                    </button>
                    <SecretariatDetailPanel
                      row={secStats.secretariats[secSelection]}
                      detail={secDetail}
                    />
                  </div>
                ) : (
                  <Empty label="Impossible de charger le détail de ce secrétariat"/>
                )
              )}
            </div>
          )}
        </>
      )}

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* Onglet 6 — Rapports & Bilans                                         */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {onglet==='rapports' && (
        <>
        {secretariatFilterLocked && (
          <div style={{
            marginBottom: '0.75rem', padding: '0.55rem 0.85rem', borderRadius: 8,
            background: '#e8eef6', border: '1px solid #c5d0e0', color: '#0a2a4d', fontSize: '0.82rem',
          }}>
            <i className="bi bi-building me-1"/>
            Périmètre limité à votre secrétariat : <strong>{secretariatScopeLabel}</strong>
          </div>
        )}

        <div style={{ display: 'flex', gap: '0.35rem', marginBottom: '0.85rem', flexWrap: 'wrap' }}>
          {RB_VIEWS.map(v => (
            <button
              key={v.id}
              type="button"
              onClick={() => setRbViewAndUrl(v.id)}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: '0.35rem',
                padding: '0.45rem 0.85rem', borderRadius: 8, cursor: 'pointer', fontSize: '0.82rem', fontWeight: 600,
                border: rbView === v.id ? '2px solid #001a33' : '1px solid #e2e8f0',
                background: rbView === v.id ? '#e8eef6' : '#fff',
                color: rbView === v.id ? '#001a33' : '#64748b',
              }}
            >
              <i className={`bi ${v.icon}`}/>{v.label}
            </button>
          ))}
        </div>

        {rbView === 'workflow' && (
          <RapportsWorkflowPanel
            user={user}
            formationId={formationId}
            secretariatId={effectiveSecretariatId}
            appliedVhPeriod={appliedVhPeriod}
          />
        )}

        {rbView === 'bilans' && (
        <>
        {/* ── Filtres bilans (même entête que Point Journalier) ─────────── */}
        <div style={{display:'flex',flexWrap:'wrap',gap:'0.5rem',alignItems:'center',marginBottom:'0.75rem'}}>
          <select className="form-select form-select-sm" style={{width:100}}
            value={rbAnnee} onChange={e=>{ setRbAnnee(Number(e.target.value)); setRbSelection(null) }}>
            {[rbAnnee-1, rbAnnee, rbAnnee+1].filter((y,i,a)=>a.indexOf(y)===i).sort().map(y=>(
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
          <select className="form-select form-select-sm" style={{width:130}}
            value={rbMois} onChange={e=>{ setRbMois(e.target.value); setRbSelection(null) }}>
            <option value="">Toute l'année</option>
            {['Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'].map((m,i)=>(
              <option key={i+1} value={String(i+1)}>{m}</option>
            ))}
          </select>
          <select className="form-select form-select-sm" style={{width:120}}
            value={rbCategorie} onChange={e=>{ setRbCategorie(e.target.value); setRbSelection(null) }}>
            <option value="">Toutes catég.</option>
            {(rbData?.categories||[]).map(c=>(
              <option key={c} value={c}>Cat. {c}</option>
            ))}
          </select>
          {rbDimension === 'matiere' ? (
            <select className="form-select form-select-sm" style={{minWidth:160,maxWidth:220}}
              value={rbMatiereKey} onChange={e=>{ setRbMatiereKey(e.target.value); setRbSelection(null) }}>
              <option value="">Toutes matières</option>
              {(rbData?.matieres||[])
                .filter(m => !rbFormationId || String(m.formation_id) === rbFormationId)
                .map(m => (
                  <option key={rbMatiereOptionValue(m)} value={rbMatiereOptionValue(m)}>
                    {m.intitule}
                  </option>
                ))}
            </select>
          ) : (
            <select className="form-select form-select-sm" style={{minWidth:160,maxWidth:220}}
              value={rbModuleId} onChange={e=>{ setRbModuleId(e.target.value); setRbSelection(null) }}>
              <option value="">Tous modules</option>
              {(rbData?.modules||[]).map(m=>(
                <option key={m.id} value={m.id}>{m.intitule}</option>
              ))}
            </select>
          )}
          <select className="form-select form-select-sm" style={{minWidth:180,maxWidth:260}}
            value={rbFormationId} onChange={e=>{ setRbFormationId(e.target.value); setRbModuleId(''); setRbMatiereKey(''); setRbSelection(null) }}>
            <option value="">Toutes formations</option>
            {(rbData?.formations||formations_liste||[]).map(f=>(
              <option key={f.id} value={f.id}>{f.formation}</option>
            ))}
          </select>
          <select className="form-select form-select-sm" style={{minWidth:150,maxWidth:180}}
            value={rbPeriode} onChange={e=>{ setRbPeriode(e.target.value); setRbSelection(null) }}>
            {RB_PERIODES.map(p=>(
              <option key={p.value||'all'} value={p.value}>{p.label}</option>
            ))}
          </select>
          <div style={{display:'flex',flexDirection:'column',gap:'0.1rem'}}>
            <span style={{fontSize:'0.65rem',color:'#94a3b8',lineHeight:1}}>Calendrier prév.</span>
            <input
              type="date"
              className="form-control form-control-sm"
              style={{width:155}}
              title="Calendrier prévisionnel"
              value={rbCalendrier}
              onChange={e=>{ setRbCalendrier(e.target.value); setRbSelection(null) }}
            />
          </div>
          <div style={{marginLeft:'auto', display:'flex', gap:'0.4rem', alignItems:'center', flexWrap:'nowrap'}}>
            <button className="btn btn-sm btn-outline-secondary" onClick={fetchBilans} disabled={loadingRb}>
              <i className="bi bi-arrow-clockwise me-1"/>Actualiser
            </button>
            {PJ_EXPORT_FORMATS.map(({ fmt, icon, label, col }) => (
              <button
                key={`rb-${fmt}`}
                className="btn btn-sm"
                disabled={!!exportingRb || loadingRb || !rbData?.bilans?.length}
                style={{ background: col, color: '#fff', border: 'none', minWidth: 88, opacity: (exportingRb || loadingRb) ? 0.65 : 1 }}
                onClick={() => downloadBilanExport(fmt)}
                title={`Exporter les bilans filtrés (${label})`}
              >
                {exportingRb === fmt ? (
                  <span className="spinner-border spinner-border-sm"/>
                ) : (
                  <><i className={`bi ${icon} me-1`}/>{label}</>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Type de bilan : Module · Catégorie · Formation */}
        <div style={{display:'flex',gap:'0.35rem',marginBottom:'0.85rem',flexWrap:'wrap'}}>
          {RB_DIMENSIONS.map(d=>(
            <button
              key={d.id}
              type="button"
              onClick={()=>{
                setRbDimension(d.id)
                setRbModuleId('')
                setRbMatiereKey('')
                setRbSelection(null)
              }}
              style={{
                display:'inline-flex', alignItems:'center', gap:'0.35rem',
                padding:'0.45rem 0.85rem', borderRadius:8, cursor:'pointer', fontSize:'0.82rem', fontWeight:600,
                border: rbDimension===d.id ? '2px solid #001a33' : '1px solid #e2e8f0',
                background: rbDimension===d.id ? '#e8eef6' : '#fff',
                color: rbDimension===d.id ? '#001a33' : '#64748b',
              }}
            >
              <i className={`bi ${d.icon}`}/>{d.label}
            </button>
          ))}
        </div>

        <AuditeursNotoiresKpiStrip data={auditeursNotoires}/>

        {/* Liste bilans + détail */}
        {loadingRb ? (
          <div style={{display:'flex',alignItems:'center',gap:'0.5rem',color:'#64748b',padding:'2rem',marginBottom:'1rem'}}>
            <div className="spinner"/>Chargement des bilans…
          </div>
        ) : !rbData?.bilans?.length ? (
          <div style={{marginBottom:'1.2rem'}}>
            <Empty label="Aucun bilan pour cette sélection"/>
          </div>
        ) : (
          <div style={{display:'grid',gridTemplateColumns:'minmax(220px,280px) 1fr',gap:'1rem',alignItems:'start',marginBottom:'1.2rem'}}>
            <div style={{background:'#fff',borderRadius:10,boxShadow:'0 1px 4px rgba(0,0,0,0.07)',overflow:'hidden',maxHeight:'55vh',overflowY:'auto'}}>
              <div style={{padding:'0.65rem 0.85rem',background:'#f8fafc',borderBottom:'1px solid #e2e8f0',fontSize:'0.78rem',color:'#64748b',fontWeight:600}}>
                {rbData.total_bilans} bilan{rbData.total_bilans > 1 ? 's' : ''} · {RB_DIMENSIONS.find(d=>d.id===rbDimension)?.label}
              </div>
              <button
                type="button"
                onClick={()=>{ setRbSelection(null); setRbDetail(null) }}
                style={{
                  display:'block', width:'100%', textAlign:'left', border:'none', cursor:'pointer',
                  padding:'0.55rem 0.85rem', fontSize:'0.78rem', fontWeight:700,
                  background: rbSelection === null ? '#e0f2fe' : '#fff',
                  borderBottom:'2px solid #e2e8f0', color: rbSelection === null ? '#0369a1' : '#475569',
                }}
              >
                <i className="bi bi-grid-3x3-gap me-1"/>
                Tous les tableaux ({rbAllTableaux.length || rbData.total_bilans})
              </button>
              {rbData.bilans.map((b,i)=>(
                <button
                  key={b.id}
                  type="button"
                  onClick={()=>setRbSelection(i)}
                  style={{
                    display:'block', width:'100%', textAlign:'left', border:'none', cursor:'pointer',
                    padding:'0.55rem 0.85rem', fontSize:'0.78rem',
                    background: rbSelection===i ? '#e8eef6' : '#fff',
                    borderBottom:'1px solid #f1f5f9',
                  }}
                >
                  <div style={{fontWeight:700, color:'#1e293b', marginBottom:'0.1rem'}}>
                    {b.dimension==='categorie' && (
                      <span style={{background:'#1565C018',color:'#1565C0',borderRadius:4,padding:'0.05rem 0.35rem',marginRight:'0.3rem',fontSize:'0.72rem'}}>
                        CAT {b.categorie}
                      </span>
                    )}
                    {b.dimension==='module' && (
                      <span style={{background:'#7B1FA218',color:'#7B1FA2',borderRadius:4,padding:'0.05rem 0.35rem',marginRight:'0.3rem',fontSize:'0.72rem'}}>
                        MOD
                      </span>
                    )}
                    {b.dimension==='matiere' && (
                      <span style={{background:'#0C3E9518',color:'#0C3E95',borderRadius:4,padding:'0.05rem 0.35rem',marginRight:'0.3rem',fontSize:'0.72rem'}}>
                        MAT
                      </span>
                    )}
                    {b.libelle}
                  </div>
                  <div style={{color:'#64748b', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>
                    {b.sous_titre}
                  </div>
                  {b.dimension === 'module' && (b.grade || b.groupe) && (
                    <div style={{color:'#94a3b8', fontSize:'0.7rem', marginTop:'0.05rem'}}>
                      {b.grade ? `Grade ${b.grade}` : ''}{b.grade && b.groupe ? ' · ' : ''}{b.groupe || ''}
                    </div>
                  )}
                  {b.inscrits != null && (
                    <div style={{color:'#94a3b8', fontSize:'0.72rem', marginTop:'0.1rem'}}>
                      {b.inscrits} inscrit{b.inscrits > 1 ? 's' : ''}
                      {b.nb_groupes != null ? ` · ${b.nb_groupes} groupe${b.nb_groupes > 1 ? 's' : ''}` : ''}
                      {b.nb_pointages != null ? ` · ${b.nb_pointages} pointages` : ''}
                    </div>
                  )}
                </button>
              ))}
            </div>
            {rbSelection === null ? (
              loadingRb && !rbAllTableaux.length ? (
                <TabSpinner label="Chargement de tous les tableaux…"/>
              ) : (
              <BilansEnsemblePanel
                items={rbAllTableaux}
                bilans={rbData.bilans}
                filtres={rbData.filtres_actifs}
                dimension={rbDimension}
                onSelectIndividuel={setRbSelection}
              />
              )
            ) : rbData.bilans[rbSelection] && (
              loadingRbDetail ? (
                <div style={{display:'flex',alignItems:'center',gap:'0.5rem',color:'#64748b',padding:'2rem',background:'#fff',borderRadius:10,boxShadow:'0 1px 4px rgba(0,0,0,0.07)'}}>
                  <div className="spinner"/>Chargement du tableau…
                </div>
              ) : (
                <div style={{ minWidth: 0 }}>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-secondary mb-2"
                    onClick={()=>{ setRbSelection(null); setRbDetail(null) }}
                  >
                    <i className="bi bi-grid-3x3-gap me-1"/>Voir tous les tableaux
                  </button>
                  <BilanDetailPanel
                    bilan={rbData.bilans[rbSelection]}
                    tableau={rbDetail}
                    filtres={rbData.filtres_actifs}
                    justificatifsText={rbJustificatifsText}
                    onJustificatifsChange={setRbJustificatifsText}
                  />
                </div>
              )
            )}
          </div>
        )}

        {/* ── Bilan FAC ─────────────────────────────────────────────────────── */}
        <div style={{marginTop:'1.5rem'}}>
          <button
            type="button"
            onClick={()=>setShowFacPanel(v=>!v)}
            style={{
              display:'flex', alignItems:'center', gap:'0.5rem', width:'100%',
              background: showFacPanel
                ? 'linear-gradient(135deg,#fffbf0 0%,#fef7e2 100%)'
                : 'linear-gradient(135deg,#f8fafc 0%,#f1f5f9 100%)',
              border: showFacPanel ? '2px solid #EDB131' : '1px solid #e2e8f0',
              borderRadius:10, padding:'0.75rem 1rem', cursor:'pointer',
              boxShadow:'0 1px 4px rgba(0,0,0,0.06)',
            }}
          >
            <span style={{
              background:'#EDB131', color:'#fff', borderRadius:6,
              padding:'0.2rem 0.55rem', fontSize:'0.72rem', fontWeight:800, letterSpacing:1,
            }}>BILAN</span>
            <span style={{fontWeight:700, fontSize:'0.9rem', color:'#1e293b'}}>
              Bilan formation
            </span>
            <span style={{marginLeft:'auto', color:'#94a3b8', fontSize:'0.78rem'}}>
              Point global · VH par groupe · Absents notoires
            </span>
            <i className={`bi bi-chevron-${showFacPanel ? 'up' : 'down'}`} style={{color:'#EDB131', fontSize:'0.85rem'}}/>
          </button>

          {showFacPanel && (
            <div style={{
              background:'#fff', border:'1px solid #fee8aa',
              borderTop:'none', borderRadius:'0 0 10px 10px',
              boxShadow:'0 4px 12px rgba(237,177,49,0.08)', padding:'1rem',
            }}>
              {/* Filtres Bilan FAC */}
              <div style={{display:'flex',flexWrap:'wrap',gap:'0.5rem',alignItems:'flex-end',marginBottom:'1rem'}}>
                <div style={{display:'flex',flexDirection:'column',gap:'0.15rem'}}>
                  <span style={{fontSize:'0.65rem',color:'#94a3b8'}}>Formation</span>
                  <select
                    className="form-select form-select-sm"
                    style={{minWidth:200,maxWidth:300}}
                    value={facFormationId}
                    onChange={e=>{ setFacFormationId(e.target.value); setFacData(null) }}
                  >
                    <option value="">— Sélectionner —</option>
                    {(rbData?.formations || formations_liste || []).map(f=>(
                      <option key={f.id} value={f.id}>{f.formation}</option>
                    ))}
                  </select>
                </div>
                <div style={{display:'flex',flexDirection:'column',gap:'0.15rem'}}>
                  <span style={{fontSize:'0.65rem',color:'#94a3b8'}}>Année</span>
                  <select
                    className="form-select form-select-sm"
                    style={{width:100}}
                    value={facAnnee}
                    onChange={e=>{ setFacAnnee(Number(e.target.value)); setFacData(null) }}
                  >
                    {[facAnnee-1, facAnnee, facAnnee+1].map(y=>(
                      <option key={y} value={y}>{y}</option>
                    ))}
                  </select>
                </div>
                <div style={{display:'flex',flexDirection:'column',gap:'0.15rem'}}>
                  <span style={{fontSize:'0.65rem',color:'#94a3b8'}}>Catégorie</span>
                  <select
                    className="form-select form-select-sm"
                    style={{width:110}}
                    value={facCategorie}
                    onChange={e=>{ setFacCategorie(e.target.value); setFacData(null) }}
                  >
                    <option value="">Toutes</option>
                    {['A','B','C','D'].map(c=>(
                      <option key={c} value={c}>Cat. {c}</option>
                    ))}
                  </select>
                </div>
                <button
                  className="btn btn-sm"
                  style={{background:'#EDB131',color:'#fff',border:'none',minWidth:110}}
                  onClick={fetchBilanFac}
                  disabled={loadingFac || (!facFormationId && !formationId) || !facGradesSelected.length}
                >
                  {loadingFac
                    ? <><span className="spinner-border spinner-border-sm me-1"/>Chargement…</>
                    : <><i className="bi bi-file-earmark-bar-graph me-1"/>Générer le bilan</>
                  }
                </button>
              </div>

              {/* Grades & groupes */}
              {(facFormationId || formationId) && (
                <div style={{
                  marginBottom: '1rem', padding: '0.75rem', borderRadius: 8,
                  background: '#fffceb', border: '1px solid #fdec8a',
                }}>
                  <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.55rem',
                  }}>
                    <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#92660e' }}>
                      <i className="bi bi-ui-checks me-1"/>
                      Périmètre — grades et groupes
                    </span>
                    {loadingFacPerimetre && (
                      <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                        <span className="spinner-border spinner-border-sm me-1"/>Chargement…
                      </span>
                    )}
                    {!loadingFacPerimetre && facPerimetre.grades.length > 0 && (
                      <span style={{ display: 'flex', gap: '0.35rem' }}>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-secondary"
                          style={{ fontSize: '0.68rem', padding: '0.15rem 0.45rem' }}
                          onClick={() => {
                            setFacGradesSelected([...facPerimetre.grades])
                            setFacGroupesSelected(facPerimetre.groupes.map(g => g.id))
                          }}
                        >
                          Tout cocher
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-secondary"
                          style={{ fontSize: '0.68rem', padding: '0.15rem 0.45rem' }}
                          onClick={() => {
                            setFacGradesSelected([])
                            setFacGroupesSelected([])
                            setFacData(null)
                          }}
                        >
                          Tout décocher
                        </button>
                      </span>
                    )}
                  </div>

                  {!loadingFacPerimetre && !facPerimetre.grades.length && (
                    <p style={{ margin: 0, fontSize: '0.78rem', color: '#94a3b8' }}>
                      Aucun grade/groupe pour cette formation et ces filtres.
                    </p>
                  )}

                  {!loadingFacPerimetre && facPerimetre.grades.length > 0 && (
                    <>
                      <div style={{ marginBottom: '0.55rem' }}>
                        <div style={{ fontSize: '0.68rem', fontWeight: 700, color: '#64748b', marginBottom: '0.3rem' }}>
                          GRADES
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem' }}>
                          {facPerimetre.grades.map(grade => (
                            <label
                              key={grade}
                              style={{
                                display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
                                fontSize: '0.78rem', fontWeight: 600, cursor: 'pointer',
                                background: facGradesSelected.includes(grade) ? '#fef6c7' : '#f8fafc',
                                border: `1px solid ${facGradesSelected.includes(grade) ? '#f5c10b' : '#e2e8f0'}`,
                                borderRadius: 6, padding: '0.25rem 0.55rem',
                              }}
                            >
                              <input
                                type="checkbox"
                                checked={facGradesSelected.includes(grade)}
                                onChange={e => {
                                  setFacData(null)
                                  setFacGradesSelected(prev => (
                                    e.target.checked
                                      ? [...prev, grade]
                                      : prev.filter(g => g !== grade)
                                  ))
                                }}
                              />
                              {grade}
                            </label>
                          ))}
                        </div>
                      </div>

                      {facGroupesVisibles.length > 0 && (
                        <div>
                          <div style={{ fontSize: '0.68rem', fontWeight: 700, color: '#64748b', marginBottom: '0.3rem' }}>
                            GROUPES
                          </div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', maxHeight: 140, overflowY: 'auto' }}>
                            {facGroupesVisibles.map(g => (
                              <label
                                key={g.id}
                                style={{
                                  display: 'inline-flex', alignItems: 'center', gap: '0.25rem',
                                  fontSize: '0.72rem', cursor: 'pointer',
                                  background: facGroupesSelected.includes(g.id) ? '#ecf3fd' : '#f8fafc',
                                  border: `1px solid ${facGroupesSelected.includes(g.id) ? '#80b7f5' : '#e2e8f0'}`,
                                  borderRadius: 6, padding: '0.2rem 0.45rem',
                                }}
                              >
                                <input
                                  type="checkbox"
                                  checked={facGroupesSelected.includes(g.id)}
                                  onChange={e => {
                                    setFacData(null)
                                    setFacGroupesSelected(prev => (
                                      e.target.checked
                                        ? [...prev, g.id]
                                        : prev.filter(id => id !== g.id)
                                    ))
                                  }}
                                />
                                <span style={{ color: '#64748b' }}>{g.grade}</span>
                                <span style={{ fontWeight: 600 }}>{g.groupe}</span>
                              </label>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* Contenu Bilan FAC */}
              {!facData && !loadingFac && (
                <div style={{
                  textAlign:'center', padding:'2.5rem 1rem', color:'#94a3b8',
                  fontSize:'0.85rem', borderTop:'1px solid #f1f5f9',
                }}>
                  <i className="bi bi-file-earmark-bar-graph" style={{fontSize:'2.5rem',display:'block',marginBottom:'0.5rem',color:'#EDB13166'}}/>
                  Sélectionnez une formation et cliquez sur &quot;Générer le bilan&quot;
                </div>
              )}

              {facData && (
                <BilanFACPanel
                  data={facData}
                  sousOnglet={facSousOnglet}
                  onChangeSousOnglet={setFacSousOnglet}
                  onMetaChange={setFacExportMeta}
                  onExport={downloadBilanFac}
                  exportingFac={exportingFac}
                />
              )}
            </div>
          )}
        </div>

        </>
        )}

        </>
      )}

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* Onglet — Point Journalier par catégorie et formation                 */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {onglet==='point_journalier' && (
        <div>
          {secretariatFilterLocked && (
            <div style={{
              marginBottom: '0.75rem', padding: '0.55rem 0.85rem', borderRadius: 8,
              background: '#e8eef6', border: '1px solid #c5d0e0', color: '#0a2a4d', fontSize: '0.82rem',
            }}>
              <i className="bi bi-building me-1"/>
              Périmètre limité à votre secrétariat : <strong>{secretariatScopeLabel}</strong>
            </div>
          )}
          {/* Filtres + Actualiser + exports (même ligne) */}
          <div style={{display:'flex',flexWrap:'wrap',gap:'0.5rem',alignItems:'center',marginBottom:'0.75rem'}}>
            <select className="form-select form-select-sm" style={{width:100}}
              value={pjAnnee} onChange={e=>{ setPjAnnee(Number(e.target.value)); setPjSelection(null) }}>
              {[pjAnnee-1, pjAnnee, pjAnnee+1].filter((y,i,a)=>a.indexOf(y)===i).sort().map(y=>(
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <select className="form-select form-select-sm" style={{width:130}}
              value={pjMois} onChange={e=>{ setPjMois(e.target.value); setPjSelection(null) }}>
              <option value="">Toute l'année</option>
              {['Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'].map((m,i)=>(
                <option key={i+1} value={String(i+1)}>{m}</option>
              ))}
            </select>
            <select className="form-select form-select-sm" style={{width:110}}
              value={pjCategorie} onChange={e=>{ setPjCategorie(e.target.value); setPjSelection(null) }}>
              <option value="">Toutes catég.</option>
              {(pjData?.categories||[]).map(c=>(
                <option key={c} value={c}>
                  Cat. {c}
                  {pjData?.categories_avec_donnees && !pjData.categories_avec_donnees.includes(c) ? ' (sans données)' : ''}
                </option>
              ))}
            </select>
            <select className="form-select form-select-sm" style={{minWidth:180,maxWidth:260}}
              value={pjFormationId} onChange={e=>{ setPjFormationId(e.target.value); setPjSelection(null) }}>
              <option value="">Toutes formations</option>
              {(pjData?.formations||formations_liste||[]).map(f=>(
                <option key={f.id} value={f.id}>{f.formation}</option>
              ))}
            </select>
            <div style={{marginLeft:'auto', display:'flex', gap:'0.4rem', alignItems:'center', flexWrap:'nowrap'}}>
              <button className="btn btn-sm btn-outline-secondary" onClick={fetchPointJournalier} disabled={loadingPj}>
                <i className="bi bi-arrow-clockwise me-1"/>Actualiser
              </button>
              {PJ_EXPORT_FORMATS.map(({ fmt, icon, label, col }) => (
                <button
                  key={fmt}
                  className="btn btn-sm"
                  disabled={!!exportingPj || loadingPj || !pjData?.tableaux?.length}
                  style={{ background: col, color: '#fff', border: 'none', minWidth: 88, opacity: (exportingPj || loadingPj) ? 0.65 : 1 }}
                  onClick={() => downloadPointJournalier(fmt)}
                  title={`Exporter la sélection filtrée (${label})`}
                >
                  {exportingPj === fmt ? (
                    <span className="spinner-border spinner-border-sm"/>
                  ) : (
                    <><i className={`bi ${icon} me-1`}/>{label}</>
                  )}
                </button>
              ))}
            </div>
          </div>

          <AuditeursNotoiresKpiStrip data={auditeursNotoires}/>

          {loadingPj ? (
            <div style={{display:'flex',alignItems:'center',gap:'0.5rem',color:'#64748b',padding:'2rem'}}>
              <div className="spinner"/>Chargement de tous les tableaux…
            </div>
          ) : !pjData?.tableaux?.length ? (
            <div style={{ background: '#fff', borderRadius: 10, padding: '2rem', textAlign: 'center', boxShadow: '0 1px 4px rgba(0,0,0,0.07)' }}>
              <Empty label="Aucun point journalier pour cette période"/>
              {pjError && (
                <p style={{ margin: '0.75rem 0 0', fontSize: '0.82rem', color: '#C62828' }}>{pjError}</p>
              )}
              <div style={{ margin: '1rem auto 0', maxWidth: 480, fontSize: '0.78rem', color: '#64748b', textAlign: 'left', background: '#f8fafc', borderRadius: 8, padding: '0.75rem 1rem', border: '1px solid #e2e8f0' }}>
                <p style={{ margin: '0 0 0.5rem', fontWeight: 700, color: '#475569' }}>Filtres actifs</p>
                <ul style={{ margin: 0, paddingLeft: '1.1rem', lineHeight: 1.6 }}>
                  <li>Année : <b>{pjAnnee}</b></li>
                  <li>Mois : <b>{pjMois ? ['','Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'][Number(pjMois)] : 'Toute l\'année'}</b></li>
                  <li>Catégorie : <b>{pjCategorie || 'Toutes'}</b></li>
                  <li>Formation : <b>{pjFormationId ? (pjData?.formations?.find(f => String(f.id) === pjFormationId)?.formation || pjFormationId) : 'Toutes'}</b></li>
                  {secretariatId && <li>Secrétariat : filtre global actif</li>}
                </ul>
                {pjData?.mois_avec_donnees?.length > 0 && (
                  <p style={{ margin: '0.65rem 0 0', fontSize: '0.76rem' }}>
                    Mois avec données en {pjAnnee} :{' '}
                    <b>{pjData.mois_avec_donnees.map(m => ['','Jan','Fév','Mar','Avr','Mai','Juin','Juil','Aoû','Sep','Oct','Nov','Déc'][m]).join(', ')}</b>
                  </p>
                )}
                <p style={{ margin: '0.65rem 0 0', fontSize: '0.76rem' }}>
                  Essayez <b>Toute l&apos;année</b>, une autre catégorie, ou vérifiez que des séances et pointages existent pour la période (import Excel / badgeage).
                </p>
              </div>
            </div>
          ) : (
            <div style={{display:'grid',gridTemplateColumns:'minmax(220px,280px) 1fr',gap:'1rem',alignItems:'start'}}>
              {/* Liste des tableaux */}
              <div style={{background:'#fff',borderRadius:10,boxShadow:'0 1px 4px rgba(0,0,0,0.07)',overflow:'hidden',maxHeight:'70vh',overflowY:'auto'}}>
                <div style={{padding:'0.65rem 0.85rem',background:'#f8fafc',borderBottom:'1px solid #e2e8f0',fontSize:'0.78rem',color:'#64748b',fontWeight:600}}>
                  {pjData.total_tableaux} tableau(x) — {pjAnnee}
                </div>
                <button
                  type="button"
                  onClick={()=>{ setPjSelection(null); setPjDetail(null) }}
                  style={{
                    display:'block', width:'100%', textAlign:'left', border:'none', cursor:'pointer',
                    padding:'0.55rem 0.85rem', fontSize:'0.78rem', fontWeight:700,
                    background: pjSelection === null ? '#e0f2fe' : '#fff',
                    borderBottom:'2px solid #e2e8f0', color: pjSelection === null ? '#0369a1' : '#475569',
                  }}
                >
                  <i className="bi bi-grid-3x3-gap me-1"/>
                  Tous les tableaux ({pjAllTableaux.length || pjData.total_tableaux})
                </button>
                {pjData.tableaux.map((tb,i)=>(
                  <button key={tb.id || `${tb.formation_id}-${tb.categorie}-${tb.date}`}
                    onClick={()=>setPjSelection(i)}
                    style={{
                      display:'block',width:'100%',textAlign:'left',border:'none',cursor:'pointer',
                      padding:'0.55rem 0.85rem',fontSize:'0.78rem',
                      background:pjSelection===i?'#e8eef6':'#fff',
                      borderBottom:'1px solid #f1f5f9',
                    }}>
                    <div style={{fontWeight:700,color:'#1e293b',marginBottom:'0.1rem'}}>
                      <span style={{background:'#2277C118',color:'#2277C1',borderRadius:4,padding:'0.05rem 0.35rem',marginRight:'0.3rem',fontSize:'0.72rem'}}>
                        CAT {tb.categorie}
                      </span>
                      {tb.grade && (
                        <span style={{background:'#EDB13118',color:'#EDB131',borderRadius:4,padding:'0.05rem 0.35rem',marginRight:'0.3rem',fontSize:'0.72rem'}}>
                          {tb.grade}
                        </span>
                      )}
                      {tb.date_fr}
                    </div>
                    <div style={{color:'#64748b',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
                      {tb.formation}
                    </div>
                    <div style={{color:'#94a3b8',fontSize:'0.72rem',marginTop:'0.1rem'}}>
                      Prés. jour : {(tb.taux_presence_jour * 100).toFixed(1)}%
                      {' · '}Matin {tb.matin_horaire || tb.matin?.horaire || '—'} / Soir {tb.soir_horaire || tb.soir?.horaire || '—'}
                    </div>
                  </button>
                ))}
              </div>

              {pjSelection === null ? (
                loadingPj && !pjAllTableaux.length ? (
                  <TabSpinner label="Chargement de tous les tableaux…"/>
                ) : (
                <PointJournalierEnsemblePanel
                  items={pjAllTableaux}
                  tableaux={pjData.tableaux}
                  annee={pjAnnee}
                  onSelectIndividuel={setPjSelection}
                />
                )
              ) : (
                loadingPjDetail ? (
                  <div style={{display:'flex',alignItems:'center',gap:'0.5rem',color:'#64748b',padding:'2rem',background:'#fff',borderRadius:10,boxShadow:'0 1px 4px rgba(0,0,0,0.07)'}}>
                    <div className="spinner"/>Chargement du tableau…
                  </div>
                ) : pjDetail ? (
                  <div style={{ minWidth: 0 }}>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-secondary mb-2"
                      onClick={()=>{ setPjSelection(null); setPjDetail(null) }}
                    >
                      <i className="bi bi-grid-3x3-gap me-1"/>Voir tous les tableaux
                    </button>
                    <PointJournalierTableauCPFAE tb={pjDetail} />
                  </div>
                ) : (
                  <div style={{ background: '#fff', borderRadius: 10, padding: '1.5rem', boxShadow: '0 1px 4px rgba(0,0,0,0.07)', color: '#64748b', fontSize: '0.85rem' }}>
                    Impossible de charger le détail de ce tableau. Réessayez ou actualisez la liste.
                  </div>
                )
              )}
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* Onglet — Alertes & Seuils (surveillance visuelle)                    */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {onglet==='alertes' && (() => {
        const alertesSidebar = buildAlertesSidebarEntries(alertesMeta, alertes)
        const alertesEntry = alertesSelection ? alertesSidebar.find(e => e.id === alertesSelection) : null
        const alertesProps = {
          alertesMeta, alertes, seuils, seuilsForm, editSeuils, setEditSeuils, setSeuilsForm,
          canValidate, initSeuilsDefaut, initSeuilsLoading, saveSeuils,
          showGuideAlertes, setShowGuideAlertes,
          formationId, secretariatId,
          auditeursNotoires,
        }
        return (
        <div>
          <div style={{display:'flex',flexWrap:'wrap',gap:'0.5rem',alignItems:'center',marginBottom:'0.75rem'}}>
            <span style={{fontSize:'0.78rem',color:'#64748b'}}>
              Surveillance INJS — seuils et alertes
              {formationId && <> · <b>{(formations_liste||[]).find(f => String(f.id) === formationId)?.formation}</b></>}
              {secretariatId && <> · <b>{(secretariats_liste||[]).find(s => String(s.id) === secretariatId)?.nom}</b></>}
            </span>
            <div style={{marginLeft:'auto', display:'flex', gap:'0.35rem'}}>
              <button className="btn btn-sm btn-outline-secondary" onClick={() => { fetchSeuils(); fetchData(TAB_SECTIONS.alertes) }} disabled={loadingTab}>
                <i className="bi bi-arrow-clockwise me-1"/>Actualiser
              </button>
            </div>
          </div>

          <div style={{display:'grid',gridTemplateColumns:'minmax(220px,280px) 1fr',gap:'1rem',alignItems:'start'}}>
            <div style={{background:'#fff',borderRadius:10,boxShadow:'0 1px 4px rgba(0,0,0,0.07)',overflow:'hidden',maxHeight:'70vh',overflowY:'auto'}}>
              <div style={{padding:'0.65rem 0.85rem',background:'#f8fafc',borderBottom:'1px solid #e2e8f0',fontSize:'0.78rem',color:'#64748b',fontWeight:600}}>
                {alertesSidebar.length} vue{alertesSidebar.length > 1 ? 's' : ''}
              </div>
              <button
                type="button"
                onClick={()=>setAlertesSelection(null)}
                style={{
                  display:'block', width:'100%', textAlign:'left', border:'none', cursor:'pointer',
                  padding:'0.55rem 0.85rem', fontSize:'0.78rem', fontWeight:700,
                  background: alertesSelection === null ? '#e0f2fe' : '#fff',
                  borderBottom:'2px solid #e2e8f0', color: alertesSelection === null ? '#0369a1' : '#475569',
                }}
              >
                <i className="bi bi-grid-3x3-gap me-1"/>
                Tous les widgets
              </button>
              {['sections', 'indicateurs'].map(group => {
                const items = alertesSidebar.filter(e => e.group === group)
                if (!items.length) return null
                const groupLabel = group === 'sections' ? 'Sections' : 'Indicateurs'
                return (
                  <div key={group}>
                    <div style={{padding:'0.4rem 0.85rem',fontSize:'0.68rem',fontWeight:700,color:'#94a3b8',background:'#fafbfc',borderBottom:'1px solid #f1f5f9'}}>
                      {groupLabel}
                    </div>
                    {items.map(entry => (
                      <button
                        key={entry.id}
                        type="button"
                        onClick={()=>setAlertesSelection(entry.id)}
                        style={{
                          display:'block', width:'100%', textAlign:'left', border:'none', cursor:'pointer',
                          padding:'0.55rem 0.85rem', fontSize:'0.78rem',
                          background: alertesSelection===entry.id ? '#e8eef6' : '#fff',
                          borderBottom:'1px solid #f1f5f9',
                        }}
                      >
                        <div style={{fontWeight:700, color:'#1e293b', marginBottom:'0.1rem'}}>
                          <i className={`bi ${entry.icon} me-1`} style={{color:entry.tagColor}}/>
                          <span style={{
                            background:`${entry.tagColor}18`, color:entry.tagColor, borderRadius:4,
                            padding:'0.05rem 0.35rem', marginRight:'0.3rem', fontSize:'0.68rem',
                          }}>{entry.tag}</span>
                          <span style={{overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',display:'inline-block',maxWidth:'calc(100% - 2.8rem)',verticalAlign:'bottom'}}>
                            {entry.label}
                          </span>
                        </div>
                        <div style={{color:'#94a3b8', fontSize:'0.72rem'}}>{entry.sub}</div>
                      </button>
                    ))}
                  </div>
                )
              })}
            </div>

            {alertesSelection === null ? (
              <AlertesEnsemblePanel {...alertesProps} onSelectWidget={setAlertesSelection} />
            ) : alertesEntry ? (
              <div style={{ minWidth: 0 }}>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-secondary mb-2"
                  onClick={()=>setAlertesSelection(null)}
                >
                  <i className="bi bi-grid-3x3-gap me-1"/>Voir tous les widgets
                </button>
                <AlertesWidgetDetailPanel
                  entry={alertesEntry}
                  {...alertesProps}
                  onGoSeuils={() => setAlertesSelection('seuils')}
                />
              </div>
            ) : (
              <Empty label="Widget introuvable"/>
            )}
          </div>
        </div>
        )
      })()}
    </div>
  )
}

// ── Point journalier (format CPFAE — voir PointJournalierCPFAE.jsx) ───────────

function PointJournalierEnsemblePanel({ items, tableaux, annee, onSelectIndividuel }) {
  const selectTableau = (tableauId) => {
    const idx = (tableaux || []).findIndex(tb => tb.id === tableauId)
    if (idx >= 0) onSelectIndividuel(idx)
  }

  if (!items?.length) {
    return (
      <div style={{
        background: '#fff', borderRadius: 10, padding: '2rem', textAlign: 'center',
        boxShadow: '0 1px 4px rgba(0,0,0,0.07)',
      }}>
        <Empty label="Aucun tableau à afficher pour cette sélection"/>
      </div>
    )
  }

  return (
    <div style={{
      background: '#fff', borderRadius: 10, boxShadow: '0 1px 4px rgba(0,0,0,0.07)',
      overflow: 'hidden', minWidth: 0,
    }}>
      <div style={{
        padding: '0.85rem 1rem', background: 'linear-gradient(135deg, #e8eef6 0%, #d4deec 100%)',
        borderBottom: '1px solid #e2e8f0', position: 'sticky', top: 0, zIndex: 2,
      }}>
        <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 800, color: '#1e293b' }}>
          <i className="bi bi-grid-3x3-gap me-2" style={{ color: '#EDB131' }}/>
          {items.length} tableau{items.length > 1 ? 'x' : ''} — Point journalier {annee}
        </h3>
        <p style={{ margin: '0.35rem 0 0', fontSize: '0.78rem', color: '#64748b' }}>
          Vue d&apos;ensemble de tous les points journaliers filtrés.
          Utilisez le panneau de gauche pour afficher un seul tableau en plein écran.
        </p>
      </div>
      <div style={{ maxHeight: '62vh', overflowY: 'auto', padding: '1rem' }}>
        {items.map((entry, i) => (
          <div
            key={entry.tableau_id}
            id={`pj-tableau-${entry.tableau_id}`}
            style={{
              marginBottom: i < items.length - 1 ? '1.75rem' : 0,
              paddingBottom: i < items.length - 1 ? '1.75rem' : 0,
              borderBottom: i < items.length - 1 ? '2px dashed #e2e8f0' : 'none',
            }}
          >
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
              gap: '0.5rem', marginBottom: '0.65rem', flexWrap: 'wrap',
            }}>
              <div>
                <div style={{ fontWeight: 800, fontSize: '0.88rem', color: '#1e293b' }}>
                  <span style={{
                    background: '#EDB13118', color: '#EDB131', borderRadius: 4,
                    padding: '0.05rem 0.35rem', marginRight: '0.3rem', fontSize: '0.72rem',
                  }}>CAT {entry.meta?.categorie}</span>
                  {entry.meta?.date_fr} — {entry.meta?.formation}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                  Prés. jour : {pjPct(entry.meta?.taux_presence_jour ?? 0)}
                </div>
              </div>
              <button
                type="button"
                className="btn btn-sm btn-outline-warning"
                style={{ fontSize: '0.72rem', flexShrink: 0 }}
                onClick={() => selectTableau(entry.tableau_id)}
              >
                <i className="bi bi-arrows-fullscreen me-1"/>Plein écran
              </button>
            </div>
            <PointJournalierTableauCPFAE tb={entry.tableau} />
          </div>
        ))}
      </div>
    </div>
  )
}
