import { FiChevronLeft, FiChevronRight } from 'react-icons/fi'

/**
 * Pagination style « Précédent · pages · plage · Suivant »
 * (inspirée du modèle fourni).
 */
export default function PaginationBar({
  page = 1,
  pageSize = 50,
  total = 0,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [25, 50, 100],
  disabled = false,
  className = '',
}) {
  const totalPages = Math.max(1, Math.ceil((total || 0) / pageSize))
  const current = Math.min(Math.max(1, page), totalPages)
  const from = total === 0 ? 0 : (current - 1) * pageSize + 1
  const to = Math.min(current * pageSize, total)
  const pages = visiblePages(current, totalPages)

  const go = (p) => {
    if (disabled || p < 1 || p > totalPages || p === current) return
    onPageChange(p)
  }

  return (
    <div className={`injs-pagination ${className}`.trim()}>
      <div className="injs-pagination-inner">
        <button
          type="button"
          className="injs-page-nav"
          disabled={current <= 1 || disabled}
          onClick={() => go(current - 1)}
          aria-label="Page précédente"
        >
          <FiChevronLeft size={16} aria-hidden />
          <span>Précédent</span>
        </button>

        <div className="injs-page-numbers" role="navigation" aria-label="Pages">
          {pages.map((p, idx) => (
            p === '…' ? (
              <span key={`e-${idx}`} className="injs-page-ellipsis" aria-hidden>…</span>
            ) : (
              <button
                key={p}
                type="button"
                className={`injs-page-num ${p === current ? 'is-active' : ''}`}
                disabled={disabled}
                aria-current={p === current ? 'page' : undefined}
                onClick={() => go(p)}
              >
                {p}
              </button>
            )
          ))}
        </div>

        <span className="injs-page-range">
          {from}–{to} sur {total.toLocaleString('fr-FR')}
        </span>

        <button
          type="button"
          className="injs-page-nav"
          disabled={current >= totalPages || disabled}
          onClick={() => go(current + 1)}
          aria-label="Page suivante"
        >
          <span>Suivant</span>
          <FiChevronRight size={16} aria-hidden />
        </button>
      </div>

      {onPageSizeChange && (
        <label className="injs-page-size mb-0">
          <span className="visually-hidden">Par page</span>
          <select
            className="form-select form-select-sm"
            value={pageSize}
            disabled={disabled}
            onChange={(ev) => onPageSizeChange(Number(ev.target.value))}
            title="Éléments par page"
          >
            {pageSizeOptions.map((n) => (
              <option key={n} value={n}>{n} / page</option>
            ))}
          </select>
        </label>
      )}
    </div>
  )
}

/** Affiche 1, 2, 3 … dernière (comme le modèle) près du début ; fenêtre autour de la page courante sinon. */
function visiblePages(current, totalPages) {
  if (totalPages <= 5) {
    return Array.from({ length: totalPages }, (_, i) => i + 1)
  }

  // Début : 1 2 3 … N
  if (current <= 3) {
    return [1, 2, 3, '…', totalPages]
  }

  // Fin : 1 … N-2 N-1 N
  if (current >= totalPages - 2) {
    return [1, '…', totalPages - 2, totalPages - 1, totalPages]
  }

  // Milieu : 1 … c-1 c c+1 … N
  return [1, '…', current - 1, current, current + 1, '…', totalPages]
}
