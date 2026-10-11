/**
 * Stockage Web résilient (aperçu intégré).
 *
 * Dans l'aperçu Arena, l'application tourne dans une iframe tierce
 * (*.e2b.app intégrée par *.arena.site) : certains navigateurs bloquent alors
 * l'accès à localStorage/sessionStorage (SecurityError — Safari, réglages
 * « bloquer les cookies tiers », navigation privée renforcée). Sans repli,
 * la connexion échouait APRÈS le 200 de l'API au moment d'écrire le jeton.
 *
 * Ce module choisit UNE fois par page le meilleur stockage disponible
 * (localStorage → sessionStorage → mémoire) pour rester cohérent entre
 * lectures et écritures ; chaque opération reste protégée (quota dépassé,
 * stockage vidé en cours de session → repli mémoire).
 */

const CLE_SONDE = '__injs_probe_storage__'
const MEMOIRE = new Map()
// Clés dont la dernière écriture dans le stockage résolu a échoué (exception,
// quota, ou écriture silencieusement ignorée — vérifiée par relecture). Pour
// celles-ci seulement, getItem replie sur MEMOIRE quand le stockage renvoie
// null ; une clé correctement écrite reste soumise à l'autorité du stockage
// (qui a pu être volontairement vidé : tests, déconnexion, autre onglet).
const ECRITURES_ECHOUEES = new Set()
let _stockage = undefined // undefined = pas encore résolu ; null = mémoire

function resoudreStockage() {
  if (_stockage !== undefined) return _stockage
  for (const candidat of [window.localStorage, window.sessionStorage]) {
    try {
      candidat.setItem(CLE_SONDE, '1')
      candidat.removeItem(CLE_SONDE)
      _stockage = candidat
      return _stockage
    } catch {
      // Stockage inaccessible (SecurityError / QuotaExceededError) → suivant.
    }
  }
  // Repli ultime : mémoire de la page courante (la session ne survit pas à un
  // rechargement, l'utilisateur se reconnecte — comportement dégradé assumé).
  _stockage = null
  return _stockage
}

export const safeLocalStorage = {
  getItem(cle) {
    const stockage = resoudreStockage()
    if (stockage) {
      try {
        const valeur = stockage.getItem(cle)
        if (valeur !== null) return valeur
        // null : le stockage fait foi, sauf si la dernière écriture de cette
        // clé a échoué (la valeur n'existe qu'en mémoire — sans ce repli, la
        // session « disparaît » et les requêtes repartent sans authentification).
        if (!ECRITURES_ECHOUEES.has(cle)) return null
      } catch {
        // Lecture impossible → tenter la mémoire (peut contenir une écriture
        // de secours posée après une panne du stockage).
      }
    }
    return MEMOIRE.has(cle) ? MEMOIRE.get(cle) : null
  },

  setItem(cle, valeur) {
    const attendu = String(valeur)
    const stockage = resoudreStockage()
    if (stockage) {
      try {
        stockage.setItem(cle, attendu)
        // Relecture : certains contextes (quota exigu, stockage révoqué,
        // mode privé) acceptent l'écriture sans la conserver — dans ce cas
        // la valeur ne vit qu'en mémoire et getItem doit la retrouver.
        if (stockage.getItem(cle) === attendu) {
          ECRITURES_ECHOUEES.delete(cle)
          MEMOIRE.set(cle, attendu)
          return
        }
      } catch {
        // Écriture impossible → conserver au moins en mémoire.
      }
      ECRITURES_ECHOUEES.add(cle)
    }
    MEMOIRE.set(cle, attendu)
  },

  removeItem(cle) {
    const stockage = resoudreStockage()
    if (stockage) {
      try {
        stockage.removeItem(cle)
      } catch {
        // Déjà hors service → purge mémoire ci-dessous.
      }
    }
    ECRITURES_ECHOUEES.delete(cle)
    MEMOIRE.delete(cle)
  },
}

export default safeLocalStorage
