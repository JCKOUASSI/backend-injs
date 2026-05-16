"""
Commande : python manage.py backfill_duree_prevue

Pour chaque Module dont ``duree_prevue_heures`` vaut 0 (ou NULL), tente de
récupérer la valeur depuis un module "jumeau" (même ``secretariat`` et même
``intitule``, insensible à la casse/espaces) qui, lui, a une durée > 0.

Ne supprime rien. N'affecte que les modules à 0.

Usage :
  python manage.py backfill_duree_prevue --dry-run
  python manage.py backfill_duree_prevue
  python manage.py backfill_duree_prevue --secretariat "FAB B"
"""

from collections import defaultdict
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Q

from formations.models import Module


def _norm(s):
    return ' '.join((s or '').strip().split()).lower()


class Command(BaseCommand):
    help = (
        "Recopie duree_prevue_heures depuis un module 'jumeau' (même secrétariat "
        "+ même intitulé) lorsque la valeur courante est 0."
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            '--secretariat',
            type=str,
            default=None,
            help="Filtrer par libellé du type de secrétariat (ex. 'FAB B').",
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        secretariat = options['secretariat']

        modules_qs = Module.objects.select_related('secretariat__type').all()
        if secretariat:
            modules_qs = modules_qs.filter(
                secretariat__type__libelle__iexact=secretariat
            )

        # Index jumeaux : (secretariat_id, intitule_norm) -> max(duree_prevue_heures>0)
        index_duree = defaultdict(float)
        for m in modules_qs:
            d = float(m.duree_prevue_heures or 0)
            if d > 0:
                cle = (m.secretariat_id, _norm(m.intitule))
                if d > index_duree[cle]:
                    index_duree[cle] = d

        rectifies = 0
        ignores = 0
        sans_jumeau = 0
        for m in modules_qs:
            d = float(m.duree_prevue_heures or 0)
            if d > 0:
                ignores += 1
                continue
            cle = (m.secretariat_id, _norm(m.intitule))
            nouvelle = index_duree.get(cle)
            if not nouvelle or nouvelle <= 0:
                sans_jumeau += 1
                continue

            sec_lib = ''
            try:
                sec_lib = m.secretariat.type.libelle if m.secretariat and m.secretariat.type else ''
            except AttributeError:
                pass

            label = (
                f"#{m.pk} {m.intitule!r} (sec={sec_lib}, grade={m.grade!r}) "
                f"0h -> {nouvelle:.1f}h"
            )
            if dry_run:
                self.stdout.write(f"[dry-run] {label}")
            else:
                m.duree_prevue_heures = Decimal(str(nouvelle))
                m.save(update_fields=['duree_prevue_heures'])
                self.stdout.write(self.style.SUCCESS(label))
            rectifies += 1

        suffixe = " (dry-run)" if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"\nTerminé{suffixe}. Rectifiés : {rectifies} | "
                f"Sans jumeau renseigné : {sans_jumeau} | "
                f"Déjà OK : {ignores}"
            )
        )
