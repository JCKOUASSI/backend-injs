# Gestion des Emplois du Temps (EDT) — INJS-LMD

Le module EDT est **natif** à `backend-injs-main`. Il ne s’appuie plus sur eptcpfaefinal (`:8000`). L’interface unique est `http://127.0.0.1:5173`.

Chaîne produit :

```
Année académique → Formation → Promotion → Période → UE → ECUE
    → Séance datée → Cours (catalogue) → Présence → Badgeage
```

---

## 1. Architecture cible

Rien n’est dupliqué : les étudiants, professeurs, ECUE, promotions et salles restent ceux de LMD.

| Rôle | Où |
|------|----|
| Période de formation, jours fériés | `apps.academics` (`FormationPeriod`, `Holiday`) |
| Moteur, séances, présences, badgeages | `apps.faculty` |
| Catalogue Cours | `apps.academics.services.cours` lit les `Seance` publiées |
| UI admin / prof / étudiant | `ings-fe` (`/admin/emploi-du-temps`, grilles prof/étudiant) |

`Schedule` (grille hebdomadaire) est **conservé** comme gabarit. `Seance` est l’unité datée de l’EDT, des cours et du badgeage.

---

## 2. Modèles

### Académique
- **FormationPeriod** — fenêtre de planification (dates, rythme `full|w1|w1_2|w1_3`), liée à une année et optionnellement à une filière.
- **Holiday** — jour exclu de la génération.

### Faculty
- **PlanningSettings** — horaires, jours ouvrés, durée de séance, règles de retard / partiel / auto-absence.
- **StudentGroup** / **StudentGroupMember** / **GroupSchedulingConfig** — sous-groupes TD/TP.
- **TeachingLoad** — volume à placer (ECUE × promotion × groupe × CM/TD/TP).
- **Seance** — séance datée (`draft|generated|validated|published|in_progress|done|cancelled|archived`).
- **TimetableRun** — trace d’une génération.
- **Attendance** — état courant d’un étudiant (entrée, sortie, durée, retard).
- **StaffAttendance** — formateur / encadrant.
- **BadgeEvent** — journal **immuable** (entrée, sortie, forçage, correction, auto-absence).
- **AttendanceSession** — séance de badgeage QR encore liée au gabarit `Schedule`.

---

## 3. Relations

```
AcademicYear 1─N FormationPeriod 1─N Seance
Program 1─N Promotion 1─N StudentGroup
Course (ECUE) 1─N TeachingLoad 1─N Seance
CourseAssignment 1─N Schedule (gabarit hebdo)
Schedule 1─N Seance (si étendu depuis le gabarit)
Seance 1─N Attendance, StaffAttendance, BadgeEvent
Attendance 1─N BadgeEvent
```

Deux groupes de la même promotion peuvent se croiser. Une séance **sans groupe** (promotion entière) bloque tous les groupes.

---

## 4. API

Base : `/api/v1` (JWT). Port local habituel **8002**.

| Méthode | Route | Rôle |
|---------|--------|------|
| CRUD | `/academics/formation-periods/` | Périodes |
| CRUD | `/academics/holidays/` | Jours fériés |
| GET | `/faculty/seances/` | Liste (filtrée par rôle) |
| POST | `/faculty/seances/generate/` | Générer (planificateur) |
| POST | `/faculty/seances/expand/` | Étendre le gabarit hebdo |
| POST | `/faculty/seances/publish/` | Publier |
| GET | `/faculty/seances/conflicts/` | Conflits |
| GET | `/faculty/seances/dashboard/` | Compteurs |
| GET | `/faculty/seances/{id}/qr/` | QR de badgeage (`INJS:SEANCE:{uuid}`) |
| GET | `/faculty/seances/export/{pdf\|excel\|word}/` | Export EDT (filtres période / promotion / dates) |
| CRUD | `/faculty/teaching-loads/` | Charges |
| GET | `/faculty/badge-events/` | Journal de badgeage |
| POST | `/faculty/attendances/check-in/` | Entrée **ou** sortie (2e scan) |
| GET | `/academics/cours/` | Catalogue ECUE × promotion |

Filtres séances : `period`, `promotion`, `date_from`, `date_to`, `visible=true`, `status`, `teacher`.

---

## 5. Workflows

1. Créer une **période** (et les jours fériés).
2. Affecter les professeurs (`CourseAssignment`) ; les charges se créent depuis la maquette si besoin.
3. **Générer** → séances `generated`.
4. Corriger / annuler dans le calendrier.
5. **Publier** (bloqué s’il reste un conflit d’erreur).
6. Le catalogue **Cours** passe en « Planifié » (lecture des séances, pas de copie).
7. Ouvrir le QR depuis le calendrier (séance publiée) ou la page Présences ; les étudiants de la promotion sont pré-inscrits **absents**.
8. 1er scan = entrée, 2e scan = sortie. Formats acceptés : `INJS:SEANCE:{uuid}` et `INJS:SESSION:{schedule}:{date}`.

---

## 6. Permissions

Pas de nouveau module RBAC : tout reste sous `faculty.*` / `academics.*`.

| Action | Qui |
|--------|-----|
| Générer, publier, conflits, réglages | Superuser ou niveau ≤ 2 (direction / responsables) |
| Voir toutes les séances | Idem |
| Professeur (niveau 3) | Ses séances (y compris brouillons) |
| Étudiant (niveau 4) | Séances **publiées** de sa promotion ; pas `faculty.view` requis pour la liste |

Un enseignant avec `faculty.create` **ne peut pas** générer l’EDT.

---

## 7. Migrations

| App | Fichier |
|-----|---------|
| academics | `0006_formationperiod_holiday` |
| faculty | `0008` groupes / charges / settings |
| faculty | `0009` Seance + FK présences |
| faculty | `0010` backfill depuis AttendanceSession |
| faculty | `0011` TimetableRun |
| faculty | `0012` horodatage + règles de présence |
| faculty | `0013` BadgeEvent |

`Schedule` n’est jamais supprimé. Le backfill est idempotent.

---

## 8. Règles métier

- Week-ends et jours fériés exclus.
- Rythme mensuel de la période (`w1`, `w1_2`, `w1_3`).
- Publication refusée si conflit **erreur** (salle, professeur, promotion).
- Durée badgeée **bornée** au créneau prévu.
- Retard si entrée > **15 min** après le début.
- Présence partielle si durée < **75 %** du créneau.
- Auto-absence **60 min** après la fin, sans entrée.
- Seuils surchargeables dans `PlanningSettings`.

---

## 9. Synchronisation

**Aucune copie** entre EDT et Cours. Le catalogue lit `Seance` (hors `cancelled` / `archived`). Le gabarit `Schedule` peut être **étendu** en séances datées (`expand`), sans écraser les séances déjà publiées.

---

## 10. Présences

`Attendance` porte l’état : `present | late | partial | absent | excused`, plus `checked_in_at`, `checked_out_at`, `duration_minutes`, `late_minutes`, FK optionnelle `seance`.

Le roster est créé absent à l’ouverture de séance. Le formateur peut corriger ; l’admin peut forcer hors fenêtre.

---

## 11. Badgeages

`BadgeEvent` est le journal. `AuditLog` reste la trace générique applicative.

Payloads QR :

- `INJS:SEANCE:{uuid}` — séance datée publiée (préféré)
- `INJS:SESSION:{schedule_uuid}:{YYYY-MM-DD}` — gabarit hebdomadaire (compatibilité)

Commandes :

```bash
python manage.py open_attendance_sessions
python manage.py close_overdue_attendances          # cron 15 min
python manage.py generate_timetable --period UUID [--promotion UUID]
```

| `kind` | Origine typique |
|--------|-----------------|
| `check_in` / `check_out` | QR (`source=qr`) |
| `force` | Admin |
| `correction` | Formateur ou PATCH |
| `auto_absent` | Système |

Un étudiant ne voit que **ses** événements.

---

## 12. Tests

```bash
cd backend
export DJANGO_SETTINGS_MODULE=injs_lmd.settings.development
./venv/bin/python manage.py test_injs
```

Référence avant intégration : **107** tests. La suite actuelle couvre fondations, moteur, API, Cours, présences, BadgeEvent, permissions, et le scénario 21 étapes (`apps.faculty.tests.test_edt_e2e`).

---

## 13. Démarrage local

```bash
# API (8002 si 8001 est pris par SYGEP)
cd backend
source venv/bin/activate
python manage.py migrate
python manage.py runserver 8002

# Front
cd ings-fe
npm run dev   # http://127.0.0.1:5173
```

Menu admin : **Gestion des Emplois du Temps (EDT)** → `/admin/emploi-du-temps`.

---

# Guide utilisateur

## Administrateur / scolarité

1. Onglet **Périodes** : créer la fenêtre (dates, rythme) et les jours fériés.
2. **Réglages** : horaires du campus et règles de présence (retard 15 min, partiel 75 %, auto-absence).
3. **Groupes** : TD/TP optionnels par promotion, puis affectation des étudiants.
4. **Charges** : volumes horaires ; répartir les TD/TP sur les groupes avant génération.
5. Filtres en haut : période + promotion.
6. **Génération** : prévisualiser, puis générer. Cocher « remplacer » uniquement pour les brouillons / générées.
7. **Calendrier** : corriger salle / horaires / encadrant, publier, ouvrir le **QR badgeage**, ou annuler avec motif.
8. **Conflits** : aucune erreur avant publication globale.
9. **Publier** : les étudiants et le catalogue Cours voient alors les séances.
10. La **grille hebdomadaire** reste disponible (gabarit LMD historique).

## Responsable pédagogique

- Catalogue **Cours** : statut Non affecté → Affecté → Planifié.
- Fiche ECUE : séances datées après publication.
- Affectations professeur / encadrant inchangées.

## Professeur / encadrant

- **Mon emploi du temps** : prochaines séances publiées + grille hebdo.
- Badgeage QR : même flux qu’avant (appareil lié, géofence si la salle a des coordonnées).
- Saisie manuelle des présences : historisée dans BadgeEvent (`correction`).

## Étudiant

- **Emploi du temps** : séances publiées de sa promotion.
- Présences / badgeage : 1er scan entrée, 2e scan sortie. L’historique personnel est dans `/faculty/badge-events/` et « mes présences ».
