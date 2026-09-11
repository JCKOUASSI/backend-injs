# Préparation de la réconciliation des groupes (PROMPT 21)

**Statut** : PRÉPARÉ, NON APPLIQUÉ. Double représentation D1 de la cartographie.

## État des lieux vérifié

| Représentation | Localisation | Usage réel |
|---|---|---|
| ✅ Groupe LMD (source de vérité cible) | `scolarite.Groupe` (année + formation + parcours + niveau + vague + site + nom + capacité) + `AffectationGroupe` (historisé : date_debut/date_fin/active) | Socle LMD : InscriptionPedagogique.groupe, export EDT, effectifs/répartition |
| ⚠️ Champs texte legacy | `formations.Participant.groupe` (L400) + `grade_groupe` (L401) ; `formations.Module.groupe` (L609, dans unique_together) | Socle formation continue historique (imports Excel, QR badgeage, notes) |

## Stratégie proposée (au prompt 21)

1. **Ajout d'une FK nullable** `Participant.groupe_lmd → scolarite.Groupe` (SET_NULL) — jamais de suppression du champ texte.
2. **Backfill contrôlé** (dry-run puis réel) : matching `Lower(Groupe.nom) == Lower(Participant.groupe)` dans la même année/formation/niveau ; valeurs non résolues conservées en texte et rapportées.
3. **Module.groupe** : conserver en legacy (entre dans l'unicité `formation+intitule+grade+groupe+vague` du socle opérationnel) ; pas de FK — le module opérationnel reste hors LMD.
4. **Bascule applicative progressive** : les écrans LMD lisent `AffectationGroupe` (déjà actif) ; le texte legacy devient lecture seule pour le socle formation continue.
5. **Interdits** : aucune migration réécrite, aucune suppression de champ, aucune donnée effacée.

## Garde-fous
- Backup `scripts/backup_injs_lmd.sh` avant chaque `migrate`.
- Tests : après backfill, aucune perte du texte legacy ; affectations LMD inchangées.
