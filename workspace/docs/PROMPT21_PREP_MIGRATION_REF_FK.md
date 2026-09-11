# Préparation de la migration legacy → FK Ref* (PROMPT 21)

**Statut** : PRÉPARÉE, NON APPLIQUÉE (décision prompt n°4 — application au lot du prompt 21).
**Sources de vérité** : Ref* de `formations` (conserver). Aucune migration existante modifiée.

## État des lieux vérifié (formations/models.py)

| Modèle | Champ legacy (texte) | FK cible | État |
|---|---|---|---|
| `Participant` | `categorie` (L394) | `RefCategorie` | texte seul — FK à créer |
| `Participant` | `grade` (L395) | `RefGrade` | texte seul — FK à créer |
| `Participant` | `vague` (L399) | `RefVague` | texte seul — FK à créer |
| `Participant` | `site` (L403) | `RefSite` | texte seul — FK à créer |
| `Participant` | `salle` (L404) | `RefSalle` | texte seul — FK à créer |
| `Participant` | `type_concours`, `libelle_concours` (L392-393) | — | hors périmètre (pas de Ref* existant — voir admissions/concours) |
| `Participant` | `groupe`, `grade_groupe` (L400-401) | — | double représentation D1 (Groupe LMD) — hors périmètre ici |
| `Module` | `site_legacy` (L620) | `RefSite` — **FK `site` déjà présente (L627)** | backfill seul |

## Stratégie proposée (à exécuter au prompt 21)

1. **Ajout des FK nullables** sur `Participant` : `categorie_ref`, `grade_ref`, `vague_ref`, `site_ref`, `salle_ref` (`on_delete=SET_NULL`, `null=True, blank=True`, `related_name='+'`). Noms suffixés `_ref` pour éviter toute collision avec les champs texte legacy conservés en lecture.
2. **Migration de schéma** : `makemigrations formations --name participant_ref_fk_bridge` (additive, aucune suppression).
3. **Backfill contrôlé** (data migration séparée, idempotente, dry-run d'abord) :
   - matching insensible à la casse/espaces : `Lower(ref.libelle) == Lower(legacy.strip())` ;
   - valeurs non résolues : **conservées en texte** (aucune perte), comptées et journalisées dans un rapport ;
   - `Module.site_legacy` → backfill `Module.site` uniquement si `site_id` est null.
4. **Bascule applicative** : serializers/admin lisent la FK avec fallback texte ; écritures basculées vers la FK (règle 9 — plus de valeur codée en dur côté React/Flutter).
5. **Nettoyage différé** (prompt 21) : dépréciation des champs texte (jamais de DROP sans autorisation explicite — règle workspace 7/15).

## Garde-fous
- Aucune migration existante réécrite ; migrations additives uniquement.
- Backup `scripts/backup_injs_lmd.sh` avant chaque `migrate`.
- Tests : après backfill, aucune ligne avec FK renseignée doit perdre son texte legacy.
