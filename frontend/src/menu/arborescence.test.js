/**
 * Cohérence de l'arborescence de navigation (tests d'invariants).
 *
 * Trois familles de garanties :
 * 1. **Couverture** : le menu rend bien les sections du modèle demandé, et les
 *    écrans historiques restent joignables (non-régression) ;
 * 2. **Intégrité** : chaque entrée déclarant un écran pointe vers un
 *    descripteur exploitable, et chaque descripteur est reachable ;
 * 3. **Contrat de droits** : tout code CURP cité existe réellement au catalogue
 *    (fixture générée depuis la base backend). C'est le garde-fou le plus
 *    important : un code inventé masquerait silencieusement l'entrée pour tous
 *    les comptes gouvernés — et personne ne s'en apercevrait en recette.
 */
import { describe, it, expect } from 'vitest'
import { ARBORESCENCE, PIED_DE_BARRE, aplatir } from './arborescence'
import { ECRANS } from './ecrans'
import CATALOGUE from './__fixtures__/catalogue-curp.json'
import CAPACITES from './__fixtures__/catalogue-capacites.json'

/** Libellés attendus, dans l'ordre du modèle fourni. */
const SECTIONS_ATTENDUES = [
  'Tableau de bord',
  'Scolarité',
  'Formations',
  'GET-INJS',
  'Évaluations',
  'Jurys',
  'Diplômation',
  'Finances étudiantes',
  'Stages',
  'Personnel',
  'Administration',
  'Utilisateurs & Accès',
  'Statistiques',
  'Référentiels',
  'Audit & Traçabilité',
]

/** Écrans dédiés (composant propre) qui n'ont pas de descripteur générique. */
const ECRANS_SUR_MESURE = ['aide']

/** Types de descripteur dont les données ne viennent pas d'une liste paginée. */
const TYPES_SANS_LISTE = ['indicateurs', 'documents']

const toutesEntrees = aplatir(ARBORESCENCE, PIED_DE_BARRE)

describe('couverture du modèle de menu', () => {
  it('rend les sections demandées, dans l\'ordre', () => {
    expect(ARBORESCENCE.map((section) => section.libelle)).toEqual(SECTIONS_ATTENDUES)
  })

  it('chaque section a un identifiant et une icône Bootstrap Icons', () => {
    for (const section of ARBORESCENCE) {
      expect(section.id, 'section sans id').toBeTruthy()
      expect(section.icone, `${section.id} : icône invalide`).toMatch(/^bi-/)
    }
  })

  it('toute section a soit un écran propre, soit des enfants', () => {
    for (const section of ARBORESCENCE) {
      const navigable = Boolean(section.chemin || section.ecran)
      expect(navigable || (section.enfants || []).length > 0, section.id).toBe(true)
    }
  })

  it('le pied de barre expose les notifications et l\'aide', () => {
    const ids = PIED_DE_BARRE.map((item) => item.id)
    expect(ids).toEqual(expect.arrayContaining(['pied.notifications', 'pied.aide']))
  })

  it('chaque entrée a un libellé lisible', () => {
    for (const entree of toutesEntrees) {
      expect(entree.libelle, entree.id).toBeTruthy()
      expect(entree.libelle.length, entree.id).toBeGreaterThan(1)
    }
  })
})

describe('contrat de droits : fermeture par défaut', () => {
  it('toute entrée déclare un droit (aucun écran offert à tous les comptes)', () => {
    const sansDroit = toutesEntrees.filter((entree) => !entree.droit).map((entree) => entree.id)
    expect(sansDroit).toEqual([])
  })

  it('tout droit déclare au moins un volet CURP ou legacy', () => {
    const vides = toutesEntrees
      .filter((entree) => !(entree.droit?.curp?.length) && !(entree.droit?.legacy?.length)
        && !(entree.droit?.roles?.length))
      .map((entree) => entree.id)
    expect(vides).toEqual([])
  })

  it('les volets legacy citent des couples [module, action]', () => {
    for (const entree of toutesEntrees) {
      for (const couple of entree.droit?.legacy || []) {
        expect(Array.isArray(couple) && couple.length === 2, entree.id).toBe(true)
        expect(couple[0], entree.id).toBeTruthy()
        expect(couple[1], entree.id).toBeTruthy()
      }
    }
  })

  it('toute capacité legacy citée existe au contrat GET /auth/capabilities/', () => {
    const introuvables = []
    for (const entree of toutesEntrees) {
      for (const [module, action] of entree.droit?.legacy || []) {
        if (!CAPACITES.capacites[module]?.includes(action)) {
          introuvables.push(`${entree.id} → ${module}.${action}`)
        }
      }
    }
    expect(introuvables).toEqual([])
  })

  it('toute capacité legacy citée est bien projetée par le backend (fixture à jour)', () => {
    expect(CAPACITES.nombre_modules).toBe(Object.keys(CAPACITES.capacites).length)
    expect(CAPACITES.capacites.scolarite).toEqual(expect.arrayContaining(['voir', 'agir']))
  })
})

describe('contrat de droits : codes CURP réels', () => {
  const codesCites = toutesEntrees.flatMap((entree) =>
    (entree.droit?.curp || []).map((code) => ({ entree: entree.id, code })))

  it('la fixture de catalogue est chargée et cohérente', () => {
    expect(CATALOGUE.codes.length).toBeGreaterThan(1000)
    expect(CATALOGUE.codes.length).toBe(CATALOGUE.nombre)
    expect(CATALOGUE.modules.length).toBeGreaterThan(10)
  })

  it('le menu cite un nombre significatif de permissions CURP', () => {
    expect(codesCites.length).toBeGreaterThan(100)
  })

  it('tout code cité suit la forme module.ressource.action', () => {
    for (const { entree, code } of codesCites) {
      expect(code, `${entree} : ${code}`).toMatch(/^[a-z_]+\.[a-z_]+\.[a-z_]+$/)
    }
  })

  it('tout code cité existe au catalogue CURP (aucun code inventé)', () => {
    const introuvables = codesCites
      .filter(({ code }) => !CATALOGUE.codes.includes(code))
      .map(({ entree, code }) => `${entree} → ${code}`)
    expect(introuvables).toEqual([])
  })

  it('tout module cité appartient au catalogue', () => {
    for (const { entree, code } of codesCites) {
      const moduleCite = code.split('.')[0]
      expect(CATALOGUE.modules, `${entree} : module « ${moduleCite} »`).toContain(moduleCite)
    }
  })
})

describe('intégrité des descripteurs d\'écrans', () => {
  it('chaque entrée déclarant un écran générique dispose d\'un descripteur', () => {
    const orphelins = toutesEntrees
      .filter((entree) => entree.ecran && !ECRANS[entree.ecran]
        && !ECRANS_SUR_MESURE.includes(entree.ecran))
      .map((entree) => `${entree.id} → ${entree.ecran}`)
    expect(orphelins).toEqual([])
  })

  it('chaque descripteur est référencé par au moins une entrée du menu', () => {
    const utilises = new Set(toutesEntrees.map((entree) => entree.ecran).filter(Boolean))
    const inutilises = Object.keys(ECRANS).filter((cle) => !utilises.has(cle))
    expect(inutilises).toEqual([])
  })

  it('chaque descripteur a une source de données exploitable', () => {
    for (const [cle, ecran] of Object.entries(ECRANS)) {
      if (TYPES_SANS_LISTE.includes(ecran.type)) continue
      const couvert = Boolean(ecran.endpoint || (ecran.onglets || []).length || ecran.composant)
      expect(couvert, `descripteur « ${cle} » sans endpoint, onglets ni composant`).toBe(true)
    }
  })

  it('chaque descripteur a un titre et un identifiant concordants', () => {
    for (const [cle, ecran] of Object.entries(ECRANS)) {
      expect(ecran.id, cle).toBe(cle)
      expect(ecran.titre, cle).toBeTruthy()
    }
  })

  it('les colonnes déclarées ont une clef et un libellé', () => {
    for (const [cle, ecran] of Object.entries(ECRANS)) {
      for (const colonne of ecran.colonnes || []) {
        expect(colonne.cle, `${cle} : colonne sans clef`).toBeTruthy()
        expect(colonne.libelle, `${cle} : colonne sans libellé`).toBeTruthy()
      }
    }
  })

  it('les priorités de colonnes automatiques sont des noms de champs', () => {
    for (const [cle, ecran] of Object.entries(ECRANS)) {
      for (const champ of ecran.priorite || []) {
        expect(typeof champ, `${cle} : priorité invalide`).toBe('string')
        expect(champ, `${cle} : champ vide`).toBeTruthy()
      }
    }
  })

  it('les actions citent un verbe et un libellé', () => {
    for (const [cle, ecran] of Object.entries(ECRANS)) {
      for (const action of [...(ecran.actions || []), ...(ecran.actionsGlobales || [])]) {
        expect(action.libelle, `${cle} : action sans libellé`).toBeTruthy()
        const executable = Boolean(action.methode || action.vers || action.telechargement
          || action.lien || action.transition)
        expect(executable, `${cle} : action « ${action.libelle} » sans effet`).toBe(true)
      }
    }
  })
})

describe('unicité des chemins de navigation', () => {
  it('deux écrans génériques distincts ne partagent jamais un chemin', () => {
    const generiques = toutesEntrees.filter((entree) => entree.ecran && entree.chemin)
    const vus = new Map()
    const conflits = []
    for (const entree of generiques) {
      const precedent = vus.get(entree.chemin)
      if (precedent && precedent !== entree.ecran) {
        conflits.push(`${entree.chemin} : ${precedent} vs ${entree.ecran}`)
      }
      vus.set(entree.chemin, entree.ecran)
    }
    expect(conflits).toEqual([])
  })

  it('les chemins commencent par « / » et n\'ont pas de double barre', () => {
    for (const entree of toutesEntrees) {
      if (!entree.chemin) continue
      expect(entree.chemin.startsWith('/'), entree.chemin).toBe(true)
      expect(entree.chemin.includes('//'), entree.chemin).toBe(false)
    }
  })

  it('les identifiants d\'entrée sont uniques', () => {
    const ids = toutesEntrees.map((entree) => entree.id)
    expect(new Set(ids).size).toBe(ids.length)
  })
})

describe('alignement menu ↔ garde serveur', () => {
  /**
   * Les entrées qui ouvrent la **console CURP** (comptes, rôles, matrice,
   * organisation, journal, intégrité) tombent sur des vues gardées par
   * `ExigeDrapeauAdmin` : drapeau `flag.curp_ui_admin` ouvert **et** trio
   * d'administration de l'habilitation. Cette garde ne consulte aucune
   * permission CURP — déclarer un volet `curp` ici ferait apparaître l'entrée
   * pour un compte gouverné qui recevrait ensuite un 403. La capacité projetée
   * `habilitations_admin.gerer` reproduit exactement la garde (même drapeau,
   * même trio) : c'est donc le seul volet admis.
   */
  const PREFIXES_CONSOLE = [
    '/administration/comptes',
    '/administration/services',
    '/administration/departements',
    '/administration/directions',
    '/audit/integrite',
    '/audit/archives',
  ]

  const entreesConsole = toutesEntrees.filter((entree) =>
    PREFIXES_CONSOLE.some((prefixe) => (entree.chemin || '').startsWith(prefixe)))

  it('toute entrée de la console porte le marqueur `console` (verrou kill-switch)', () => {
    const nonMarquees = entreesConsole.filter((entree) => !entree.console).map((e) => e.id)
    expect(nonMarquees).toEqual([])
    // Réciproque : aucun marqueur hors des chemins de la console.
    const horsConsole = toutesEntrees
      .filter((entree) => entree.console)
      .filter((entree) => !PREFIXES_CONSOLE.some((p) => (entree.chemin || '').startsWith(p)))
      .map((entree) => entree.id)
    expect(horsConsole).toEqual([])
  })

  it('des entrées de la console CURP sont bien présentes au menu', () => {
    expect(entreesConsole.length).toBeGreaterThan(10)
  })

  it('aucune n\'ajoute de volet CURP ou de repli par rôles', () => {
    const ecarts = entreesConsole
      .filter((entree) => entree.droit?.curp?.length || entree.droit?.roles?.length)
      .map((entree) => entree.id)
    expect(ecarts).toEqual([])
  })

  it('toutes exigent la capacité projetée de la console', () => {
    const ecarts = entreesConsole
      .filter((entree) => !(entree.droit?.legacy || []).some(
        ([module, action]) => module === 'habilitations_admin' && action === 'gerer'))
      .map((entree) => entree.id)
    expect(ecarts).toEqual([])
  })
})

describe('non-régression : les écrans historiques restent accessibles', () => {
  const chemins = new Set(toutesEntrees.map((entree) => entree.chemin))

  it.each([
    '/dashboard',
    '/scolarite/candidatures',
    '/scolarite/campagnes',
    '/scolarite/admissions',
    '/scolarite/inscriptions',
    '/participants',
    '/scolarite/jurys',
    '/scolarite/graduation',
    '/scolarite/finances',
    '/formations',
    '/modules',
    '/formateurs',
    '/edt',
    '/evaluations',
    '/administration/comptes',
    '/administration/comptes/roles',
    '/administration/comptes/matrice',
    '/users',
    '/organisation',
    '/statistiques',
    '/referentiels',
    '/parametres',
    '/archives',
    '/finance-encadrants',
    '/finance-parametrage',
    '/import',
    '/archives/listes-notes',
    '/archives/cahiers-appel',
    '/evaluations?tab=dashboard',
  ])('conserve l\'entrée %s', (chemin) => {
    expect(chemins.has(chemin), `${chemin} a disparu du menu`).toBe(true)
  })

  it('le personnel reste joignable', () => {
    expect(chemins.has('/personnel/agents')).toBe(true)
  })
})
