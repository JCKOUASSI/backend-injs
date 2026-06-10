/** Persistance des filtres de listes (URL + sessionStorage pour les liens « Retour »). */

import { appendPeriodToSearchParams } from './financePeriod'

export const LIST_STORAGE_KEYS = {
  modules: 'modules_list_query',
  participants: 'participants_list_query',
  users: 'users_list_query',
  formateurs: 'formateurs_list_query',
  referentiels: 'referentiels_list_query',
  dashboard: 'dashboard_list_query',
  secretariats: 'secretariats_list_query',
}

export const parseListPage = (searchParams, fallback = 1) => {
  const n = parseInt(searchParams.get('page') || String(fallback), 10)
  return Number.isFinite(n) && n > 0 ? n : fallback
}

export const persistListQuery = (storageKey, params) => {
  const qs = params.toString()
  try {
    sessionStorage.setItem(storageKey, qs)
  } catch {
    /* ignore */
  }
  return qs ? `?${qs}` : ''
}

export const listHref = (pathname, storageKey) => {
  let qs = ''
  try {
    qs = sessionStorage.getItem(storageKey) || ''
  } catch {
    /* ignore */
  }
  return qs ? `${pathname}?${qs}` : pathname
}

export const modulesListHref = () => listHref('/modules', LIST_STORAGE_KEYS.modules)
export const participantsListHref = () => listHref('/participants', LIST_STORAGE_KEYS.participants)
export const usersListHref = () => listHref('/users', LIST_STORAGE_KEYS.users)
export const formateursListHref = () => listHref('/formateurs', LIST_STORAGE_KEYS.formateurs)
export const referentielsListHref = () => listHref('/referentiels', LIST_STORAGE_KEYS.referentiels)
export const dashboardListHref = () => listHref('/', LIST_STORAGE_KEYS.dashboard)

const MODULE_FILTER_KEYS = [
  'statut',
  'search',
  'secretariat_type',
  'vague',
  'grade',
  'groupe',
  'date_mode',
  'date',
]

export const readModulesFilters = (searchParams, getTodayIso) => ({
  statut: searchParams.get('statut') || '',
  search: searchParams.get('search') || '',
  secretariat_type: searchParams.get('secretariat_type') || '',
  vague: searchParams.get('vague') || '',
  grade: searchParams.get('grade') || '',
  groupe: searchParams.get('groupe') || '',
  date_mode: searchParams.get('date_mode') || 'today',
  date: searchParams.get('date') || getTodayIso(),
})

export const buildModulesSearchParams = (filters, page, debouncedSearch) => {
  const p = new URLSearchParams()
  if (page > 1) p.set('page', String(page))
  const merged = { ...filters, search: debouncedSearch }
  for (const key of MODULE_FILTER_KEYS) {
    const v = merged[key]
    if (v == null || v === '') continue
    if (key === 'date_mode' && v === 'today') continue
    p.set(key, v)
  }
  return p
}

export const readParticipantsFilters = (searchParams) => ({
  search: searchParams.get('search') || '',
  sexe: searchParams.get('sexe') || '',
  secretariat: searchParams.get('secretariat') || '',
  grade: searchParams.get('grade') || '',
  groupe: searchParams.get('groupe') || '',
  type_concours: searchParams.get('type_concours') || '',
  vague: searchParams.get('vague') || '',
})

export const buildParticipantsSearchParams = (filters, page, debouncedSearch) => {
  const p = new URLSearchParams()
  if (page > 1) p.set('page', String(page))
  const merged = { ...filters, search: debouncedSearch }
  for (const [key, val] of Object.entries(merged)) {
    if (val) p.set(key, val)
  }
  return p
}

export const readUsersFilters = (searchParams) => ({
  tab: searchParams.get('tab') || 'personnel',
  search: searchParams.get('search') || '',
  role: searchParams.get('role') || '',
})

export const buildUsersSearchParams = (tab, roleFilter, page, debouncedSearch) => {
  const p = new URLSearchParams()
  if (page > 1) p.set('page', String(page))
  if (tab && tab !== 'personnel') p.set('tab', tab)
  if (debouncedSearch) p.set('search', debouncedSearch)
  if (tab === 'personnel' && roleFilter) p.set('role', roleFilter)
  return p
}

export const readFormateursListExtras = (searchParams) => ({
  search: searchParams.get('search') || '',
})

export const buildFormateursListSearchParams = (
  page,
  debouncedSearch,
  financePeriod,
  financeFilters,
  withFinance,
  buildFinanceListSearchParams,
) => {
  if (withFinance && buildFinanceListSearchParams) {
    return buildFinanceListSearchParams(financePeriod, financeFilters, {
      page,
      search: debouncedSearch,
    })
  }
  const p = new URLSearchParams()
  if (page > 1) p.set('page', String(page))
  if (debouncedSearch) p.set('search', debouncedSearch)
  return p
}

export const readReferentielsTab = (searchParams) => {
  const tab = searchParams.get('tab') || 'formations'
  const allowed = [
    'formations', 'modules', 'categories', 'grades', 'vagues',
    'sites', 'batiments', 'salles', 'types_secretariat',
  ]
  return allowed.includes(tab) ? tab : 'formations'
}

export const buildReferentielsSearchParams = (tab) => {
  const p = new URLSearchParams()
  if (tab && tab !== 'formations') p.set('tab', tab)
  return p
}

export const readDashboardFilters = (searchParams) => ({
  secretariat: searchParams.get('secretariat') || '',
  presence_period: searchParams.get('presence_period') || 'jour',
  reference_date: searchParams.get('reference_date') || new Date().toISOString().slice(0, 10),
})

export const buildDashboardSearchParams = (filters, period) => {
  const p = new URLSearchParams()
  if (filters.secretariat) p.set('secretariat', filters.secretariat)
  if (filters.presence_period && filters.presence_period !== 'jour') {
    p.set('presence_period', filters.presence_period)
  }
  const today = new Date().toISOString().slice(0, 10)
  if (filters.reference_date && filters.reference_date !== today) {
    p.set('reference_date', filters.reference_date)
  }
  if (period) appendPeriodToSearchParams(p, period)
  return p
}

export const readSecretariatsExpanded = (searchParams) => searchParams.get('expanded') || ''

export const buildSecretariatsSearchParams = (expandedId) => {
  const p = new URLSearchParams()
  if (expandedId != null && expandedId !== '') p.set('expanded', String(expandedId))
  return p
}
