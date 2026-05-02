"""
Commande : python manage.py auto_close_pointages

Pour chaque pointage EN_COURS dont la séance est terminée depuis plus d'1 heure
(ou dont heure_fin_prevue + 1h est dépassée) :
  - timestamp_sortie = timestamp_entree  (durée = 0)
  - duree_presence_minutes = 0
  - statut = ABSENT_NON_BADGE
  - motif tracé en AuditLog (AUTO_ABSENT)

À planifier via cron toutes les 5-15 minutes :
  */10 * * * * /path/to/venv/bin/python /path/to/manage.py auto_close_pointages

Les pointages issus du badgeage web (device_id WEB_BADGE / OFFLINE_WEB) ne sont pas
soumis aux règles MOBILE_HEARTBEAT_* (pas de heartbeat navigateur).
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from django.conf import settings

from presences.models import AuditLog, Pointage
from authentication.emails import send_suspect_heartbeat_email


MOTIF = "N'a pas badgé à la sortie de la séance"
DELAI_MINUTES = getattr(settings, 'AUTO_ABSENT_DELAI_MINUTES', 60)
SUSPECT_TIMEOUT_MINUTES = getattr(settings, 'MOBILE_HEARTBEAT_SUSPECT_TIMEOUT_MINUTES', 60)
AUTO_EXIT_TIMEOUT_MINUTES = getattr(settings, 'MOBILE_HEARTBEAT_AUTO_EXIT_TIMEOUT_MINUTES', 120)

# Badgeage web : pas d’endpoint heartbeat → ne pas appliquer les timeouts mobile.
NO_MOBILE_HEARTBEAT_DEVICE_IDS = frozenset({'WEB_BADGE', 'OFFLINE_WEB'})


class Command(BaseCommand):
    help = "Marque ABSENT les auditeurs/formateurs qui n'ont pas badgé la sortie 1h après la fin de la séance."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Affiche les pointages concernés sans les modifier.",
        )
        parser.add_argument(
            '--delai',
            type=int,
            default=None,
            help="Délai en minutes après la fin de séance avant marquage absent "
                 "(défaut : valeur AUTO_ABSENT_DELAI_MINUTES du .env).",
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        delai = options['delai'] if options['delai'] is not None else getattr(settings, 'AUTO_ABSENT_DELAI_MINUTES', 60)
        now = timezone.now()

        pointages_ouverts = (
            Pointage.objects
            .filter(
                statut__in=[Pointage.Statut.EN_COURS, Pointage.Statut.HORS_LIGNE_SUSPECT],
                timestamp_sortie__isnull=True,
            )
            .select_related(
                'session__module__formation',
                'session__module__superviseur',
                'participant',
                'formateur',
                'encadrant',
            )
        )

        traites = 0
        for pt in pointages_ouverts:
            seance = pt.session
            fin_seance = self._fin_seance(seance)

            personne = pt.participant or pt.formateur or pt.encadrant
            if personne:
                nom = (
                    f"{getattr(personne, 'nom', '')} {getattr(personne, 'prenom', '')}".strip()
                    or f"{getattr(personne, 'last_name', '')} {getattr(personne, 'first_name', '')}".strip()
                    or getattr(personne, 'username', '?')
                )
            else:
                nom = "?"
            numero = (
                getattr(personne, 'numerobadge', None)
                or getattr(personne, 'matricule', None)
                or getattr(personne, 'numero', '?')
            ) if personne else '?'
            type_str = 'formateur' if pt.formateur_id else 'encadrant' if pt.encadrant_id else 'participant'

            if dry_run:
                self.stdout.write(
                    f"[DRY-RUN] {numero} {nom} — séance {seance} — fin estimée {fin_seance}"
                )
                traites += 1
                continue

            # 1) Règle historique : absent non badgé après fin de séance + délai
            if fin_seance and fin_seance + timedelta(minutes=delai) <= now:
                pt.timestamp_sortie = pt.timestamp_entree
                pt.duree_presence_minutes = 0
                pt.statut = Pointage.Statut.ABSENT_NON_BADGE
                pt.save(update_fields=['timestamp_sortie', 'duree_presence_minutes', 'statut', 'updated_at'])

                AuditLog.objects.create(
                    action=AuditLog.Action.AUTO_ABSENT,
                    acteur=None,
                    acteur_label='Système',
                    cible_type=type_str,
                    cible_numero=numero,
                    cible_nom=nom,
                    formation=seance.module.formation,
                    formation_titre=seance.module.formation.formation,
                    pointage=pt,
                    ip_address=None,
                    device_id='SYSTEM',
                    extra={
                        'motif': MOTIF,
                        'delai_minutes': delai,
                        'fin_seance': fin_seance.isoformat(),
                    },
                )

                traites += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"ABSENT_NON_BADGE : {numero} {nom} — {seance.module.formation.formation}"
                    )
                )
                continue

            # 2) Règle anti-fraude mobile : gestion du timeout heartbeat
            if (pt.device_id or '') in NO_MOBILE_HEARTBEAT_DEVICE_IDS:
                continue

            last_seen_at = pt.last_heartbeat_at or pt.timestamp_entree
            silence_minutes = int((now - last_seen_at).total_seconds() // 60)

            if silence_minutes >= AUTO_EXIT_TIMEOUT_MINUTES:
                pt.timestamp_sortie = now
                pt.statut = Pointage.Statut.SORTIE_AUTO
                pt.calculer_duree()
                pt.save(update_fields=['timestamp_sortie', 'duree_presence_minutes', 'statut', 'updated_at'])

                AuditLog.objects.create(
                    action=AuditLog.Action.AUTO_EXIT,
                    acteur=None,
                    acteur_label='Système',
                    cible_type=type_str,
                    cible_numero=numero,
                    cible_nom=nom,
                    formation=seance.module.formation,
                    formation_titre=seance.module.formation.formation,
                    pointage=pt,
                    ip_address=None,
                    device_id='SYSTEM',
                    extra={
                        'motif': 'NO_HEARTBEAT_TIMEOUT',
                        'silence_minutes': silence_minutes,
                        'last_heartbeat_at': last_seen_at.isoformat() if last_seen_at else None,
                        'auto_exit_timeout_minutes': AUTO_EXIT_TIMEOUT_MINUTES,
                        'battery_level': pt.last_battery_level,
                        'is_charging': pt.last_is_charging,
                    },
                )

                traites += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"SORTIE_AUTO : {numero} {nom} — {seance.module.formation.formation}"
                    )
                )
                continue

            if (
                silence_minutes >= SUSPECT_TIMEOUT_MINUTES
                and pt.statut == Pointage.Statut.EN_COURS
            ):
                pt.statut = Pointage.Statut.HORS_LIGNE_SUSPECT
                pt.save(update_fields=['statut', 'updated_at'])

                AuditLog.objects.create(
                    action=AuditLog.Action.NO_HEARTBEAT,
                    acteur=None,
                    acteur_label='Système',
                    cible_type=type_str,
                    cible_numero=numero,
                    cible_nom=nom,
                    formation=seance.module.formation,
                    formation_titre=seance.module.formation.formation,
                    pointage=pt,
                    ip_address=None,
                    device_id='SYSTEM',
                    extra={
                        'motif': 'NO_HEARTBEAT',
                        'silence_minutes': silence_minutes,
                        'last_heartbeat_at': last_seen_at.isoformat() if last_seen_at else None,
                        'suspect_timeout_minutes': SUSPECT_TIMEOUT_MINUTES,
                        'battery_level': pt.last_battery_level,
                        'is_charging': pt.last_is_charging,
                    },
                )

                traites += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"HORS_LIGNE_SUSPECT : {numero} {nom} — {seance.module.formation.formation}"
                    )
                )

                encadrant = seance.module.superviseur
                seance_label = seance.intitule or f'Séance {seance.numero}'
                send_suspect_heartbeat_email(
                    encadrant=encadrant,
                    personne_nom=nom,
                    personne_numero=numero,
                    formation_titre=seance.module.formation.formation,
                    module_intitule=seance.module.intitule,
                    seance_label=seance_label,
                    silence_minutes=silence_minutes,
                )
                continue

        label = "simulés" if dry_run else "traités"
        self.stdout.write(self.style.SUCCESS(f"{traites} pointage(s) {label}."))

    def _fin_seance(self, seance):
        """
        Retourne le datetime de fin de séance (UTC-aware) :
          1. seance.terminee_le  (fin réelle)
          2. combinaison date_journee + heure_fin_prevue
          3. None si aucune info disponible
        """
        if seance.terminee_le:
            return seance.terminee_le

        if seance.date_journee and seance.heure_fin_prevue:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            tz = ZoneInfo('Africa/Abidjan')
            return timezone.make_aware(
                datetime.combine(seance.date_journee, seance.heure_fin_prevue),
                tz,
            )

        return None
