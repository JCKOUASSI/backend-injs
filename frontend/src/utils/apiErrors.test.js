import { describe, it, expect } from 'vitest'
import { formatApiErrors } from './apiErrors'

describe('utils/apiErrors — formatApiErrors', () => {
  it('renvoie le fallback par défaut sans donnée', () => {
    expect(formatApiErrors(null)).toBe('Une erreur est survenue.')
    expect(formatApiErrors(undefined)).toBe('Une erreur est survenue.')
  })

  it('accepte un fallback et des libellés de champ personnalisés', () => {
    expect(formatApiErrors(null, { fallback: 'BAD' })).toBe('BAD')
  })

  it('renvoie directement une chaîne', () => {
    expect(formatApiErrors('Erreur générique')).toBe('Erreur générique')
  })

  it('retourne detail lorsqu’il est une chaîne', () => {
    expect(formatApiErrors({ detail: 'Compte verrouillé' })).toBe('Compte verrouillé')
  })

  it('joint les éléments d’un detail en tableau', () => {
    expect(formatApiErrors({ detail: ['Une première raison', 'Une seconde'] })).toBe(
      'Une première raison\nUne seconde',
    )
  })

  it('stringifie un detail non textuel', () => {
    expect(formatApiErrors({ detail: 42 })).toBe('42')
  })

  it('privilégie error quand c’est une chaîne non vide', () => {
    expect(formatApiErrors({ error: 'Quelque chose cloche' })).toBe('Quelque chose cloche')
  })

  it('[écart] traite un error uniquement composé d’espaces comme un champ normal', () => {
    // Comportement constaté (non corrigé au LOT 1) : un `error` blanc n’est pas
    // retenu comme message, mais l’objet n’est pas vide pour autant → la clé
    // « error » est formatée comme une erreur de champ.
    expect(formatApiErrors({ error: '   ' })).toBe('error :    ')
  })

  it('formate les erreurs de champ avec les libellés FR par défaut', () => {
    const out = formatApiErrors({
      username: ['Ce champ est obligatoire.'],
      email: ['Adresse invalide'],
      password: 'Trop court',
    })
    expect(out).toContain('Identifiant : Ce champ est obligatoire.')
    expect(out).toContain('Adresse e-mail : Adresse invalide')
    expect(out).toContain('Mot de passe : Trop court')
  })

  it('utilise le nom brut d’un champ inconnu et joint les valeurs en tableau', () => {
    const out = formatApiErrors({ code_metier: ['a', 'b'] })
    expect(out).toBe('code_metier : a, b')
  })

  it('retombe sur le fallback avec un objet vide', () => {
    expect(formatApiErrors({})).toBe('Une erreur est survenue.')
  })
})
