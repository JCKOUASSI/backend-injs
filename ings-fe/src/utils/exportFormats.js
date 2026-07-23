import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'
import { getAccessToken } from '../api/client'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/** Export tableau côté client → Excel (CSV UTF-8 BOM, ouvrable dans Excel). */
export function exportTableToExcel(filename, headers, rows) {
  const lines = [
    headers.map((h) => `"${String(h).replace(/"/g, '""')}"`).join(';'),
    ...rows.map((row) => row.map((cell) => `"${String(cell ?? '').replace(/"/g, '""')}"`).join(';')),
  ]
  const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  downloadBlob(blob, `${filename}.csv`)
}

/** Export tableau côté client → PDF (jsPDF). */
export function exportTableToPdf(filename, title, headers, rows) {
  const doc = new jsPDF({ orientation: headers.length > 5 ? 'landscape' : 'portrait' })
  doc.setFontSize(14)
  doc.text(title || 'Export INJS', 14, 16)
  doc.setFontSize(9)
  doc.text(`Généré le ${new Date().toLocaleString('fr-FR')} — INJS-LMD`, 14, 22)
  autoTable(doc, {
    startY: 28,
    head: [headers],
    body: rows,
    styles: { fontSize: 8 },
    headStyles: { fillColor: [51, 73, 161] },
  })
  doc.save(`${filename}.pdf`)
}

/** Export tableau côté client → Word (HTML .doc compatible MS Word). */
export function exportTableToWord(filename, title, headers, rows) {
  const thead = headers.map((h) => `<th>${escapeHtml(h)}</th>`).join('')
  const tbody = rows
    .map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join('')}</tr>`)
    .join('')
  const html = `
<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word">
<head><meta charset="utf-8"><title>${escapeHtml(title)}</title></head>
<body>
  <h1>${escapeHtml(title || 'Export INJS')}</h1>
  <p>Généré le ${new Date().toLocaleString('fr-FR')} — INJS Abidjan / UFR STAPS-JL</p>
  <table border="1" cellspacing="0" cellpadding="6" style="border-collapse:collapse;width:100%">
    <thead><tr>${thead}</tr></thead>
    <tbody>${tbody}</tbody>
  </table>
</body>
</html>`
  const blob = new Blob(['\ufeff' + html], { type: 'application/msword;charset=utf-8' })
  downloadBlob(blob, `${filename}.doc`)
}

/**
 * Télécharge un export backend ExportMixin :
 * GET /api/v1/{resource}/export/{pdf|excel|word}/
 */
export async function downloadBackendExport(resourcePath, format, fallbackFilename = 'export_injs') {
  const token = getAccessToken()
  const path = resourcePath.replace(/\/$/, '')
  const url = `${API_BASE}${path}/export/${format}/`
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Export ${format} impossible (${res.status})`)
  }
  const blob = await res.blob()
  const disposition = res.headers.get('Content-Disposition') || ''
  const match = disposition.match(/filename="?([^"]+)"?/)
  const filename = match?.[1] || `${fallbackFilename}.${format === 'excel' ? 'xlsx' : format === 'word' ? 'docx' : 'pdf'}`
  downloadBlob(blob, filename)
}

/** Télécharge un fichier binaire authentifié (ex. relevé PDF). */
export async function downloadAuthenticatedFile(apiPath, filename) {
  const token = getAccessToken()
  const url = apiPath.startsWith('http') ? apiPath : `${API_BASE}${apiPath}`
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error(`Téléchargement impossible (${res.status})`)
  const blob = await res.blob()
  downloadBlob(blob, filename)
}
