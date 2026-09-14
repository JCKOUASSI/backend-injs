/**
 * Résolution des droits de navigation — fonctions **pures** (aucun effet de
 * bord, aucune dépendance React) pour être testables unitairement.
 *
 * Modèle hybride retenu avec le commanditaire :
 *
 * 1. un compte **gouverné** (profil CURP `CompteUtilisateur` + attributions)
 *    est filtré sur ses **permissions effectives CURP**
 *    (`GET /api/habilitations/mes-acces/ → permissions_effectives`) ;
 * 2. un compte **non gouverné** (cas de tout le legacy aujourd'hui) est filtré
 *    sur les **capacités projetées** (`GET /api/auth/capabilities/`), avec le
 *    repli statique historique de `utils/roles.js` tant que la réponse n'est
 *    pas arrivée ;
 * 3. une entrée qui ne déclare **aucun** code CURP (écran purement legacy, ex.
 *    Finance historique) reste évaluée par le volet legacy, quel que soit le
 *    compte : la réorganisation ne retire d'accès à personne.
 *
 * **L'interface n'accorde jamais rien** (règle S3) : ce module ne fait que
 * masquer des entrées. Chaque vue DRF conserve ses `permission_classes`, et le
 * moteur d'habilitation reste l'autorité (règle S4 : fermeture par défaut).
 */
import { peut, hasAppRole } from '../utils/roles'

/** Origine de la décision d'affichage, exposée pour le diagnostic et les tests. */
export const SOURCES = {
  CURP: 'CURP',
  LEGACY: 'LEGACY',
}

/**
 * Détermine la source applicable au compte courant.
 *
 * @param {object} params.user      utilisateur exposé par `useAuth` (avec `capabilities`)
 * @param {object} params.mesAcces  réponse de `GET /habilitations/mes-acces/`
 * @returns {{source: string, codes: Set<string>, gouverne: boolean}}
 */
export function resoudreSource({ user, mesAcces } = {}) {
  const liste = Array.isArray(mesAcces?.permissions_effectives)
    ? mesAcces.permissions_effectives
    : null
  // Un compte est « gouverné » pour la navigation dès lors que le backend le
  // dit gouverné ET expose la liste (clé additive) de ses permissions.
  const gouverne = Boolean(mesAcces?.gouverne) && liste !== null
  return {
    source: gouverne ? SOURCES.CURP : SOURCES.LEGACY,
    codes: new Set(liste || []),
    gouverne,
    user: user ?? null,
  }
}

/**
 * Une entrée de menu est-elle autorisée pour le contexte donné ?
 *
 * Ordre d'évaluation (OU interne à chaque volet) :
 * 1. volet CURP si le compte est gouverné **et** si l'entrée déclare des codes ;
 * 2. volet legacy (capacités projetées, repli statique inclus) ;
 * 3. volet rôles : secours avant chargement des capacités **et** élargissement
 *    volontaire pour les écrans purement legacy (l'ancienne barre latérale
 *    mélangeait déjà `peut(...)` et `hasAppRole(...)`) ;
 * 4. entrée sans aucun droit déclaré → visible (écran authentifié simple).
 */
export function itemAutorise(item, contexte) {
  if (!item) return false
  const droit = item.droit || {}
  const curp = Array.isArray(droit.curp) ? droit.curp : []
  const legacy = Array.isArray(droit.legacy) ? droit.legacy : []
  const roles = Array.isArray(droit.roles) ? droit.roles : []
  const { source, codes, user } = contexte || {}

  if (source === SOURCES.CURP && curp.length > 0) {
    return curp.some((code) => codes?.has(code))
  }
  if (legacy.length > 0 && legacy.some(([module, action]) => peut(user, module, action))) {
    return true
  }
  if (roles.length > 0 && hasAppRole(user, roles)) {
    return true
  }
  return curp.length === 0 && legacy.length === 0 && roles.length === 0
}

/**
 * Filtre l'arborescence : une section sans enfants est conservée si elle est
 * autorisée ; une section à enfants est conservée dès qu'**au moins un** enfant
 * l'est (les entrées non autorisées disparaissent — choix commanditaire).
 *
 * @returns {Array} nouvelle arborescence (mêmes objets, aucun mutation)
 */
export function filtrerArborescence(arbre, contexte) {
  if (!Array.isArray(arbre)) return []
  const resultat = []
  for (const section of arbre) {
    const enfants = Array.isArray(section.enfants) ? section.enfants : null
    if (!enfants) {
      if (itemAutorise(section, contexte)) resultat.push(section)
      continue
    }
    const enfantsAutorises = enfants.filter((e) => itemAutorise(e, contexte))
    if (enfantsAutorises.length > 0) {
      resultat.push({ ...section, enfants: enfantsAutorises })
    }
  }
  return resultat
}

/**
 * Droit requis par une entrée, sous forme lisible (diagnostic, infobulles,
 * documentation et tests). Ne sert jamais à décider : voir `itemAutorise`.
 */
export function droitRequis(item) {
  const droit = item?.droit || {}
  return {
    curp: Array.isArray(droit.curp) ? [...droit.curp] : [],
    legacy: Array.isArray(droit.legacy)
      ? droit.legacy.map(([module, action]) => `${module}.${action}`)
      : [],
    roles: Array.isArray(droit.roles) ? [...droit.roles] : [],
  }
}

/**
 * Indexe les entrées autorisées par chemin : sert au garde de route générique
 * (une URL saisie à la main ne doit pas contourner le masquage du menu).
 */
export function indexParChemin(arbreFiltre) {
  const index = new Map()
  for (const section of arbreFiltre || []) {
    if (section.chemin) index.set(section.chemin, section)
    for (const enfant of section.enfants || []) {
      if (enfant.chemin) index.set(enfant.chemin, enfant)
    }
  }
  return index
}
