import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import MainLayout from '../components/layout/MainLayout'
import ProtectedRoute from './ProtectedRoute'
import Login from '../pages/auth/Login'

import AdminDashboard from '../pages/admin/Dashboard'
import AdminStudents from '../pages/admin/Students'
import AdminProfessors from '../pages/admin/Professors'
import AdminDepartments from '../pages/admin/Departments'
import AdminFormations from '../pages/admin/Formations'
import AdminImportExcel from '../pages/admin/ImportExcel'
import AdminReferentiels from '../pages/admin/Referentiels'
import AdminUE from '../pages/admin/UE'
import AdminGrades from '../pages/admin/Grades'
import AdminInternships from '../pages/admin/Internships'
import AdminEvents from '../pages/admin/Events'
import AdminFinances from '../pages/admin/Finances'
import AdminReports from '../pages/admin/Reports'
import AdminStatistiques from '../pages/admin/Statistiques'
import AdminSettings from '../pages/admin/Settings'
import AdminAdmissions from '../pages/admin/Admissions'
import AdminRooms from '../pages/admin/Rooms'
import AdminReservations from '../pages/admin/Reservations'
import AdminMaintenance from '../pages/admin/Maintenance'
import AdminEquipment from '../pages/admin/Equipment'
import AdminCampusMap from '../pages/admin/CampusMap'

import ProfDashboard from '../pages/professor/Dashboard'
import ProfStudents from '../pages/professor/Students'
import ProfEvaluations from '../pages/professor/Evaluations'
import ProfInternships from '../pages/professor/Internships'
import ProfResearch from '../pages/professor/Research'
import ProfDocuments from '../pages/professor/Documents'
import ProfessorRooms from '../pages/professor/Rooms'

import StudentDashboard from '../pages/student/Dashboard'
import StudentParcours from '../pages/student/Parcours'
import StudentGrades from '../pages/student/Grades'
import StudentInternships from '../pages/student/Internships'
import StudentDocuments from '../pages/student/Documents'
import StudentInscriptions from '../pages/student/Inscriptions'
import StudentPayments from '../pages/student/Payments'

// Module EPT-INJS : emplois du temps, cours (ECUE), présences et badgeage.
import EptEmploiDuTemps from '@eptinjs/pages/admin/EmploiDuTemps'
import EptCours from '@eptinjs/pages/admin/Cours'
import EptCoursDetail from '@eptinjs/pages/admin/CoursDetail'
import EptPresences from '@eptinjs/pages/admin/Presences'
import EptProfPlanning from '@eptinjs/pages/professeur/MonEmploiDuTemps'
import EptProfCours from '@eptinjs/pages/professeur/MesCours'
import EptProfPresences from '@eptinjs/pages/professeur/MesPresences'
import EptEtudiantPlanning from '@eptinjs/pages/etudiant/MonEmploiDuTemps'
import EptEtudiantCours from '@eptinjs/pages/etudiant/MesCours'
import EptBadgeage from '@eptinjs/pages/etudiant/Badgeage'
import '@eptinjs/styles/eptinjs.css'

function HomeRedirect() {
  const { isAuthenticated, user } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <Navigate to={`/${user.role}`} replace />
}

function RedirectPreserveQuery({ to }) {
  const { search, hash } = useLocation()
  return <Navigate to={`${to}${search}${hash}`} replace />
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<HomeRedirect />} />

      <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
        <Route element={<MainLayout />}>
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/admin/etudiants" element={<AdminStudents />} />
          <Route path="/admin/professeurs" element={<AdminProfessors />} />
          <Route path="/admin/departements" element={<AdminDepartments />} />
          <Route path="/admin/formations" element={<AdminFormations />} />
          <Route path="/admin/import-excel" element={<AdminImportExcel />} />
          <Route path="/admin/referentiels" element={<AdminReferentiels />} />
          <Route path="/admin/ue" element={<AdminUE />} />
          <Route path="/admin/cours" element={<EptCours />} />
          <Route path="/admin/cours/:offeringId" element={<EptCoursDetail />} />
          <Route path="/admin/notes" element={<AdminGrades />} />
          <Route path="/admin/emploi-du-temps" element={<EptEmploiDuTemps />} />
          <Route path="/admin/presences" element={<EptPresences />} />
          <Route path="/admin/badgeage" element={<RedirectPreserveQuery to="/admin/presences" />} />
          <Route path="/admin/salles" element={<AdminRooms />} />
          <Route path="/admin/stages" element={<AdminInternships />} />
          <Route path="/admin/reservations" element={<AdminReservations />} />
          <Route path="/admin/maintenance" element={<AdminMaintenance />} />
          <Route path="/admin/equipements" element={<AdminEquipment />} />
          <Route path="/admin/carte-campus" element={<AdminCampusMap />} />
          <Route path="/admin/evenements" element={<AdminEvents />} />
          <Route path="/admin/finances" element={<AdminFinances />} />
          <Route path="/admin/statistiques" element={<AdminStatistiques />} />
          <Route path="/admin/rapports" element={<AdminReports />} />
          <Route path="/admin/parametres" element={<AdminSettings />} />
          <Route path="/admin/admissions" element={<AdminAdmissions />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allowedRoles={['professeur']} />}>
        <Route element={<MainLayout />}>
          <Route path="/professeur" element={<ProfDashboard />} />
          <Route path="/professeur/cours" element={<EptProfCours />} />
          <Route
            path="/professeur/cours/:offeringId"
            element={<EptCoursDetail baseRetour="/professeur/cours" />}
          />
          <Route path="/professeur/emploi-du-temps" element={<EptProfPlanning />} />
          <Route path="/professeur/presences" element={<EptProfPresences />} />
          <Route path="/professeur/presence" element={<RedirectPreserveQuery to="/professeur/presences" />} />
          <Route path="/professeur/etudiants" element={<ProfStudents />} />
          <Route path="/professeur/salles" element={<ProfessorRooms />} />
          <Route path="/professeur/evaluations" element={<ProfEvaluations />} />
          <Route path="/professeur/stages" element={<ProfInternships />} />
          <Route path="/professeur/recherche" element={<ProfResearch />} />
          <Route path="/professeur/documents" element={<ProfDocuments />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allowedRoles={['etudiant']} />}>
        <Route element={<MainLayout />}>
          <Route path="/etudiant" element={<StudentDashboard />} />
          <Route path="/etudiant/parcours" element={<StudentParcours />} />
          <Route path="/etudiant/notes" element={<StudentGrades />} />
          <Route path="/etudiant/cours" element={<EptEtudiantCours />} />
          <Route
            path="/etudiant/cours/:offeringId"
            element={<EptCoursDetail peutGerer={false} baseRetour="/etudiant/cours" />}
          />
          <Route path="/etudiant/emploi-du-temps" element={<EptEtudiantPlanning />} />
          <Route path="/etudiant/presences" element={<EptBadgeage />} />
          <Route path="/etudiant/badgeage" element={<RedirectPreserveQuery to="/etudiant/presences" />} />
          <Route path="/etudiant/stages" element={<StudentInternships />} />
          <Route path="/etudiant/documents" element={<StudentDocuments />} />
          <Route path="/etudiant/paiements" element={<StudentPayments />} />
          <Route path="/etudiant/inscriptions" element={<StudentInscriptions />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
