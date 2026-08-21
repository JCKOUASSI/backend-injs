# Schéma Base de Données INJS-LMD

## Entités principales

### accounts
- `User` (email, password argon2, photo, MFA, institution FK, department FK)
- `Group` (Django natif) + `GroupProfile` (code métier, level 0–4, is_active)
- `ModulePermissionRegistry` (catalogue des permissions `accounts.{module}_{action}`)
- `AuditLog` (user, action, module, object_type, ip, timestamp)

Permissions exposées en API : `{module}.{action}` (ex. `students.view`, `reports.export_pdf`).

### academics
- `Institution`, `Department`, `Program` (filière L/M/D, track PL/PC)
- `Specialization` (TC, EM, ES, MS, APA — spécialités STAPS)
- `Promotion`, `AcademicYear`, `Semester`
- `TeachingUnit` (UE), `Course` (ECUE)
- `ProgramCourse` (liaison filière ↔ UE ↔ spécialité + crédits ECTS)
- `FormationPeriod` (fenêtre de planification EDT), `Holiday`
- `StapsJobNomenclature` (emplois A3/A4, diplômes CAPS/CAPEPS/CAPCS/CAPCEPS)

### students
- `Student` (user FK, matricule, QR, filière, promotion, spécialisation)
- `Enrollment` (administrative/pédagogique, année, statut)
- `AcademicRecord` (historique non modifiable, snapshot délibération)

### faculty
- `Teacher` (user FK, grade académique, département)
- `CourseAssignment`, `Schedule` (gabarit hebdomadaire), `Room`
- `Seance` (séance datée), `TeachingLoad`, `StudentGroup`, `PlanningSettings`, `TimetableRun`
- `Attendance`, `StaffAttendance`, `AttendanceSession`, `BadgeEvent`

### exams
- `ExamSession` (normale/rattrapage, année, semestre)
- `Evaluation` (CC, CT, examen), `Grade`
- `Deliberation`, `Jury`, `Defense` (soutenance)

### finance
- `FeeType`, `StudentFee`, `Payment`, `PaymentTransaction`
- `PaymentProviderConfig`

### reports
- Services de génération (relevé PDF semestriel, analytics, exports)

## Nomenclature emplois STAPS

`StapsJobNomenclature` — unique par `(degree_type, specialization)` :

| Formation | Grade | Voie | Diplômes |
|-----------|-------|------|----------|
| Licence (L) | A3 | Collège (PC) | CAPCS, CAPCEPS |
| Master (M) | A4 | Lycée (PL) | CAPS, CAPEPS |

Import : `python manage.py import_nomenclature_staps --replace`

## Relations clés

```
Institution 1─N Department 1─N Program 1─N Promotion
Program 1─N ProgramCourse N─1 TeachingUnit
ProgramCourse N─1 Specialization (optionnel, filtrage LMD)
TeachingUnit 1─N Course (ECUE)
Student N─1 Program, N─1 Promotion, N─1 Specialization
FormationPeriod N─1 AcademicYear, N─1 Program
Seance N─1 Course, N─1 Promotion, N─1 FormationPeriod
Attendance N─1 Student, N─1 Schedule, N─1 Seance
BadgeEvent N─1 Attendance
Enrollment N─1 Student, N─1 AcademicYear
Grade N─1 Student, N─1 Evaluation
StapsJobNomenclature N─1 Specialization
User M─N Group (via GroupProfile.level pour hiérarchie RBAC)
Payment N─1 StudentFee, N─1 PaymentTransaction
```

## Maquette STAPS 2026

Import depuis `elements/MAQUETTE REVISEE TC EM ES MS APA LMD PROFESSEUR DE LYCEE ET DE COLLEGE 2026 CONSOLIDEE.docx` :

- Filières : `L-STAPS-PL` (Professeur de Lycée), `L-STAPS-PC` (Professeur de Collège)
- ~88 UE, ~135 ECUE répartis par semestre et spécialité

Commande : `python manage.py import_maquette_staps2026 --replace`

## Index recommandés

- `students_student(matricule)` UNIQUE
- `accounts_user(email)` UNIQUE
- `exams_grade(student_id, evaluation_id)` UNIQUE
- `students_enrollment(student_id, academic_year_id, enrollment_type)` UNIQUE
- `academics_stapsjobnomenclature(degree_type, specialization_id)` UNIQUE
- `academics_programcourse(program_id, teaching_unit_id, specialization_id)` UNIQUE
