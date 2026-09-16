# Statistiques INJS-LMD — Traçabilité des indicateurs

> Référence technique : origine de chaque chiffre, pourcentage et filtre affiché dans l’application **Statistiques** (juin 2026).

| Fichier code principal | Rôle |
|------------------------|------|
| `backend/statistiques/views.py` | KPI, pédagogique, admin, alertes, historique, secrétariats |
| `backend/statistiques/effectifs.py` | Séances comptabilisables, présences, auditeurs notoires |
| `backend/formations/volume_horaire.py` | Volume horaire prévu / réalisé |
| `backend/statistiques/point_journalier.py` | Point journalier CPFAE |
| `backend/statistiques/bilans.py` | Bilans & Bilan FAC |
| `backend/formations/period_filter.py` | Filtre de période (preset / dates) |
| `frontend/src/pages/Statistiques.jsx` | Affichage & libellés UI |

---

## 1. Périmètre et filtres

### Filtres de requête (`_filtres` dans `views.py`)

| Paramètre | Portée |
|-----------|--------|
| `formation_id` | Modules, séances, pointages, inscrits de la formation |
| `secretariat_id` | Idem pour le secrétariat |
| `scope.module_ids` | Encadrant : modules assignés uniquement |

### Filtre de période (panneau « PÉRIODE — INDICATEURS CLÉS »)

Paramètres : `preset` (`tout`, `mois`, `trimestre`, `annee`, `custom`), `date_debut`, `date_fin`.

**S’applique à** : tous les KPI globaux (`formations`, `modules`, `participants`, `formateurs`, `sessions_total`, `sessions_terminees`, VH, alertes dérivées), pédagogique, admin (séances comptabilisées), secrétariats.

Règle commune hors « toutes périodes » : un module est **actif** s’il a au moins une séance dont `date_journee` est dans l’intervalle ; les effectifs (formations, modules, auditeurs, formateurs) portent sur ces modules ; `sessions_total` = toutes les séances planifiées dans l’intervalle.

**Ne s’applique pas à** : Point journalier, Bilans, Bilan FAC, Historique (12 mois fixes).

---

## 2. Règles métier centrales (`effectifs.py`)

### Séance comptabilisable (`filter_sessions`)

Une séance est incluse si :

1. `date_journee ≤ aujourd’hui`, **ou**
2. `terminee_le` renseigné, **ou**
3. Au moins une présence valide sur la séance.

Pas d’exigence de `demarree_le` (compatible import EDT). Aligné avec le **Point journalier**.

### Présence valide (`q_pointage_present`)

Pointage **participant** avec :

- `statut ≠ ABSENT_NON_BADGE`
- entrée enregistrée **ou** sortie avec `duree_presence_minutes > 0`

### Absent notoire (`participant_ids_notoires`)

Inscrit au périmètre, **inscrit à au moins un module démarré** :

- **sans aucune présence enregistrée** (pointage valide), **ou**
- avec `motif_notoire` non vide sur le profil.

Un module est considéré **démarré** si : statut EN_COURS / SUSPENDUE / TERMINÉE, `date_debut` atteinte, au moins une séance avec `demarree_le`, ou au moins une séance comptabilisable.

Utilisé par : dashboard, alertes `nb_absences_notoires`, bilans, Bilan FAC, liste nominative.

### Formule pourcentage standard

```text
_taux(a, b) = round(a / b × 100, 1)   si b > 0, sinon 0
```

---

## 3. KPI globaux (`kpis`)

| Champ API | Source | Calcul |
|-----------|--------|--------|
| `formations` | `Formation` / `Module` | Distinct formations des modules actifs sur la période (ou périmètre entier si `preset=tout`) |
| `modules` | `Module` filtré | Modules ayant ≥1 séance dans la période (ou tous si `preset=tout`) |
| `participants` | `ModuleParticipant` | Inscrits distincts sur les modules actifs de la période |
| `formateurs` | `Formateur` / modules | Assignés aux modules actifs de la période |
| `sessions_total` | `SessionModule` | Séances planifiées dont `date_journee` ∈ période (inclut le futur de l’intervalle) |
| `sessions_terminees` | `count_sessions_comptabilisables` | Séances comptabilisables + **filtre période** |
| `sessions_en_cours` | `SessionModule` | `demarree_le` présent, `terminee_le` absent |
| `pointages` | `Pointage` | Tous statuts, périmètre filtré |
| `vh_prevu_heures` | `compute_volume_horaire_from_module_ids` | Σ créneaux EDT des séances de la période |
| `vh_realise_heures` | idem | Réalisé sur séances terminées (durée plafonnée au créneau) |
| `taux_execution_vh` | idem | `min(réalisé, prévu) / prévu × 100` |

---

## 4. Indicateurs pédagogiques (`pedagogiques`)

Base : `aggregation_seances_modules` sur modules du périmètre + séances comptabilisables (période).

| Champ | Calcul |
|-------|--------|
| `total_inscrits` | Auditeurs distincts inscrits (`ModuleParticipant`) |
| `total_presents` | Inscrits avec ≥1 présence sur une séance comptabilisée |
| `total_absents` | `inscrits − presents` (niveau auditeur) |
| `places_attendues` | Σ (inscrits module × séances comptabilisées du module) |
| `places_presentes` | Σ présents par séance |
| `places_absentes` | `places_attendues − places_presentes` |
| `nb_seances_terminees` | Nombre de séances dans l’agrégat |
| `taux_presence` | **Assiduité séance** : `places_presentes / places_attendues × 100` |
| `taux_absence` | `places_absentes / places_attendues × 100` |
| `taux_couverture_auditeurs` | `total_presents / total_inscrits × 100` |
| `taux_achevement` | Alias de couverture (compat. API) |
| `total_abandons` | `count(Pointage)` `ABSENT_NON_BADGE` ou `HORS_LIGNE_SUSPECT` |
| `taux_abandon` | **Événements absence/suspect** : `total_abandons / total_inscrits × 100` |
| `taux_par_formation` / `grade` / `secrétariat` | Même assiduité sur sous-périmètre |
| `auditeurs_notoires` | `{ total, inscrits, pct, liste }` via `participant_ids_notoires` |

---

## 5. Administratif (`admin_operationnel`)

| Champ | Calcul |
|-------|--------|
| `nb_groupes` | `distinct groupe` sur modules (non vide) |
| `nb_encadrants` | `distinct superviseur` |
| `nb_seances_annulees` | Séances passées sans `demarree_le` (heuristique) — **≠** comptabilisables |
| `nb_seances_terminees` | `count_sessions_comptabilisables` (+ période) |
| `nb_absences_notoires` | **Nombre d’auditeurs notoires** (pas de pointages) |
| `moy_auditeurs_groupe` | Inscrits distincts / nb_groupes |
| `ratio_hf` | H/F sur inscrits modules ; `pct_hommes`, `pct_femmes` |
| `charge_formateurs` | Nb séances distinctes par formateur (badge + module + ModuleFormateur) |
| `stats_secretariats[]` | Par secrétariat : modules, participants secrétariat, assiduité, VH, notoires |

---

## 6. Historique (`historique`)

12 derniers mois calendaires, **sans** filtre période UI.

| Série | Calcul |
|-------|--------|
| `taux_presence_par_mois` | Places présentes / (présentes + absentes) par mois |
| `sessions_par_mois` | Séances comptabilisables par mois |
| `modules_par_mois` | Créations, actifs (avec séance comptabilisable), cumul |

---

## 7. Alertes (`alertes` / `alertes_overview`)

| Code | Valeur | Seuils défaut |
|------|--------|----------------|
| `taux_presence` | `ped.taux_presence` | 75 % / 60 % |
| `taux_absence` | `ped.taux_absence` | inverse 20 % / 35 % |
| `taux_abandon` | `ped.taux_abandon` | inverse 10 % / 20 % |
| `taux_execution_vh` | `kpis.taux_execution_vh` | 70 % / 50 % |
| `nb_absences_notoires` | `adm.nb_absences_notoires` | 50 / 100 |
| `saturation_groupe` | `moy_auditeurs_groupe / 40 × 100` (max 100) | inverse 80 % / 95 % |

Bandeau vue d’ensemble : `taux_presence`, `taux_execution_vh`, `saturation_groupe`.

---

## 8. Point journalier

API : `GET /api/statistiques/point-journalier/`. Séances via `filter_sessions`.

Par créneau (matin/soir) et groupe :

| Champ | Calcul |
|-------|--------|
| `effectif` | Inscrits catégorie sur le module |
| `presents` / `absents` | Présents valides / reste |
| `taux_presence` | `presents / effectif` |
| `taux_presence_jour` | **Moyenne non pondérée** `(taux_matin + taux_soir) / 2` |

---

## 9. Bilans & Bilan FAC

- **Bilans effectifs** : inscrits, présents (≥1 séance), absents, H/F — `effectifs_tableau_agrege`.
- **Bilan période** : `absents_notoires` = `count_auditeurs_notoires` ; paramètre `periode` = libellé seul.
- **Bilan FAC** : VH via `compute_volume_horaire_from_module_ids` ; assiduité via places ; liste notoires unifiée.

---

## 10. Synthèse des pourcentages UI

| Libellé | Formule | Denominateur |
|---------|---------|--------------|
| Assiduité séance | places présentes / places attendues | Places (inscrit × séance) |
| Couverture auditeurs | auditeurs avec présence / inscrits | Auditeurs |
| Événements absence/suspect | pointages suspects / inscrits | Auditeurs |
| Avancement VH | réalisé_h / prévu_h | Heures |
| Auditeurs notoires % | notoires / inscrits | Inscrits |
| Saturation groupe | moy_inscrits_groupe / 40 | Référence fixe 40 |

---

## 11. Comparaisons qui prêtent à confusion

| A | B | Différence |
|---|---|------------|
| Séances totales | Séances comptabilisées | Total = séances planifiées dans la période ; comptabilisées = règle EDT + période |
| Séances annulées | Comptabilisées | Annulées = passées sans démarrage badge |
| Auditeurs notoires | Événements absence/suspect | Personnes jamais badgées vs pointages par séance |
| Dashboard assiduité | Point journalier | Même règle séances ; PJ agrège par jour/créneau |
| Filtre période | Historique | Période UI ignorée par l’historique 12 mois |

---

*Document généré pour aligner l’UI, les alertes et les exports CPFAE sur une seule définition métier.*
