import { buildPaginationItems } from '../utils/paginationPages'

/**
 * @param {number} page — page courante (1-based)
 * @param {number} totalPages
 * @param {(page: number) => void} onPageChange
 * @param {number} [totalItems] — libellé « x–y sur z »
 * @param {number} [pageSize]
 * @param {string} [className]
 * @param {string} [activeClassName] — ex. pagination-num--finance
 */
export default function Pagination({
  page,
  totalPages,
  onPageChange,
  totalItems,
  pageSize,
  className = '',
  activeClassName = '',
}) {
  if (totalPages <= 1) return null

  const items = buildPaginationItems(page, totalPages)
  const activeNumClass = activeClassName || 'pagination-num--active'

  let rangeLabel = null
  if (totalItems != null && pageSize != null && totalItems > 0) {
    const from = (page - 1) * pageSize + 1
    const to = Math.min(page * pageSize, totalItems)
    rangeLabel = `${from}–${to} sur ${totalItems}`
  }

  return (
    <div className={`pagination ${className}`.trim()}>
      <button
        type="button"
        className="pagination-btn"
        onClick={() => onPageChange(Math.max(1, page - 1))}
        disabled={page === 1}
        aria-label="Page précédente"
      >
        <i className="bi bi-chevron-left" aria-hidden /> Précédent
      </button>

      <div className="pagination-pages" role="navigation" aria-label="Pages">
        {items.map((item, idx) =>
          item === '…' ? (
            <span key={`ellipsis-${idx}`} className="pagination-ellipsis" aria-hidden>
              …
            </span>
          ) : (
            <button
              key={item}
              type="button"
              className={`pagination-btn pagination-num ${item === page ? activeNumClass : ''}`}
              onClick={() => onPageChange(item)}
              aria-label={`Page ${item}`}
              aria-current={item === page ? 'page' : undefined}
            >
              {item}
            </button>
          ),
        )}
      </div>

      {rangeLabel && <span className="pagination-summary">{rangeLabel}</span>}

      <button
        type="button"
        className="pagination-btn"
        onClick={() => onPageChange(Math.min(totalPages, page + 1))}
        disabled={page === totalPages}
        aria-label="Page suivante"
      >
        Suivant <i className="bi bi-chevron-right" aria-hidden />
      </button>
    </div>
  )
}
