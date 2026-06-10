"""
Commande Django pour importer les données depuis les fichiers Excel ou CSV.

Usage :
  python manage.py import_excel import_formations.xlsx
  python manage.py import_excel import_participants.xlsx
  python manage.py import_excel import_participants.csv
  python manage.py import_excel import_formations.xlsx --dry-run
"""
import csv
import io
import re
from datetime import datetime, date

from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction
from django.utils import timezone

from openpyxl import load_workbook

from formations.models import (
    Formation, Participant, Formateur, Module,
    ModuleParticipant, ModuleFormateur, SessionModule, RefSite, RefModule,
)
FormationParticipant = ModuleParticipant
FormationFormateur = ModuleFormateur

MODULE_TITLE_TYPO_FIXES = {
    'ETHIQUE PUBLIQUE ET MUTTE CONTRE LA CORRUPTION': 'ETHIQUE PUBLIQUE ET LUTTE CONTRE LA CORRUPTION',
    'DROIT ADMINISTRATIVF': 'DROIT ADMINISTRATIF',
}


class Command(BaseCommand):
    help = 'Importer les données depuis un fichier Excel ou CSV (formations ou participants)'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.account_provision_stats = {}

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='Chemin vers le fichier Excel (.xlsx) ou CSV (.csv)')
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Simuler l\'import sans écrire en base',
        )

    def handle(self, *args, **options):
        filepath = options['file']
        dry_run = options['dry_run']

        is_csv = filepath.lower().endswith('.csv')
        stats = {}
        errors = []

        try:
            with transaction.atomic():
                if is_csv:
                    ws = self._load_csv(filepath)
                    # Detect type from filename
                    fname = filepath.lower()
                    if 'participant' in fname:
                        stats['participants'] = self._import_participants(ws, errors)
                    elif 'formation' in fname:
                        stats['formations'] = self._import_formations(ws, errors)  # tuple (created, updated)
                    elif 'formateur' in fname:
                        stats['formateurs'] = self._import_formateurs(ws, errors)
                    else:
                        stats['participants'] = self._import_participants(ws, errors)
                else:
                    try:
                        wb = load_workbook(filepath, read_only=True)
                    except Exception as e:
                        raise CommandError(f"Impossible d'ouvrir le fichier : {e}")

                    if 'Formations' in wb.sheetnames:
                        stats['formations'] = self._import_formations(wb['Formations'], errors)  # tuple (created, updated)
                    if 'Formateurs' in wb.sheetnames:
                        stats['formateurs'] = self._import_formateurs(wb['Formateurs'], errors)
                    if 'Participants' in wb.sheetnames:
                        stats['participants'] = self._import_participants(wb['Participants'], errors)
                    elif 'Auditeurs' in wb.sheetnames:
                        # Alias d'export epdtcpfae : l'onglet « Auditeurs » correspond aux participants.
                        stats['participants'] = self._import_participants(wb['Auditeurs'], errors)
                    if 'Inscriptions' in wb.sheetnames:
                        stats['inscriptions'] = self._import_inscriptions(wb['Inscriptions'], errors)
                    if 'Formateurs_Formations' in wb.sheetnames:
                        stats['formateurs_formations'] = self._import_formateurs_formations(
                            wb['Formateurs_Formations'], errors
                        )
                    if 'Emploi du temps' in wb.sheetnames:
                        stats['seances'] = self._import_emploi_du_temps(wb['Emploi du temps'], errors)
                    for sheet_name in ('Séances', 'Seances'):
                        if sheet_name in wb.sheetnames:
                            ws_s = wb[sheet_name]
                            # Détecter le format : emploi du temps (pas de module_titre/groupe)
                            # vs séances multi-modules (avec module_titre ou grade/groupe)
                            first_row = next(ws_s.iter_rows(values_only=True), ())
                            headers_lower = [str(h).lower().strip() if h else '' for h in first_row]
                            has_module = any('module' in h or 'grade' in h for h in headers_lower)
                            if has_module:
                                created, updated = self._import_seances(ws_s, errors)
                            else:
                                created = self._import_emploi_du_temps(ws_s, errors)
                                updated = 0
                            stats['seances'] = created
                            if updated: stats['seances_mises_a_jour'] = updated
                            break

                    wb.close()

                if dry_run:
                    raise _DryRunRollback()

        except _DryRunRollback:
            self.stdout.write(self.style.WARNING('\n🔸 DRY RUN — aucune donnée écrite en base.\n'))

        # Résumé
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('📊 Résumé de l\'import :'))
        for label, count in stats.items():
            # _import_seances retourne un tuple (created, updated) dans certains cas
            if isinstance(count, tuple):
                created, updated = count
                icon = '✅' if created > 0 else '⏭️'
                self.stdout.write(f'  {icon} {label.capitalize():.<30} {created} créées, {updated} mises à jour')
            else:
                icon = '✅' if count > 0 else '⏭️'
                self.stdout.write(f'  {icon} {label.capitalize():.<30} {count}')

        for label, provision in self.account_provision_stats.items():
            if not provision:
                continue
            self.stdout.write(
                f"  🔐 Comptes {label}: {provision.get('created', 0)} créés, "
                f"{provision.get('updated', 0)} mis à jour, "
                f"{provision.get('emails_sent', 0)} email(s) envoyé(s)"
            )

        if errors:
            self.stdout.write(self.style.ERROR(f'\n⚠️  {len(errors)} erreur(s) :'))
            for err in errors:
                self.stdout.write(self.style.ERROR(f'  ❌ {err}'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Import terminé sans erreur.'))

    # ─── Helpers ─────────────────────────────────────

    def _load_csv(self, filepath):
        """Charge un fichier CSV et retourne un objet itérable compatible avec _rows()."""
        class _CsvSheet:
            def __init__(self, filepath):
                self._rows_data = []
                with open(filepath, newline='', encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        # Convertir les chaînes vides en None pour cohérence avec Excel
                        self._rows_data.append(
                            tuple(v.strip() if v.strip() else None for v in row)
                        )

            def iter_rows(self, values_only=True):
                return iter(self._rows_data)

        return _CsvSheet(filepath)

    def _load_csv_from_bytes(self, content_bytes):
        """Charge un CSV depuis des bytes (pour l'API)."""
        class _CsvSheet:
            def __init__(self, content_bytes):
                self._rows_data = []
                text = content_bytes.decode('utf-8-sig')
                reader = csv.reader(io.StringIO(text))
                for row in reader:
                    self._rows_data.append(
                        tuple(v.strip() if v.strip() else None for v in row)
                    )

            def iter_rows(self, values_only=True):
                return iter(self._rows_data)

        return _CsvSheet(content_bytes)

    def _rows(self, ws, sheet_type='participant'):
        """Itère sur les lignes de données (ignore l'en-tête, s'arrête à la première ligne vide)."""
        headers = None
        for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
            if row_idx == 1:
                # Normaliser les en-têtes
                headers = []
                for h in row:
                    if h:
                        clean = str(h).strip().lower()
                        # Mapper les noms de colonnes du template vers les noms internes
                        # Capturer les noms composés AVANT toute autre règle
                        if clean in ('module_titre', 'module titre', 'formation_titre', 'formation titre'):
                            headers.append('module_titre')
                            continue
                        if clean in (
                            'formation (cycle)', 'formation(cycle)', 'cycle de formation', 'cycle',
                            'formation',
                        ):
                            headers.append('formation')
                            continue
                        if clean in ('intitule', 'intitulé', 'libelle', 'libellé') and sheet_type != 'formation':
                            headers.append('intitule')
                            continue
                        elif 'module' in clean and '(titre)' in clean:
                            clean = 'module'
                        else:
                            clean = clean.replace('(numero)', '').replace('(titre)', '')
                            clean = clean.replace('(h)', '').strip()
                        # Spécifiques en premier (avant les règles génériques)
                        clean = clean.replace('n° d\'inscription', 'matricule').replace('n° d inscription', 'matricule')
                        clean = clean.replace('n°d\'inscription', 'matricule')
                        clean = clean.replace('téléphone 1', 'telephone').replace('telephone 1', 'telephone')
                        clean = clean.replace('téléphone 2', 'telephone2').replace('telephone 2', 'telephone2')
                        clean = clean.replace('libelle concours', 'libelle_concours').replace('libellé concours', 'libelle_concours')
                        clean = clean.replace('type concours', 'type_concours')
                        clean = clean.replace('grade/groupe', 'grade_groupe').replace('grade groupe', 'grade_groupe').replace('grade-groupe', 'grade_groupe')
                        clean = clean.replace('date de naissance', 'date_naissance').replace('date naissance', 'date_naissance')
                        clean = clean.replace('lieu de naissance', 'lieu_naissance').replace('lieu naissance', 'lieu_naissance')

                        clean = clean.replace('volume horaire', 'duree_prevue_heures')
                        if '_' not in clean:
                            clean = clean.replace('duree', 'duree_prevue_heures').replace('durée', 'duree_prevue_heures')
                        if clean == 'module' or (('module' in clean) and ('titre' in clean or 'intitule' in clean or 'intitulé' in clean)):
                            clean = 'module'
                        clean = clean.replace('intitulé du module', 'formation').replace('intitule du module', 'formation')
                        clean = clean.replace('libellé du module', 'formation').replace('libelle du module', 'formation')
                        clean = clean.replace('intitulé de la formation', 'formation').replace('intitule de la formation', 'formation')
                        clean = clean.replace('intitulé', 'formation').replace('intitule', 'formation')
                        clean = clean.replace('libellé de la formation', 'formation').replace('libelle de la formation', 'formation')
                        if '_' not in clean:
                            clean = clean.replace('libellé', 'formation').replace('libelle', 'formation')
                        clean = clean.replace('désignation', 'formation').replace('designation', 'formation')
                        clean = clean.replace('matière', 'formation').replace('matiere', 'formation')
                        if clean == 'cours':
                            clean = 'formation'
                        clean = clean.replace('lieu de formation', 'site')
                        clean = clean.replace('centre de formation', 'site')
                        if '_' not in clean:
                            clean = clean.replace('lieu', 'site')
                        clean = clean.replace('date début', 'date_debut').replace('date fin', 'date_fin')
                        clean = clean.replace('heure début', 'heure_debut').replace('heure debut', 'heure_debut')
                        clean = clean.replace('heure fin', 'heure_fin')
                        clean = clean.replace('date journée', 'date_journee').replace('date journee', 'date_journee')
                        # Règles génériques
                        clean = clean.replace('prénoms', 'prenom').replace('prénom', 'prenom')
                        clean = clean.replace('prenom(s)', 'prenom').replace('prenoms', 'prenom')
                        clean = clean.replace('catégorie/corps', 'categorie').replace('categorie/corps', 'categorie')
                        clean = clean.replace('genre', 'sexe')
                        clean = clean.replace('téléphone', 'telephone')
                        clean = clean.replace('catégorie', 'categorie')
                        clean = clean.replace('bâtiment', 'batiment').replace('batîment', 'batiment')
                        clean = clean.replace('spécialité', 'specialite')
                        clean = clean.replace('numéro', 'numero')
                        clean = clean.replace('fncp', 'matricule')
                        if clean in ('matricule',):
                            headers.append(clean)
                            continue
                        if sheet_type == 'formation':
                            clean = clean.replace('n°', 'numero_formation')
                        else:
                            clean = clean.replace('n°', 'numero')
                            if clean == 'module':
                                clean = 'formation'
                        headers.append(clean)
                    else:
                        headers.append('')
                if headers:
                    self.stdout.write(f'  [DEBUG] Headers normalisés : {headers}')
                continue
            # Ligne vide → fin des données
            if all(v is None or str(v).strip() == '' for v in row):
                break
            yield row_idx, dict(zip(headers, row))

    def _str(self, val, default=''):
        if val is None:
            return default
        return str(val).strip()

    def _normalize_categorie(self, cat):
        """Normalise la catégorie vers le libellé RefTypeSecretariat.
        - Compacte les variantes collées (ex. 'FABA' -> 'FAB A', 'FACB' -> 'FAC B').
        - Lettre seule ('A'/'B'/'C') → 'FAB A' / 'FAB B' / 'FAB C' (convention imports).
        - Préserve les autres codes pour permettre une résolution dynamique
          (ex. 'FAC A', 'FAR B'… seront cherchés tels quels dans RefTypeSecretariat).
        """
        c = cat.strip().upper()
        if not c:
            return c
        if c in ('A', 'B', 'C'):
            return f'FAB {c}'
        # Variantes collées : "FABA" -> "FAB A", "FAC B" reste "FAC B".
        import re as _re
        m = _re.fullmatch(r'([A-Z]{2,4})\s*([A-C])', c)
        if m:
            return f'{m.group(1)} {m.group(2)}'
        return c

    def _normalize_module_title(self, titre):
        """Corrige les fautes de frappe connues dans les intitulés de modules."""
        s = (titre or '').strip()
        if not s:
            return s
        return MODULE_TITLE_TYPO_FIXES.get(s.upper(), s)

    def _secretariat_hint_from_matricule(self, matricule):
        """Retourne le code secrétariat prioritaire selon le matricule.
        FNCE* -> FAB, FNCP* -> FAC.
        """
        m = (matricule or '').strip().upper()
        if m.startswith('FNCE'):
            return 'FAB'
        if m.startswith('FNCP'):
            return 'FAC'
        return ''

    def _resolve_secretariat(self, SecretariatModel, hint, categorie=''):
        """Résout un secrétariat depuis un hint (nom ou type libellé)."""
        if not hint:
            return None
        h = hint.strip()
        sec = (
            SecretariatModel.objects.filter(nom__iexact=h).first()
            or SecretariatModel.objects.filter(type__libelle__iexact=h).first()
            or SecretariatModel.objects.filter(nom__istartswith=f'{h} ').first()
        )
        if sec:
            return sec
        cat = self._normalize_categorie(categorie) if categorie else ''
        if cat:
            sec = SecretariatModel.objects.filter(type__libelle__iexact=cat).first()
            if sec:
                return sec
        if h.upper() in ('FAB', 'FAC'):
            return SecretariatModel.objects.filter(
                type__libelle__istartswith=f'{h.upper()} ',
            ).first()
        return None

    def _int(self, val, default=None):
        if val is None:
            return default
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return default

    def _normalize_date_string(self, val):
        """Corrige les saisies Excel fréquentes : espaces parasites, slash manquant."""
        s = str(val).strip()
        if not s:
            return s
        s = re.sub(r'\s+', ' ', s)
        # « 15/06/ 2026 » ou « 15/06 2026 » → « 15/06/2026 »
        s = re.sub(r'(\d{1,2}/\d{1,2})/?\s+(\d{4})', r'\1/\2', s)
        # « 03/072026 » → « 03/07/2026 » (slash manquant avant l'année)
        s = re.sub(r'^(\d{1,2})/(\d{2})(\d{4})(.*)$', r'\1/\2/\3\4', s)
        return s

    def _from_excel_serial(self, val):
        """Convertit un numéro de série Excel (float/int) en datetime naïf."""
        if not isinstance(val, (int, float)) or val <= 0:
            return None
        try:
            from openpyxl.utils.datetime import from_excel
            return from_excel(val)
        except (ValueError, TypeError, OverflowError):
            return None

    def _parse_datetime(self, val):
        if val is None:
            return None
        if isinstance(val, datetime):
            if timezone.is_naive(val):
                return timezone.make_aware(val)
            return val
        if isinstance(val, date):
            return timezone.make_aware(datetime.combine(val, datetime.min.time()))
        excel_dt = self._from_excel_serial(val)
        if excel_dt is not None:
            if timezone.is_naive(excel_dt):
                return timezone.make_aware(excel_dt)
            return excel_dt
        val = self._normalize_date_string(val)
        if not val or val.lower() in ('-', 'n/a', '#n/a', 'na'):
            return None
        for fmt in (
            '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%d/%m/%Y %H:%M:%S',
            '%d/%m/%Y %H:%M', '%d.%m.%Y %H:%M', '%d-%m-%Y %H:%M', '%Y-%m-%dT%H:%M',
            '%Y-%m-%d', '%d/%m/%Y', '%d.%m.%Y', '%d-%m-%Y', '%d/%m/%y', '%Y/%m/%d',
        ):
            try:
                dt = datetime.strptime(val, fmt)
                return timezone.make_aware(dt)
            except ValueError:
                continue
        return None

    def _parse_date(self, val):
        if val is None:
            return None
        if isinstance(val, (datetime, date)):
            return val if isinstance(val, date) else val.date()
        excel_dt = self._from_excel_serial(val)
        if excel_dt is not None:
            return excel_dt.date()
        val = self._normalize_date_string(val)
        if not val or val.lower() in ('-', 'n/a', '#n/a', 'na'):
            return None
        for fmt in ('%d/%m/%Y', '%d.%m.%Y', '%d/%m/%y', '%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d'):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
        return None

    def _format_import_cell(self, val):
        if val is None:
            return 'vide'
        if isinstance(val, datetime):
            return val.isoformat(sep=' ', timespec='minutes')
        if isinstance(val, date):
            return val.isoformat()
        s = str(val).strip()
        return s or 'vide'

    def _parse_formation_datetime(self, val, anchor=None):
        """Parse une date/heure de formation ; accepte une heure seule si ``anchor`` est fourni."""
        from datetime import time as dt_time

        if val is None:
            return None
        if isinstance(val, dt_time) and anchor:
            return timezone.make_aware(datetime.combine(anchor.date(), val))
        if isinstance(val, (int, float)) and 0 < val < 1 and anchor:
            t = self._parse_time(val)
            if t:
                return timezone.make_aware(datetime.combine(anchor.date(), t))

        dt = self._parse_datetime(val)
        if dt and dt.year < 1980:
            if anchor:
                return timezone.make_aware(datetime.combine(anchor.date(), dt.time()))
            return None
        if dt:
            return dt
        if anchor:
            t = self._parse_time(val)
            if t:
                return timezone.make_aware(datetime.combine(anchor.date(), t))
        return None

    # ─── Import Formations ───────────────────────────

    def _import_formations(self, ws, errors, secretariat=None):
        from formations.models import Secretariat as SecretariatModel
        count = 0
        modules_updated = 0
        _secretariat_cache = {}
        _module_order = {}  # (formation_id) -> ordre courant
        for row_idx, data in self._rows(ws, sheet_type='formation'):
            titre = self._str(data.get('formation'))
            if not titre:
                # Lignes résiduelles Excel (formatage, formules, cellules parasites)
                if not self._str(data.get('module')) and not (
                    data.get('date_debut') or data.get('date_fin')
                ):
                    continue
                errors.append(f'Formations ligne {row_idx}: formation (module) manquante')
                continue

            module_val = self._str(data.get('module')) or titre

            date_debut = self._parse_formation_datetime(data.get('date_debut'))
            date_fin = self._parse_formation_datetime(data.get('date_fin'), anchor=date_debut)
            if not date_debut or not date_fin:
                parts = []
                if not date_debut:
                    parts.append(f'début={self._format_import_cell(data.get("date_debut"))}')
                if not date_fin:
                    parts.append(f'fin={self._format_import_cell(data.get("date_fin"))}')
                errors.append(
                    f'Formations ligne {row_idx} (« {module_val} »): '
                    f'date(s) invalide(s) ou vide(s) ({", ".join(parts)})'
                )
                continue

            # ``duree_prevue_heures`` est facultative dans le fichier source.
            # Si la cellule est vide pour cette ligne, on **ne touche pas** au
            # ``duree_prevue_heures`` du module existant (évite d'écraser à 0
            # une valeur déjà saisie lors d'un import précédent).
            duree_raw = data.get('duree_prevue_heures')
            duree_renseignee = duree_raw not in (None, '', 0, '0')
            duree = duree_raw or 0
            try:
                duree = float(duree)
            except (ValueError, TypeError):
                duree = 0

            # Formation ne porte que : formation (titre) + numero_formation
            formation_defaults = {
                'numero_formation': self._int(data.get('numero_formation')),
            }

            # Résolution du secrétariat (pour le Module)
            _secretariat = None
            if secretariat is not None:
                _secretariat = secretariat
            else:
                raw_cat = self._str(data.get('categorie'))
                if not raw_cat and self._str(data.get('grade')):
                    first_letter = self._str(data.get('grade')).strip()[:1].upper()
                    if first_letter in ('A', 'B', 'C'):
                        raw_cat = first_letter
                cat_val = self._normalize_categorie(raw_cat)
                if cat_val:
                    if cat_val not in _secretariat_cache:
                        sec = SecretariatModel.objects.filter(type__libelle__iexact=cat_val).first()
                        # Lettre seule (A/B/C) : tenter un match par suffixe sur le libellé
                        # du type secrétariat (ex. 'FAB A', 'FAC A'). On ne sélectionne que
                        # si un seul candidat correspond, pour éviter l'ambiguïté.
                        if sec is None and len(cat_val) == 1 and cat_val in ('A', 'B', 'C'):
                            candidates = list(
                                SecretariatModel.objects.filter(
                                    type__libelle__iendswith=f' {cat_val}'
                                )[:2]
                            )
                            if len(candidates) == 1:
                                sec = candidates[0]
                        _secretariat_cache[cat_val] = sec
                        if sec:
                            self.stdout.write(f'  🗂  Catégorie {cat_val} → Secrétariat : {sec.nom}')
                        else:
                            errors.append(
                                f'Formations ligne {row_idx}: aucun secrétariat '
                                f'de type "{cat_val}" trouvé pour "{titre}"'
                            )
                    _secretariat = _secretariat_cache.get(cat_val)

            try:
                obj, created = Formation.objects.get_or_create(
                    formation=titre,
                    defaults=formation_defaults,
                )
                if not created and formation_defaults.get('numero_formation'):
                    Formation.objects.filter(pk=obj.pk).update(**{k: v for k, v in formation_defaults.items() if v is not None})
            except Formation.MultipleObjectsReturned:
                obj = Formation.objects.filter(formation=titre).order_by('id').first()
                created = False
            except Exception as e:
                errors.append(f'Formations ligne {row_idx}: erreur lors de la sauvegarde de "{titre}" — {e}')
                continue

            # Créer ou mettre à jour le Module correspondant
            # Tous les champs métier vont sur Module
            if obj.id not in _module_order:
                existing_max = obj.modules.aggregate(m=models.Max('ordre'))['m'] or 0
                _module_order[obj.id] = existing_max
            _module_order[obj.id] += 1

            module_defaults = {
                'ordre': _module_order[obj.id],
                'grade': self._str(data.get('grade')),
                'groupe': self._str(data.get('groupe')),
                'vague': self._str(data.get('vague')),
                'date_debut': date_debut.date() if hasattr(date_debut, 'date') else date_debut,
                'date_fin': date_fin.date() if hasattr(date_fin, 'date') else date_fin,
                'statut': self._str(data.get('statut')) or 'PLANIFIEE',
                # Champ `cycle` (NOT NULL sur certaines bases) : libellé du cycle = formation parente.
                'cycle': titre,
            }
            _site_name = self._str(data.get('site'))
            _bat  = self._str(data.get('batiment'))
            _sal  = self._str(data.get('salle'))
            if _site_name:
                _site, _ = RefSite.objects.get_or_create(
                    nom=_site_name, defaults={'actif': True},
                )
                module_defaults['site'] = _site
                module_defaults['site_legacy'] = _site_name
            if _bat:  module_defaults['batiment'] = _bat
            if _sal:  module_defaults['salle'] = _sal
            if _secretariat: module_defaults['secretariat'] = _secretariat
            # On n'inscrit la durée prévue que si elle est explicitement
            # renseignée dans le fichier source, afin de ne pas écraser une
            # valeur déjà saisie par une cellule vide ou nulle.
            if duree_renseignee and duree > 0:
                module_defaults['duree_prevue_heures'] = duree

            # Lookup Module : formation + intitule + grade + groupe (unicité)
            module_lookup = {'formation': obj, 'intitule': module_val}
            grade_key = self._str(data.get('grade'))
            groupe_key = self._str(data.get('groupe'))
            if grade_key: module_lookup['grade'] = grade_key
            if groupe_key: module_lookup['groupe'] = groupe_key

            _mod, mod_created = Module.objects.update_or_create(
                **module_lookup,
                defaults=module_defaults,
            )
            ref_module, _ = RefModule.get_or_create_for_intitule(module_val)
            if ref_module and _mod.ref_module_id != ref_module.id:
                _mod.ref_module = ref_module
                _mod.save(update_fields=['ref_module'])

            if mod_created:
                count += 1
                self.stdout.write(f'  + Module : {module_val} ({grade_key}/{groupe_key}) ({duree}h)')
            else:
                modules_updated += 1
                self.stdout.write(f'  ~ Module mis à jour : {module_val} ({grade_key}/{groupe_key})')

            # Auto-inscrire les participants déjà en base qui correspondent
            # au module (grade + groupe requis, categorie/vague optionnels sur Participant)
            grade_val = module_defaults.get('grade', '')
            groupe_val = module_defaults.get('groupe', '')
            vague_val = module_defaults.get('vague', '')
            cat_val_raw = self._str(data.get('categorie'))  # categorie est sur Participant, pas Module
            if grade_val and groupe_val:
                qs = Participant.objects.filter(
                    grade__iexact=grade_val,
                    groupe__iexact=groupe_val,
                )
                if cat_val_raw:
                    qs = qs.filter(categorie__iexact=cat_val_raw)
                if vague_val:
                    qs = qs.filter(vague__iexact=vague_val)
                inscrits = 0
                for participant in qs:
                    try:
                        _, insc_created = ModuleParticipant.objects.get_or_create(
                            module=_mod, participant=participant,
                        )
                        if insc_created:
                            inscrits += 1
                    except Exception as e:
                        errors.append(
                            f'Auto-inscription impossible : {participant} → {titre} ({e})'
                        )
                if inscrits:
                    self.stdout.write(
                        f'    ↳ {inscrits} participant(s) auto-inscrit(s) '
                        f'({cat_val_raw}/{grade_val}/{groupe_val}'
                        + (f'/{vague_val}' if vague_val else '') + ')'
                    )
        return count, modules_updated

    # ─── Import Participants ─────────────────────────

    def _import_participants(self, ws, errors, secretariat=None):
        from authentication.badge_accounts import provision_auditeur_accounts
        from formations.models import Secretariat as SecretariatModel
        count = 0
        inscriptions = 0
        touched_ids = set()
        # Cache secretariat par categorie pour éviter une requête DB par ligne
        _secretariat_cache = {}

        for row_idx, data in self._rows(ws):
            nom = self._str(data.get('nom'))
            prenom = self._str(data.get('prenom'))
            if not nom or not prenom:
                errors.append(f'Participants ligne {row_idx}: nom ou prénom manquant')
                continue
            matricule = self._str(data.get('matricule') or data.get('numero'))

            date_naissance = self._parse_date(data.get('date_naissance'))

            fields = {
                'nom': nom,
                'prenom': prenom,
                'sexe': self._str(data.get('sexe')).upper(),
                'date_naissance': date_naissance,
                'lieu_naissance': self._str(data.get('lieu_naissance')),
                'email': self._str(data.get('email')),
                'telephone': self._str(data.get('telephone')),
                'telephone2': self._str(data.get('telephone2')),
                'type_concours': self._str(data.get('type_concours') or data.get('type')),
                'libelle_concours': self._str(data.get('libelle_concours')),
                'categorie': self._str(data.get('categorie')),
                'grade': self._str(data.get('grade')),
                'groupe': self._str(data.get('groupe')),
                'grade_groupe': self._str(data.get('grade_groupe')),
                'vague': self._str(data.get('vague')),
            }

            if secretariat is not None:
                # Secretariat explicitement fourni (import via API avec user SECRETARIAT)
                fields['secretariat'] = secretariat
            else:
                # Règle prioritaire par matricule:
                # FNCE* -> secrétariat FAB ; FNCP* -> secrétariat FAC.
                # Si aucun match, on conserve la règle historique par catégorie/grade.
                forced_hint = self._secretariat_hint_from_matricule(matricule)
                if forced_hint:
                    cache_key = f'prefix:{forced_hint}'
                    if cache_key not in _secretariat_cache:
                        sec = self._resolve_secretariat(
                            SecretariatModel, forced_hint, fields.get('categorie'),
                        )
                        _secretariat_cache[cache_key] = sec
                        if sec:
                            self.stdout.write(
                                f'  🗂  Matricule {forced_hint}* → Secrétariat : {sec.nom}'
                            )
                        else:
                            errors.append(
                                f'Participants ligne {row_idx}: aucun secrétariat '
                                f'"{forced_hint}" trouvé pour {nom} {prenom}'
                            )
                    sec = _secretariat_cache.get(cache_key)
                    if sec:
                        fields['secretariat'] = sec
                else:
                    # Auto-affectation par catégorie : ex 'A'/'FAB A' -> secrétariat type='FAB A'
                    # Fallback : si categorie vide, déduire depuis le grade (A4 -> A, B2 -> B, C1 -> C)
                    raw_cat = fields['categorie']
                    if not raw_cat and fields['grade']:
                        first_letter = fields['grade'].strip()[:1].upper()
                        if first_letter in ('A', 'B', 'C'):
                            raw_cat = first_letter
                    cat = self._normalize_categorie(raw_cat) if raw_cat else ''
                    if cat:
                        if cat not in _secretariat_cache:
                            sec = SecretariatModel.objects.filter(type__libelle__iexact=cat).first()
                            _secretariat_cache[cat] = sec
                            if sec:
                                self.stdout.write(
                                    f'  🗂  Catégorie {cat} → Secrétariat : {sec.nom}'
                                )
                            else:
                                errors.append(
                                    f'Participants ligne {row_idx}: aucun secrétariat '
                                    f'de type "{cat}" trouvé pour {nom} {prenom}'
                                )
                        sec = _secretariat_cache.get(cat)
                        if sec:
                            fields['secretariat'] = sec

            if matricule:
                obj, created = Participant.objects.update_or_create(
                    matricule=matricule,
                    defaults=fields,
                )
            else:
                obj = Participant(**fields)
                obj.save()
                created = True

            if created:
                count += 1
                self.stdout.write(f'  + Participant : {obj.matricule} — {nom} {prenom}')
            else:
                self.stdout.write(f'  ~ Participant mis à jour : {matricule}')
            touched_ids.add(obj.pk)

            # Inscrire le participant aux formations
            formations_str = self._str(data.get('formation(s)') or data.get('formations'))
            if formations_str:
                # Cas 1 : colonne Formation(s) renseignée → inscription par titre
                # Filtre par groupe + grade + vague pour identifier la bonne formation
                p_groupe = self._str(data.get('groupe'))
                p_grade  = self._str(data.get('grade'))
                p_vague  = self._str(data.get('vague'))
                titres = [t.strip() for t in formations_str.split('|') if t.strip()]
                for titre in titres:
                    mod_qs = Module.objects.filter(formation__formation__iexact=titre)
                    if p_grade:
                        mod_qs_g = mod_qs.filter(grade__iexact=p_grade)
                        if mod_qs_g.exists():
                            mod_qs = mod_qs_g
                    if p_groupe:
                        mod_qs_g = mod_qs.filter(groupe__iexact=p_groupe)
                        if mod_qs_g.exists():
                            mod_qs = mod_qs_g
                    if p_vague:
                        mod_qs_g = mod_qs.filter(vague__iexact=p_vague)
                        if mod_qs_g.exists():
                            mod_qs = mod_qs_g
                    matched_mods = list(mod_qs.order_by('ordre'))
                    if not matched_mods:
                        errors.append(f'Participants ligne {row_idx}: formation "{titre}" introuvable')
                        continue
                    for _mod in matched_mods:
                        try:
                            _, insc_created = ModuleParticipant.objects.get_or_create(
                                module=_mod, participant=obj,
                            )
                            if insc_created:
                                inscriptions += 1
                                self.stdout.write(f'    ↳ Inscrit à : {_mod.formation.formation} / {_mod.intitule} ({_mod.groupe})')
                        except Exception as e:
                            errors.append(f'Participants ligne {row_idx}: inscription impossible à "{titre}" ({e})')
            else:
                # Cas 2 : colonne Formation(s) vide
                # Auto-match strict : catégorie + grade + groupe tous les 3 requis
                # Filtre optionnel supplémentaire : vague
                cat = self._str(data.get('categorie'))
                grade = self._str(data.get('grade'))
                groupe = self._str(data.get('groupe'))
                vague = self._str(data.get('vague'))
                if grade and groupe:
                    mod_qs = Module.objects.filter(
                        grade__iexact=grade,
                        groupe__iexact=groupe,
                    )
                    if vague:
                        mod_qs = mod_qs.filter(vague__iexact=vague)
                    matched_mods = list(mod_qs)
                    if not matched_mods:
                        crit = f'grade={grade} groupe={groupe}'
                        if vague:
                            crit += f' vague={vague}'
                        errors.append(
                            f'Participants ligne {row_idx}: '
                            f'aucun module trouvé pour {nom} {prenom} '
                            f'({crit})'
                        )
                    else:
                        for _mod in matched_mods:
                            try:
                                _, insc_created = ModuleParticipant.objects.get_or_create(
                                    module=_mod, participant=obj,
                                )
                                if insc_created:
                                    inscriptions += 1
                                    self.stdout.write(
                                        f'    ↳ Auto-inscrit → {_mod.formation.formation} / {_mod.intitule}'
                                    )
                            except Exception as e:
                                errors.append(
                                    f'Participants ligne {row_idx}: auto-inscription impossible '
                                    f'à "{_mod.formation.formation}" ({e})'
                                )
                elif not (grade or groupe):
                    errors.append(
                        f'Participants ligne {row_idx}: {nom} {prenom} '
                        f'sans Formation(s) ni grade/groupe — pas inscrit'
                    )
                else:
                    errors.append(
                        f'Participants ligne {row_idx}: {nom} {prenom} '
                        f'auto-match incomplet (grade={grade!r} groupe={groupe!r}) '
                        f'— les 2 critères grade+groupe sont requis'
                    )

        if inscriptions:
            self.stdout.write(f'  📌 {inscriptions} inscription(s) créée(s)')

        self.account_provision_stats['auditeurs'] = provision_auditeur_accounts(
            touched_ids,
            log=self.stdout.write,
        )
        return count

    # ─── Import Formateurs ───────────────────────────

    def _import_formateurs(self, ws, errors):
        from authentication.badge_accounts import provision_formateur_accounts
        count = 0
        touched_ids = set()
        for row_idx, data in self._rows(ws):
            nom = self._str(data.get('nom'))
            prenom = self._str(data.get('prenom'))
            if not nom or not prenom:
                errors.append(f'Formateurs ligne {row_idx}: nom ou prénom manquant')
                continue
            numero = self._str(data.get('numero'))

            fields = {
                'nom': nom,
                'prenom': prenom,
                'email': self._str(data.get('email')),
                'telephone': self._str(data.get('telephone')),
                'specialite': self._str(data.get('specialite')),
                'organisation': self._str(data.get('organisation')),
            }

            try:
                if numero:
                    obj, created = Formateur.objects.update_or_create(
                        numerobadge=numero,
                        defaults=fields,
                    )
                else:
                    obj, created = Formateur.objects.get_or_create(
                        nom__iexact=nom,
                        prenom__iexact=prenom,
                        defaults=fields,
                    )
                    if not created:
                        for k, v in fields.items():
                            setattr(obj, k, v)
                        obj.save()
            except Exception as e:
                errors.append(f'Formateurs ligne {row_idx}: erreur lors de la sauvegarde de {nom} {prenom} — {e}')
                continue

            if created:
                count += 1
                self.stdout.write(f'  + Formateur : {obj.numerobadge} — {nom} {prenom}')
            else:
                self.stdout.write(f'  ~ Formateur mis à jour : {obj.numerobadge} — {nom} {prenom}')
            touched_ids.add(obj.pk)

        self.account_provision_stats['formateurs'] = provision_formateur_accounts(
            touched_ids,
            log=self.stdout.write,
        )
        return count

    # ─── Import Inscriptions ─────────────────────────

    def _import_inscriptions(self, ws, errors):
        count = 0
        for row_idx, data in self._rows(ws):
            titre = self._str(data.get('formation_titre'))
            numero = self._str(data.get('participant_numero'))
            if not titre or not numero:
                errors.append(f'Inscriptions ligne {row_idx}: formation_titre ou participant_numero manquant')
                continue

            try:
                formation = Formation.objects.get(formation=titre)
            except Formation.DoesNotExist:
                errors.append(f'Inscriptions ligne {row_idx}: formation "{titre}" introuvable')
                continue
            except Formation.MultipleObjectsReturned:
                formation = Formation.objects.filter(formation=titre).first()

            try:
                participant = Participant.objects.get(matricule=numero)
            except Participant.DoesNotExist:
                errors.append(f'Inscriptions ligne {row_idx}: participant "{numero}" introuvable')
                continue

            module_intitule = self._str(data.get('module_titre') or data.get('module'))
            if module_intitule:
                _mod = formation.modules.filter(intitule__iexact=module_intitule).first()
            else:
                _mod = formation.modules.order_by('ordre').first()
            if not _mod:
                errors.append(f'Inscriptions ligne {row_idx}: formation "{titre}" n\'a aucun module')
                continue

            _, created = ModuleParticipant.objects.get_or_create(
                module=_mod, participant=participant,
            )
            if created:
                count += 1
                self.stdout.write(f'  + Inscription : {numero} → {titre} / {_mod.intitule}')
            else:
                self.stdout.write(f'  ~ Déjà inscrit : {numero} → {titre} / {_mod.intitule}')
        return count

    # ─── Import Formateurs ↔ Formations ──────────────

    def _import_formateurs_formations(self, ws, errors):
        count = 0
        for row_idx, data in self._rows(ws):
            titre = self._str(data.get('formation_titre'))
            numero = self._str(data.get('formateur_numero'))
            if not titre or not numero:
                errors.append(f'Formateurs_Formations ligne {row_idx}: données manquantes')
                continue

            try:
                formation = Formation.objects.get(formation=titre)
            except Formation.DoesNotExist:
                errors.append(f'Formateurs_Formations ligne {row_idx}: formation "{titre}" introuvable')
                continue
            except Formation.MultipleObjectsReturned:
                formation = Formation.objects.filter(formation=titre).first()

            try:
                formateur = Formateur.objects.get(numerobadge=numero)
            except Formateur.DoesNotExist:
                errors.append(f'Formateurs_Formations ligne {row_idx}: formateur "{numero}" introuvable')
                continue

            _mod = formation.modules.order_by('ordre').first()
            if not _mod:
                errors.append(f'Formateurs_Formations ligne {row_idx}: formation "{titre}" n\'a aucun module')
                continue
            _, created = ModuleFormateur.objects.get_or_create(
                module=_mod, formateur=formateur,
            )
            if created:
                count += 1
                self.stdout.write(f'  + Formateur assigné : {numero} → {titre}')
            else:
                self.stdout.write(f'  ~ Déjà assigné : {numero} → {titre}')
        return count


    # ─── Import Séances ──────────────────────────────

    def _import_seances_for_formation(self, ws, errors, formation):
        """Import séances pour une formation déjà connue (pas besoin de formation_titre)."""
        count = 0
        for row_idx, data in self._rows(ws):
            date_journee = self._parse_date(data.get('date_journee') or data.get('date'))
            if not date_journee:
                errors.append(f'Séances ligne {row_idx}: date_journee invalide ou manquante')
                continue

            numero = self._int(data.get('numero') or data.get('numero_seance'), default=None)
            if numero is None:
                errors.append(f'Séances ligne {row_idx}: numero de séance manquant')
                continue

            heure_debut = self._parse_time(
                data.get('heure_debut') or data.get('heure debut') or data.get('heure_debut_prevue')
            )
            heure_fin = self._parse_time(
                data.get('heure_fin') or data.get('heure fin') or data.get('heure_fin_prevue')
            )

            update_fields = {'intitule': self._str(data.get('intitule'))}
            if heure_debut is not None:
                update_fields['heure_debut_prevue'] = heure_debut
            if heure_fin is not None:
                update_fields['heure_fin_prevue'] = heure_fin

            _mod = formation.modules.order_by('ordre').first()
            if not _mod:
                errors.append(f'Séances ligne {row_idx}: formation sans module')
                continue
            obj, created = SessionModule.objects.update_or_create(
                module=_mod,
                date_journee=date_journee,
                numero=numero,
                defaults=update_fields,
            )
            if created:
                count += 1
        return count

    def _import_emploi_du_temps(self, ws, errors):
        """
        Import emploi du temps (séances) depuis un fichier à headers libres.
        Colonnes reconnues (insensible à la casse/accents) :
          - formation / titre           → titre de la formation (obligatoire)
          - date / date journée         → date de la séance (obligatoire)
          - numéro / numero / n°        → numéro de séance (obligatoire)
          - intitulé / intitule         → libellé de la séance (OPTIONNEL)
          - heure début / heure_debut   → heure de début (optionnel)
          - heure fin / heure_fin       → heure de fin (optionnel)
          - auto-démarrage / auto       → booléen (optionnel, défaut=True)
        Si les colonnes ne sont pas détectées par nom, fallback par position :
          0=formation, 1=date, 2=numéro, 3=heure début, 4=heure fin, 5=auto
        """
        count = 0
        col_map = {}  # nom normalisé → index colonne

        def _norm(h):
            import unicodedata
            s = unicodedata.normalize('NFD', str(h).strip().lower())
            s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
            return s.replace('-', ' ').replace('_', ' ')

        for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
            if row_idx == 1:
                # Construire le mapping header → index
                for idx, h in enumerate(row):
                    if h is None:
                        continue
                    n = _norm(h)
                    if any(k in n for k in ('formation',)) and 'col_formation' not in col_map:
                        col_map['col_formation'] = idx
                    elif any(k in n for k in ('date',)) and 'col_date' not in col_map:
                        col_map['col_date'] = idx
                    elif any(k in n for k in ('numero', 'n°', 'no')) and 'col_numero' not in col_map:
                        col_map['col_numero'] = idx
                    elif any(k in n for k in ('intitule', 'intitule', 'libelle', 'session')):
                        col_map['col_intitule'] = idx
                    elif any(k in n for k in ('heure debut', 'debut')) and 'col_hdebut' not in col_map:
                        col_map['col_hdebut'] = idx
                    elif any(k in n for k in ('heure fin', 'fin')) and 'col_hfin' not in col_map:
                        col_map['col_hfin'] = idx
                    elif any(k in n for k in ('auto',)):
                        col_map['col_auto'] = idx

                # Fallback par position si colonnes non détectées
                if 'col_formation' not in col_map: col_map['col_formation'] = 0
                if 'col_date' not in col_map: col_map['col_date'] = 1
                if 'col_numero' not in col_map: col_map['col_numero'] = 2
                # Sans intitulé : heure début = col 3, heure fin = col 4
                if 'col_intitule' not in col_map:
                    if 'col_hdebut' not in col_map: col_map['col_hdebut'] = 3
                    if 'col_hfin' not in col_map: col_map['col_hfin'] = 4
                    if 'col_auto' not in col_map: col_map['col_auto'] = 5
                else:
                    if 'col_hdebut' not in col_map: col_map['col_hdebut'] = 4
                    if 'col_hfin' not in col_map: col_map['col_hfin'] = 5
                    if 'col_auto' not in col_map: col_map['col_auto'] = 6

                self.stdout.write(f'  [EDT] Mapping colonnes : {col_map}')
                continue

            if not row or all(v is None or str(v).strip() == '' for v in row):
                break

            def _col(key): return row[col_map[key]] if col_map.get(key) is not None and col_map[key] < len(row) else None

            titre = self._str(_col('col_formation'))
            date_val = _col('col_date')
            numero_val = _col('col_numero')
            heure_debut_val = _col('col_hdebut')
            heure_fin_val = _col('col_hfin')
            auto_val = self._str(_col('col_auto'))
            intitule_val = _col('col_intitule') if 'col_intitule' in col_map else None

            if not titre:
                errors.append(f'Emploi du temps ligne {row_idx}: titre de formation manquant')
                continue

            date_journee = self._parse_date(date_val)
            if not date_journee:
                errors.append(f'Emploi du temps ligne {row_idx}: date invalide pour "{titre}"')
                continue

            numero = self._int(numero_val, default=None)
            if numero is None:
                errors.append(f'Emploi du temps ligne {row_idx}: numéro de séance manquant pour "{titre}"')
                continue

            try:
                formation = Formation.objects.get(formation=titre)
            except Formation.DoesNotExist:
                errors.append(f'Emploi du temps ligne {row_idx}: formation "{titre}" introuvable en base')
                continue
            except Formation.MultipleObjectsReturned:
                formation = Formation.objects.filter(formation=titre).first()

            heure_debut = self._parse_time(heure_debut_val)
            heure_fin = self._parse_time(heure_fin_val)
            auto_demarrage = auto_val.lower() in ('oui', 'yes', '1', 'true') if auto_val else True

            _mod = formation.modules.order_by('ordre').first()
            if not _mod:
                errors.append(f'Emploi du temps ligne {row_idx}: formation "{titre}" sans module')
                continue
            obj, created = SessionModule.objects.update_or_create(
                module=_mod,
                date_journee=date_journee,
                numero=numero,
                defaults={
                    'intitule': self._str(intitule_val),
                    'heure_debut_prevue': heure_debut,
                    'heure_fin_prevue': heure_fin,
                    'auto_demarrage': auto_demarrage,
                },
            )
            if created:
                count += 1
                self.stdout.write(f'  + Séance : {titre} — {date_journee} n°{numero}')
            else:
                self.stdout.write(f'  ~ Séance mise à jour : {titre} — {date_journee} n°{numero}')
        return count

    def _match_seance_module(self, titre, grade, groupe, vague):
        """Rapproche un module de séance ; assouplit grade/vague si correspondance unique."""
        strategies = []
        if grade and vague:
            strategies.append((
                Module.objects.filter(
                    intitule__iexact=titre,
                    grade__iexact=grade,
                    groupe__iexact=groupe,
                    vague__iexact=vague,
                ),
                'exacte',
            ))
        if grade:
            strategies.append((
                Module.objects.filter(
                    intitule__iexact=titre,
                    grade__iexact=grade,
                    groupe__iexact=groupe,
                ),
                'sans vague',
            ))
        if vague:
            strategies.append((
                Module.objects.filter(
                    intitule__iexact=titre,
                    groupe__iexact=groupe,
                    vague__iexact=vague,
                ),
                'sans grade',
            ))
        strategies.append((
            Module.objects.filter(
                intitule__iexact=titre,
                groupe__iexact=groupe,
            ),
            'sans grade ni vague',
        ))

        for qs, label in strategies:
            matches = list(qs.select_related('formation'))
            if len(matches) == 1:
                mod = matches[0]
                if label == 'exacte':
                    return matches, None
                return matches, (
                    f'rapprochement {label} → grade={mod.grade!r}, vague={mod.vague!r}'
                )
            if len(matches) > 1:
                details = sorted({
                    f'{m.grade}/{m.vague}' for m in matches if m.grade or m.vague
                })
                return None, f'ambigu ({label}) — candidats : {", ".join(details)}'
        return None, None

    def _import_seances(self, ws, errors):
        """
        Dispatch des séances par Module (intitule + grade + groupe + vague).
        ``groupe`` est obligatoire ; ``grade``/``vague`` sont assouplis si la
        correspondance unique existe (cellules fusionnées Excel, écarts mineurs).
        """
        count = 0
        updated = 0
        for row_idx, data in self._rows(ws):
            titre = self._normalize_module_title(self._str(
                data.get('module_titre')
                or data.get('formation_titre')
                or data.get('formation')
                or data.get('module')
            ))
            if not titre:
                errors.append(f'Séances ligne {row_idx}: module_titre manquant')
                continue

            date_journee = self._parse_date(data.get('date_journee') or data.get('date'))
            if not date_journee:
                errors.append(f'Séances ligne {row_idx}: date_journee invalide ou manquante')
                continue

            numero = self._int(data.get('numero') or data.get('numero_seance'), default=None)
            if numero is None:
                errors.append(f'Séances ligne {row_idx}: numero de séance manquant')
                continue

            groupe = self._str(data.get('groupe'))
            grade = self._str(data.get('grade'))
            vague = self._str(data.get('vague'))

            if not groupe:
                errors.append(
                    f'Séances ligne {row_idx}: groupe manquant '
                    f'(obligatoire pour identifier le cours)'
                )
                continue

            modules_matched, hint = self._match_seance_module(titre, grade, groupe, vague)
            if not modules_matched:
                if hint and hint.startswith('ambigu'):
                    errors.append(
                        f'Séances ligne {row_idx}: module "{titre}" {hint} '
                        f'(fichier : grade={grade!r}, groupe={groupe!r}, vague={vague!r})'
                    )
                else:
                    errors.append(
                        f'Séances ligne {row_idx}: module "{titre}" introuvable '
                        f'(grade={grade!r}, groupe={groupe!r}, vague={vague!r})'
                    )
                continue
            if hint:
                self.stdout.write(f'  ⚠ Séances ligne {row_idx}: {hint}')

            heure_debut = self._parse_time(data.get('heure_debut'))
            heure_fin = self._parse_time(data.get('heure_fin'))
            intitule = self._str(data.get('intitule') or titre)

            for module_obj in modules_matched:
                obj, created = SessionModule.objects.get_or_create(
                    module=module_obj,
                    date_journee=date_journee,
                    numero=numero,
                    defaults={
                        'intitule': intitule,
                        'heure_debut_prevue': heure_debut,
                        'heure_fin_prevue': heure_fin,
                    },
                )
                if created:
                    count += 1
                    self.stdout.write(
                        f'  + Séance : {module_obj.intitule} '
                        f'({module_obj.grade}/{module_obj.groupe}) — {date_journee} n°{numero}'
                    )
                else:
                    # Mettre à jour les heures si fournies
                    changed = False
                    if heure_debut and obj.heure_debut_prevue != heure_debut:
                        obj.heure_debut_prevue = heure_debut
                        changed = True
                    if heure_fin and obj.heure_fin_prevue != heure_fin:
                        obj.heure_fin_prevue = heure_fin
                        changed = True
                    if changed:
                        obj.save(update_fields=['heure_debut_prevue', 'heure_fin_prevue'])
                    updated += 1
                    self.stdout.write(
                        f'  ~ Séance existante : {module_obj.intitule} '
                        f'({module_obj.grade}/{module_obj.groupe}) — {date_journee} n°{numero}'
                    )
        return count, updated

    def _parse_time(self, val):
        if val is None:
            return None
        from datetime import time
        if isinstance(val, time):
            return val
        if isinstance(val, datetime):
            return val.time()
        if isinstance(val, float):
            # Excel stores times as a fraction of 24h (e.g. 0.333... = 08:00)
            total_seconds = round(val * 86400)
            h = (total_seconds // 3600) % 24
            m = (total_seconds % 3600) // 60
            s = total_seconds % 60
            return time(h, m, s)
        val = str(val).strip()
        for fmt in ('%H:%M:%S', '%H:%M', '%H%M'):
            try:
                return datetime.strptime(val, fmt).time()
            except ValueError:
                continue
        return None


class _DryRunRollback(Exception):
    """Exception interne pour annuler la transaction en dry-run."""
    pass
