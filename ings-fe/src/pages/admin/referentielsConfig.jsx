/**
 * Registre des entités référentielles : colonnes de tableau et formulaires.
 *
 * Les clés correspondent à celles du registre backend
 * (`apps/academics/services/referentiels.py`), qui fournit libellés, endpoints
 * et compteurs. Ce fichier ne décrit que la présentation.
 */

export const TRACK_OPTIONS = [
  { value: '', label: 'Général' },
  { value: 'PL', label: 'Professeur de Lycée' },
  { value: 'PC', label: 'Professeur de Collège' },
  { value: 'BOTH', label: 'Lycée et Collège' },
]

export const DEGREE_OPTIONS = [
  { value: 'L', label: 'Licence' },
  { value: 'M', label: 'Master' },
  { value: 'D', label: 'Doctorat' },
  { value: 'DU', label: 'Diplôme Universitaire' },
]

const currentYear = new Date().getFullYear()

function trackLabel(track) {
  return TRACK_OPTIONS.find((item) => item.value === (track || ''))?.label || '—'
}

function period(row) {
  if (!row.start_date && !row.end_date) return '—'
  return `${row.start_date || '?'} → ${row.end_date || '?'}`
}

function yesNo(value) {
  return value ? 'Oui' : 'Non'
}

export const RESOURCE_CONFIG = {
  academicYear: {
    singular: 'Année académique',
    searchPlaceholder: 'Libellé, institution…',
    defaultOrdering: '-start_date',
    columns: [
      { key: 'label', label: 'Libellé', sortKey: 'label' },
      { key: 'institution', label: 'Institution', render: (row, lookups) => lookups.institutions.get(row.institution)?.name || '—' },
      { key: 'period', label: 'Période', sortKey: 'start_date', render: period },
      { key: 'archived', label: 'Archivée', render: (row) => yesNo(row.is_archived) },
    ],
    emptyForm: { institution: '', label: '', start_date: '', end_date: '', is_current: false, is_archived: false },
    toForm: (item) => ({
      institution: item.institution || '',
      label: item.label || '',
      start_date: item.start_date || '',
      end_date: item.end_date || '',
      is_current: !!item.is_current,
      is_archived: !!item.is_archived,
    }),
    toPayload: (form) => ({
      institution: form.institution,
      label: form.label.trim(),
      start_date: form.start_date,
      end_date: form.end_date,
      is_current: !!form.is_current,
      is_archived: !!form.is_archived,
    }),
    prefill: (snapshot) => ({ institution: snapshot.institutions?.[0]?.id || '' }),
    fields: [
      { type: 'select', name: 'institution', label: 'Institution', required: true, options: (s) => s.institutions.map((i) => ({ value: i.id, label: `${i.acronym || i.code} — ${i.name}` })) },
      { type: 'text', name: 'label', label: 'Libellé', required: true, placeholder: '2026-2027' },
      { type: 'date', name: 'start_date', label: 'Date de début', required: true },
      { type: 'date', name: 'end_date', label: 'Date de fin', required: true },
      { type: 'check', name: 'is_current', label: 'Année courante', hint: 'Les autres années de l’institution seront basculées en non courantes.' },
      { type: 'check', name: 'is_archived', label: 'Archivée' },
    ],
  },

  semester: {
    singular: 'Semestre',
    searchPlaceholder: 'Nom, année académique…',
    defaultOrdering: 'number',
    columns: [
      { key: 'name', label: 'Nom', sortKey: 'name' },
      { key: 'number', label: 'Numéro', sortKey: 'number', render: (row) => `S${row.number}` },
      { key: 'academic_year', label: 'Année', render: (row, lookups) => row.academic_year_label || lookups.years.get(row.academic_year)?.label || '—' },
      { key: 'period', label: 'Période', sortKey: 'start_date', render: period },
    ],
    emptyForm: { academic_year: '', number: 1, name: '', start_date: '', end_date: '', is_current: false },
    toForm: (item) => ({
      academic_year: item.academic_year || '',
      number: item.number || 1,
      name: item.name || '',
      start_date: item.start_date || '',
      end_date: item.end_date || '',
      is_current: !!item.is_current,
    }),
    toPayload: (form) => ({
      academic_year: form.academic_year,
      number: Number(form.number),
      name: form.name.trim(),
      start_date: form.start_date,
      end_date: form.end_date,
      is_current: !!form.is_current,
    }),
    prefill: (snapshot) => ({ academic_year: snapshot.current_academic_year || snapshot.academic_years?.[0]?.id || '' }),
    fields: [
      { type: 'select', name: 'academic_year', label: 'Année académique', required: true, options: (s) => s.academic_years.map((y) => ({ value: y.id, label: y.label })) },
      { type: 'number', name: 'number', label: 'Numéro', required: true, min: 1, max: 12 },
      { type: 'text', name: 'name', label: 'Nom', required: true, placeholder: 'Semestre 1' },
      { type: 'date', name: 'start_date', label: 'Date de début', required: true },
      { type: 'date', name: 'end_date', label: 'Date de fin', required: true },
      { type: 'check', name: 'is_current', label: 'Semestre courant', hint: 'Un seul semestre courant par année académique.' },
    ],
  },

  institution: {
    singular: 'Institution',
    searchPlaceholder: 'Code, nom, ville…',
    defaultOrdering: 'name',
    columns: [
      { key: 'code', label: 'Code', sortKey: 'code' },
      { key: 'name', label: 'Nom', sortKey: 'name' },
      { key: 'acronym', label: 'Sigle' },
      { key: 'city', label: 'Ville', sortKey: 'city' },
    ],
    emptyForm: { code: '', name: '', acronym: '', city: 'Abidjan', country: "Côte d'Ivoire", phone: '', email: '', is_active: true },
    toForm: (item) => ({
      code: item.code || '',
      name: item.name || '',
      acronym: item.acronym || '',
      city: item.city || '',
      country: item.country || '',
      phone: item.phone || '',
      email: item.email || '',
      is_active: item.is_active !== false,
    }),
    toPayload: (form) => ({
      code: form.code.trim(),
      name: form.name.trim(),
      acronym: form.acronym.trim(),
      city: form.city,
      country: form.country,
      phone: form.phone || '',
      email: form.email || '',
      is_active: !!form.is_active,
    }),
    fields: [
      { type: 'text', name: 'code', label: 'Code', required: true },
      { type: 'text', name: 'acronym', label: 'Sigle', required: true },
      { type: 'text', name: 'name', label: 'Nom', required: true, full: true },
      { type: 'text', name: 'city', label: 'Ville' },
      { type: 'text', name: 'country', label: 'Pays' },
      { type: 'text', name: 'phone', label: 'Téléphone' },
      { type: 'email', name: 'email', label: 'Email' },
      { type: 'check', name: 'is_active', label: 'Institution active' },
    ],
  },

  department: {
    singular: 'Département',
    searchPlaceholder: 'Code, nom, institution…',
    defaultOrdering: 'name',
    needsUsers: true,
    columns: [
      { key: 'code', label: 'Code', sortKey: 'code' },
      { key: 'name', label: 'Nom', sortKey: 'name' },
      { key: 'institution_name', label: 'Institution', render: (row, lookups) => row.institution_name || lookups.institutions.get(row.institution)?.name || '—' },
      { key: 'head_name', label: 'Responsable', render: (row) => row.head_name || '—' },
    ],
    emptyForm: { institution: '', code: '', name: '', description: '', head: '' },
    toForm: (item) => ({
      institution: item.institution || '',
      code: item.code || '',
      name: item.name || '',
      description: item.description || '',
      head: item.head || '',
    }),
    toPayload: (form) => ({
      institution: form.institution,
      code: form.code.trim(),
      name: form.name.trim(),
      description: form.description || '',
      head: form.head || null,
    }),
    prefill: (snapshot) => ({ institution: snapshot.institutions?.[0]?.id || '' }),
    fields: [
      { type: 'select', name: 'institution', label: 'Institution', required: true, options: (s) => s.institutions.map((i) => ({ value: i.id, label: `${i.acronym || i.code} — ${i.name}` })) },
      { type: 'text', name: 'code', label: 'Code', required: true },
      { type: 'text', name: 'name', label: 'Nom', required: true },
      { type: 'select', name: 'head', label: 'Responsable', options: (s, ctx) => ctx.users.map((u) => ({ value: u.id, label: `${u.prenom || u.first_name || ''} ${u.nom || u.last_name || ''} (${u.email})`.trim() })) },
      { type: 'textarea', name: 'description', label: 'Description' },
    ],
  },

  program: {
    singular: 'Programme',
    searchPlaceholder: 'Code, nom, département…',
    defaultOrdering: 'name',
    columns: [
      { key: 'code', label: 'Code', sortKey: 'code' },
      { key: 'name', label: 'Nom', sortKey: 'name' },
      { key: 'degree_type_display', label: 'Cycle', sortKey: 'degree_type', render: (row) => row.degree_type_display || row.degree_type || '—' },
      { key: 'department', label: 'Département', render: (row, lookups) => row.department_name || lookups.departments.get(row.department)?.name || '—' },
      { key: 'track', label: 'Voie', render: (row) => trackLabel(row.track) },
      { key: 'credits', label: 'Crédits', sortKey: 'total_credits', render: (row) => `${row.total_credits} ECTS · ${row.duration_semesters} sem.` },
    ],
    emptyForm: { department: '', code: '', name: '', degree_type: 'L', track: '', duration_semesters: 6, total_credits: 180, description: '', is_active: true },
    toForm: (item) => ({
      department: item.department || '',
      code: item.code || '',
      name: item.name || '',
      degree_type: item.degree_type || 'L',
      track: item.track || '',
      duration_semesters: item.duration_semesters || 6,
      total_credits: item.total_credits || 180,
      description: item.description || '',
      is_active: item.is_active !== false,
    }),
    toPayload: (form) => ({
      department: form.department,
      code: form.code.trim(),
      name: form.name.trim(),
      degree_type: form.degree_type,
      track: form.track,
      duration_semesters: Number(form.duration_semesters),
      total_credits: Number(form.total_credits),
      description: form.description || '',
      is_active: !!form.is_active,
    }),
    prefill: (snapshot) => ({ department: snapshot.departments?.[0]?.id || '' }),
    fields: [
      { type: 'select', name: 'department', label: 'Département', required: true, options: (s) => s.departments.map((d) => ({ value: d.id, label: `${d.code} — ${d.name}` })) },
      { type: 'text', name: 'code', label: 'Code', required: true },
      { type: 'text', name: 'name', label: 'Nom', required: true },
      { type: 'select', name: 'degree_type', label: 'Cycle', required: true, options: () => DEGREE_OPTIONS, allowEmpty: false },
      { type: 'select', name: 'track', label: 'Voie', options: () => TRACK_OPTIONS.filter((o) => o.value !== 'BOTH'), allowEmpty: false },
      { type: 'number', name: 'duration_semesters', label: 'Durée (semestres)', required: true, min: 1 },
      { type: 'number', name: 'total_credits', label: 'Crédits totaux', required: true, min: 1 },
      { type: 'textarea', name: 'description', label: 'Description' },
      { type: 'check', name: 'is_active', label: 'Programme actif' },
    ],
  },

  promotion: {
    singular: 'Promotion',
    searchPlaceholder: 'Nom, programme…',
    defaultOrdering: '-entry_year',
    columns: [
      { key: 'name', label: 'Nom', sortKey: 'name' },
      { key: 'program', label: 'Programme', render: (row, lookups) => row.program_name || lookups.programs.get(row.program)?.name || '—' },
      { key: 'entry_year', label: 'Année d’entrée', sortKey: 'entry_year' },
      { key: 'current_semester', label: 'Semestre courant', sortKey: 'current_semester', render: (row) => `S${row.current_semester}` },
    ],
    emptyForm: { program: '', name: '', entry_year: currentYear, current_semester: 1, is_active: true },
    toForm: (item) => ({
      program: item.program || '',
      name: item.name || '',
      entry_year: item.entry_year || currentYear,
      current_semester: item.current_semester || 1,
      is_active: item.is_active !== false,
    }),
    toPayload: (form) => ({
      program: form.program,
      name: form.name.trim(),
      entry_year: Number(form.entry_year),
      current_semester: Number(form.current_semester),
      is_active: !!form.is_active,
    }),
    prefill: (snapshot) => ({ program: snapshot.programs?.[0]?.id || '' }),
    fields: [
      { type: 'select', name: 'program', label: 'Programme', required: true, options: (s) => s.programs.map((p) => ({ value: p.id, label: `${p.code} — ${p.name}` })) },
      { type: 'text', name: 'name', label: 'Nom', required: true, placeholder: 'L1 2026' },
      { type: 'number', name: 'entry_year', label: 'Année d’entrée', required: true, min: 2000 },
      { type: 'number', name: 'current_semester', label: 'Semestre courant', required: true, min: 1, max: 12 },
      { type: 'check', name: 'is_active', label: 'Promotion active' },
    ],
  },

  specialization: {
    singular: 'Spécialisation',
    searchPlaceholder: 'Code, nom…',
    defaultOrdering: 'code',
    columns: [
      { key: 'code', label: 'Code', sortKey: 'code' },
      { key: 'name', label: 'Nom', sortKey: 'name' },
      { key: 'track', label: 'Voie', sortKey: 'track', render: (row) => trackLabel(row.track) },
      { key: 'is_tronc_commun', label: 'Tronc commun', render: (row) => yesNo(row.is_tronc_commun) },
    ],
    emptyForm: { code: '', name: '', track: 'BOTH', is_tronc_commun: false, description: '' },
    toForm: (item) => ({
      code: item.code || '',
      name: item.name || '',
      track: item.track || 'BOTH',
      is_tronc_commun: !!item.is_tronc_commun,
      description: item.description || '',
    }),
    toPayload: (form) => ({
      code: form.code.trim(),
      name: form.name.trim(),
      track: form.track,
      is_tronc_commun: !!form.is_tronc_commun,
      description: form.description || '',
    }),
    fields: [
      { type: 'text', name: 'code', label: 'Code', required: true },
      { type: 'text', name: 'name', label: 'Nom', required: true },
      { type: 'select', name: 'track', label: 'Voie', options: () => TRACK_OPTIONS.filter((o) => o.value !== ''), allowEmpty: false },
      { type: 'check', name: 'is_tronc_commun', label: 'Tronc commun' },
      { type: 'textarea', name: 'description', label: 'Description' },
    ],
  },

  teachingUnit: {
    singular: 'Unité d’enseignement',
    searchPlaceholder: 'Code, intitulé, département…',
    defaultOrdering: 'code',
    columns: [
      { key: 'code', label: 'Code', sortKey: 'code' },
      { key: 'name', label: 'Intitulé', sortKey: 'name' },
      { key: 'semester_number', label: 'Semestre', sortKey: 'semester_number', render: (row) => `S${row.semester_number}` },
      { key: 'credits_ects', label: 'Crédits', sortKey: 'credits_ects', render: (row) => `${row.credits_ects} ECTS` },
      { key: 'courses', label: 'ECUE', render: (row) => (row.courses?.length ?? 0) },
      { key: 'department', label: 'Département', render: (row, lookups) => row.department_name || lookups.departments.get(row.department)?.name || '—' },
    ],
    emptyForm: { department: '', code: '', name: '', credits_ects: 3, coefficient: 1, semester_number: 1, passing_score: 10, description: '' },
    toForm: (item) => ({
      department: item.department || '',
      code: item.code || '',
      name: item.name || '',
      credits_ects: item.credits_ects ?? 3,
      coefficient: item.coefficient ?? 1,
      semester_number: item.semester_number ?? 1,
      passing_score: item.passing_score ?? 10,
      description: item.description || '',
    }),
    toPayload: (form) => ({
      department: form.department,
      code: form.code.trim(),
      name: form.name.trim(),
      credits_ects: Number(form.credits_ects),
      coefficient: Number(form.coefficient),
      semester_number: Number(form.semester_number),
      passing_score: Number(form.passing_score),
      description: form.description || '',
    }),
    prefill: (snapshot) => ({ department: snapshot.departments?.[0]?.id || '' }),
    fields: [
      { type: 'select', name: 'department', label: 'Département', required: true, options: (s) => s.departments.map((d) => ({ value: d.id, label: `${d.code} — ${d.name}` })) },
      { type: 'text', name: 'code', label: 'Code', required: true },
      { type: 'text', name: 'name', label: 'Intitulé', required: true },
      { type: 'number', name: 'semester_number', label: 'Semestre', required: true, min: 1, max: 12 },
      { type: 'number', name: 'credits_ects', label: 'Crédits ECTS', required: true, min: 0 },
      { type: 'number', name: 'coefficient', label: 'Coefficient', min: 0, step: '0.1' },
      { type: 'number', name: 'passing_score', label: 'Note de validation (/20)', min: 0, max: 20, step: '0.5' },
      { type: 'textarea', name: 'description', label: 'Description' },
    ],
  },

  course: {
    singular: 'ECUE',
    searchPlaceholder: 'Code, intitulé, UE…',
    defaultOrdering: 'code',
    columns: [
      { key: 'code', label: 'Code', sortKey: 'code' },
      { key: 'name', label: 'Intitulé', sortKey: 'name' },
      { key: 'teaching_unit', label: 'UE', render: (row, lookups) => row.teaching_unit_code || lookups.teachingUnits.get(row.teaching_unit)?.code || '—' },
      { key: 'hours', label: 'CM / TD / TP', sortKey: 'hours_cm', render: (row) => `${row.hours_cm}h / ${row.hours_td}h / ${row.hours_tp}h` },
      { key: 'hours_total', label: 'Volume', render: (row) => `${row.hours_total ?? (row.hours_cm + row.hours_td + row.hours_tp)} h` },
    ],
    emptyForm: { teaching_unit: '', code: '', name: '', hours_cm: 0, hours_td: 0, hours_tp: 0, coefficient: 1, passing_score: 10 },
    toForm: (item) => ({
      teaching_unit: item.teaching_unit || '',
      code: item.code || '',
      name: item.name || '',
      hours_cm: item.hours_cm ?? 0,
      hours_td: item.hours_td ?? 0,
      hours_tp: item.hours_tp ?? 0,
      coefficient: item.coefficient ?? 1,
      passing_score: item.passing_score ?? 10,
    }),
    toPayload: (form) => ({
      teaching_unit: form.teaching_unit,
      code: form.code.trim(),
      name: form.name.trim(),
      hours_cm: Number(form.hours_cm) || 0,
      hours_td: Number(form.hours_td) || 0,
      hours_tp: Number(form.hours_tp) || 0,
      coefficient: Number(form.coefficient) || 1,
      passing_score: Number(form.passing_score),
    }),
    prefill: (snapshot) => ({ teaching_unit: snapshot.teaching_units?.[0]?.id || '' }),
    fields: [
      { type: 'select', name: 'teaching_unit', label: 'Unité d’enseignement', required: true, full: true, options: (s) => s.teaching_units.map((u) => ({ value: u.id, label: `S${u.semester_number} · ${u.code} — ${u.name}` })) },
      { type: 'text', name: 'code', label: 'Code', required: true },
      { type: 'text', name: 'name', label: 'Intitulé', required: true },
      { type: 'number', name: 'hours_cm', label: 'CM (h)', min: 0 },
      { type: 'number', name: 'hours_td', label: 'TD (h)', min: 0 },
      { type: 'number', name: 'hours_tp', label: 'TP (h)', min: 0 },
      { type: 'number', name: 'coefficient', label: 'Coefficient', min: 0, step: '0.1' },
      { type: 'number', name: 'passing_score', label: 'Note de validation (/20)', min: 0, max: 20, step: '0.5' },
    ],
  },

  programCourse: {
    singular: 'Ligne de maquette',
    searchPlaceholder: 'Programme, UE, spécialité…',
    defaultOrdering: 'semester_number',
    columns: [
      { key: 'program', label: 'Programme', render: (row, lookups) => lookups.programs.get(row.program)?.code || '—' },
      { key: 'teaching_unit', label: 'UE', render: (row, lookups) => {
        const unit = row.teaching_unit_detail || lookups.teachingUnits.get(row.teaching_unit)
        return unit ? `${unit.code} — ${unit.name}` : '—'
      } },
      { key: 'semester_number', label: 'Semestre', sortKey: 'semester_number', render: (row) => `S${row.semester_number}` },
      { key: 'specialization', label: 'Spécialité', render: (row, lookups) => row.specialization_detail?.code || lookups.specializations.get(row.specialization)?.code || 'Toutes' },
      { key: 'credits', label: 'Crédits', sortKey: 'credits_override', render: (row) => `${row.credits ?? row.credits_override ?? '—'} ECTS` },
      { key: 'is_mandatory', label: 'Obligatoire', render: (row) => yesNo(row.is_mandatory) },
    ],
    emptyForm: { program: '', teaching_unit: '', specialization: '', semester_number: 1, is_mandatory: true, credits_override: '' },
    toForm: (item) => ({
      program: item.program || '',
      teaching_unit: item.teaching_unit || '',
      specialization: item.specialization || '',
      semester_number: item.semester_number || 1,
      is_mandatory: item.is_mandatory !== false,
      credits_override: item.credits_override ?? '',
    }),
    toPayload: (form) => ({
      program: form.program,
      teaching_unit: form.teaching_unit,
      specialization: form.specialization || null,
      semester_number: Number(form.semester_number),
      is_mandatory: !!form.is_mandatory,
      credits_override: form.credits_override === '' ? null : Number(form.credits_override),
    }),
    prefill: (snapshot) => ({
      program: snapshot.programs?.[0]?.id || '',
      teaching_unit: snapshot.teaching_units?.[0]?.id || '',
    }),
    fields: [
      { type: 'select', name: 'program', label: 'Programme', required: true, options: (s) => s.programs.map((p) => ({ value: p.id, label: `${p.code} — ${p.name}` })) },
      { type: 'select', name: 'teaching_unit', label: 'Unité d’enseignement', required: true, options: (s) => s.teaching_units.map((u) => ({ value: u.id, label: `S${u.semester_number} · ${u.code} — ${u.name}` })) },
      { type: 'select', name: 'specialization', label: 'Spécialité', emptyLabel: 'Toutes les spécialités', options: (s) => s.specializations.map((sp) => ({ value: sp.id, label: `${sp.code} — ${sp.name}` })) },
      { type: 'number', name: 'semester_number', label: 'Semestre', required: true, min: 1, max: 12 },
      { type: 'number', name: 'credits_override', label: 'Crédits spécifiques', min: 0, placeholder: 'Hérités de l’UE si vide' },
      { type: 'check', name: 'is_mandatory', label: 'UE obligatoire' },
    ],
  },

  jobNomenclature: {
    singular: 'Nomenclature emploi',
    searchPlaceholder: 'Emploi, compétences, spécialité…',
    defaultOrdering: 'degree_type',
    columns: [
      { key: 'degree_type', label: 'Cycle', sortKey: 'degree_type', render: (row) => row.degree_type_display || row.degree_type || '—' },
      { key: 'specialization', label: 'Spécialité', render: (row, lookups) => row.specialization_detail?.code || lookups.specializations.get(row.specialization)?.code || '—' },
      { key: 'civil_service_grade', label: 'Grade', sortKey: 'civil_service_grade', render: (row) => row.civil_service_grade_display || row.civil_service_grade || '—' },
      { key: 'job_title', label: 'Emploi', sortKey: 'job_title' },
      { key: 'diploma_code', label: 'Diplôme', render: (row) => row.diploma_label || row.diploma_code || '—' },
    ],
  },
}

/**
 * Endpoints connus à l'avance pour charger la liste en parallèle de la vue
 * d'ensemble. Le backend reste la référence : il renvoie le même `endpoint`
 * dans `/referentiels/overview/`.
 */
export const RESOURCE_ENDPOINTS = {
  academicYear: '/academics/academic-years/',
  semester: '/academics/semesters/',
  institution: '/academics/institutions/',
  department: '/academics/departments/',
  program: '/academics/programs/',
  promotion: '/academics/promotions/',
  specialization: '/academics/specializations/',
  teachingUnit: '/academics/teaching-units/',
  course: '/academics/courses/',
  programCourse: '/academics/program-courses/',
  jobNomenclature: '/academics/job-nomenclatures/',
}

export const HEALTH_CHECKS = [
  { key: 'missing_current_year', level: 'danger', message: 'Aucune année académique courante : les modules Cours, Présences et Examens ne peuvent pas se positionner.', resource: 'academicYear' },
  { key: 'multiple_current_years', level: 'danger', message: 'Plusieurs années sont marquées « courante » pour une même institution.', resource: 'academicYear' },
  { key: 'missing_current_semester', level: 'warning', message: 'Aucun semestre courant défini.', resource: 'semester' },
  { key: 'years_without_semester', level: 'warning', message: 'année(s) académique(s) sans aucun semestre.', countable: true, resource: 'semester' },
  { key: 'programs_without_promotion', level: 'warning', message: 'programme(s) sans promotion rattachée.', countable: true, resource: 'promotion' },
  { key: 'programs_without_maquette', level: 'warning', message: 'programme(s) sans maquette pédagogique.', countable: true, resource: 'programCourse' },
  { key: 'units_without_course', level: 'info', message: 'UE sans aucun ECUE.', countable: true, resource: 'course' },
  { key: 'units_outside_maquette', level: 'info', message: 'UE absente(s) de toute maquette.', countable: true, resource: 'programCourse' },
]
