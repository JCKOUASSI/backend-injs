import { FaFilePdf, FaFileExcel, FaFileWord } from 'react-icons/fa'
import { useToast } from '../../context/ToastContext'
import {
  exportTableToExcel,
  exportTableToPdf,
  exportTableToWord,
  downloadBackendExport,
} from '../../utils/exportFormats'

/**
 * Boutons d'export PDF / Excel / Word (icônes colorées par type).
 * - mode "client" : headers + rows (tableaux UI)
 * - mode "backend" : resourcePath vers ExportMixin (ex. /students)
 * - onExport : handler custom (format) => void|Promise — pas de toast automatique
 */
export default function ExportButtons({
  title = 'Exportation INJS',
  filename = 'export_injs',
  headers = [],
  rows = [],
  resourcePath = null,
  resourceParams = {},
  onExport = null,
  size = 'sm',
  className = '',
  iconOnly = false,
}) {
  const { showToast } = useToast()

  const run = async (format) => {
    try {
      if (onExport) {
        await onExport(format)
        return
      }
      if (resourcePath) {
        await downloadBackendExport(resourcePath, format, filename, resourceParams)
      } else {
        if (!headers.length) {
          showToast('Aucune donnée à exporter', 'warning')
          return
        }
        if (format === 'pdf') exportTableToPdf(filename, title, headers, rows)
        else if (format === 'excel') exportTableToExcel(filename, headers, rows)
        else exportTableToWord(filename, title, headers, rows)
      }
      showToast(`Exportation ${format.toUpperCase()} prête`, 'success')
    } catch (err) {
      showToast(err.message || `Échec exportation ${format}`, 'danger')
    }
  }

  const base = `btn btn-${size} d-inline-flex align-items-center gap-1 export-format-btn`

  return (
    <div className={`btn-group export-buttons ${className}`} role="group" aria-label="Exports">
      <button
        type="button"
        className={`${base} export-btn-pdf`}
        onClick={() => run('pdf')}
        title="Exporter PDF"
        aria-label="Exporter PDF"
      >
        <FaFilePdf size={iconOnly ? 16 : 15} />
        {!iconOnly && <span>PDF</span>}
      </button>
      <button
        type="button"
        className={`${base} export-btn-excel`}
        onClick={() => run('excel')}
        title="Exporter Excel"
        aria-label="Exporter Excel"
      >
        <FaFileExcel size={iconOnly ? 16 : 15} />
        {!iconOnly && <span>Excel</span>}
      </button>
      <button
        type="button"
        className={`${base} export-btn-word`}
        onClick={() => run('word')}
        title="Exporter Word"
        aria-label="Exporter Word"
      >
        <FaFileWord size={iconOnly ? 16 : 15} />
        {!iconOnly && <span>Word</span>}
      </button>
    </div>
  )
}
