import { SEMESTRES, GRADES_LMD } from '../data/mockData'

const NIVEAU_SEMESTRES = {
  L1: [1, 2],
  L2: [3, 4],
  L3: [5, 6],
  M1: [7, 8],
  M2: [9, 10],
  D1: [11, 12],
  D2: [13, 14],
  D3: [15, 16],
}

export function niveauToGradeId(niveau) {
  if (!niveau) return 'licence'
  if (niveau.startsWith('L')) return 'licence'
  if (niveau.startsWith('M')) return 'master'
  if (niveau.startsWith('D')) return 'doctorat'
  return 'licence'
}

export function semestreIdsForNiveau(niveau) {
  return NIVEAU_SEMESTRES[niveau] || NIVEAU_SEMESTRES.L1
}

export function filterSemestresByNiveau(niveau) {
  const ids = semestreIdsForNiveau(niveau)
  return SEMESTRES.filter((s) => ids.includes(s.id))
}

export function filterGradesByNiveau(niveau) {
  const gradeId = niveauToGradeId(niveau)
  return GRADES_LMD.filter((g) => g.id === gradeId)
}

export function isSemestreInNiveau(semestreId, niveau) {
  return semestreIdsForNiveau(niveau).includes(Number(semestreId))
}
