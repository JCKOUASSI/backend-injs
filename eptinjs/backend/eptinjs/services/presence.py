"""Présences et badgeage QR.

Une ``Seance`` étant déjà datée, elle tient le rôle de séance de badgeage : pas
d'entité ``AttendanceSession`` intermédiaire. Le premier scan enregistre une
entrée, le second une sortie.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.faculty.models import BadgeDevice, Teacher
from apps.students.models import Student

from ..models import GroupeMembre, PlanningAuditLog, Pointage, Seance, SeanceQRToken

DUREE_VALIDITE_QR = timedelta(hours=12)
SEUIL_RETARD_MINUTES = 15


class BadgeageRefuse(Exception):
    """Scan rejeté (jeton invalide, séance fermée, hors géofence, appareil non lié)."""


def debut_prevu(seance: Seance):
    """Datetime de début théorique de la séance, dans le fuseau du projet."""
    naif = datetime.combine(seance.date, seance.heure_debut)
    if settings.USE_TZ:
        return timezone.make_aware(naif, timezone.get_current_timezone())
    return naif


def distance_metres(lat1, lon1, lat2, lon2) -> float:
    """Distance orthodromique en mètres."""
    rayon = 6_371_000
    phi1, phi2 = radians(float(lat1)), radians(float(lat2))
    delta_phi = radians(float(lat2) - float(lat1))
    delta_lambda = radians(float(lon2) - float(lon1))
    a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
    return 2 * rayon * asin(sqrt(a))


def verifier_geofence(seance: Seance, latitude, longitude, accuracy_m) -> None:
    """Contrôle la position si la salle est géolocalisée."""
    room = seance.room
    if not room or room.latitude is None or room.longitude is None:
        return
    if latitude is None or longitude is None:
        raise BadgeageRefuse('Position GPS requise pour badger sur cette salle.')

    precision_max = getattr(settings, 'INJS_GEOFENCE_MAX_ACCURACY_M', 80)
    if accuracy_m is not None and float(accuracy_m) > precision_max:
        raise BadgeageRefuse(
            f'Précision GPS insuffisante ({int(float(accuracy_m))} m, maximum {precision_max} m).',
        )

    rayon = getattr(settings, 'INJS_GEOFENCE_RADIUS_M', 250)
    distance = distance_metres(latitude, longitude, room.latitude, room.longitude)
    if distance > rayon:
        raise BadgeageRefuse(
            f'Vous êtes à {int(distance)} m de la salle {room.code} (rayon autorisé : {rayon} m).',
        )


def verifier_appareil(user, device_id: str) -> None:
    """Un utilisateur ne badge que depuis son appareil déclaré."""
    if not device_id:
        return
    actif = BadgeDevice.objects.filter(user=user, is_active=True).first()
    if actif is None:
        BadgeDevice.objects.create(user=user, device_id=device_id, is_active=True, last_seen_at=timezone.now())
        return
    if actif.device_id != device_id:
        raise BadgeageRefuse(
            'Cet appareil n’est pas celui enregistré pour votre compte. '
            'Contactez la scolarité pour le réinitialiser.',
        )
    BadgeDevice.objects.filter(pk=actif.pk).update(last_seen_at=timezone.now())


def etudiants_attendus(seance: Seance):
    """Étudiants concernés : membres du groupe, sinon promotion entière."""
    if seance.groupe_id:
        ids = GroupeMembre.objects.filter(groupe_id=seance.groupe_id).values_list('student_id', flat=True)
        return Student.objects.filter(id__in=list(ids), status='active').select_related('user')
    return Student.objects.filter(promotion_id=seance.promotion_id, status='active').select_related('user')


@transaction.atomic
def constituer_liste(seance: Seance) -> int:
    """Crée les pointages « attendu » manquants pour la séance."""
    existants_etudiants = set(
        seance.pointages.filter(student__isnull=False).values_list('student_id', flat=True),
    )
    nouveaux = [
        Pointage(seance=seance, role='etudiant', student=etudiant, statut='attendu')
        for etudiant in etudiants_attendus(seance)
        if etudiant.id not in existants_etudiants
    ]

    for role, teacher_id in (('formateur', seance.teacher_id), ('encadrant', seance.supervisor_id)):
        if not teacher_id:
            continue
        if seance.pointages.filter(teacher_id=teacher_id, role=role).exists():
            continue
        nouveaux.append(Pointage(seance=seance, role=role, teacher_id=teacher_id, statut='attendu'))

    if nouveaux:
        Pointage.objects.bulk_create(nouveaux, ignore_conflicts=True)
    return len(nouveaux)


@transaction.atomic
def demarrer_seance(seance: Seance, actor=None) -> SeanceQRToken:
    """Ouvre la séance au badgeage et émet un jeton QR."""
    if seance.statut == 'terminee':
        raise BadgeageRefuse('Cette séance est déjà terminée.')
    if seance.statut == 'annulee':
        raise BadgeageRefuse('Cette séance est annulée.')

    conflit = (
        Seance.objects
        .filter(statut='en_cours', date=seance.date, promotion_id=seance.promotion_id)
        .exclude(pk=seance.pk)
    )
    if seance.groupe_id:
        conflit = conflit.filter(groupe_id=seance.groupe_id)
    if conflit.exists():
        raise BadgeageRefuse('Une autre séance est déjà en cours pour cet auditoire.')

    seance.statut = 'en_cours'
    seance.started_at = seance.started_at or timezone.now()
    seance.started_by = actor
    seance.save(update_fields=['statut', 'started_at', 'started_by', 'updated_at'])

    constituer_liste(seance)
    token = generer_token(seance, actor=actor)
    PlanningAuditLog.log('start', actor=actor, periode=seance.periode, seance=seance)
    return token


@transaction.atomic
def cloturer_seance(seance: Seance, actor=None) -> dict:
    """Ferme la séance : sorties automatiques et absences sur les non-badgés."""
    maintenant = timezone.now()
    sorties, absents = 0, 0

    for pointage in seance.pointages.select_related('seance'):
        if pointage.entree_at and not pointage.sortie_at:
            pointage.sortie_at = maintenant
            pointage.recalculer_duree()
            pointage.save(update_fields=['sortie_at', 'duree_minutes', 'updated_at'])
            sorties += 1
        elif pointage.statut == 'attendu':
            pointage.statut = 'absent'
            pointage.source = 'auto'
            pointage.save(update_fields=['statut', 'source', 'updated_at'])
            absents += 1

    seance.qr_tokens.filter(is_active=True).update(is_active=False)
    seance.statut = 'terminee'
    seance.ended_at = maintenant
    seance.save(update_fields=['statut', 'ended_at', 'updated_at'])

    PlanningAuditLog.log(
        'stop', actor=actor, periode=seance.periode, seance=seance,
        sorties_auto=sorties, absents=absents,
    )
    return {'sorties_automatiques': sorties, 'absents': absents}


def generer_token(seance: Seance, actor=None, *, regenerer: bool = False) -> SeanceQRToken:
    """Renvoie le jeton actif, ou en crée un nouveau."""
    if regenerer:
        seance.qr_tokens.filter(is_active=True).update(is_active=False)
    else:
        actif = seance.token_actif()
        if actif is not None:
            return actif
    return SeanceQRToken.objects.create(
        seance=seance,
        expires_at=timezone.now() + DUREE_VALIDITE_QR,
        created_by=actor,
    )


def _resoudre_participant(user, seance: Seance) -> tuple[str, Student | None, Teacher | None]:
    """Détermine le rôle du porteur du compte sur cette séance."""
    etudiant = Student.objects.filter(user=user).select_related('user').first()
    if etudiant is not None:
        attendus = etudiants_attendus(seance).values_list('id', flat=True)
        if etudiant.id not in set(attendus):
            raise BadgeageRefuse('Vous n’êtes pas inscrit à cette séance.')
        return 'etudiant', etudiant, None

    enseignant = Teacher.objects.filter(user=user).select_related('user').first()
    if enseignant is not None:
        if seance.teacher_id == enseignant.id:
            return 'formateur', None, enseignant
        if seance.supervisor_id == enseignant.id:
            return 'encadrant', None, enseignant
        raise BadgeageRefuse('Vous n’intervenez pas sur cette séance.')

    raise BadgeageRefuse('Votre compte n’est associé ni à un étudiant ni à un enseignant.')


@transaction.atomic
def scanner(*, token_value, user, device_id='', latitude=None, longitude=None, accuracy_m=None) -> dict:
    """Traite un scan QR : première lecture = entrée, seconde = sortie."""
    token = (
        SeanceQRToken.objects
        .select_related('seance', 'seance__room', 'seance__course', 'seance__periode')
        .filter(token=token_value)
        .first()
    )
    if token is None:
        raise BadgeageRefuse('QR code inconnu.')
    if not token.est_valide:
        raise BadgeageRefuse('QR code expiré. Demandez à l’enseignant d’en régénérer un.')

    seance = token.seance
    if seance.statut != 'en_cours':
        raise BadgeageRefuse('La séance n’est pas ouverte au badgeage.')

    verifier_appareil(user, device_id)
    verifier_geofence(seance, latitude, longitude, accuracy_m)

    role, etudiant, enseignant = _resoudre_participant(user, seance)
    pointage, _ = Pointage.objects.get_or_create(
        seance=seance,
        student=etudiant,
        teacher=enseignant,
        role=role,
        defaults={'statut': 'attendu'},
    )

    maintenant = timezone.now()
    pointage.device_id = device_id or pointage.device_id
    pointage.latitude = latitude if latitude is not None else pointage.latitude
    pointage.longitude = longitude if longitude is not None else pointage.longitude
    pointage.accuracy_m = accuracy_m if accuracy_m is not None else pointage.accuracy_m
    pointage.last_heartbeat_at = maintenant
    pointage.source = 'qr'

    if pointage.entree_at is None:
        pointage.entree_at = maintenant
        retard_minutes = (maintenant - debut_prevu(seance)).total_seconds() / 60
        pointage.statut = 'retard' if retard_minutes > SEUIL_RETARD_MINUTES else 'present'
        sens = 'entree'
    elif pointage.sortie_at is None:
        pointage.sortie_at = maintenant
        pointage.recalculer_duree()
        sens = 'sortie'
    else:
        raise BadgeageRefuse('Vous avez déjà badgé votre entrée et votre sortie sur cette séance.')

    pointage.save()
    PlanningAuditLog.log(
        'badge', actor=user, periode=seance.periode, seance=seance, sens=sens, role=role,
    )

    return {
        'sens': sens,
        'role': role,
        'pointage': str(pointage.id),
        'statut': pointage.statut,
        'personne': pointage.personne_nom,
        'seance': {
            'id': str(seance.id),
            'course_code': seance.course.code,
            'date': seance.date.isoformat(),
            'heure_debut': seance.heure_debut.strftime('%H:%M'),
            'heure_fin': seance.heure_fin.strftime('%H:%M'),
            'room_code': seance.room.code if seance.room_id else None,
        },
        'entree_at': pointage.entree_at.isoformat() if pointage.entree_at else None,
        'sortie_at': pointage.sortie_at.isoformat() if pointage.sortie_at else None,
        'duree_minutes': pointage.duree_minutes,
    }


@transaction.atomic
def marquer(seance: Seance, *, statut: str, students=None, teachers=None, notes='', actor=None) -> int:
    """Marquage manuel en masse depuis la fiche Cours."""
    constituer_liste(seance)
    maintenant = timezone.now()
    modifies = 0

    queryset = seance.pointages.all()
    filtres = []
    if students:
        filtres.append(queryset.filter(student_id__in=students))
    if teachers:
        filtres.append(queryset.filter(teacher_id__in=teachers))
    if not filtres:
        filtres = [queryset]

    for lot in filtres:
        for pointage in lot:
            pointage.statut = statut
            pointage.source = 'manuel'
            pointage.recorded_by = actor
            if notes:
                pointage.notes = notes
            if statut in {'present', 'retard', 'force'} and pointage.entree_at is None:
                pointage.entree_at = maintenant
            pointage.save()
            modifies += 1

    PlanningAuditLog.log(
        'update', actor=actor, periode=seance.periode, seance=seance,
        marquage=statut, pointages=modifies,
    )
    return modifies


@transaction.atomic
def forcer_badgeage(seance: Seance, *, taux_min=80, taux_max=95, actor=None) -> dict:
    """Force aléatoirement une proportion d'étudiants en présence.

    Reprise du forçage en masse de SYGEP : dépannage lorsque le badgeage
    mobile est indisponible pendant une séance.
    """
    constituer_liste(seance)
    attendus = list(seance.pointages.filter(role='etudiant', statut='attendu'))
    if not attendus:
        return {'forces': 0, 'attendus': 0}

    taux = random.randint(min(taux_min, taux_max), max(taux_min, taux_max))
    nombre = max(1, round(len(attendus) * taux / 100))
    selection = random.sample(attendus, min(nombre, len(attendus)))
    maintenant = timezone.now()

    for pointage in selection:
        pointage.statut = 'force'
        pointage.source = 'force'
        pointage.entree_at = pointage.entree_at or maintenant
        pointage.recorded_by = actor
        pointage.save(update_fields=['statut', 'source', 'entree_at', 'recorded_by', 'updated_at'])

    PlanningAuditLog.log(
        'force', actor=actor, periode=seance.periode, seance=seance,
        forces=len(selection), taux=taux,
    )
    return {'forces': len(selection), 'attendus': len(attendus), 'taux_applique': taux}


def resume_seance(seance: Seance) -> dict:
    """Compteurs et listes pour l'onglet Présences."""
    pointages = list(
        seance.pointages.select_related('student__user', 'teacher__user').order_by('role', 'id'),
    )
    presents = [item for item in pointages if item.est_present]
    absents = [item for item in pointages if item.statut == 'absent']
    attendus = [item for item in pointages if item.statut == 'attendu']

    return {
        'seance': str(seance.id),
        'statut': seance.statut,
        'date': seance.date.isoformat(),
        'heure_debut': seance.heure_debut.strftime('%H:%M'),
        'heure_fin': seance.heure_fin.strftime('%H:%M'),
        'compteurs': {
            'attendus': len(pointages),
            'presents': len(presents),
            'absents': len(absents),
            'non_badges': len(attendus),
            'en_salle': len([item for item in presents if item.entree_at and not item.sortie_at]),
            'taux_presence': round(len(presents) / len(pointages) * 100, 1) if pointages else 0.0,
        },
        'pointages': [
            {
                'id': str(item.id),
                'role': item.role,
                'role_display': item.get_role_display(),
                'student': str(item.student_id) if item.student_id else None,
                'teacher': str(item.teacher_id) if item.teacher_id else None,
                'nom': item.personne_nom,
                'matricule': (
                    item.student.matricule if item.student_id
                    else (item.teacher.employee_id if item.teacher_id else None)
                ),
                'statut': item.statut,
                'statut_display': item.get_statut_display(),
                'source': item.source,
                'entree_at': item.entree_at.isoformat() if item.entree_at else None,
                'sortie_at': item.sortie_at.isoformat() if item.sortie_at else None,
                'duree_minutes': item.duree_minutes,
                'en_salle': bool(item.entree_at and not item.sortie_at),
            }
            for item in pointages
        ],
    }
