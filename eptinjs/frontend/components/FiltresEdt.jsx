/** Barre de filtres commune aux vues d'emploi du temps. */
import { NATURES_SEANCE, STATUTS_SEANCE } from '../api/eptinjs'

function Champ({ label, children }) {
  return (
    <div className="d-flex flex-column">
      <span className="form-label">{label}</span>
      {children}
    </div>
  )
}

export default function FiltresEdt({
  valeurs,
  onChange,
  periodes = [],
  promotions = [],
  salles = [],
  enseignants = [],
  champs = ['periode', 'promotion', 'teacher', 'room', 'session_kind', 'statut', 'dates'],
  extra,
}) {
  const modifier = (champ) => (event) => onChange({ ...valeurs, [champ]: event.target.value })
  const actif = (champ) => champs.includes(champ)

  return (
    <div className="ept-toolbar mb-3">
      {actif('periode') && (
        <Champ label="Période de formation">
          <select className="form-select form-select-sm" value={valeurs.periode || ''} onChange={modifier('periode')}>
            <option value="">Toutes les périodes</option>
            {periodes.map((periode) => (
              <option key={periode.id} value={periode.id}>
                {periode.code} — {periode.libelle}
              </option>
            ))}
          </select>
        </Champ>
      )}

      {actif('promotion') && (
        <Champ label="Promotion">
          <select
            className="form-select form-select-sm"
            value={valeurs.promotion || ''}
            onChange={modifier('promotion')}
          >
            <option value="">Toutes</option>
            {promotions.map((promotion) => (
              <option key={promotion.id} value={promotion.id}>{promotion.name}</option>
            ))}
          </select>
        </Champ>
      )}

      {actif('teacher') && (
        <Champ label="Enseignant">
          <select className="form-select form-select-sm" value={valeurs.teacher || ''} onChange={modifier('teacher')}>
            <option value="">Tous</option>
            {enseignants.map((item) => (
              <option key={item.id} value={item.id}>{item.nom}</option>
            ))}
          </select>
        </Champ>
      )}

      {actif('room') && (
        <Champ label="Salle">
          <select className="form-select form-select-sm" value={valeurs.room || ''} onChange={modifier('room')}>
            <option value="">Toutes</option>
            {salles.map((salle) => (
              <option key={salle.id} value={salle.id}>{salle.code}</option>
            ))}
          </select>
        </Champ>
      )}

      {actif('session_kind') && (
        <Champ label="Nature">
          <select
            className="form-select form-select-sm"
            value={valeurs.session_kind || ''}
            onChange={modifier('session_kind')}
          >
            <option value="">Toutes</option>
            {NATURES_SEANCE.map((nature) => (
              <option key={nature.value} value={nature.value}>{nature.label}</option>
            ))}
          </select>
        </Champ>
      )}

      {actif('statut') && (
        <Champ label="Statut">
          <select className="form-select form-select-sm" value={valeurs.statut || ''} onChange={modifier('statut')}>
            <option value="">Tous</option>
            {STATUTS_SEANCE.map((statut) => (
              <option key={statut.value} value={statut.value}>{statut.label}</option>
            ))}
          </select>
        </Champ>
      )}

      {actif('dates') && (
        <>
          <Champ label="Du">
            <input
              type="date" className="form-control form-control-sm"
              value={valeurs.date_debut || ''} onChange={modifier('date_debut')}
            />
          </Champ>
          <Champ label="Au">
            <input
              type="date" className="form-control form-control-sm"
              value={valeurs.date_fin || ''} onChange={modifier('date_fin')}
            />
          </Champ>
        </>
      )}

      {extra}
    </div>
  )
}
