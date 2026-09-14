/**
 * Gabarit de la console CURP (U4) : garde dérivée des capacités backend
 * (``habilitations_admin.gerer``), bandeau de traçabilité permanent et
 * navigation latérale entre les onze écrans. La console est entièrement
 * nouvelle ; elle ne remplace pas l'écran Utilisateurs existant.
 */
import { NavLink, Outlet } from 'react-router-dom'
import { useDroits } from '@/hooks/useDroits'
import { BandeauTraçabilite, Message403 } from './partages'

const LIENS = [
  { to: '/administration/comptes', fin: true, icone: 'bi-people', libelle: 'Comptes' },
  { to: '/administration/comptes/nouveau', icone: 'bi-person-plus', libelle: 'Nouveau compte' },
  { to: '/administration/comptes/roles', icone: 'bi-person-badge', libelle: 'Rôles' },
  { to: '/administration/comptes/matrice', icone: 'bi-grid-3x3-gap', libelle: 'Matrice des permissions' },
  { to: '/administration/comptes/derogations', icone: 'bi-key', libelle: 'Dérogations' },
  { to: '/administration/comptes/delegations', icone: 'bi-person-check', libelle: 'Délégations' },
  { to: '/administration/comptes/operations-masse', icone: 'bi-upload', libelle: 'Opérations en masse' },
  { to: '/administration/comptes/revue', icone: 'bi-clipboard-check', libelle: 'Revue des habilitations' },
  { to: '/administration/comptes/journal', icone: 'bi-journal-text', libelle: 'Journal' },
]

export default function HabilitationsLayout() {
  const droits = useDroits()
  const autorise = droits.peut('habilitations_admin', 'gerer')

  if (!droits.charge) {
    return <p className="hab-muted"><div className="spinner-border spinner-border-sm me-2" />Vérification des droits…</p>
  }
  if (!autorise) {
    return (
      <div className="container py-3">
        <Message403 detail="La console est réservée aux administrateurs de l'habilitation et doit être activée par le drapeau CURP_UI_ADMIN." />
      </div>
    )
  }

  return (
    <div className="container-fluid py-3">
      <BandeauTraçabilite />
      <h2 className="h4 mt-2 mb-3">
        <i className="bi bi-shield-lock me-2" />Administration des comptes — CURP
      </h2>
      <div className="hab-layout">
        <nav className="hab-nav" aria-label="Navigation de la console d'habilitation">
          {LIENS.map((lien) => (
            <NavLink
              key={lien.to}
              to={lien.to}
              end={lien.fin}
              className={({ isActive }) => (isActive ? 'active' : '')}
            >
              <i className={`bi ${lien.icone}`} />{lien.libelle}
            </NavLink>
          ))}
        </nav>
        <div className="hab-contenu">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
