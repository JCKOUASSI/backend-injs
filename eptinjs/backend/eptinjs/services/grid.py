"""Grilles d'emploi du temps et statistiques."""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from django.db.models import Count, Q, Sum

from ..models import PeriodeFormation, Pointage, Seance
from .common import heures, parse_date, parse_uuid, parse_uuid_list

JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']


def seances_filtrees(params, *, base=None):
    """Applique les filtres communs de l'emploi du temps."""
    queryset = base if base is not None else Seance.objects.exclude(statut='annulee')
    queryset = queryset.select_related(
        'periode', 'course', 'course__teaching_unit', 'promotion', 'promotion__program',
        'groupe', 'room', 'teacher__user', 'supervisor__user',
    )

    if periode := parse_uuid(params.get('periode')):
        queryset = queryset.filter(periode_id=periode)
    if academic_year := parse_uuid(params.get('academic_year')):
        queryset = queryset.filter(periode__academic_year_id=academic_year)
    if promotions := parse_uuid_list(params.get('promotion')):
        queryset = queryset.filter(promotion_id__in=promotions)
    if courses := parse_uuid_list(params.get('course')):
        queryset = queryset.filter(course_id__in=courses)
    if teacher := parse_uuid(params.get('teacher')):
        queryset = queryset.filter(Q(teacher_id=teacher) | Q(supervisor_id=teacher))
    if room := parse_uuid(params.get('room')):
        queryset = queryset.filter(room_id=room)
    if groupe := parse_uuid(params.get('groupe')):
        queryset = queryset.filter(groupe_id=groupe)
    if session_kind := (params.get('session_kind') or '').strip():
        queryset = queryset.filter(session_kind=session_kind)
    if statut := (params.get('statut') or '').strip():
        queryset = queryset.filter(statut=statut)
    if debut := parse_date(params.get('date_debut')):
        queryset = queryset.filter(date__gte=debut)
    if fin := parse_date(params.get('date_fin')):
        queryset = queryset.filter(date__lte=fin)
    if jour := parse_date(params.get('date')):
        queryset = queryset.filter(date=jour)

    return queryset.order_by('date', 'heure_debut')


def construire_grille(params, *, base=None) -> dict:
    """Grille hebdomadaire ou complète, prête à afficher.

    Sans ``semaine``, la grille couvre l'intégralité du périmètre filtré, ce
    qui permet d'afficher les séances de toutes les périodes de formation.
    ``base`` restreint le périmètre en amont (emploi du temps personnel).
    """
    queryset = seances_filtrees(params, base=base)

    semaine = parse_date(params.get('semaine'))
    if semaine:
        lundi = semaine - timedelta(days=semaine.weekday())
        dimanche = lundi + timedelta(days=6)
        queryset = queryset.filter(date__gte=lundi, date__lte=dimanche)

    seances = list(queryset)
    stats = {
        ligne['seance_id']: ligne
        for ligne in Pointage.objects.filter(seance__in=seances).values('seance_id').annotate(
            attendus=Count('id'),
            presents=Count('id', filter=Q(statut__in=['present', 'retard', 'force'])),
        )
    }

    par_jour = defaultdict(list)
    for seance in seances:
        compteurs = stats.get(seance.id, {})
        par_jour[seance.date.isoformat()].append({
            'id': str(seance.id),
            'periode': str(seance.periode_id),
            'periode_code': seance.periode.code,
            'course': str(seance.course_id),
            'course_code': seance.course.code,
            'course_name': seance.course.name,
            'teaching_unit_code': seance.course.teaching_unit.code,
            'promotion': str(seance.promotion_id),
            'promotion_name': seance.promotion.name,
            'program_code': seance.promotion.program.code,
            'groupe_code': seance.groupe.code if seance.groupe_id else None,
            'room': str(seance.room_id) if seance.room_id else None,
            'room_code': seance.room.code if seance.room_id else None,
            'teacher': str(seance.teacher_id) if seance.teacher_id else None,
            'teacher_name': seance.teacher.user.get_full_name() if seance.teacher_id else None,
            'session_kind': seance.session_kind,
            'session_kind_display': seance.get_session_kind_display(),
            'date': seance.date.isoformat(),
            'day_of_week': seance.date.weekday(),
            'day_display': JOURS[seance.date.weekday()],
            'heure_debut': seance.heure_debut.strftime('%H:%M'),
            'heure_fin': seance.heure_fin.strftime('%H:%M'),
            'duree_heures': seance.duree_heures,
            'statut': seance.statut,
            'statut_display': seance.get_statut_display(),
            'attendus_count': compteurs.get('attendus', 0),
            'presents_count': compteurs.get('presents', 0),
        })

    minutes = sum(seance.duree_minutes or 0 for seance in seances)
    dates = [seance.date for seance in seances]
    return {
        'count': len(seances),
        'heures_totales': heures(minutes),
        'jours': [
            {'date': jour, 'day_display': JOURS[seances_du_jour[0]['day_of_week']], 'seances': seances_du_jour}
            for jour, seances_du_jour in sorted(par_jour.items())
        ],
        'seances': [item for jour in sorted(par_jour) for item in par_jour[jour]],
        'plage': {
            'debut': min(dates).isoformat() if dates else None,
            'fin': max(dates).isoformat() if dates else None,
        },
    }


def statistiques(params) -> dict:
    """Indicateurs de pilotage de l'emploi du temps et du badgeage."""
    queryset = seances_filtrees(params)
    seances = queryset.aggregate(
        total=Count('id'),
        minutes=Sum('duree_minutes'),
        planifiees=Count('id', filter=Q(statut='planifiee')),
        en_cours=Count('id', filter=Q(statut='en_cours')),
        terminees=Count('id', filter=Q(statut='terminee')),
        sans_salle=Count('id', filter=Q(room__isnull=True)),
        sans_enseignant=Count('id', filter=Q(teacher__isnull=True)),
    )

    pointages = Pointage.objects.filter(seance__in=queryset).aggregate(
        attendus=Count('id'),
        presents=Count('id', filter=Q(statut__in=['present', 'retard', 'force'])),
        absents=Count('id', filter=Q(statut='absent')),
        retards=Count('id', filter=Q(statut='retard')),
    )

    par_periode = list(
        queryset.values('periode_id', 'periode__code', 'periode__libelle')
        .annotate(seances=Count('id'), minutes=Sum('duree_minutes'))
        .order_by('periode__ordre')
    )

    attendus = pointages['attendus'] or 0
    return {
        'seances': {
            **{cle: valeur or 0 for cle, valeur in seances.items() if cle != 'minutes'},
            'heures': heures(seances['minutes']),
        },
        'presences': {
            **{cle: valeur or 0 for cle, valeur in pointages.items()},
            'taux_presence': round((pointages['presents'] or 0) / attendus * 100, 1) if attendus else 0.0,
        },
        'par_periode': [
            {
                'periode': str(ligne['periode_id']),
                'code': ligne['periode__code'],
                'libelle': ligne['periode__libelle'],
                'seances': ligne['seances'],
                'heures': heures(ligne['minutes']),
            }
            for ligne in par_periode
        ],
        'periodes_actives': PeriodeFormation.objects.filter(is_active=True).count(),
    }
