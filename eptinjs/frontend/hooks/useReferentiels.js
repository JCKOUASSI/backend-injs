/** Charge une fois les référentiels communs aux écrans EPT-INJS. */
import { useEffect, useState } from 'react'
import { fetchPromotions } from '@app/api/academics'
import { fetchRooms, fetchTeachers } from '@app/api/faculty'
import { fetchPeriodes } from '../api/eptinjs'

const INITIAL = { periodes: [], promotions: [], salles: [], enseignants: [] }

export default function useReferentiels() {
  const [donnees, setDonnees] = useState(INITIAL)
  const [chargement, setChargement] = useState(true)
  const [erreur, setErreur] = useState('')

  useEffect(() => {
    let annule = false

    Promise.all([
      fetchPeriodes({ page_size: 100 }),
      fetchPromotions({ page_size: 200 }),
      fetchRooms({ page_size: 300 }),
      fetchTeachers({ page_size: 300 }),
    ])
      .then(([periodes, promotions, salles, enseignants]) => {
        if (annule) return
        setDonnees({
          periodes: periodes.results || [],
          promotions: Array.isArray(promotions) ? promotions : promotions.results || [],
          salles: salles.results || [],
          enseignants: enseignants.results || [],
        })
      })
      .catch((err) => !annule && setErreur(err.message || 'Chargement des référentiels impossible.'))
      .finally(() => !annule && setChargement(false))

    return () => { annule = true }
  }, [])

  return { ...donnees, chargement, erreur }
}
