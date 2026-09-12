import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react'

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal()
  const mod = await import('@/test/utils/mockApi')
  return { ...actual, default: mod.default, setSessionExpiredCallback: vi.fn() }
})

import apiMock, { apiController } from '@/test/utils/mockApi'
import { renderWithProviders } from '@/test/utils/renderWithProviders'
import { makeUser } from '@/test/utils/factories'
import { useAuth } from '@/context/AuthContext'
import Statistiques, { BilanPeriodeFormationTable } from '@/pages/Statistiques'

// Reproduit la garde ProtectedRoute de production : la page ne se monte
// qu'une fois l'utilisateur courant résolu (GET /auth/me), comme en vrai.
function WaitForAuth({ children }) {
  const { isAuthenticated, loading } = useAuth()
  if (loading || !isAuthenticated) return <div className="loading"><div className="spinner" /></div>
  return children
}

const SECRETARIATS = [
  { id: 1, nom: 'INJS Centre' },
  { id: 2, nom: 'INJS Marcory' },
  { id: 3, nom: 'INJS Yopougon' },
]
const FORMATIONS = [
  { id: 10, formation: 'Licence 1 LSF' },
  { id: 11, formation: 'Licence 2 LSF' },
]

const BASE = 'http://testserver'
const paramsOf = (url) => new URL(url, BASE).searchParams
const callsTo = (pathOnly) =>
  apiMock.get.mock.calls
    .filter(([p]) => p.split('?')[0] === pathOnly)
    .map(([p]) => paramsOf(p))
const lastParams = (pathOnly) => callsTo(pathOnly).at(-1) ?? null

/** Distingue l'appel « méta-listes » (React Query) des chargements d'onglets. */
const isMetaCall = (q) => (q.get('sections') || '').includes('secretariats_liste')

const mountStats = (me, initialEntry = '/statistiques') => {
  apiController.setMe(me)
  return renderWithProviders(
    <WaitForAuth><Statistiques /></WaitForAuth>,
    { authUser: me, initialEntries: [initialEntry], routePattern: '/statistiques' },
  )
}

const adminMe = () => makeUser('ADMIN', { username: 'admin' })

const selectGlobalSecretariat = async (nom) => {
  const option = await screen.findByRole('option', { name: nom })
  const select = option.closest('select')
  fireEvent.change(select, { target: { value: String(SECRETARIATS.find((s) => s.nom === nom).id) } })
  return select
}
const resetGlobalSecretariat = async () => {
  const option = await screen.findByRole('option', { name: 'Tous les secrétariats' })
  const select = option.closest('select')
  fireEvent.change(select, { target: { value: '' } })
}

describe('pages/Statistiques.jsx — périmètre secrétariat (isolation des données)', () => {
  beforeEach(() => {
    apiController.reset()
    window.localStorage.clear()

    // Endpoint principal : méta-listes (React Query) vs données d'onglet.
    apiController.setRoute('/statistiques/', (path) => {
      const q = paramsOf(path)
      if (isMetaCall(q)) {
        return {
          formations_liste: FORMATIONS,
          secretariats_liste: SECRETARIATS,
          filtre_actif: { scope_locked: false },
        }
      }
      return {}
    })
    apiController.setRoute('/statistiques/point-journalier/', () => ({
      tableaux: [],
      tableaux_complets: [],
    }))
    apiController.setRoute('/statistiques/bilans/', () => ({
      bilans: [],
      tableaux_complets: [],
    }))
    apiController.setRoute('/statistiques/alertes/seuils/', () => ({
      seuils: [],
      indicateurs: [],
      synthese: {},
      seuils_vides: true,
    }))
  })

  it('charge la vue d’ensemble sans secrétariat forcé pour un administrateur', async () => {
    mountStats(adminMe())
    await screen.findByRole('option', { name: 'INJS Marcory' })

    const params = lastParams('/statistiques/')
    expect(params.get('secretariat_id')).toBe(null)
    // Le sélecteur global de secrétariat est bien proposé (non verrouillé).
    expect(screen.getByRole('option', { name: 'Tous les secrétariats' })).toBeInTheDocument()
  })

  it('applique le filtre global de secrétariat à la requête de statistiques', async () => {
    mountStats(adminMe())
    await screen.findByRole('option', { name: 'INJS Marcory' })

    await selectGlobalSecretariat('INJS Marcory')

    await waitFor(() => expect(lastParams('/statistiques/').get('secretariat_id')).toBe('2'))
    // L'appel méta (listes) respecte aussi le périmètre.
    const meta = callsTo('/statistiques/').filter(isMetaCall).at(-1)
    expect(meta.get('secretariat_id')).toBe('2')
  })

  it('[effectiveSecretariatId] utilise le secrétariat COURANT dans l’onglet Point Journalier', async () => {
    // Régression visée : un useCallback omet effectiveSecretariatId dans ses
    // dépendances ; on vérifie qu'aucune requête n'utilise un secrétariat périmé.
    mountStats(adminMe())
    await screen.findByRole('option', { name: 'INJS Marcory' })

    await selectGlobalSecretariat('INJS Yopougon')
    fireEvent.click(screen.getByRole('button', { name: 'Point Journalier' }))

    await waitFor(() => expect(callsTo('/statistiques/point-journalier/').length).toBeGreaterThan(0))
    const pj = callsTo('/statistiques/point-journalier/')
    expect(pj.at(-1).get('secretariat_id')).toBe('3')
    // Toutes les requêtes émises après le choix portent bien l'id courant.
    for (const q of pj) expect(q.get('secretariat_id')).toBe('3')

    // Repasser à « Tous » retire le paramètre et refait une requête.
    await resetGlobalSecretariat()
    await waitFor(() => {
      const dernier = callsTo('/statistiques/point-journalier/').at(-1)
      expect(dernier.get('secretariat_id')).toBe(null)
    })
  })

  it('[effectiveSecretariatId] porte le secrétariat courant dans l’onglet Rapports & Bilans', async () => {
    mountStats(adminMe())
    await screen.findByRole('option', { name: 'INJS Marcory' })

    await selectGlobalSecretariat('INJS Marcory')
    fireEvent.click(screen.getByRole('button', { name: 'Rapports & Bilans' }))

    await waitFor(() => expect(callsTo('/statistiques/bilans/').length).toBeGreaterThan(0))
    expect(callsTo('/statistiques/bilans/').at(-1).get('secretariat_id')).toBe('2')
  })

  it('[effectiveSecretariatId] porte le secrétariat courant dans l’onglet Alertes (seuils)', async () => {
    mountStats(adminMe())
    await screen.findByRole('option', { name: 'INJS Marcory' })

    await selectGlobalSecretariat('INJS Yopougon')
    fireEvent.click(screen.getByRole('button', { name: 'Alertes' }))

    await waitFor(() => expect(callsTo('/statistiques/alertes/seuils/').length).toBeGreaterThan(0))
    expect(callsTo('/statistiques/alertes/seuils/').at(-1).get('secretariat_id')).toBe('3')
  })

  it('verrouille TOUTES les requêtes sur le secrétariat du compte Chef Secrétariat', async () => {
    const chef = makeUser('CHEF_SECRETARIAT', {
      username: 'chefsec',
      secretariat: 77,
      secretariat_nom: 'Secrétariat Pédagogique',
    })
    mountStats(chef)

    // Onglet par défaut = Point Journalier ; dès la PREMIÈRE requête l'id
    // verrouillé est transmis (pas de fuite de données globales).
    await waitFor(() => expect(callsTo('/statistiques/point-journalier/').length).toBeGreaterThan(0))
    for (const q of callsTo('/statistiques/point-journalier/')) {
      expect(q.get('secretariat_id')).toBe('77')
    }

    // Le chargement d'onglet et les méta-listes sont aussi verrouillés.
    await waitFor(() => {
      const dataCalls = callsTo('/statistiques/').filter((q) => !isMetaCall(q))
      expect(dataCalls.length).toBeGreaterThan(0)
      for (const q of dataCalls) expect(q.get('secretariat_id')).toBe('77')
    })
    const meta = await waitFor(() => {
      const m = callsTo('/statistiques/').filter(isMetaCall)
      if (!m.length) throw new Error('pas encore de méta')
      return m.at(-1)
    })
    expect(meta.get('secretariat_id')).toBe('77')

    // Le sélecteur global est absent et le badge de périmètre est affiché.
    expect(screen.queryByRole('option', { name: 'Tous les secrétariats' })).not.toBeInTheDocument()
    expect(screen.getByText(/Secrétariat Pédagogique/)).toBeInTheDocument()

    // Onglets autorisés : Point Journalier et Rapports ; les autres sont masqués.
    expect(screen.getByRole('button', { name: 'Point Journalier' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Rapports & Bilans' }))
    await waitFor(() => expect(callsTo('/statistiques/bilans/').length).toBeGreaterThan(0))
    expect(callsTo('/statistiques/bilans/').at(-1).get('secretariat_id')).toBe('77')

    expect(screen.queryByRole('button', { name: /vue d'ensemble/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Pédagogique' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Alertes' })).not.toBeInTheDocument()
  })
})

/* Sous-composant pur : pas de provider, rendu direct. */
const jStats = {
  nb_groupes: 1, nb_encadrants: 2, effectif_secretariat: 3,
  inscrits_actifs: 10, inscrits_reference: 12, pct_inscrits: 83,
  masculin_inscrits: 6, feminin_inscrits: 6, auditeurs_listes: 9,
  effectifs_presents: 8, pct_presents_total: 80,
  masculin: 4, pct_masculins_presents: 50, feminin: 4, pct_feminins_presents: 50,
  absents: 1, pct_absents_total: 10,
}
const makeJTableau = (overrides = {}) => ({
  type: 'bilan_periode_formation',
  titre: 'Bilan L1 — 2025',
  formation_id: 42,
  annee: 2025,
  date_inscrits: '01/01/2026',
  justificatifs: '',
  lignes: [{ categorie: 'Grade A', totaux: jStats }],
  total: jStats,
  ...overrides,
})
const justifBox = () => screen.getByPlaceholderText(/saisir les justificatifs/i)

describe('BilanPeriodeFormationTable — synchronisation des justificatifs (§10.7 LOT 6)', () => {
  it('reprend les justificatifs serveur reçus pour une ligne DÉJÀ affichée (clés identiques)', async () => {
    const { rerender } = render(
      <BilanPeriodeFormationTable data={makeJTableau()} justificatifsText="" />,
    )
    expect(justifBox().value).toBe('')

    // Rafraîchissement : mêmes titre/formation_id/année, mais le serveur fournit
    // maintenant les justificatifs (tableau → liste à puces). Avant le LOT 6,
    // l'effet ne se redéclenchait pas et la zone restait vide.
    rerender(
      <BilanPeriodeFormationTable
        data={makeJTableau({ justificatifs: ['Report de formation', 'Maladie'] })}
        justificatifsText=""
      />,
    )
    await waitFor(() => expect(justifBox().value).toContain('Report de formation'))
    expect(justifBox().value).toBe('• Report de formation\n• Maladie')
  })

  it('ne remplace jamais une saisie utilisateur par la valeur renvoyée par le serveur', () => {
    const onChange = vi.fn()
    const { rerender } = render(
      <BilanPeriodeFormationTable data={makeJTableau()} justificatifsText="" onJustificatifsChange={onChange} />,
    )

    fireEvent.change(justifBox(), { target: { value: 'Mon texte saisi' } })
    expect(onChange).toHaveBeenCalledWith('Mon texte saisi')

    // Une mise à jour serveur pour la même ligne ne doit pas écraser la saisie :
    // dès que le parent porte un texte, il reste prioritaire.
    rerender(
      <BilanPeriodeFormationTable
        data={makeJTableau({ justificatifs: ['Valeur serveur'] })}
        justificatifsText="Mon texte saisi"
        onJustificatifsChange={onChange}
      />,
    )
    expect(justifBox().value).toBe('Mon texte saisi')
  })
})

// ════════════════════════════════════════════════════════════════════════════
// LOT 38a — Socle du dashboard Statistiques : montage, navigation par onglets,
// états de chargement / erreur, filtres d'en-tête et de période, états vides,
// alertes/seuils et garde-fous des exports. Tests PURS (aucune modification de
// Statistiques.jsx dans ce lot).
// ════════════════════════════════════════════════════════════════════════════

const CURRENT_YEAR = new Date().getFullYear()
const CURRENT_MONTH = `${CURRENT_YEAR}-${String(new Date().getMonth() + 1).padStart(2, '0')}`
const CURRENT_QUARTER = `${CURRENT_YEAR}-Q${Math.floor(new Date().getMonth() / 3) + 1}`

const KPIS = {
  formations: 3, modules: 9, participants: 42, formateurs: 7,
  sessions_total: 30, sessions_terminees: 20,
  vh_prevu_heures: 600, taux_execution_vh: 66,
}
const PED = {
  total_inscrits: 42, total_presents: 30, total_absents: 12, total_abandons: 2,
  taux_presence: 71.4, taux_absence: 28.6, taux_abandon: 4.8,
  taux_couverture_auditeurs: 80, taux_achevement: 80,
  taux_par_formation: [], taux_par_grade: [], taux_par_secretariat: [],
  par_type_concours: [], auditeurs_notoires: null,
}
const ADM = {
  nb_groupes: 5, nb_encadrants: 7, nb_seances_annulees: 1, nb_seances_terminees: 20,
  nb_absences_notoires: 3, moy_auditeurs_groupe: 8,
  ratio_hf: { pct_hommes: 55, pct_femmes: 45 },
  participants_par_sexe: [], participants_par_categorie: [],
  participants_par_grade: [], participants_par_vague: [],
  charge_enseignants: [], charge_formateurs: [], auditeurs_notoires: null,
}
const HIST = {
  resume: {
    total_pointages: 110, moy_pointages_mois: 55, total_sessions: 30,
    sessions_mois_courant: 16, moy_taux_presence: 81.5,
    modules_actifs_dernier_mois: 9, pointages_mois_courant: 60,
    variation_pointages_pct: 20,
  },
  pointages_par_mois: [
    { mois: `${CURRENT_YEAR}-08`, total: 50, presents: 40, absents: 10 },
    { mois: `${CURRENT_YEAR}-09`, total: 60, presents: 50, absents: 10 },
  ],
  taux_presence_par_mois: [
    { mois: `${CURRENT_YEAR}-08`, total: 80 },
    { mois: `${CURRENT_YEAR}-09`, total: 83 },
  ],
  sessions_par_mois: [
    { mois: `${CURRENT_YEAR}-08`, total: 14 },
    { mois: `${CURRENT_YEAR}-09`, total: 16 },
  ],
  modules_par_mois: [
    { mois: `${CURRENT_YEAR}-08`, total: 2, actifs: 8, cumul: 8 },
    { mois: `${CURRENT_YEAR}-09`, total: 1, actifs: 9, cumul: 9 },
  ],
}

/** Construit une réponse `/statistiques/` selon les sections demandées. */
function statsDataFor(q, overrides = {}) {
  const sections = (q.get('sections') || '').split(',')
  if (sections.includes('secretariats_liste')) {
    return {
      formations_liste: FORMATIONS,
      secretariats_liste: overrides.secretariats_liste ?? SECRETARIATS,
      filtre_actif: { scope_locked: false },
    }
  }
  const out = {}
  if (sections.includes('kpis')) out.kpis = overrides.kpis ?? KPIS
  if (sections.includes('pedagogiques')) out.pedagogiques = overrides.pedagogiques ?? PED
  if (sections.includes('admin_operationnel')) out.admin_operationnel = overrides.adm ?? ADM
  if (sections.includes('historique')) out.historique = overrides.historique ?? HIST
  if (sections.includes('alertes')) out.alertes = overrides.alertes ?? []
  if (sections.includes('alertes_overview')) out.alertes_overview = overrides.alertes_overview ?? []
  out.periode = overrides.periode ?? { label: 'Septembre 2026', filtre_actif: true }
  return out
}

const dataCalls = () => callsTo('/statistiques/').filter((q) => !isMetaCall(q))
const lastDataCall = () => dataCalls().at(-1) ?? null
const tabButton = (name) => screen.getByRole('button', { name })

/** Promesse piloteable depuis le test (pour figer un état de chargement). */
function deferred() {
  let res
  let rej
  const p = new Promise((a, b) => { res = a; rej = b })
  return { p, res, rej }
}

function installStdRoutes(overrides = {}) {
  apiController.setRoute('/statistiques/', (path) => statsDataFor(paramsOf(path), overrides))
  apiController.setRoute(
    '/statistiques/point-journalier/',
    typeof overrides.pj === 'function'
      ? (path) => overrides.pj(paramsOf(path), path)
      : () => ({ tableaux: [], tableaux_complets: [] }),
  )
  apiController.setRoute(
    '/statistiques/bilans/',
    typeof overrides.bilans === 'function'
      ? (path) => overrides.bilans(paramsOf(path), path)
      : () => ({ bilans: [], tableaux_complets: [], total_bilans: 0 }),
  )
  apiController.setRoute('/statistiques/secretariats/', () => ({
    secretariats: [], total: 0, auditeurs_notoires: null,
  }))
  apiController.setRoute('/statistiques/alertes/seuils/', () => ({
    seuils: [], indicateurs: [], synthese: {}, seuils_vides: true,
  }))
}

const PJ_TABLEAUX = [
  {
    id: 'pj-1', date: `${CURRENT_YEAR}-09-15`, date_fr: '15/09/2026',
    formation_id: 10, formation: 'Licence 1 LSF', categorie: 'A',
    taux_presence_jour: 0.9,
  },
]

describe('Statistiques (LOT 38a) — socle : onglets, sections API et navigation', () => {
  beforeEach(() => {
    apiController.reset()
    window.localStorage.clear()
    window.sessionStorage.clear()
    installStdRoutes()
  })

  it("rend les 8 onglets pour un administrateur, avec la vue d'ensemble active par défaut", async () => {
    mountStats(adminMe())
    await screen.findByRole('option', { name: 'INJS Marcory' })

    for (const label of [
      "Vue d'ensemble", 'Pédagogique', 'Administratif', 'Historique', 'Secrétariats',
      'Rapports & Bilans', 'Point Journalier', 'Alertes',
    ]) {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument()
    }
    expect(screen.getByText('Statistiques & Bilans')).toBeInTheDocument()
    // Sections requêtées au montage (onglet overview).
    expect(lastDataCall().get('sections')).toBe(
      'kpis,pedagogiques,admin_operationnel,alertes_overview,alertes',
    )
  })

  it('requête les sections dédiées à chaque changement d’onglet', async () => {
    mountStats(adminMe())
    await screen.findByText('4 sections')

    const cases = [
      { tab: 'Pédagogique', sections: ['pedagogiques'] },
      { tab: 'Administratif', sections: ['admin_operationnel'] },
      { tab: 'Historique', sections: ['historique', 'pedagogiques', 'admin_operationnel'] },
      { tab: 'Alertes', sections: ['alertes', 'pedagogiques', 'admin_operationnel'] },
      { tab: 'Point Journalier', sections: ['admin_operationnel'] },
      { tab: 'Rapports & Bilans', sections: ['admin_operationnel'] },
      { tab: "Vue d'ensemble", sections: ['kpis', 'pedagogiques', 'admin_operationnel', 'alertes_overview', 'alertes'] },
    ]
    for (const { tab, sections } of cases) {
      fireEvent.click(tabButton(tab))
      await waitFor(() => {
        const q = lastDataCall()
        expect(q.get('sections').split(',').sort()).toEqual([...sections].sort())
      })
    }
  })

  it('charge la liste des secrétariats via l’endpoint dédié à l’ouverture de l’onglet', async () => {
    mountStats(adminMe())
    await screen.findByText('4 sections')

    fireEvent.click(tabButton('Secrétariats'))
    await waitFor(() => expect(callsTo('/statistiques/secretariats/').length).toBeGreaterThan(0))
    // État vide : aucun secrétariat renvoyé par la fixture standard.
    expect(await screen.findByText('Aucun secrétariat trouvé')).toBeInTheDocument()
  })

  it("affiche le panneau de période sur les onglets d'indicateurs, masqué en Point Journalier et Rapports", async () => {
    mountStats(adminMe())
    await screen.findByText('PÉRIODE — INDICATEURS CLÉS')

    fireEvent.click(tabButton('Point Journalier'))
    await waitFor(() =>
      expect(screen.queryByText('PÉRIODE — INDICATEURS CLÉS')).not.toBeInTheDocument())
    fireEvent.click(tabButton('Rapports & Bilans'))
    expect(screen.queryByText('PÉRIODE — INDICATEURS CLÉS')).not.toBeInTheDocument()

    fireEvent.click(tabButton('Historique'))
    expect(await screen.findByText('PÉRIODE — INDICATEURS CLÉS')).toBeInTheDocument()
    fireEvent.click(tabButton('Alertes'))
    expect(screen.getByText('PÉRIODE — INDICATEURS CLÉS')).toBeInTheDocument()
  })

  it('porte la période par défaut (mois courant) sur les requêtes de données', async () => {
    mountStats(adminMe())
    await screen.findByText('4 sections')
    expect(lastDataCall().get('preset')).toBe('mois')
    expect(lastDataCall().get('mois')).toBe(CURRENT_MONTH)
  })

  it('ouvre directement l’onglet Rapports en sous-vue workflow via ?rbView=workflow', async () => {
    mountStats(adminMe(), '/statistiques?rbView=workflow')
    expect(await screen.findByText('Rapports périodiques — validation')).toBeInTheDocument()
    // La vue « Bilans INJS » n'est pas affichée tant qu'on ne bascule pas.
    expect(screen.queryByText('Aucun bilan pour cette sélection')).not.toBeInTheDocument()
  })
})

describe('Statistiques (LOT 38a) — états de chargement et d’erreur', () => {
  beforeEach(() => {
    apiController.reset()
    window.localStorage.clear()
    window.sessionStorage.clear()
  })

  it('affiche le spinner de chargement initial tant que le premier appel n’est pas résolu', async () => {
    const gate = deferred()
    apiController.setRoute('/statistiques/', async (path) => {
      await gate.p
      return statsDataFor(paramsOf(path))
    })
    mountStats(adminMe())
    expect(await screen.findByText('Chargement des statistiques…')).toBeInTheDocument()

    gate.res()
    await screen.findByRole('option', { name: 'INJS Marcory' })
    expect(screen.queryByText('Chargement des statistiques…')).not.toBeInTheDocument()
  })

  it('affiche l’erreur initiale avec le détail backend et un bouton Réessayer qui répare la page', async () => {
    let fail = true
    apiController.setRoute('/statistiques/', (path) => {
      if (fail) throw { response: { data: { detail: 'Serveur indisponible' } } }
      return statsDataFor(paramsOf(path))
    })
    mountStats(adminMe())

    expect(await screen.findByText('Serveur indisponible')).toBeInTheDocument()
    const retry = screen.getByRole('button', { name: /Réessayer/ })

    fail = false
    fireEvent.click(retry)
    // Le retry recharge les sections de l'onglet (la méta React Query, hors
    // ligne, n'est pas rejouée) : le dashboard se rouvre sur la vue d'ensemble.
    expect(await screen.findByText('4 sections')).toBeInTheDocument()
    expect(screen.queryByText('Serveur indisponible')).not.toBeInTheDocument()
  })

  it("retombe sur un message générique quand l'erreur n'a pas de détail", async () => {
    apiController.setRoute('/statistiques/', () => { throw new Error('réseau') })
    mountStats(adminMe())
    expect(await screen.findByText('Erreur de chargement.')).toBeInTheDocument()
  })

  it('affiche un bandeau d’erreur non bloquant si un rechargement échoue après chargement', async () => {
    let failData = false
    apiController.setRoute('/statistiques/', (path) => {
      const q = paramsOf(path)
      if (failData && !isMetaCall(q)) throw { response: { data: { detail: 'Coupure momentanée' } } }
      return statsDataFor(q)
    })
    apiController.setRoute('/statistiques/point-journalier/', () => ({ tableaux: [], tableaux_complets: [] }))
    apiController.setRoute('/statistiques/bilans/', () => ({ bilans: [], tableaux_complets: [] }))
    apiController.setRoute('/statistiques/secretariats/', () => ({ secretariats: [], total: 0 }))
    apiController.setRoute('/statistiques/alertes/seuils/', () => ({ seuils: [], indicateurs: [], synthese: {}, seuils_vides: true }))
    mountStats(adminMe())
    await screen.findByText('4 sections')

    failData = true
    fireEvent.click(screen.getAllByRole('button', { name: /Actualiser/ })[0])
    expect(await screen.findByText('Coupure momentanée')).toBeInTheDocument()
    // Les onglets et le contenu restent montés : pas d'écran plein bloquant.
    expect(screen.queryByRole('button', { name: /Réessayer/ })).not.toBeInTheDocument()
    expect(tabButton('Alertes')).toBeInTheDocument()
  })

  it('indique « Actualisation… » pendant un rechargement manuel', async () => {
    const gate = deferred()
    let dataCallCount = 0
    apiController.setRoute('/statistiques/', async (path) => {
      const q = paramsOf(path)
      if (!isMetaCall(q)) {
        dataCallCount += 1
        if (dataCallCount >= 2) await gate.p // le chargement initial passe, le refresh fige
      }
      return statsDataFor(q)
    })
    mountStats(adminMe())
    await screen.findByText('Formations') // chargement initial terminé (KPIs rendus)

    fireEvent.click(screen.getAllByRole('button', { name: /Actualiser/ })[0])
    expect(await screen.findByText('Actualisation…')).toBeInTheDocument()
    gate.res()
    await waitFor(() =>
      expect(screen.queryByText('Actualisation…')).not.toBeInTheDocument())
  })

  it('affiche le message d’erreur du Point Journalier dans l’état vide', async () => {
    apiController.setRoute('/statistiques/', (path) => statsDataFor(paramsOf(path)))
    apiController.setRoute('/statistiques/point-journalier/', () => {
      throw { response: { data: { detail: 'Point journalier inaccessible' } } }
    })
    mountStats(adminMe())
    await screen.findByRole('option', { name: 'INJS Marcory' })

    fireEvent.click(tabButton('Point Journalier'))
    expect(await screen.findByText('Aucun point journalier pour cette période')).toBeInTheDocument()
    expect(screen.getByText('Point journalier inaccessible')).toBeInTheDocument()
  })
})

describe('Statistiques (LOT 38a) — filtres d’en-tête (formation / secrétariat / actualisation)', () => {
  beforeEach(() => {
    apiController.reset()
    window.localStorage.clear()
    window.sessionStorage.clear()
    installStdRoutes()
  })

  // Les options viennent de la méta React Query : toujours les attendre
  // (findByRole) avant de lire le select pour éviter toute course.
  const formationSelect = async () =>
    (await screen.findByRole('option', { name: 'Licence 1 LSF' })).closest('select')
  const secretariatSelect = async () =>
    (await screen.findByRole('option', { name: 'Tous les secrétariats' })).closest('select')
  it('peuple le sélecteur de formation via la méta et propage formation_id aux données et à la méta', async () => {
    mountStats(adminMe())
    await screen.findByText('4 sections')

    fireEvent.change(await formationSelect(), { target: { value: '10' } })
    await waitFor(() => expect(lastDataCall().get('formation_id')).toBe('10'))
    const meta = callsTo('/statistiques/').filter(isMetaCall).at(-1)
    expect(meta.get('formation_id')).toBe('10')
    // Le libellé de la formation apparaît dans le chapeau de l'onglet (en plus
    // de l'option du sélecteur).
    expect(screen.getAllByText('Licence 1 LSF').length).toBeGreaterThan(1)
  })

  it('propose un bouton « Effacer les filtres » qui réinitialise formation et secrétariat', async () => {
    mountStats(adminMe())
    await screen.findByText('4 sections')

    fireEvent.change(await formationSelect(), { target: { value: '11' } })
    await waitFor(() => expect(lastDataCall().get('formation_id')).toBe('11'))
    const resetBtn = document.querySelector('button[title="Effacer les filtres"]')
    expect(resetBtn).toBeInTheDocument()

    fireEvent.click(resetBtn)
    await waitFor(() => expect(lastDataCall().get('formation_id')).toBe(null))
    expect((await formationSelect()).value).toBe('')
  })

  it('affiche l’horodatage de dernière mise à jour après le premier chargement', async () => {
    mountStats(adminMe())
    expect(await screen.findByText(/Mis à jour le/)).toBeInTheDocument()
  })

  it('redéclenche un chargement via le bouton Actualiser de l’en-tête', async () => {
    mountStats(adminMe())
    await screen.findByText('4 sections')
    const avant = dataCalls().length
    expect(avant).toBeGreaterThan(0)

    fireEvent.click(screen.getAllByRole('button', { name: /Actualiser/ })[0])
    await waitFor(() => expect(dataCalls().length).toBeGreaterThan(avant))
  })

  it('laisse le sélecteur de secrétariat activé pour un encadrant avec plusieurs secrétariats', async () => {
    mountStats(makeUser('ENCADRANT', { username: 'enc1' }))
    expect(await secretariatSelect()).not.toBeDisabled()
  })

  it('désactive le sélecteur de secrétariat pour un encadrant quand un seul secrétariat existe', async () => {
    apiController.reset()
    installStdRoutes({ secretariats_liste: [SECRETARIATS[0]] })
    mountStats(makeUser('ENCADRANT', { username: 'enc2' }))
    expect(await secretariatSelect()).toBeDisabled()
  })
})

describe('Statistiques (LOT 38a) — filtre de période des indicateurs clés', () => {
  beforeEach(() => {
    apiController.reset()
    window.localStorage.clear()
    window.sessionStorage.clear()
    installStdRoutes()
  })

  const periodPanel = () => document.querySelector('.finance-filter-panel')
  const presetPill = (label) => within(periodPanel()).getByRole('button', { name: label })

  it('applique immédiatement un changement de preset (auto-apply) : « Cette année »', async () => {
    mountStats(adminMe())
    await screen.findByText('4 sections')

    fireEvent.click(presetPill('Cette année'))
    await waitFor(() => {
      expect(lastDataCall().get('preset')).toBe('annee')
      expect(lastDataCall().get('annee')).toBe(String(CURRENT_YEAR))
    })
    // Persistance de la période pour la prochaine visite.
    expect(window.sessionStorage.getItem('finance_period')).toContain('"annee"')
  })

  it('signale une période entièrement future et permet de revenir au trimestre courant', async () => {
    mountStats(adminMe())
    await screen.findByText('4 sections')

    fireEvent.click(presetPill('Cette année'))
    // Le libellé « Année » n'est pas relié par htmlFor : cibler l'input number
    // du panneau de période directement.
    const anneeInput = periodPanel().querySelector('input[type="number"]')
    fireEvent.change(anneeInput, { target: { value: '2099' } })

    const warning = await screen.findByText(/pas encore commencé/)
    expect(warning).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Voir le trimestre en cours/ }))
    await waitFor(() => {
      expect(lastDataCall().get('preset')).toBe('trimestre')
      expect(lastDataCall().get('trimestre')).toBe(CURRENT_QUARTER)
    })
    await waitFor(() =>
      expect(screen.queryByText(/pas encore commencé/)).not.toBeInTheDocument())
  })

  it('affiche le badge de période renvoyé par l’API', async () => {
    mountStats(adminMe())
    // La fixture standard renvoie periode.label = « Septembre 2026 ».
    expect((await screen.findAllByText('Septembre 2026')).length).toBeGreaterThan(0)
  })

  it('signale l’absence de séance comptabilisable quand les KPI sont à 0 sur la période', async () => {
    apiController.reset()
    installStdRoutes({
      kpis: { ...KPIS, sessions_terminees: 0, sessions_total: 0 },
      periode: { label: 'Septembre 2026', filtre_actif: true },
    })
    mountStats(adminMe())
    expect(await screen.findByText(/Aucune séance comptabilisable/)).toBeInTheDocument()
  })

  it('n’affiche pas le message « aucune séance » quand le preset est « Tout »', async () => {
    window.sessionStorage.setItem('finance_period', JSON.stringify({ preset: 'tout' }))
    apiController.reset()
    installStdRoutes({
      kpis: { ...KPIS, sessions_terminees: 0, sessions_total: 0 },
      periode: { label: 'Toutes les périodes', filtre_actif: true },
    })
    mountStats(adminMe())
    await screen.findByText('4 sections')
    expect(screen.queryByText(/Aucune séance comptabilisable/)).not.toBeInTheDocument()
  })
})

describe('Statistiques (LOT 38a) — états vides et rendu minimal par onglet', () => {
  beforeEach(() => {
    apiController.reset()
    window.localStorage.clear()
    window.sessionStorage.clear()
    installStdRoutes()
  })

  it('Point Journalier vide : message, encart « Filtres actifs » et exports désactivés', async () => {
    mountStats(adminMe())
    await screen.findByText('4 sections')
    fireEvent.click(tabButton('Point Journalier'))

    expect(await screen.findByText('Aucun point journalier pour cette période')).toBeInTheDocument()
    expect(screen.getByText('Filtres actifs')).toBeInTheDocument()
    expect(screen.getByText(/Essayez/)).toBeInTheDocument()
    for (const label of ['Excel', 'PDF', 'Word']) {
      expect(screen.getByRole('button', { name: label })).toBeDisabled()
    }
  })

  it('Rapports & Bilans : vue bilans vide avec exports désactivés, puis bascule workflow', async () => {
    mountStats(adminMe())
    await screen.findByText('4 sections')
    fireEvent.click(tabButton('Rapports & Bilans'))

    expect(await screen.findByText('Aucun bilan pour cette sélection')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Excel' })).toBeDisabled()

    fireEvent.click(screen.getByRole('button', { name: /Rapports périodiques/ }))
    expect(await screen.findByText('Rapports périodiques — validation')).toBeInTheDocument()
    expect(screen.queryByText('Aucun bilan pour cette sélection')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Bilans INJS' }))
    expect(await screen.findByText('Aucun bilan pour cette sélection')).toBeInTheDocument()
  })

  it('Historique vide : message d’aide contextuel', async () => {
    apiController.reset()
    installStdRoutes({ historique: { pointages_par_mois: [] } })
    mountStats(adminMe())
    await screen.findByText('4 sections')

    fireEvent.click(tabButton('Historique'))
    expect(await screen.findByText('Aucune donnée historique pour cette sélection')).toBeInTheDocument()
    expect(screen.getByText(/Vérifiez les filtres/)).toBeInTheDocument()
  })

  it("Vue d'ensemble : rend les KPI clés et permet d'ouvrir une section puis de revenir", async () => {
    mountStats(adminMe())
    await screen.findByText('4 sections')

    expect(await screen.findByText("Vue d'ensemble — synthèse")).toBeInTheDocument()
    // KPI de la synthèse.
    expect(screen.getByText('Formations')).toBeInTheDocument()
    expect(screen.getByText('Modules')).toBeInTheDocument()
    expect(screen.getAllByText('42').length).toBeGreaterThan(0) // participants
    expect(screen.getByText('66%')).toBeInTheDocument() // taux d'exécution VH

    // Navigation vers la section « Chiffres clés ».
    fireEvent.click(screen.getByRole('button', { name: /Chiffres clés/ }))
    expect(await screen.findByText(/Effectifs et volumes sur le périmètre filtré/)).toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('button', { name: /Voir tous les indicateurs/ })[0])
    expect(await screen.findByText("Vue d'ensemble — synthèse")).toBeInTheDocument()
  })

  it('Administratif : rend les KPI opérationnels et les cartes de répartition', async () => {
    mountStats(adminMe())
    await screen.findByText('4 sections')
    fireEvent.click(tabButton('Administratif'))

    expect(await screen.findByText('Groupes actifs')).toBeInTheDocument()
    expect(screen.getByText('Encadrants')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument() // nb_groupes
    expect(screen.getByText('Répartition Hommes / Femmes')).toBeInTheDocument()
    expect(screen.getByText('Charge des enseignants')).toBeInTheDocument()
  })

  it('Pédagogique : rend les totaux et annonce 0 périmètre listé', async () => {
    mountStats(adminMe())
    await screen.findByText('4 sections')
    fireEvent.click(tabButton('Pédagogique'))

    expect(await screen.findByText('0 périmètre')).toBeInTheDocument()
    expect(screen.getByText(/Pédagogique — vue d'ensemble/)).toBeInTheDocument()
    // Plusieurs KPI portent le libellé « Inscrits » (synthèse + taux principaux).
    expect(screen.getAllByText('Inscrits').length).toBeGreaterThan(0)
  })

  it('Historique : liste les mois disponibles et ouvre le détail d’un mois', async () => {
    mountStats(adminMe())
    await screen.findByText('4 sections')
    fireEvent.click(tabButton('Historique'))

    expect(await screen.findByText('2 mois')).toBeInTheDocument()
    expect(screen.getByText('Historique — 12 derniers mois')).toBeInTheDocument()

    // La sidebar liste les mois du plus récent au plus ancien (le libellé
    // « Septembre 2026 » apparaît aussi dans le badge de période du filtre).
    const moisBtn = screen.getByRole('button', { name: /Septembre 2026.*ptg/ })
    fireEvent.click(moisBtn)
    // En détail mensuel, le KPI spécifique « Pointages » (sans suffixe) et la
    // carte « Contexte — 2 mois » (fenêtre glissante août→septembre) s'affichent.
    expect(await screen.findByText('Pointages')).toBeInTheDocument()
    expect(screen.getByText(/Contexte — 2 mois/)).toBeInTheDocument()
    expect(screen.getAllByText('60').length).toBeGreaterThan(0)

    fireEvent.click(screen.getByRole('button', { name: /Voir tous les mois/ }))
    expect(await screen.findByText('Historique — 12 derniers mois')).toBeInTheDocument()
  })

  it('Secrétariats : charge le comparatif puis le détail d’un secrétariat sélectionné', async () => {
    const lignes = [
      {
        secretariat_id: 1, numero: 1, secretariat: 'INJS Centre', responsable: 'M. Konan',
        nb_modules: 4, nb_participants: 20, nb_formateurs: 3, nb_sessions: 12,
        nb_inscrits: 20, nb_presents: 15, taux_presence: 75, nb_absences: 5,
        nb_auditeurs_notoires: 1, nb_pointages: 100, vh_prevu: 300, taux_execution_vh: 60,
        ratio_hf: { hommes: 12, femmes: 8 },
      },
      {
        secretariat_id: 2, numero: 2, secretariat: 'INJS Marcory', responsable: 'Mme Aya',
        nb_modules: 5, nb_participants: 22, nb_formateurs: 4, nb_sessions: 18,
        nb_inscrits: 22, nb_presents: 20, taux_presence: 90.9, nb_absences: 2,
        nb_auditeurs_notoires: 0, nb_pointages: 140, vh_prevu: 400, taux_execution_vh: 80,
        ratio_hf: { hommes: 10, femmes: 12 },
      },
    ]
    apiController.reset()
    // Enregistrées AVANT les routes standard : la première route enregistrée
    // étant prioritaire, ces surcharges gagnent sur les réponses « vides ».
    apiController.setRoute('/statistiques/secretariats/', () => ({
      secretariats: lignes, total: 2, auditeurs_notoires: { total: 1, pct: 2.4 },
    }))
    apiController.setRoute('/statistiques/', (path) => {
      const q = paramsOf(path)
      const sections = q.get('sections') || ''
      if (sections.includes('filtre_actif') && q.get('secretariat_id') === '1') {
        return { kpis: { modules: 4, participants: 20, formateurs: 3, sessions_total: 12, pointages: 100, vh_prevu_heures: 300 }, pedagogiques: { taux_presence: 75, taux_absence: 25, taux_par_formation: [], taux_par_grade: [] }, admin_operationnel: { pointages_par_statut: [], participants_par_sexe: [], participants_par_categorie: [], charge_formateurs: [], auditeurs_notoires: { total: 1, pct: 5 } } }
      }
      return statsDataFor(q)
    })
    installStdRoutes()
    mountStats(adminMe())
    await screen.findByText('4 sections')
    fireEvent.click(tabButton('Secrétariats'))

    expect(await screen.findByText('2 secrétariats')).toBeInTheDocument()
    // Présents dans la sidebar ET dans le tableau comparatif.
    expect(screen.getAllByText('INJS Centre').length).toBeGreaterThan(1)
    expect(screen.getAllByText('INJS Marcory').length).toBeGreaterThan(1)
    expect(screen.getByText('M. Konan')).toBeInTheDocument()

    // Sélection du premier secrétariat dans la sidebar.
    fireEvent.click(screen.getByRole('button', { name: /INJS Centre.*prés\./ }))
    // Le détail demande bien les sections kpis/pedagogiques/admin pour ce secrétariat.
    await waitFor(() => {
      const q = dataCalls().at(-1)
      expect(q.get('secretariat_id')).toBe('1')
      expect(q.get('sections')).toContain('filtre_actif')
    })
    expect(await screen.findByText('Responsable : M. Konan')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Voir tous les secrétariats/ }))
    expect(await screen.findByText('2 secrétariats')).toBeInTheDocument()
  })
})

const SEUILS_CFG = [
  {
    id: 1, indicateur: 'taux_presence', libelle: 'Assiduité séance', icone: 'bi-people',
    seuil_avertissement: 70, seuil_critique: 50, actif: true,
  },
]
const INDICATEURS_CFG = [
  {
    indicateur: 'taux_presence', libelle: 'Assiduité séance', icone: 'bi-people',
    couleur: '#2277C1', niveau: 'critique', valeur: 42, unite: '%',
    seuil_avertissement: 70, seuil_critique: 50, inverse: true,
    configure: true, actif: true, aide: 'Assiduité des places présentes.', echelle_max: 100,
  },
]
const ALERTE_ACTIVE = {
  indicateur: 'saturation_groupe', libelle: 'Saturation groupe F1',
  niveau: 'critique', valeur: 110, unite: '%',
  seuil_avertissement: 90, seuil_critique: 100,
}

/** Routes pour l'onglet Alertes : `initialized` débute à true si seuils présents. */
function installSeuilsRoutes({ initialized = false } = {}) {
  apiController.reset()
  const state = { initialized }
  const seuilsPayload = () => ({
    seuils: state.initialized ? SEUILS_CFG : [],
    indicateurs: state.initialized ? INDICATEURS_CFG : [],
    synthese: state.initialized ? { ok: 4, avertissement: 0, critique: 1 } : {},
    seuils_vides: !state.initialized,
  })
  apiController.setRoute('/statistiques/alertes/seuils/', () => seuilsPayload())
  apiController.setRoute('/statistiques/', (path) => {
    const q = paramsOf(path)
    const sections = q.get('sections') || ''
    if (sections.includes('secretariats_liste')) {
      return { formations_liste: FORMATIONS, secretariats_liste: SECRETARIATS, filtre_actif: { scope_locked: false } }
    }
    const alerte = state.initialized ? [ALERTE_ACTIVE] : []
    return statsDataFor(q, { alertes: alerte, alertes_overview: alerte })
  })
  apiController.setRoute('/statistiques/point-journalier/', () => ({ tableaux: [], tableaux_complets: [] }))
  apiController.setRoute('/statistiques/bilans/', () => ({ bilans: [], tableaux_complets: [] }))
  apiController.setRoute('/statistiques/secretariats/', () => ({ secretariats: [], total: 0 }))
  return state
}

describe('Statistiques (LOT 38a) — alertes et configuration des seuils', () => {
  beforeEach(() => {
    apiController.reset()
    window.localStorage.clear()
    window.sessionStorage.clear()
    vi.restoreAllMocks()
  })

  it('état sans seuil : invite à l’initialisation INJS (administrateur)', async () => {
    installSeuilsRoutes({ initialized: false })
    mountStats(adminMe())
    await screen.findByText('4 sections')
    fireEvent.click(tabButton('Alertes'))

    expect(await screen.findByText('Initialiser les seuils INJS')).toBeInTheDocument()
    expect(screen.getByText('Init. INJS')).toBeInTheDocument()
    expect(screen.getByText(/Configurez les seuils/)).toBeInTheDocument()
    expect(screen.getByText('Tout est conforme')).toBeInTheDocument()
  })

  it('masque les actions de configuration pour un rôle non validant (encadrant)', async () => {
    installSeuilsRoutes({ initialized: false })
    mountStats(makeUser('ENCADRANT', { username: 'enc3' }))
    await screen.findByText('4 sections')
    fireEvent.click(tabButton('Alertes'))

    await screen.findByText('Tout est conforme')
    expect(screen.queryByText('Initialiser les seuils INJS')).not.toBeInTheDocument()
    expect(screen.queryByText('Init. INJS')).not.toBeInTheDocument()
  })

  it('POST l’initialisation des seuils puis recharge la configuration', async () => {
    const state = installSeuilsRoutes({ initialized: false })
    mountStats(adminMe())
    await screen.findByText('4 sections')
    fireEvent.click(tabButton('Alertes'))

    const cta = await screen.findByText('Initialiser les seuils INJS')
    apiMock.post.mockImplementationOnce(async () => {
      state.initialized = true
      return { data: {}, status: 200 }
    })
    fireEvent.click(cta.closest('button'))

    await waitFor(() => expect(apiMock.post).toHaveBeenCalledTimes(1))
    expect(apiMock.post.mock.calls[0][0]).toMatch(/^\/statistiques\/alertes\/seuils\//)
    // Le re-fetch des seuils fait apparaître le bouton Modifier.
    expect(await screen.findByText('Modifier')).toBeInTheDocument()
    // Et un re-fetch des données d'alertes a eu lieu.
    const dataWithAlertes = dataCalls().filter((q) =>
      (q.get('sections') || '').includes('alertes'))
    expect(dataWithAlertes.length).toBeGreaterThan(0)
  })

  it('affiche les alertes déclenchées et les compteurs de synthèse quand les seuils existent', async () => {
    installSeuilsRoutes({ initialized: true })
    mountStats(adminMe())
    await screen.findByText('4 sections')
    fireEvent.click(tabButton('Alertes'))

    expect(await screen.findByText('Saturation groupe F1')).toBeInTheDocument()
    expect(screen.getAllByText('110%').length).toBeGreaterThan(0)
    // Pilule de synthèse : 1 critique.
    const critLabel = screen.getByText('Critiques')
    expect(critLabel.parentElement).toHaveTextContent('1')
    // Sidebar : sous-texte « 1 alerte active ».
    expect(screen.getByText(/1 alerte active/)).toBeInTheDocument()
  })

  it('permet de modifier un seuil puis d’enregistrer (PUT) avec les nouvelles valeurs', async () => {
    installSeuilsRoutes({ initialized: true })
    mountStats(adminMe())
    await screen.findByText('4 sections')
    fireEvent.click(tabButton('Alertes'))

    // Ouvrir le widget détail « Configuration seuils » via la sidebar.
    fireEvent.click(await screen.findByRole('button', { name: /Configuration seuils/ }))
    fireEvent.click(await screen.findByRole('button', { name: /^Modifier$/ }))

    const numberInputs = screen.getAllByRole('spinbutton')
    expect(numberInputs.length).toBeGreaterThanOrEqual(2)
    fireEvent.change(numberInputs[0], { target: { value: '75' } }) // avertissement

    apiMock.put.mockImplementationOnce(async () => ({ data: {}, status: 200 }))
    fireEvent.click(screen.getByRole('button', { name: /Enregistrer/ }))

    await waitFor(() => expect(apiMock.put).toHaveBeenCalledTimes(1))
    expect(apiMock.put.mock.calls[0][0]).toMatch(/^\/statistiques\/alertes\/seuils\//)
    const body = apiMock.put.mock.calls[0][1]
    expect(Array.isArray(body)).toBe(true)
    expect(body[0].seuil_avertissement).toBe(75)
  })

  it('signale un échec d’initialisation des seuils via window.alert', async () => {
    installSeuilsRoutes({ initialized: false })
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    mountStats(adminMe())
    await screen.findByText('4 sections')
    fireEvent.click(tabButton('Alertes'))
    const cta = await screen.findByText('Initialiser les seuils INJS')

    apiMock.post.mockRejectedValueOnce({ response: { data: { detail: 'Init impossible' } } })
    fireEvent.click(cta.closest('button'))
    await waitFor(() => expect(alertSpy).toHaveBeenCalledWith('Init impossible'))
  })

  it('signale un échec de sauvegarde des seuils via window.alert', async () => {
    installSeuilsRoutes({ initialized: true })
    vi.spyOn(window, 'alert').mockImplementation(() => {})
    mountStats(adminMe())
    await screen.findByText('4 sections')
    fireEvent.click(tabButton('Alertes'))

    fireEvent.click(await screen.findByRole('button', { name: /Configuration seuils/ }))
    fireEvent.click(await screen.findByRole('button', { name: /^Modifier$/ }))
    apiMock.put.mockRejectedValueOnce({ response: { data: { detail: 'Sauvegarde KO' } } })
    fireEvent.click(screen.getByRole('button', { name: /Enregistrer/ }))
    await waitFor(() => expect(window.alert).toHaveBeenCalledWith('Sauvegarde KO'))
  })
})

describe('Statistiques (LOT 38a) — exports Point Journalier et Bilans', () => {
  let anchorClickSpy

  beforeEach(() => {
    apiController.reset()
    window.localStorage.clear()
    window.sessionStorage.clear()
    URL.createObjectURL = vi.fn(() => 'blob:test-export')
    URL.revokeObjectURL = vi.fn()
    anchorClickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    installStdRoutes()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  const pjPayload = () => ({
    total_tableaux: 1,
    categories: ['A'],
    formations: FORMATIONS,
    tableaux: PJ_TABLEAUX,
    // Pas de tableau complet en cache : le détail passera par un appel detail=1.
    tableaux_complets: [],
  })

  const pjWithDetail = (q) => {
    if (q.get('detail') === '1') {
      return { tableau: { date: `${CURRENT_YEAR}-09-15`, matin: null, soir: null } }
    }
    return pjPayload()
  }

  it('Point Journalier : export Excel annuel avec les filtres actifs', async () => {
    apiController.reset()
    installStdRoutes({ pj: pjWithDetail })
    apiMock.getBlob.mockResolvedValue({
      blob: new Blob(['x']), fileName: 'PJ.xlsx', contentType: 'application/vnd.ms-excel',
    })
    mountStats(adminMe())
    await screen.findByText('4 sections')
    fireEvent.click(tabButton('Point Journalier'))

    const excelBtn = await screen.findByRole('button', { name: 'Excel' })
    await waitFor(() => expect(excelBtn).not.toBeDisabled())
    fireEvent.click(excelBtn)

    await waitFor(() => expect(apiMock.getBlob).toHaveBeenCalledTimes(1))
    const url = apiMock.getBlob.mock.calls[0][0]
    expect(url).toMatch(/^\/statistiques\/point-journalier-export\/\?/)
    const q = paramsOf(url)
    expect(q.get('export')).toBe('xlsx')
    expect(q.get('annee')).toBe(String(CURRENT_YEAR))
    expect(q.get('jour')).toBe(null) // aucune ligne sélectionnée : export annuel
    expect(anchorClickSpy).toHaveBeenCalledTimes(1)
    expect(URL.createObjectURL).toHaveBeenCalled()
  })

  it('Point Journalier : export PDF du tableau sélectionné (jour / formation / catégorie)', async () => {
    apiController.reset()
    installStdRoutes({ pj: pjWithDetail })
    apiMock.getBlob.mockResolvedValue({ blob: new Blob(['p']), fileName: 'PJ.pdf' })
    mountStats(adminMe())
    await screen.findByText('4 sections')
    fireEvent.click(tabButton('Point Journalier'))

    // Ouvrir le tableau depuis la liste de gauche (entête avec date_fr).
    const entry = await screen.findByText('15/09/2026')
    fireEvent.click(entry.closest('button'))
    await waitFor(() => expect(callsTo('/statistiques/point-journalier/')
      .some((q) => q.get('detail') === '1')).toBe(true))

    fireEvent.click(screen.getByRole('button', { name: 'PDF' }))
    await waitFor(() => expect(apiMock.getBlob).toHaveBeenCalledTimes(1))
    const q = paramsOf(apiMock.getBlob.mock.calls[0][0])
    expect(q.get('export')).toBe('pdf')
    expect(q.get('jour')).toBe(`${CURRENT_YEAR}-09-15`)
    expect(q.get('formation_id')).toBe('10')
    expect(q.get('categorie')).toBe('A')
  })

  it('Point Journalier : un échec d’export déclenche window.alert sans planter', async () => {
    apiController.reset()
    installStdRoutes({ pj: () => pjPayload() })
    apiMock.getBlob.mockRejectedValue({ response: { data: { detail: 'Génération Excel KO' } } })
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    mountStats(adminMe())
    await screen.findByText('4 sections')
    fireEvent.click(tabButton('Point Journalier'))

    fireEvent.click(await screen.findByRole('button', { name: 'Word' }))
    await waitFor(() => expect(alertSpy).toHaveBeenCalledWith('Génération Excel KO'))
    // Les boutons sont de nouveau utilisables (état exporting remis à null).
    expect(screen.getByRole('button', { name: 'Excel' })).not.toBeDisabled()
  })

  it('Bilans : export Excel de la dimension module avec l’année et la dimension', async () => {
    apiController.reset()
    installStdRoutes({ bilans: () => ({
      total_bilans: 1,
      bilans: [{
        id: 'b1', dimension: 'module', libelle: 'Module Alpha', sous_titre: 'L1',
        module_id: 5, formation_id: 10, categorie: '—', inscrits: 12,
      }],
      tableaux_complets: [],
      modules: [{ id: 5, intitule: 'Alpha' }],
      formations: FORMATIONS,
    }) })
    apiMock.getBlob.mockResolvedValue({ blob: new Blob(['x']), fileName: 'B.xlsx' })
    mountStats(adminMe())
    await screen.findByText('4 sections')
    fireEvent.click(tabButton('Rapports & Bilans'))

    const excelBtn = await screen.findByRole('button', { name: 'Excel' })
    await waitFor(() => expect(excelBtn).not.toBeDisabled())
    fireEvent.click(excelBtn)
    await waitFor(() => expect(apiMock.getBlob).toHaveBeenCalledTimes(1))
    const q = paramsOf(apiMock.getBlob.mock.calls[0][0])
    expect(apiMock.getBlob.mock.calls[0][0]).toMatch(/^\/statistiques\/bilans-export\/\?/)
    expect(q.get('export')).toBe('xlsx')
    expect(q.get('dimension')).toBe('module')
    expect(q.get('annee')).toBe(String(CURRENT_YEAR))
  })

  it('Bilans : un échec d’export déclenche window.alert', async () => {
    apiController.reset()
    installStdRoutes({ bilans: () => ({
      total_bilans: 1,
      bilans: [{ id: 'b2', dimension: 'module', libelle: 'Module Beta', module_id: 6 }],
      tableaux_complets: [],
    }) })
    apiMock.getBlob.mockRejectedValue(new Error('réseau'))
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    mountStats(adminMe())
    await screen.findByText('4 sections')
    fireEvent.click(tabButton('Rapports & Bilans'))

    fireEvent.click(await screen.findByRole('button', { name: 'PDF' }))
    await waitFor(() => expect(alertSpy).toHaveBeenCalled())
    expect(alertSpy.mock.calls[0][0]).toMatch(/réseau|téléchargement/i)
  })

  it('reflète l’état d’export (spinner) pendant le téléchargement puis réactive les boutons', async () => {
    let resolveBlob
    const pending = new Promise((res) => { resolveBlob = res })
    apiController.reset()
    installStdRoutes({ pj: () => pjPayload() })
    apiMock.getBlob.mockReturnValue(pending)
    mountStats(adminMe())
    await screen.findByText('4 sections')
    fireEvent.click(tabButton('Point Journalier'))

    fireEvent.click(await screen.findByRole('button', { name: 'Excel' }))
    // Pendant l'export, les autres formats sont désactivés.
    await waitFor(() => expect(screen.getByRole('button', { name: 'PDF' })).toBeDisabled())

    resolveBlob({ blob: new Blob(['x']), fileName: 'PJ.xlsx' })
    await waitFor(() => expect(screen.getByRole('button', { name: 'PDF' })).not.toBeDisabled())
  })
})

// ════════════════════════════════════════════════════════════════════════════
// LOT 38b — Bilans INJS (4 dimensions, navigation liste ↔ détail, exports) et
// Bilan FAC complet (périmètre grades/groupes, génération, 4 sous-onglets,
// exports avec meta justificatifs/difficultés). Tests PURS : aucune
// modification de Statistiques.jsx.
// ════════════════════════════════════════════════════════════════════════════

const RB_CATS = ['A', 'B']
const RB_MODS = [
  { id: 5, intitule: 'Module Alpha' },
  { id: 6, intitule: 'Module Beta' },
]
const RB_MATS = [
  { intitule: 'Droit civil', ref_module_id: 5, formation_id: 10 },
  { intitule: 'Grammaire LSF', formation_id: 11 },
]

const RB_BILANS = {
  module: [
    {
      id: 'bm1', dimension: 'module', libelle: 'Module Alpha', sous_titre: 'Licence 1 LSF',
      module_id: 5, formation_id: 10, formation: 'Licence 1 LSF', module: 'Module Alpha',
      categorie: 'A', grade: 'A1', groupe: 'Groupe 1',
      inscrits: 12, nb_groupes: 1, nb_pointages: 40,
      annee: CURRENT_YEAR, periode_label: 'Toutes périodes',
    },
    {
      id: 'bm2', dimension: 'module', libelle: 'Module orphelin', sous_titre: 'sans identifiant',
      categorie: '—', inscrits: 5,
    },
  ],
  matiere: [
    {
      id: 'bma1', dimension: 'matiere', libelle: 'Droit civil', sous_titre: 'Licence 1 LSF',
      formation_id: 10, ref_module_id: 5, matiere_intitule: 'Droit civil',
      categorie: 'A', inscrits: 20, nb_groupes: 2,
    },
    {
      id: 'bma2', dimension: 'matiere', libelle: 'Grammaire LSF', sous_titre: 'Licence 2 LSF',
      formation_id: 11, matiere_intitule: 'Grammaire LSF',
      categorie: 'B', inscrits: 8,
    },
    {
      id: 'bma3', dimension: 'matiere', libelle: 'Matière orpheline', sous_titre: 'sans formation',
      categorie: '—', inscrits: 3,
    },
  ],
  categorie: [
    {
      id: 'bc1', dimension: 'categorie', libelle: 'Catégorie A', sous_titre: 'Toutes formations',
      categorie: 'A', inscrits: 30, nb_groupes: 4,
    },
    {
      id: 'bc2', dimension: 'categorie', libelle: 'Catégorie sans code', sous_titre: '—',
      categorie: '—',
    },
  ],
  formation: [
    {
      id: 'bf1', dimension: 'formation', libelle: 'Bilan Licence 1 LSF',
      sous_titre: 'Toutes périodes', formation_id: 10, formation: 'Licence 1 LSF',
      categorie: '—', annee: CURRENT_YEAR, periode_label: 'Toutes périodes',
    },
    {
      id: 'bf2', dimension: 'formation', libelle: 'Bilan sans formation', sous_titre: 'orphelin',
      categorie: '—',
    },
  ],
}

const EFF_FIXTURE = {
  effectifs_auditeurs: 1500, masculin_inscrits: 800, feminin_inscrits: 700,
  effectifs_presents: 1200, pct_presents_total: 80,
  masculin: 700, pct_masculin_presents: 58.33,
  feminin: 500, pct_feminin_presents: 41.67,
  absents: 300, pct_absents_total: 20,
}
const RB_TABLEAUX = {
  module: { type: 'effectifs_module', titre: 'EFFECTIFS — MODULE ALPHA', ...EFF_FIXTURE },
  matiere: { type: 'effectifs_matiere', titre: 'EFFECTIFS — DROIT CIVIL', nb_groupes: 2, ...EFF_FIXTURE },
  categorie: { type: 'effectifs_categorie', titre: 'EFFECTIFS — CATÉGORIE A', ...EFF_FIXTURE },
  formation: makeJTableau({
    titre: 'BILAN PÉRIODE — LICENCE 1 LSF', formation_id: 10,
    lignes: [{ categorie: 'A', totaux: jStats }],
  }),
}

const rbCacheEntry = (bilan, tableau) => ({ bilan_id: bilan.id, bilan, tableau })

function rbPayload(dim, liste, entries = []) {
  return {
    total_bilans: liste.length,
    bilans: liste,
    tableaux_complets: entries,
    categories: RB_CATS,
    modules: RB_MODS,
    matieres: RB_MATS,
    formations: FORMATIONS,
    filtres_actifs: { annee: CURRENT_YEAR, periode_label: 'Toutes périodes' },
  }
}

/**
 * Route `/statistiques/bilans/` : renvoie la liste adaptée à `dimension` et,
 * pour `detail=1`, le tableau ciblé via `detailFor(q)` (null par défaut).
 */
function rbRoute({ detailFor = () => null, bilansFor } = {}) {
  return (q) => {
    if (q.get('detail') === '1') return { tableau: detailFor(q) }
    const dim = q.get('dimension') || 'module'
    const liste = bilansFor ? bilansFor(q, dim) : (RB_BILANS[dim] || [])
    return rbPayload(dim, liste)
  }
}

/** Ouvre l'onglet Rapports & Bilans (vue « Bilans INJS » par défaut). */
async function openRapports() {
  mountStats(adminMe())
  await screen.findByText('4 sections')
  fireEvent.click(tabButton('Rapports & Bilans'))
}

/** Select de la barre de filtres bilans identifié par le libellé d'une option. */
const rbOptionSelect = (optionName) =>
  screen.getByRole('option', { name: optionName }).closest('select')

const dimensionBtn = (label) => screen.getByRole('button', { name: label })
const bilanCalls = () => callsTo('/statistiques/bilans/')
const listCalls = () => bilanCalls().filter((q) => q.get('detail') !== '1')
const detailCalls = () => bilanCalls().filter((q) => q.get('detail') === '1')

describe('Statistiques (LOT 38b) — Bilans INJS : liste, dimensions et filtres', () => {
  beforeEach(() => {
    apiController.reset()
    window.localStorage.clear()
    window.sessionStorage.clear()
    installStdRoutes({ bilans: rbRoute() })
  })

  it('charge les bilans en dimension module avec tous les filtres de base (tous_tableaux=1)', async () => {
    await openRapports()

    expect(await screen.findByRole('button', { name: /Module Alpha/ })).toBeInTheDocument()
    const q = listCalls().at(-1)
    expect(q.get('annee')).toBe(String(CURRENT_YEAR))
    expect(q.get('dimension')).toBe('module')
    expect(q.get('tous_tableaux')).toBe('1')
    expect(q.get('mois')).toBe(null)
    expect(q.get('periode')).toBe(null)

    // En-tête de la sidebar et libellés des lignes.
    expect(screen.getByText(/2 bilans? · Par Module/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Tous les tableaux/ })).toHaveTextContent('2')
    expect(screen.getAllByText('MOD')).toHaveLength(2) // un badge par ligne module
    expect(screen.getByText(/Grade A1/)).toBeInTheDocument()
    expect(screen.getByText(/Groupe 1/)).toBeInTheDocument()
    expect(screen.getByText(/12 inscrits · 1 groupe · 40 pointages/)).toBeInTheDocument()
  })

  it('bascule entre les 4 dimensions et requête la bonne valeur de dimension', async () => {
    await openRapports()
    await screen.findByRole('button', { name: /Module Alpha/ })

    fireEvent.click(dimensionBtn('Par Catégorie'))
    expect(await screen.findByRole('button', { name: /Catégorie A/ })).toBeInTheDocument()
    await waitFor(() => expect(listCalls().at(-1).get('dimension')).toBe('categorie'))

    fireEvent.click(dimensionBtn('Par Formation'))
    expect(await screen.findByRole('button', { name: /Bilan Licence 1 LSF/ })).toBeInTheDocument()
    await waitFor(() => expect(listCalls().at(-1).get('dimension')).toBe('formation'))

    fireEvent.click(dimensionBtn('Par Matière'))
    expect((await screen.findAllByText('MAT')).length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: /Droit civil/ })).toBeInTheDocument()
    await waitFor(() => {
      const q = listCalls().at(-1)
      expect(q.get('dimension')).toBe('matiere')
      expect(q.get('module_id')).toBe(null) // aucun module_id en dimension matière
    })
    // Le sélecteur de module est remplacé par celui des matières.
    expect(screen.queryByRole('option', { name: 'Tous modules' })).not.toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Toutes matières' })).toBeInTheDocument()

    fireEvent.click(dimensionBtn('Par Module'))
    await waitFor(() => expect(listCalls().at(-1).get('dimension')).toBe('module'))
    expect(screen.getByRole('option', { name: 'Tous modules' })).toBeInTheDocument()
  })

  it('porte les filtres mois, catégorie, module, période et calendrier prévisionnel', async () => {
    await openRapports()
    await screen.findByRole('button', { name: /Module Alpha/ })

    fireEvent.change(rbOptionSelect('Septembre'), { target: { value: '9' } })
    await waitFor(() => expect(listCalls().at(-1).get('mois')).toBe('9'))

    fireEvent.change(rbOptionSelect('Cat. A'), { target: { value: 'A' } })
    await waitFor(() => expect(listCalls().at(-1).get('categorie')).toBe('A'))

    fireEvent.change(rbOptionSelect('Module Alpha'), { target: { value: '5' } })
    await waitFor(() => expect(listCalls().at(-1).get('module_id')).toBe('5'))

    fireEvent.change(rbOptionSelect('Mensuel'), { target: { value: 'MENSUEL' } })
    await waitFor(() => expect(listCalls().at(-1).get('periode')).toBe('MENSUEL'))

    const dateInput = document.querySelector('input[type="date"][title="Calendrier prévisionnel"]')
    fireEvent.change(dateInput, { target: { value: '2026-09-01' } })
    await waitFor(() => expect(listCalls().at(-1).get('calendrier')).toBe('2026-09-01'))
  })

  it('change l’année du bilan et répercute la valeur sur la requête', async () => {
    await openRapports()
    await screen.findByRole('button', { name: /Module Alpha/ })

    const anneeSel = screen.getByRole('option', { name: String(CURRENT_YEAR + 1) }).closest('select')
    fireEvent.change(anneeSel, { target: { value: String(CURRENT_YEAR + 1) } })
    await waitFor(() => expect(listCalls().at(-1).get('annee')).toBe(String(CURRENT_YEAR + 1)))
  })

  it('filtre par formation (sélecteur bilans) et transmet formation_id', async () => {
    await openRapports()
    await screen.findByRole('button', { name: /Module Alpha/ })

    // Le select bilans porte « Toutes formations » (sans « les »), distinct du
    // sélecteur global d'en-tête « Toutes les formations ».
    fireEvent.change(rbOptionSelect('Toutes formations'), { target: { value: '11' } })
    await waitFor(() => expect(listCalls().at(-1).get('formation_id')).toBe('11'))
  })

  it('dimension matière : porte ref_module_id pour une matière référencée (clé r:id)', async () => {
    await openRapports()
    await screen.findByRole('button', { name: /Module Alpha/ })

    fireEvent.click(dimensionBtn('Par Matière'))
    await screen.findByText('Droit civil')

    fireEvent.change(rbOptionSelect('Droit civil'), { target: { value: 'r:5' } })
    await waitFor(() => {
      const q = listCalls().at(-1)
      expect(q.get('ref_module_id')).toBe('5')
      expect(q.get('module_id')).toBe(null)
    })
  })

  it('dimension matière : les options matière sont filtrées selon la formation choisie', async () => {
    await openRapports()
    await screen.findByRole('button', { name: /Module Alpha/ })
    fireEvent.click(dimensionBtn('Par Matière'))
    await screen.findByText('Droit civil')

    const matiereSel = screen.getByRole('option', { name: 'Toutes matières' }).closest('select')
    expect(Array.from(matiereSel.options).map((o) => o.textContent)).toContain('Droit civil')

    fireEvent.change(rbOptionSelect('Toutes formations'), { target: { value: '11' } })
    await waitFor(() => {
      const options = Array.from(matiereSel.options).map((o) => o.textContent)
      expect(options).not.toContain('Droit civil') // formation_id 10
      expect(options).toContain('Grammaire LSF') // formation_id 11
    })
  })

  it('réinitialise la sélection quand un filtre change (retour à la vue d’ensemble)', async () => {
    await openRapports()
    await screen.findByRole('button', { name: /Module Alpha/ })

    // Ouvrir un bilan en détail (tableau en cache ci-dessous simulé par la
    // même route renvoyant le tableau en détail).
    fireEvent.click(screen.getByRole('button', { name: /Module Alpha/ }))
    await waitFor(() => expect(detailCalls().length).toBeGreaterThan(0))
    expect(screen.getByRole('button', { name: /Voir tous les tableaux/ })).toBeInTheDocument()

    fireEvent.change(rbOptionSelect('Mensuel'), { target: { value: 'MENSUEL' } })
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: /Voir tous les tableaux/ })).not.toBeInTheDocument())
  })

  it('le bouton Actualiser de la barre bilans relance le chargement', async () => {
    await openRapports()
    await screen.findByRole('button', { name: /Module Alpha/ })
    const avant = listCalls().length
    expect(avant).toBeGreaterThan(0)

    // En onglet rapports : 1 bouton Actualiser global (en-tête) + 1 bilans.
    const btns = screen.getAllByRole('button', { name: /Actualiser/ })
    fireEvent.click(btns[btns.length - 1])
    await waitFor(() => expect(listCalls().length).toBeGreaterThan(avant))
  })

  it('affiche l’état vide « Aucun bilan » quand la liste revient vide, avec exports désactivés', async () => {
    apiController.reset()
    installStdRoutes({
      bilans: () => ({
        total_bilans: 0, bilans: [], tableaux_complets: [],
        categories: [], modules: [], matieres: [], formations: FORMATIONS,
      }),
    })
    await openRapports()
    expect(await screen.findByText('Aucun bilan pour cette sélection')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Excel' })).toBeDisabled()
  })
})

describe('Statistiques (LOT 38b) — Bilans INJS : vue d’ensemble et détails par type de tableau', () => {
  beforeEach(() => {
    apiController.reset()
    window.localStorage.clear()
    window.sessionStorage.clear()
  })

  it('vue d’ensemble : rend tous les tableaux complets et la navigation « Plein écran »', async () => {
    const liste = [
      { id: 'm1', dimension: 'module', libelle: 'Module Alpha', sous_titre: 'G1', module_id: 5, formation_id: 10, categorie: 'A' },
      { id: 'm2', dimension: 'module', libelle: 'Module Beta', sous_titre: 'G2', module_id: 6, formation_id: 10, categorie: 'A' },
    ]
    const entries = [
      rbCacheEntry(liste[0], RB_TABLEAUX.module),
      rbCacheEntry(liste[1], { ...RB_TABLEAUX.module, titre: 'EFFECTIFS — MODULE BETA' }),
    ]
    // La route bilans (avec tableaux complets) est enregistrée AVANT les
    // routes standard : la première route enregistrée est prioritaire.
    apiController.setRoute('/statistiques/bilans/', (path) => {
      const q = paramsOf(path)
      if (q.get('detail') === '1') return { tableau: null }
      return rbPayload('module', liste, entries)
    })
    installStdRoutes()

    await openRapports()
    expect(await screen.findByText('2 tableaux — Par Module')).toBeInTheDocument()
    expect(screen.getByText('EFFECTIFS — MODULE ALPHA')).toBeInTheDocument()
    expect(screen.getByText('EFFECTIFS — MODULE BETA')).toBeInTheDocument()
    expect(screen.getByText(/Vue d'ensemble \(2026/)).toBeInTheDocument()

    // Plein écran sur le deuxième tableau : sélection retrouvée par identifiant.
    const pleinEcran = screen.getAllByRole('button', { name: /Plein écran/ })
    fireEvent.click(pleinEcran[1])
    expect(await screen.findByRole('button', { name: /Voir tous les tableaux/ })).toBeInTheDocument()
    expect(screen.getByText('EFFECTIFS — MODULE BETA')).toBeInTheDocument()
    // Le cache évite tout appel detail=1.
    expect(detailCalls().length).toBe(0)

    fireEvent.click(screen.getByRole('button', { name: /Voir tous les tableaux/ }))
    expect(await screen.findByText('2 tableaux — Par Module')).toBeInTheDocument()
  })

  it('vue d’ensemble : message spécifique si aucun tableau complet n’est renvoyé', async () => {
    installStdRoutes({ bilans: rbRoute() })
    await openRapports()
    expect(await screen.findByText('Aucun tableau à afficher pour cette sélection')).toBeInTheDocument()
  })

  it('détail module (cache) : tableau d’effectifs avec formatage français milliers et pourcentages', async () => {
    const liste = RB_BILANS.module
    installStdRoutes({
      bilans: (path) => {
        const q = paramsOf(path)
        if (q.get('detail') === '1') return { tableau: RB_TABLEAUX.module }
        return rbPayload('module', liste, [rbCacheEntry(liste[0], RB_TABLEAUX.module)])
      },
    })
    await openRapports()
    fireEvent.click(await screen.findByRole('button', { name: /Module Alpha/ }))

    expect(await screen.findByText('EFFECTIFS — MODULE ALPHA')).toBeInTheDocument()
    // Les en-têtes contiennent des <br/> : les cibler par nom accessible (role).
    expect(screen.getByRole('columnheader', { name: /EFFECTIFS DES AUDITEURS/ })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: /^EFFECTIFS PRESENTS$/ })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'MASCULIN' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'FEMININ' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'ABSENTS' })).toBeInTheDocument()
    // 1500 formaté avec le séparateur de milliers français (espace/insécable).
    expect(screen.getByText(/1\s?500/)).toBeInTheDocument()
    expect(screen.getByText(/800 H \/ 700 F inscrits/)).toBeInTheDocument()
    // Pourcentage en virgule, 2 décimales (l'apostrophe du libellé est droite).
    expect(screen.getByText(/80,00% de l'effectif total/)).toBeInTheDocument()
    expect(screen.getByText(/20,00% de l'effectif total/)).toBeInTheDocument()
  })

  it('détail matière : bandeau d’agrégation des groupes puis tableau d’effectifs', async () => {
    const liste = RB_BILANS.matiere
    installStdRoutes({
      bilans: (path) => {
        const q = paramsOf(path)
        if (q.get('detail') === '1') return { tableau: RB_TABLEAUX.matiere }
        return rbPayload('matiere', liste, [rbCacheEntry(liste[0], RB_TABLEAUX.matiere)])
      },
    })
    await openRapports()
    fireEvent.click(dimensionBtn('Par Matière'))
    fireEvent.click(await screen.findByRole('button', { name: /Droit civil/ }))

    // Texte fragmenté par un <strong> : matcher fonction sur le <p>.
    expect(screen.getByText(
      (_content, el) => el?.tagName === 'P' && /Agrégation de 2 groupes/.test(el.textContent),
    )).toBeInTheDocument()
    expect(screen.getByText('EFFECTIFS — DROIT CIVIL')).toBeInTheDocument()
  })

  it('détail catégorie : tableau d’effectifs', async () => {
    const liste = RB_BILANS.categorie
    installStdRoutes({
      bilans: (path) => {
        const q = paramsOf(path)
        if (q.get('detail') === '1') return { tableau: RB_TABLEAUX.categorie }
        return rbPayload('categorie', liste, [rbCacheEntry(liste[0], RB_TABLEAUX.categorie)])
      },
    })
    await openRapports()
    fireEvent.click(dimensionBtn('Par Catégorie'))
    fireEvent.click(await screen.findByRole('button', { name: /Catégorie A/ }))

    expect(await screen.findByText('EFFECTIFS — CATÉGORIE A')).toBeInTheDocument()
    expect(detailCalls().length).toBe(0) // servi depuis le cache
  })

  it('détail formation : modèle INJS bilan de période avec textarea justificatifs synchronisable', async () => {
    const liste = RB_BILANS.formation
    installStdRoutes({
      bilans: (path) => {
        const q = paramsOf(path)
        if (q.get('detail') === '1') return { tableau: RB_TABLEAUX.formation }
        return rbPayload('formation', liste, [rbCacheEntry(liste[0], RB_TABLEAUX.formation)])
      },
    })
    await openRapports()
    fireEvent.click(dimensionBtn('Par Formation'))
    fireEvent.click(await screen.findByRole('button', { name: /Bilan Licence 1 LSF/ }))

    expect(await screen.findByText('BILAN PÉRIODE — LICENCE 1 LSF')).toBeInTheDocument()
    expect(screen.getByText("NBRE D'ENCADRANTS")).toBeInTheDocument()
    const zone = screen.getByPlaceholderText(/saisir les justificatifs/i)
    expect(zone).toBeInTheDocument()

    // La saisie est bien remontée au parent (servira à l'export) : la valeur
    // reste affichée après frappe.
    fireEvent.change(zone, { target: { value: 'Report de séance pour cause d’intempéries' } })
    expect(zone.value).toBe('Report de séance pour cause d’intempéries')
  })

  it('détail sans cache : appelle l’API avec detail=1 et les bonnes clés (module)', async () => {
    installStdRoutes({
      bilans: rbRoute({ detailFor: () => RB_TABLEAUX.module }),
    })
    await openRapports()
    fireEvent.click(await screen.findByRole('button', { name: /Module Alpha/ }))

    await waitFor(() => expect(detailCalls().length).toBe(1))
    const q = detailCalls()[0]
    expect(q.get('detail')).toBe('1')
    expect(q.get('dimension')).toBe('module')
    expect(q.get('module_id')).toBe('5')
    expect(q.get('formation_id')).toBe('10')
    expect(q.get('categorie')).toBe('A')
    expect(await screen.findByText('EFFECTIFS — MODULE ALPHA')).toBeInTheDocument()
  })

  it('détail matière sans cache : transmet ref_module_id et matiere_intitule', async () => {
    installStdRoutes({
      bilans: rbRoute({
        detailFor: (q) => (q.get('matiere_intitule') === 'Grammaire LSF'
          ? { ...RB_TABLEAUX.matiere, nb_groupes: 1, titre: 'EFFECTIFS — GRAMMAIRE LSF' }
          : RB_TABLEAUX.matiere),
      }),
    })
    await openRapports()
    fireEvent.click(dimensionBtn('Par Matière'))
    fireEvent.click(await screen.findByRole('button', { name: /Grammaire LSF/ }))

    await waitFor(() => expect(detailCalls().length).toBe(1))
    const q = detailCalls()[0]
    expect(q.get('dimension')).toBe('matiere')
    expect(q.get('formation_id')).toBe('11')
    expect(q.get('matiere_intitule')).toBe('Grammaire LSF')
    expect(q.get('ref_module_id')).toBe(null) // matière sans module de référence (clé i:)
    expect(await screen.findByText('EFFECTIFS — GRAMMAIRE LSF')).toBeInTheDocument()
  })

  it('garde-fous : un bilan mal identifié n’émet aucun appel detail=1', async () => {
    const liste = [
      RB_BILANS.module[1], // module sans module_id
      RB_BILANS.matiere[2], // matière sans formation_id
      RB_BILANS.categorie[1], // catégorie '—'
      RB_BILANS.formation[1], // formation sans formation_id
      { id: 'bx', dimension: 'inconnue', libelle: 'Bilan étrange', sous_titre: 'dimension inconnue', categorie: 'A' },
    ]
    installStdRoutes({ bilans: rbRoute({ bilansFor: () => liste }) })
    await openRapports()

    // Module / matière / catégorie sans clé : message « aucune séance ».
    fireEvent.click(await screen.findByRole('button', { name: /Module orphelin/ }))
    expect(await screen.findByText(/Aucune séance comptabilisable/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Matière orpheline/ }))
    expect(await screen.findByText(/Aucune séance comptabilisable/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Catégorie sans code/ }))
    expect(await screen.findByText(/Aucune séance comptabilisable/)).toBeInTheDocument()

    // Formation sans id et dimension inconnue : carte de secours « Zone tableau bilan ».
    fireEvent.click(screen.getByRole('button', { name: /Bilan sans formation/ }))
    expect(await screen.findByText('Zone tableau bilan')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Bilan étrange/ }))
    expect(await screen.findByText('Zone tableau bilan')).toBeInTheDocument()
    expect(screen.getByText('BILAN — INCONNUE')).toBeInTheDocument()

    expect(detailCalls().length).toBe(0)
  })

  it('carte de secours pour un type de tableau non modélisé, avec les chips de contexte', async () => {
    const liste = [RB_BILANS.module[0]]
    installStdRoutes({
      bilans: (path) => {
        const q = paramsOf(path)
        if (q.get('detail') === '1') return { tableau: { type: 'autre_modele' } }
        return rbPayload('module', liste, [rbCacheEntry(liste[0], { type: 'autre_modele' })])
      },
    })
    await openRapports()
    fireEvent.click(await screen.findByRole('button', { name: /Module Alpha/ }))

    expect(await screen.findByText('Zone tableau bilan')).toBeInTheDocument()
    expect(screen.getByText('BILAN — PAR MODULE')).toBeInTheDocument()
    expect(screen.getByText(/Le modèle INJS pour ce bilan/)).toBeInTheDocument()
    // Le libellé et le sous-titre sont repris dans l'en-tête ET dans la grille
    // de contexte de la carte (d'où 2 occurrences chacun, sans compter les
    // <option> des sélecteurs qui sont hors de la carte).
    // <p> « Zone tableau bilan » → div jaune → carte de secours (2 niveaux).
    const fallbackCard = screen.getByText('Zone tableau bilan').parentElement.parentElement
    expect(within(fallbackCard).getAllByText('Module Alpha').length).toBeGreaterThanOrEqual(2)
    expect(within(fallbackCard).getAllByText('Licence 1 LSF').length).toBeGreaterThanOrEqual(2)
  })
})

describe('Statistiques (LOT 38b) — Bilans INJS : exports filtrés', () => {
  let anchorCreateSpy

  beforeEach(() => {
    apiController.reset()
    window.localStorage.clear()
    window.sessionStorage.clear()
    URL.createObjectURL = vi.fn(() => 'blob:rb-export')
    URL.revokeObjectURL = vi.fn()
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    anchorCreateSpy = vi.spyOn(document, 'createElement')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  const rbExportButton = (label) => document.querySelector(`button[title="Exporter les bilans filtrés (${label})"]`)

  it('export PDF d’un module sélectionné : module_id, formation_id et catégorie ciblés', async () => {
    installStdRoutes({ bilans: rbRoute() })
    apiMock.getBlob.mockResolvedValue({ blob: new Blob(['p']), fileName: 'B.pdf' })
    await openRapports()
    fireEvent.click(await screen.findByRole('button', { name: /Module Alpha/ }))
    await waitFor(() => expect(detailCalls().length).toBeGreaterThan(0))

    fireEvent.click(rbExportButton('PDF'))
    await waitFor(() => expect(apiMock.getBlob).toHaveBeenCalledTimes(1))
    const q = paramsOf(apiMock.getBlob.mock.calls[0][0])
    expect(apiMock.getBlob.mock.calls[0][0]).toMatch(/^\/statistiques\/bilans-export\/\?/)
    expect(q.get('export')).toBe('pdf')
    expect(q.get('dimension')).toBe('module')
    expect(q.get('module_id')).toBe('5')
    expect(q.get('formation_id')).toBe('10')
    expect(q.get('categorie')).toBe('A')
  })

  it('export Excel d’une matière (clé i:) : matiere_intitule sans module_id', async () => {
    installStdRoutes({ bilans: rbRoute() })
    apiMock.getBlob.mockResolvedValue({ blob: new Blob(['x']) })
    await openRapports()
    fireEvent.click(dimensionBtn('Par Matière'))
    fireEvent.click(await screen.findByRole('button', { name: /Grammaire LSF/ }))
    await waitFor(() => expect(detailCalls().length).toBe(1))

    fireEvent.click(rbExportButton('Excel'))
    await waitFor(() => expect(apiMock.getBlob).toHaveBeenCalledTimes(1))
    const q = paramsOf(apiMock.getBlob.mock.calls[0][0])
    expect(q.get('dimension')).toBe('matiere')
    expect(q.get('matiere_intitule')).toBe('Grammaire LSF')
    expect(q.get('formation_id')).toBe('11')
    expect(q.get('ref_module_id')).toBe(null)
    expect(q.get('module_id')).toBe(null)
  })

  it('export Word d’un bilan formation avec les justificatifs saisis', async () => {
    const liste = RB_BILANS.formation
    installStdRoutes({
      bilans: (path) => {
        const q = paramsOf(path)
        if (q.get('detail') === '1') return { tableau: RB_TABLEAUX.formation }
        return rbPayload('formation', liste, [rbCacheEntry(liste[0], RB_TABLEAUX.formation)])
      },
    })
    apiMock.getBlob.mockResolvedValue({ blob: new Blob(['d']) })
    await openRapports()
    fireEvent.click(dimensionBtn('Par Formation'))
    fireEvent.click(await screen.findByRole('button', { name: /Bilan Licence 1 LSF/ }))
    expect(await screen.findByText('BILAN PÉRIODE — LICENCE 1 LSF')).toBeInTheDocument()

    const zone = screen.getByPlaceholderText(/saisir les justificatifs/i)
    fireEvent.change(zone, { target: { value: 'Justif export bilans' } })

    fireEvent.click(rbExportButton('Word'))
    await waitFor(() => expect(apiMock.getBlob).toHaveBeenCalledTimes(1))
    const q = paramsOf(apiMock.getBlob.mock.calls[0][0])
    expect(q.get('export')).toBe('docx')
    expect(q.get('formation_id')).toBe('10')
    expect(q.get('justificatifs')).toBe('Justif export bilans')
  })

  it('utilise le nom de fichier par défaut BILANS_<année>.xlsx si le backend n’en fournit pas', async () => {
    installStdRoutes({ bilans: rbRoute() })
    apiMock.getBlob.mockResolvedValue({ blob: new Blob(['x']) }) // pas de fileName
    await openRapports()
    await screen.findByRole('button', { name: /Module Alpha/ })

    fireEvent.click(rbExportButton('Excel'))
    await waitFor(() => expect(apiMock.getBlob).toHaveBeenCalledTimes(1))
    const anchors = anchorCreateSpy.mock.results
      .map((r) => r.value)
      .filter((el) => el && el.tagName === 'A')
    expect(anchors.at(-1).download).toBe(`BILANS_${CURRENT_YEAR}.xlsx`)
  })

  it('un échec d’export bilans signale une alerte sans bloquer les boutons', async () => {
    installStdRoutes({ bilans: rbRoute() })
    apiMock.getBlob.mockRejectedValue({ response: { data: { detail: 'Export bilans indisponible' } } })
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    await openRapports()
    await screen.findByRole('button', { name: /Module Alpha/ })

    fireEvent.click(rbExportButton('PDF'))
    await waitFor(() => expect(alertSpy).toHaveBeenCalledWith('Export bilans indisponible'))
    expect(rbExportButton('Excel')).not.toBeDisabled()
  })
})

// ── Bilan FAC ─────────────────────────────────────────────────────────────────

const FAC_PERIMETRE = {
  grades: ['A1', 'A2'],
  groupes: [
    { id: 'g1', grade: 'A1', groupe: 'Groupe 1' },
    { id: 'g2', grade: 'A1', groupe: 'Groupe 2' },
    { id: 'g3', grade: 'A2', groupe: 'Groupe 1' },
  ],
}

function facLigne(grade, vals = {}) {
  return {
    grade,
    effectif_secretariat: 2, nb_encadrants: 2, nb_groupes: 1,
    effectif_auditeurs: 40, absents_notoires: 4, groupes_termines: 0,
    taux_participation: 90, taux_absents_notoires: 10,
    vh_total: 600, vh_epuise: 300, taux_exec_vh: 50,
    taux_presence_cours: 88, taux_absence_cours: 12,
    ...vals,
  }
}

const FAC_DATA = {
  titre: 'BILAN FORMATION — LICENCE 1 LSF',
  formation: 'Licence 1 LSF',
  formation_id: 10,
  annee: CURRENT_YEAR,
  grades: ['A1', 'A2'],
  date_generation: '12/09/2026',
  absents_notoires: [],
  point_global: {
    lignes: [
      facLigne('A1'),
      facLigne('A2', {
        nb_groupes: 2, effectif_auditeurs: 30, absents_notoires: 3,
        vh_total: 400, vh_epuise: 100, taux_exec_vh: 25,
      }),
    ],
    totaux: {
      effectif_secretariat: 4, nb_encadrants: 4, nb_groupes: 3,
      effectif_auditeurs: 70, absents_notoires: 7, groupes_termines: 1,
      vh_total: 1000, vh_epuise: 400, taux_exec_vh: 40,
    },
  },
  vh_par_grade: [
    {
      grade: 'A1',
      recap: { vh_prevu: 300, vh_epuise: 150, taux_execution: 50, vh_restant: 150, taux_restant: 50 },
      // Deux entrées « Groupe 1 » en doublon : l'UI doit les agréger (150 prévu).
      groupes: [
        { groupe: 'Groupe 1', vh_prevu: 100, vh_epuise: 50, vh_restant: 50, taux_execution: 50, taux_restant: 50 },
        { groupe: 'Groupe 1', vh_prevu: 50, vh_epuise: 25, vh_restant: 25, taux_execution: 50, taux_restant: 50 },
        { groupe: 'Groupe 2', vh_prevu: 150, vh_epuise: 75, vh_restant: 75, taux_execution: 50, taux_restant: 50 },
      ],
    },
    {
      grade: 'A2',
      recap: { vh_prevu: 200, vh_epuise: 50, taux_execution: 25, vh_restant: 150, taux_restant: 75 },
      groupes: [
        { groupe: 'Groupe 1', vh_prevu: 200, vh_epuise: 50, vh_restant: 150, taux_execution: 25, taux_restant: 75 },
      ],
    },
  ],
  modules_statuts: [
    { id: 1, intitule: 'Module Alpha', grade: 'A1', groupe: 'Groupe 1', vh_prevu: 100, vh_restant: 0, date_debut: '01/09/2026', date_fin: '30/09/2026', statut: 'TERMINEE' },
    { id: 2, intitule: 'Module Beta', grade: 'A1', groupe: 'Groupe 2', vh_prevu: 100, vh_restant: 60, date_debut: '05/09/2026', date_fin: '', statut: 'EN_COURS' },
    { id: 3, intitule: 'Module Gamma', grade: 'A2', groupe: 'Groupe 1', vh_prevu: 80, vh_restant: 80, date_debut: '', date_fin: '', statut: 'PLANIFIEE' },
    { id: 4, intitule: 'Module Delta', grade: 'A2', groupe: 'Groupe 1', vh_prevu: 80, vh_restant: 80, date_debut: '', date_fin: '', statut: 'SUSPENDUE' },
  ],
}

const FAC_ABSENT = {
  numero: 1, matricule: 'MC-001', nom: 'KOUASSI', prenom: 'Jean',
  libelle_concours: 'Concours INJS 2024', contacts: '0700000000',
  grade: 'A1', groupe: 'Groupe 1', observations: 'Maladie longue durée',
}

/**
 * Installe les routes Bilan FAC AVANT les routes standard (1re route
 * enregistrée prioritaire). `bilan`/`perimetre` sont des fonctions ou valeurs.
 */
function installFacRoutes({ perimetre, fac, bilansFn } = {}) {
  apiController.reset()
  apiController.setRoute('/statistiques/bilan-fac/perimetre/', (path) => {
    const v = typeof perimetre === 'function' ? perimetre(paramsOf(path)) : perimetre
    return v === undefined ? FAC_PERIMETRE : v
  })
  apiController.setRoute('/statistiques/bilan-fac/', (path) => {
    const v = typeof fac === 'function' ? fac(paramsOf(path)) : fac
    return v === undefined ? FAC_DATA : v
  })
  installStdRoutes(bilansFn ? { bilans: bilansFn } : { bilans: rbRoute() })
}

const facToggleButton = () => screen.getByRole('button', { name: /Bilan formation/ })
const facFormationSelect = () => screen.getByRole('option', { name: '— Sélectionner —' }).closest('select')
const facFieldSelect = (label) => screen.getByText(label).closest('div').querySelector('select')
const facGenerateButton = () => screen.getByRole('button', { name: /Générer le bilan/ })
const facExportButton = (label) => document.querySelector(`button[title="Exporter le bilan FAC (${label})"]`)
const perimetreCalls = () => callsTo('/statistiques/bilan-fac/perimetre/')
const facDataCalls = () => callsTo('/statistiques/bilan-fac/')

async function openFacAndSelectFormation(formationValue = '10') {
  fireEvent.click(facToggleButton())
  // Le libellé existe aussi dans le placeholder : cibler le bouton.
  expect(await screen.findByRole('button', { name: /Générer le bilan/ })).toBeInTheDocument()
  fireEvent.change(facFormationSelect(), { target: { value: formationValue } })
  await screen.findByText('Périmètre — grades et groupes')
  await screen.findByLabelText('A1')
}

describe('Statistiques (LOT 38b) — Bilan FAC : panneau, périmètre et garde-fous', () => {
  beforeEach(() => {
    apiController.reset()
    window.localStorage.clear()
    window.sessionStorage.clear()
    installFacRoutes()
  })

  it('panneau replié : aucune requête FAC ; ouvert sans formation : placeholder et bouton désactivé', async () => {
    await openRapports()
    expect(perimetreCalls().length).toBe(0)
    expect(screen.queryByText(/Générer le bilan/)).not.toBeInTheDocument()

    fireEvent.click(facToggleButton())
    expect(await screen.findByText(/Sélectionnez une formation et cliquez sur/)).toBeInTheDocument()
    expect(perimetreCalls().length).toBe(0) // garde-fou : pas de formation
    expect(screen.queryByText('Périmètre — grades et groupes')).not.toBeInTheDocument()
    expect(facGenerateButton()).toBeDisabled()
    expect(facExportButton('Excel')).toBe(null) // aucun export tant que pas de bilan

    // Repli / déploiement.
    fireEvent.click(facToggleButton())
    expect(screen.queryByText(/Sélectionnez une formation/)).not.toBeInTheDocument()
    fireEvent.click(facToggleButton())
    expect(await screen.findByText(/Sélectionnez une formation/)).toBeInTheDocument()
  })

  it('charge le périmètre (grades + groupes) dès la sélection d’une formation, tout coché', async () => {
    await openRapports()
    await openFacAndSelectFormation('10')

    expect(perimetreCalls().at(-1).get('formation_id')).toBe('10')
    // 2 chips grades + 3 chips groupes, toutes cochées.
    for (const grade of ['A1', 'A2']) {
      const box = screen.getByLabelText(grade)
      expect(box).toBeChecked()
    }
    const groupes = screen.getAllByLabelText(/Groupe \d/)
    expect(groupes).toHaveLength(3)
    for (const g of groupes) expect(g).toBeChecked()
    expect(screen.getByText('GRADES')).toBeInTheDocument()
    expect(screen.getByText('GROUPES')).toBeInTheDocument()
    // Bouton génération désormais actif.
    expect(facGenerateButton()).not.toBeDisabled()
  })

  it('utilise la formation du filtre global d’en-tête si aucune formation FAC n’est choisie', async () => {
    await openRapports()
    await screen.findByRole('button', { name: /Module Alpha/ })

    // Sélecteur GLOBAL d'en-tête (« Toutes les formations »), distinct de celui
    // de la barre bilans (« Toutes formations » sans article).
    const globalSel = screen.getByRole('option', { name: 'Toutes les formations' }).closest('select')
    fireEvent.change(globalSel, { target: { value: '10' } })
    await waitFor(() => expect(lastDataCall().get('formation_id')).toBe('10'))

    fireEvent.click(facToggleButton())
    expect(await screen.findByText('Périmètre — grades et groupes')).toBeInTheDocument()
    expect(perimetreCalls().at(-1).get('formation_id')).toBe('10')
    expect(await screen.findByLabelText('A1')).toBeChecked()
    expect(facGenerateButton()).not.toBeDisabled()
  })

  it('périmètre vide : message dédié et génération impossible', async () => {
    installFacRoutes({ perimetre: { grades: [], groupes: [] } })
    await openRapports()
    fireEvent.click(facToggleButton())
    fireEvent.change(facFormationSelect(), { target: { value: '11' } })

    expect(await screen.findByText('Aucun grade/groupe pour cette formation et ces filtres.')).toBeInTheDocument()
    expect(facGenerateButton()).toBeDisabled()
  })

  it('un échec de chargement du périmètre retombe sur l’état vide sans planter', async () => {
    installFacRoutes({ perimetre: () => { throw new Error('périmètre KO') } })
    await openRapports()
    fireEvent.click(facToggleButton())
    fireEvent.change(facFormationSelect(), { target: { value: '10' } })

    expect(await screen.findByText('Aucun grade/groupe pour cette formation et ces filtres.')).toBeInTheDocument()
  })

  it('« Tout décocher » vide la sélection (génération bloquée) puis « Tout cocher » réalimente', async () => {
    await openRapports()
    await openFacAndSelectFormation('10')

    fireEvent.click(screen.getByRole('button', { name: 'Tout décocher' }))
    expect(screen.getByLabelText('A1')).not.toBeChecked()
    expect(screen.getByLabelText('A2')).not.toBeChecked()
    // Les chips groupe sont calculées depuis les grades cochés : plus aucune
    // n'est visible tant qu'aucun grade n'est sélectionné.
    expect(screen.queryAllByLabelText(/Groupe \d/)).toHaveLength(0)
    expect(facGenerateButton()).toBeDisabled()

    fireEvent.click(screen.getByRole('button', { name: 'Tout cocher' }))
    expect(await screen.findByLabelText('A1')).toBeChecked()
    expect(await screen.findAllByLabelText(/Groupe \d/)).toHaveLength(3)
    expect(facGenerateButton()).not.toBeDisabled()
  })

  it('décocher un grade retire ses groupes du périmètre visible et de la sélection', async () => {
    await openRapports()
    await openFacAndSelectFormation('10')

    fireEvent.click(screen.getByLabelText('A2'))
    // Les groupes A2 disparaissent, ceux de A1 restent.
    await waitFor(() => {
      const visibles = screen.getAllByLabelText(/Groupe \d/)
      expect(visibles).toHaveLength(2) // g1 et g2 (A1)
    })
    // Le label groupe est la concaténation des deux spans (grade + groupe).
    expect(screen.queryByLabelText(/A2Groupe 1/)).not.toBeInTheDocument()

    fireEvent.click(facGenerateButton())
    await waitFor(() => expect(facDataCalls().length).toBe(1))
    const q = facDataCalls()[0]
    expect(q.get('grades')).toBe('A1') // sous-ensemble de grades
    expect(q.get('groupes')).toBe(null) // tous les groupes visibles sont cochés

    // Recocher le grade A2 : ses groupes REAPPARAISSENT mais ne sont pas
    // recochés automatiquement ; la requête porte alors le sous-ensemble groupes.
    fireEvent.click(screen.getByLabelText('A2'))
    await screen.findByLabelText(/A2Groupe 1/)
    expect(screen.getByLabelText(/A2Groupe 1/)).not.toBeChecked()
    fireEvent.click(facGenerateButton())
    await waitFor(() => expect(facDataCalls().length).toBe(2))
    expect(facDataCalls().at(-1).get('grades')).toBe(null) // tous les grades
    expect(facDataCalls().at(-1).get('groupes')).toBe('g1,g2')
  })

  it('porte la catégorie et l’année FAC sur le périmètre puis la génération', async () => {
    await openRapports()
    await openFacAndSelectFormation('10')

    fireEvent.change(facFieldSelect('Catégorie'), { target: { value: 'B' } })
    await waitFor(() => expect(perimetreCalls().at(-1).get('categorie')).toBe('B'))

    fireEvent.change(facFieldSelect('Année'), { target: { value: String(CURRENT_YEAR + 1) } })
    fireEvent.click(facGenerateButton())
    await waitFor(() => expect(facDataCalls().length).toBe(1))
    const q = facDataCalls()[0]
    expect(q.get('categorie')).toBe('B')
    expect(q.get('annee')).toBe(String(CURRENT_YEAR + 1))
  })

  it('changer la formation après génération réinitialise le bilan affiché', async () => {
    await openRapports()
    await openFacAndSelectFormation('10')
    fireEvent.click(facGenerateButton())
    expect(await screen.findByText('BILAN FORMATION — LICENCE 1 LSF')).toBeInTheDocument()

    fireEvent.change(facFormationSelect(), { target: { value: '11' } })
    await waitFor(() => {
      expect(screen.queryByText('BILAN FORMATION — LICENCE 1 LSF')).not.toBeInTheDocument()
    })
    expect(perimetreCalls().at(-1).get('formation_id')).toBe('11')
  })

  it('un échec de génération laisse le placeholder sans planter', async () => {
    installFacRoutes({ fac: () => { throw new Error('fac KO') } })
    await openRapports()
    await openFacAndSelectFormation('10')
    fireEvent.click(facGenerateButton())

    await waitFor(() => expect(facDataCalls().length).toBe(1))
    expect(screen.queryByText('BILAN FORMATION — LICENCE 1 LSF')).not.toBeInTheDocument()
    expect(screen.getByText(/Sélectionnez une formation/)).toBeInTheDocument()
  })
})

describe('Statistiques (LOT 38b) — Bilan FAC : génération, sous-onglets et exports', () => {
  let anchorCreateSpy

  beforeEach(() => {
    apiController.reset()
    window.localStorage.clear()
    window.sessionStorage.clear()
    URL.createObjectURL = vi.fn(() => 'blob:fac-export')
    URL.revokeObjectURL = vi.fn()
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    anchorCreateSpy = vi.spyOn(document, 'createElement')
    installFacRoutes()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  async function genererFac(formationValue = '10') {
    await openRapports()
    await openFacAndSelectFormation(formationValue)
    fireEvent.click(facGenerateButton())
    await screen.findByText('BILAN FORMATION — LICENCE 1 LSF')
  }

  it('génère le bilan (périmètre complet, sans params grades/groupes) et rend l’en-tête', async () => {
    await genererFac()

    const q = facDataCalls()[0]
    expect(q.get('formation_id')).toBe('10')
    expect(q.get('annee')).toBe(String(CURRENT_YEAR))
    expect(q.get('grades')).toBe(null)
    expect(q.get('groupes')).toBe(null)

    // En-tête du panneau bilan.
    expect(screen.getByText(/Grades : A1, A2/)).toBeInTheDocument()
    expect(screen.getByText(/Absents notoires : 0/)).toBeInTheDocument()
    expect(screen.getByText(/Généré le 12\/09\/2026/)).toBeInTheDocument()
    for (const label of ['Point global', 'Volume horaire', 'Absents notoires', 'État des modules']) {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument()
    }
  })

  it('sous-onglet Point global : agrège les grades, les totaux et expose justificatifs/difficultés', async () => {
    await genererFac()

    expect(screen.getByText('TAUX DE PARTICIPATION')).toBeInTheDocument()
    expect(screen.getByText("TAUX D'EXÉCUTION DU VOLUME HORAIRE")).toBeInTheDocument()
    const table = screen.getByText('TAUX DE PARTICIPATION').closest('table')
    const bodyRows = within(table.tBodies[0]).getAllByRole('row')
    // 2 grades triés (A1, A2) + ligne TOTAL.
    const gradeRows = bodyRows.filter((r) => ['A1', 'A2'].includes(r.cells[0].textContent))
    expect(gradeRows).toHaveLength(2)
    expect(gradeRows[0].cells[0].textContent).toBe('A1')
    expect(gradeRows[1].cells[0].textContent).toBe('A2')

    // TOTAL : effectif 70, VH cumulé 1000.
    const totalRow = bodyRows.find((r) => r.cells[0].textContent === 'TOTAL')
    expect(totalRow.textContent).toContain('70')
    expect(totalRow.textContent).toContain('1000')

    // Deux textareas par grade (justificatifs + difficultés).
    expect(table.querySelectorAll('textarea')).toHaveLength(4)
  })

  it('Point global : fusionne les lignes en doublon d’un même grade (une seule ligne, sommes VH/absents)', async () => {
    const facDoublon = {
      ...FAC_DATA,
      point_global: {
        lignes: [
          facLigne('A1', { effectif_auditeurs: 20, absents_notoires: 2, vh_total: 100, vh_epuise: 40 }),
          facLigne('A1', { effectif_auditeurs: 25, absents_notoires: 1, vh_total: 50, vh_epuise: 20 }),
        ],
        totaux: {
          effectif_auditeurs: 45, absents_notoires: 3, vh_total: 150, vh_epuise: 60,
          effectif_secretariat: 4, nb_encadrants: 4, nb_groupes: 2, groupes_termines: 0, taux_exec_vh: 40,
        },
      },
    }
    installFacRoutes({ fac: facDoublon })
    await genererFac()

    const table = screen.getByText('TAUX DE PARTICIPATION').closest('table')
    const rows = within(table.tBodies[0]).getAllByRole('row')
    const a1 = rows.filter((r) => r.cells[0].textContent === 'A1')
    expect(a1).toHaveLength(1) // les deux lignes A1 sont bien fusionnées
    // Sommes correctes pour les clés listées dans sumKeys (absents, VH,
    // secrétariat/encadreurs/groupes).
    expect(a1[0].cells[3].textContent.trim()).toBe('2') // nombre de groupes
    expect(a1[0].cells[5].textContent.trim()).toBe('3') // absents notoires
    expect(a1[0].cells[10].textContent.trim()).toBe('150') // VH total
    expect(a1[0].cells[11].textContent.trim()).toBe('60') // VH épuisé
    // Le TOTAL fourni par le backend est affiché tel quel.
    const totalRow = rows.find((r) => r.cells[0].textContent === 'TOTAL')
    expect(totalRow.cells[4].textContent.trim()).toBe('45')
  })

  // NOTE (écart constaté, P00-04, §10.15) : dans BilanFACPointGlobalTable,
  // la liste `sumKeys` de la fusion des lignes par grade contient la clé
  // erronée 'effectif_étudiants' (accent) au lieu de 'effectif_auditeurs'.
  // Conséquence : en cas de doublon de grade, l'effectif auditeurs de la
  // ligne fusionnée reste figé à la première ligne (20), alors que la ligne
  // TOTAL affiche bien 45 — les deux totaux sont incohérents. Comportement
  // ACTUEL documenté ci-dessous ; correction (clé 'effectif_auditeurs')
  // réservée à un lot correctif soumis au feu vert utilisateur.
  it('[écart] Point global : l’effectif auditeurs d’un grade en doublon n’est pas sommé (clé erronée effectif_étudiants)', async () => {
    const facDoublon = {
      ...FAC_DATA,
      point_global: {
        lignes: [
          facLigne('A1', { effectif_auditeurs: 20, absents_notoires: 2 }),
          facLigne('A1', { effectif_auditeurs: 25, absents_notoires: 1 }),
        ],
        totaux: {
          effectif_auditeurs: 45, absents_notoires: 3, vh_total: 150, vh_epuise: 60,
          effectif_secretariat: 4, nb_encadrants: 4, nb_groupes: 2, groupes_termines: 0, taux_exec_vh: 40,
        },
      },
    }
    installFacRoutes({ fac: facDoublon })
    await genererFac()

    const table = screen.getByText('TAUX DE PARTICIPATION').closest('table')
    const rows = within(table.tBodies[0]).getAllByRole('row')
    const a1 = rows.filter((r) => r.cells[0].textContent === 'A1')[0]
    const totalRow = rows.find((r) => r.cells[0].textContent === 'TOTAL')

    // Comportement ACTUEL (incorrect) : 20 au lieu de 45 attendus.
    expect(a1.cells[4].textContent.trim()).toBe('20')
    expect(totalRow.cells[4].textContent.trim()).toBe('45')
  })

  it('sous-onglet Volume horaire : tableaux par grade, agrégation des groupes doublons et récap global', async () => {
    await genererFac()
    fireEvent.click(screen.getByRole('button', { name: 'Volume horaire' }))

    expect(await screen.findByText(/TABLEAU MENSUEL RÉCAPITULANT/)).toBeInTheDocument()
    // Le libellé de ligne est répété dans chaque tableau par grade.
    expect(screen.getAllByText('VOLUME HORAIRE DU CYCLE DE FORMATION')).toHaveLength(2)
    expect(screen.getAllByText(/Grade A1/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Grade A2/).length).toBeGreaterThan(0)
    // Deux grades → récapitulatif global, VH cycle total 300 + 200 = 500.
    expect(screen.getByText('RÉCAPITULATIF GLOBAL')).toBeInTheDocument()
    // 2 libellés de ligne « TAUX D'EXÉCUTION (%) » + 1 en-tête du récap global.
    expect(screen.getAllByText(/TAUX D'EXÉCUTION/).length).toBeGreaterThanOrEqual(3)
    // TOTAL VH cycle du récap : 300 + 200 = 500 (table repérée à sa colonne VH CYCLE).
    const recapTable = screen.getAllByRole('table')
      .find((t) => t.textContent.includes('VH CYCLE') && t.textContent.includes('TOTAL'))
    expect(recapTable).toBeTruthy()
    const totalCells = within(recapTable.tBodies[0]).getAllByRole('row')
      .find((r) => r.cells[0].textContent === 'TOTAL').cells
    expect(totalCells[1].textContent.trim()).toBe('500')

    // Blocs par grade : les tables portent un en-tête GROUPES (1re = grade A1).
    const gradeTables = screen.getAllByRole('table')
      .filter((t) => t.textContent.startsWith('GROUPES'))
    expect(gradeTables).toHaveLength(2)
    // Bloc A1 : les deux entrées « Groupe 1 » sont fusionnées en une colonne
    // et leur VH est sommée (100+50 = 150).
    const headersA1 = within(gradeTables[0]).getAllByRole('columnheader', { name: 'Groupe 1' })
    expect(headersA1).toHaveLength(1)
    const rowsA1 = within(gradeTables[0].tBodies[0]).getAllByRole('row')
    const vhPrevRow = rowsA1.find((r) => r.cells[0].textContent.includes('CYCLE DE FORMATION'))
    expect(vhPrevRow.cells[1].textContent.trim()).toBe('150')
  })

  it('sous-onglet Absents notoires : message vide puis tableau détaillé après régénération', async () => {
    await genererFac()
    fireEvent.click(screen.getByRole('button', { name: 'Absents notoires' }))
    expect(await screen.findByText('Aucun absent notoire enregistré.')).toBeInTheDocument()

    // Régénération avec un absent (les routes et compteurs sont réinitialisés).
    installFacRoutes({
      fac: () => ({ ...FAC_DATA, absents_notoires: [FAC_ABSENT] }),
    })
    fireEvent.click(facGenerateButton())
    await waitFor(() => expect(facDataCalls().length).toBe(1))
    expect(await screen.findByText('KOUASSI')).toBeInTheDocument()
    expect(screen.getByText('MC-001')).toBeInTheDocument()
    expect(screen.getByText('A1 / Groupe 1')).toBeInTheDocument()
    expect(screen.getByText('Maladie longue durée')).toBeInTheDocument()
    expect(screen.getByText(/1 absent notoire/)).toBeInTheDocument()
    expect(screen.getByText(/Absents notoires : 1/)).toBeInTheDocument()
  })

  it('sous-onglet État des modules : regroupe par grade avec les 4 statuts', async () => {
    await genererFac()
    fireEvent.click(screen.getByRole('button', { name: 'État des modules' }))

    const titreModules = await screen.findByText(/ÉTAT D.AVANCEMENT DES MODULES/)
    expect(titreModules).toBeInTheDocument()
    const sectionModules = titreModules.parentElement
    expect(screen.getAllByText(/Grade A1/).length).toBeGreaterThan(0)
    for (const intitule of ['Module Alpha', 'Module Beta', 'Module Gamma', 'Module Delta']) {
      expect(within(sectionModules).getByText(intitule)).toBeInTheDocument()
    }
    for (const statut of ['Terminé', 'En cours', 'Planifié', 'Suspendu']) {
      expect(screen.getByText(statut)).toBeInTheDocument()
    }
  })

  it('export Excel du bilan FAC avec les meta justificatifs/difficultés saisies', async () => {
    apiMock.getBlob.mockResolvedValue({ blob: new Blob(['x']), fileName: 'FAC.xlsx' })
    await genererFac()

    const table = screen.getByText('TAUX DE PARTICIPATION').closest('table')
    const zones = within(table).getAllByPlaceholderText(/Justificatifs \(saisie libre\)/)
    fireEvent.change(zones[0], { target: { value: 'Justif A1' } })
    const diffs = within(table).getAllByPlaceholderText(/Difficultés rencontrées/)
    fireEvent.change(diffs[0], { target: { value: 'Salle indisponible' } })
    await screen.findByDisplayValue('Justif A1')

    fireEvent.click(facExportButton('Excel'))
    await waitFor(() => expect(apiMock.getBlob).toHaveBeenCalledTimes(1))
    const url = apiMock.getBlob.mock.calls[0][0]
    expect(url).toMatch(/^\/statistiques\/bilan-fac-export\/\?/)
    const q = paramsOf(url)
    expect(q.get('export')).toBe('xlsx')
    expect(q.get('formation_id')).toBe('10')
    expect(q.get('annee')).toBe(String(CURRENT_YEAR))
    const meta = JSON.parse(q.get('meta'))
    expect(meta.justificatifs.A1).toBe('Justif A1')
    expect(meta.difficultes.A1).toBe('Salle indisponible')
  })

  it('export PDF du bilan FAC : pas de meta quand aucune saisie, nom par défaut si absent du backend', async () => {
    apiMock.getBlob.mockResolvedValue({ blob: new Blob(['p']) }) // pas de fileName
    await genererFac()

    fireEvent.click(facExportButton('PDF'))
    await waitFor(() => expect(apiMock.getBlob).toHaveBeenCalledTimes(1))
    const q = paramsOf(apiMock.getBlob.mock.calls[0][0])
    expect(q.get('export')).toBe('pdf')
    expect(q.get('meta')).toBe(null)
    const anchors = anchorCreateSpy.mock.results
      .map((r) => r.value)
      .filter((el) => el && el.tagName === 'A')
    expect(anchors.at(-1).download).toBe(`BILAN_FAC_${CURRENT_YEAR}.pdf`)
  })

  it('un échec d’export FAC déclenche window.alert sans planter', async () => {
    apiMock.getBlob.mockRejectedValue(new Error('export fac KO'))
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    await genererFac()

    fireEvent.click(facExportButton('Word'))
    await waitFor(() => expect(alertSpy).toHaveBeenCalled())
    expect(alertSpy.mock.calls[0][0]).toMatch(/export fac KO|téléchargement/i)
  })
})
