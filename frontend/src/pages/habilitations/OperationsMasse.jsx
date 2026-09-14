/**
 * OperationsMasse — import tabulaire avec PRÉVISUALISATION INTÉGRALE et
 * rapport ligne à ligne. L'écriture en une transaction et la réversibilité
 * sont livrées à l'unité U5 : le bouton d'écriture est volontairement masqué.
 */
import { useState } from 'react'
import { simulerImport } from '@/services/habilitations'
import { analyserCsv, lignesCsvVersImport } from '@/utils/habilitations'
import { messageErreur } from '@/services/habilitations'
import './habilitations.css'

const ENTETE = 'identifiant;nom;prenoms;email;mot_de_passe;roles;canal'
const EXEMPLE = 'curp_demo1;Traore;Salif;demo1@injs.ci;Essai#2026;ENSEIGNANT;MOBILE'

function telechargerModele() {
  const blob = new Blob([`${ENTETE}\n${EXEMPLE}\n`], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'modele_import_comptes.csv'
  a.click()
  URL.revokeObjectURL(url)
}

export default function OperationsMasse() {
  const [rapport, setRapport] = useState(null)
  const [enCours, setEnCours] = useState(false)
  const [erreur, setErreur] = useState('')

  const lireFichier = async (fichier) => {
    setEnCours(true)
    setErreur('')
    try {
      const texte = await fichier.text()
      const lignes = lignesCsvVersImport(analyserCsv(texte))
      if (lignes.length === 0) {
        setErreur("Le fichier ne contient aucune ligne de données.")
      } else {
        setRapport(await simulerImport(lignes))
      }
    } catch (e) {
      setErreur(messageErreur(e, "Lecture du fichier impossible."))
    } finally {
      setEnCours(false)
    }
  }

  return (
    <section data-testid="ecran-operations-masse">
      <div className="hab-carte">
        <h2 className="h5">Création de comptes en masse</h2>
        <div className="hab-avertissement">
          <i className="bi bi-info-circle me-1" />
          Aperçu uniquement : la création effective en une transaction, le rejeu de l'import
          corrigé et la réversibilité sont prévus à l'unité <strong>U5</strong>. Aucune ligne
          n'est écrite à ce stade.
        </div>
        <div className="d-flex gap-2 align-items-center flex-wrap">
          <input type="file" accept=".csv,text/csv" className="form-control" style={{ maxWidth: 420 }}
                 data-testid="fichier-import"
                 onChange={(e) => e.target.files[0] && lireFichier(e.target.files[0])} />
          <button type="button" className="btn btn-outline-secondary btn-sm" onClick={telechargerModele}>
            <i className="bi bi-download me-1" />Modèle CSV
          </button>
        </div>
        {enCours && <p className="hab-muted mt-2">Analyse et prévisualisation…</p>}
        {erreur && <p className="text-danger mt-2">{erreur}</p>}
      </div>

      {rapport && (
        <div className="hab-carte" data-testid="rapport-import">
          <h3 className="h6">Rapport de prévisualisation</h3>
          <p>
            {rapport.total} ligne(s) · <span className="hab-diff-gagne">{rapport.valides} valide(s)</span> ·{' '}
            <span className="hab-diff-perdu">{rapport.erreurs} en erreur</span>
          </p>
          <table className="hab-table">
            <thead><tr><th>Ligne</th><th>Identifiant</th><th>Nom</th><th>Rôles</th><th>État / problèmes</th></tr></thead>
            <tbody>
              {rapport.lignes.map((l) => (
                <tr key={l.numero} data-testid={`ligne-import-${l.numero}`}>
                  <td>{l.numero}</td>
                  <td>{l.valeurs.username}</td>
                  <td>{[l.valeurs.prenoms, l.valeurs.nom].filter(Boolean).join(' ')}</td>
                  <td>{l.valeurs.roles}</td>
                  <td>
                    {l.etat === 'VALIDE'
                      ? <span className="hab-diff-gagne">Valide{l.roles ? ` — ${l.roles.join(', ')}` : ''}</span>
                      : <span className="hab-diff-perdu">{l.problemes.join(' ')}</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <button className="btn btn-secondary mt-2" disabled title="Écriture en une transaction livrée à U5"
                  data-testid="bouton-ecrire">
            <i className="bi bi-lock me-1" />Créer les comptes (disponible en U5)
          </button>
        </div>
      )}
    </section>
  )
}
