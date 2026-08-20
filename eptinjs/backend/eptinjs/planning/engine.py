"""Allocateur glouton jour par jour.

Portage de ``GroupePlanningOrchestrator.executer()`` adapté au modèle LMD :
l'unité planifiée n'est plus « groupe × module » mais « programme de période ×
flux » (la promotion entière, ou chacun de ses groupes pédagogiques).

Deux modes, comme dans l'application source :

``strict``
    la première impossibilité interrompt la génération et annule la transaction ;
``best_effort``
    la génération se poursuit, le volume non placé est reporté dans les échecs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_cls, timedelta

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.faculty.models import Room
from apps.students.models import Student

from ..models import (
    JourFerie,
    ParametresPlanification,
    PlanningAuditLog,
    PlanningRun,
    ProgrammePeriode,
    Seance,
)
from .allocation import choisir_salle, enseignant_disponible
from .occupations import AudienceLock, OccupationIndex, to_minutes, to_time

PAS_GLISSEMENT_MINUTES = 30
DUREE_MINIMALE_MINUTES = 30


class PlanificationImpossible(Exception):
    """Levée en mode strict lorsqu'un volume ne peut pas être placé."""


@dataclass
class Flux:
    """Un flux d'étudiants à planifier pour un programme donné."""

    programme: ProgrammePeriode
    groupe: object | None
    effectif: int
    volume_restant: int

    @property
    def libelle(self) -> str:
        cible = self.groupe.code if self.groupe else self.programme.promotion.name
        return f'{self.programme.course.code} · {cible} · {self.programme.session_kind.upper()}'


@dataclass
class GenerationResult:
    seances: list = field(default_factory=list)
    echecs: list = field(default_factory=list)
    synthese: dict = field(default_factory=dict)
    run: PlanningRun | None = None


def _creneaux_autorises(params: ParametresPlanification, creneau_mode: str):
    plages = []
    for label, debut, fin in params.creneaux():
        if creneau_mode == 'matin' and label != 'matin':
            continue
        if creneau_mode == 'soir' and label != 'soir':
            continue
        plages.append((label, to_minutes(debut), to_minutes(fin)))
    return plages


def _dates_candidates(periode, debut: date_cls, fin: date_cls, jours_actifs, feries: set) -> list[date_cls]:
    jours = []
    courant = debut
    while courant <= fin:
        if (
            courant.weekday() in jours_actifs
            and courant not in feries
            and periode.semaine_autorisee(courant)
        ):
            jours.append(courant)
        courant += timedelta(days=1)
    return jours


def _effectifs_promotions(promotion_ids) -> dict[str, int]:
    rows = (
        Student.objects
        .filter(status='active', promotion_id__in=promotion_ids)
        .values('promotion_id')
        .annotate(total=Count('id'))
    )
    return {str(row['promotion_id']): row['total'] for row in rows}


def _construire_flux(programmes, effectifs_promo) -> list[Flux]:
    flux: list[Flux] = []
    for programme in programmes:
        volume = programme.volume_horaire_minutes or programme.volume_maquette_minutes()
        if volume <= 0:
            continue
        groupes = list(programme.groupes.filter(is_active=True))
        if groupes:
            for groupe in groupes:
                flux.append(Flux(
                    programme=programme,
                    groupe=groupe,
                    effectif=groupe.effectif or groupe.effectif_max,
                    volume_restant=volume,
                ))
        else:
            flux.append(Flux(
                programme=programme,
                groupe=None,
                effectif=effectifs_promo.get(str(programme.promotion_id), 0),
                volume_restant=volume,
            ))
    # Les gros volumes d'abord : ils sont les plus contraints.
    flux.sort(key=lambda item: (-item.volume_restant, item.libelle))
    return flux


def _placer_flux(
    flux: Flux,
    *,
    params: ParametresPlanification,
    periode,
    rooms,
    occupations: OccupationIndex,
    audiences: AudienceLock,
    feries: set,
) -> tuple[list[Seance], int]:
    """Place le volume d'un flux ; renvoie les séances et le reliquat non placé."""
    programme = flux.programme
    fenetre_debut, fenetre_fin = programme.fenetre
    jours = _dates_candidates(periode, fenetre_debut, fenetre_fin, set(params.jours_actifs or []), feries)
    plages = _creneaux_autorises(params, programme.creneau_mode)
    if not jours or not plages:
        return [], flux.volume_restant

    salle_imposee = programme.salle_preferee
    salle_precedente_id = None
    creees: list[Seance] = []
    numero = 1

    for jour in jours:
        if flux.volume_restant <= 0:
            break
        for _label, plage_debut, plage_fin in plages:
            if flux.volume_restant <= 0:
                break
            if audiences.compte_du_jour(programme.promotion_id, flux.groupe.id if flux.groupe else None, jour) \
                    >= params.max_seances_par_jour:
                break

            duree = min(params.duree_seance_minutes, flux.volume_restant, plage_fin - plage_debut)
            if duree < DUREE_MINIMALE_MINUTES:
                continue

            seance = _tenter_placement(
                flux,
                jour=jour,
                plage_debut=plage_debut,
                plage_fin=plage_fin,
                duree=duree,
                rooms=rooms,
                occupations=occupations,
                audiences=audiences,
                params=params,
                salle_imposee=salle_imposee,
                salle_precedente_id=salle_precedente_id,
                numero=numero,
            )
            if seance is None:
                continue

            creees.append(seance)
            flux.volume_restant -= duree
            numero += 1
            if params.verrouiller_salle_par_groupe and seance.room_id:
                salle_precedente_id = seance.room_id

    return creees, max(flux.volume_restant, 0)


def _tenter_placement(
    flux: Flux,
    *,
    jour: date_cls,
    plage_debut: int,
    plage_fin: int,
    duree: int,
    rooms,
    occupations: OccupationIndex,
    audiences: AudienceLock,
    params: ParametresPlanification,
    salle_imposee,
    salle_precedente_id,
    numero: int,
) -> Seance | None:
    """Cherche un début d'heure viable en glissant dans la plage."""
    programme = flux.programme
    groupe_id = flux.groupe.id if flux.groupe else None
    debut = plage_debut

    while debut + duree <= plage_fin:
        fin = debut + duree
        if not audiences.est_libre(programme.promotion_id, groupe_id, jour, debut, fin):
            debut += PAS_GLISSEMENT_MINUTES
            continue
        if not enseignant_disponible(programme.teacher_id, jour, debut, fin, occupations):
            debut += PAS_GLISSEMENT_MINUTES
            continue
        if not enseignant_disponible(programme.supervisor_id, jour, debut, fin, occupations):
            debut += PAS_GLISSEMENT_MINUTES
            continue

        room = choisir_salle(
            rooms,
            jour=jour,
            debut=debut,
            fin=fin,
            effectif=flux.effectif,
            session_kind=programme.session_kind,
            occupations=occupations,
            tolerance_pct=params.tolerance_capacite_pct,
            salle_imposee=salle_imposee,
            salle_precedente_id=salle_precedente_id,
            poids_ecart_capacite=params.poids_ecart_capacite,
            poids_rotation_salle=params.poids_rotation_salle,
            poids_equilibrage_salles=params.poids_equilibrage_salles,
        )
        if room is None:
            debut += PAS_GLISSEMENT_MINUTES
            continue

        seance = Seance(
            programme=programme,
            periode_id=programme.periode_id,
            course_id=programme.course_id,
            promotion_id=programme.promotion_id,
            groupe=flux.groupe,
            teacher_id=programme.teacher_id,
            supervisor_id=programme.supervisor_id,
            room=room,
            session_kind=programme.session_kind,
            numero=numero,
            intitule=f'{programme.course.name} — séance {numero}',
            date=jour,
            heure_debut=to_time(debut),
            heure_fin=to_time(fin),
            duree_minutes=duree,
            statut='planifiee',
            origine='auto',
        )

        occupations.add('room', room.id, jour, debut, fin)
        occupations.add('teacher', programme.teacher_id, jour, debut, fin)
        occupations.add('teacher', programme.supervisor_id, jour, debut, fin)
        audiences.reserver(programme.promotion_id, groupe_id, jour, debut, fin)
        return seance

    return None


@transaction.atomic
def generer_planning(
    periode,
    *,
    promotions=None,
    courses=None,
    mode: str = 'best_effort',
    remplacer: bool = True,
    dry_run: bool = False,
    actor=None,
) -> GenerationResult:
    """Génère l'emploi du temps d'une période de formation."""
    params = ParametresPlanification.resolve(periode)

    programmes_qs = (
        ProgrammePeriode.objects
        .filter(periode=periode, is_active=True)
        .select_related('course', 'course__teaching_unit', 'promotion', 'teacher', 'supervisor', 'salle_preferee')
        .prefetch_related('groupes')
    )
    if promotions:
        programmes_qs = programmes_qs.filter(promotion_id__in=promotions)
    if courses:
        programmes_qs = programmes_qs.filter(course_id__in=courses)
    programmes = list(programmes_qs)

    run = None
    if not dry_run:
        run = PlanningRun.objects.create(
            periode=periode,
            mode=mode,
            statut='running',
            scope={
                'promotions': [str(item) for item in (promotions or [])],
                'courses': [str(item) for item in (courses or [])],
                'remplacer': remplacer,
            },
            started_by=actor,
        )

    if not programmes:
        synthese = {
            'programmes': 0, 'flux': 0, 'seances': 0,
            'heures_placees': 0.0, 'heures_demandees': 0.0, 'taux_couverture': 0.0,
            'message': 'Aucun programme actif sur ce périmètre.',
        }
        if run:
            run.statut = 'done'
            run.synthese = synthese
            run.finished_at = timezone.now()
            run.save(update_fields=['statut', 'synthese', 'finished_at'])
        return GenerationResult(seances=[], echecs=[], synthese=synthese, run=run)

    if remplacer and not dry_run:
        Seance.objects.filter(
            programme__in=programmes, origine='auto', statut='planifiee', started_at__isnull=True,
        ).delete()

    feries = set(
        JourFerie.objects
        .filter(institution_id=periode.academic_year.institution_id, is_active=True)
        .values_list('date', flat=True)
    )
    rooms = list(Room.objects.filter(is_active=True, status='available').order_by('code'))

    # L'index d'occupation est global : il couvre toutes les périodes et toutes
    # les promotions, afin d'éviter les collisions de salles et d'enseignants.
    occupations = OccupationIndex.depuis_seances(
        Seance.objects.exclude(statut='annulee').only(
            'date', 'heure_debut', 'heure_fin', 'room_id', 'teacher_id',
            'supervisor_id', 'groupe_id', 'promotion_id',
        )
    )

    promotion_ids = {programme.promotion_id for programme in programmes}
    effectifs_promo = _effectifs_promotions(promotion_ids)
    groupes_par_promotion: dict[str, list[str]] = {}
    for programme in programmes:
        for groupe in programme.groupes.all():
            groupes_par_promotion.setdefault(str(programme.promotion_id), []).append(str(groupe.id))
    audiences = AudienceLock(occupations, groupes_par_promotion)

    flux_list = _construire_flux(programmes, effectifs_promo)
    toutes_seances: list[Seance] = []
    echecs: list[dict] = []
    minutes_demandees = sum(item.volume_restant for item in flux_list)

    for flux in flux_list:
        demande = flux.volume_restant
        seances, reliquat = _placer_flux(
            flux,
            params=params,
            periode=periode,
            rooms=rooms,
            occupations=occupations,
            audiences=audiences,
            feries=feries,
        )
        toutes_seances.extend(seances)
        if reliquat > 0:
            echec = {
                'flux': flux.libelle,
                'programme': str(flux.programme.id),
                'course_code': flux.programme.course.code,
                'promotion': flux.programme.promotion.name,
                'groupe': flux.groupe.code if flux.groupe else None,
                'heures_demandees': round(demande / 60, 2),
                'heures_placees': round((demande - reliquat) / 60, 2),
                'heures_non_placees': round(reliquat / 60, 2),
            }
            echecs.append(echec)
            if mode == 'strict':
                raise PlanificationImpossible(
                    f'{flux.libelle} : {echec["heures_non_placees"]} h non planifiables.',
                )

    minutes_placees = sum(seance.duree_minutes for seance in toutes_seances)
    synthese = {
        'programmes': len(programmes),
        'flux': len(flux_list),
        'seances': len(toutes_seances),
        'heures_demandees': round(minutes_demandees / 60, 2),
        'heures_placees': round(minutes_placees / 60, 2),
        'taux_couverture': round(minutes_placees / minutes_demandees * 100, 1) if minutes_demandees else 0.0,
        'echecs': len(echecs),
        'dry_run': dry_run,
    }

    if not dry_run:
        Seance.objects.bulk_create(toutes_seances, batch_size=500)
        if run:
            run.statut = 'done'
            run.synthese = synthese
            run.finished_at = timezone.now()
            run.save(update_fields=['statut', 'synthese', 'finished_at'])
        PlanningAuditLog.log(
            'generate', actor=actor, periode=periode,
            seances=len(toutes_seances), mode=mode, synthese=synthese,
        )

    return GenerationResult(seances=toutes_seances, echecs=echecs, synthese=synthese, run=run)
