"""Lot C — service des séances LMD (créneaux d'EDT) pour la présence QR/émargement.

Modèle fonctionnel de référence, MODULE 08 : la chaîne
`EDT → SÉANCE → ÉMARGEMENT (QR auto | cases enseignant | administratif habilité)
→ JUSTIFICATION (forçage à motif) → CLÔTURE (auto)` s'exerce ici sur
``edts.AffectationCreneau`` (la séance planifiée) sans toucher au flux legacy
``formations.SessionModule`` (empilement, non-remplacement).

Conventions héritées du socle présences (préserver) :
- statut de badgeage ``Pointage.Statut`` (EN_COURS/TERMINE/FORCE_DFRC/SORTIE_AUTO/…)
- résultat pédagogique ``Pointage.StatutAssiduite`` (PRESENT/RETARD/ABSENT/…)
- ``AuditLog`` pour tout geste sensible (scan, forçage avec motif, clôture auto).
"""
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from formations.models import Participant, QRToken
from parametres.models import Parametre

from .models import AuditLog, Pointage

#: Index lundi=0..dimanche=6 aligné sur les codes `JOUR_CHOICES` de l'EDT.
_JOURS = {'LUNDI': 0, 'MARDI': 1, 'MERCREDI': 2, 'JEUDI': 3,
          'VENDREDI': 4, 'SAMEDI': 5, 'DIMANCHE': 6}

#: Tolérances (minutes), configurables par paramètre — modèle 08.3/08.5.
CLE_OUVERTURE_ANTICIPEE = 'presences.edt.ouverture_anticipee_minutes'
CLE_TOLERANCE_RETARD = 'presences.edt.tolerance_retard_minutes'
CLE_TOLERANCE_CLOTURE = 'presences.edt.tolerance_cloture_minutes'
DEFAUTS = {CLE_OUVERTURE_ANTICIPEE: 10, CLE_TOLERANCE_RETARD: 10, CLE_TOLERANCE_CLOTURE: 15}


def _parametre(cle):
    objet = Parametre.get_by_cle(cle, None)
    if objet is None:
        return DEFAUTS[cle]
    try:
        valeur = objet.get_valeur_typed()
        return int(valeur) if valeur is not None else DEFAUTS[cle]
    except (TypeError, ValueError, AttributeError):
        return DEFAUTS[cle]


# ---------------------------------------------------------------------------
# Résolution « séance du jour » : une AffectationCreneau couvre des semaines
# académiques ; l'occurrence du jour est déterminée par (jour de semaine,
# n° de semaine depuis le début de l'année académique).
# ---------------------------------------------------------------------------

def semaine_academique(affectation, date):
    """Numéro de semaine académique de `date` (1-based) pour l'EDT donné."""
    annee = getattr(affectation.emploi_du_temps, 'annee_academique', None)
    if annee is None or annee.date_debut is None:
        return None
    return (date - annee.date_debut).days // 7 + 1


def est_seance_du_jour(affectation, date):
    """True si `affectation` a séance ce jour-là (jour + plage de semaines)."""
    if not affectation.actif:
        return False
    numero = semaine_academique(affectation, date)
    if numero is None:
        return False
    if not (affectation.semaine_debut <= numero <= affectation.semaine_fin):
        return False
    code_jour = getattr(affectation.creneau_template, 'jour', None)
    return _JOURS.get(code_jour) == date.weekday()


def horodatages(affectation, date):
    """(début, fin) datés de l'occurrence de séance pour `date`."""
    ct = affectation.creneau_template
    debut = timezone.make_aware(datetime.combine(date, ct.heure_debut))
    fin = timezone.make_aware(datetime.combine(date, ct.heure_fin))
    if fin <= debut:  # créneau nocturne résiduel : borne haute + 1 jour
        fin += timedelta(days=1)
    return debut, fin


def fenetre_scan(affectation, date):
    """Fenêtre d'ouverture du QR : début − tolérance anticipée → fin + tolérance clôture."""
    debut, fin = horodatages(affectation, date)
    return (debut - timedelta(minutes=_parametre(CLE_OUVERTURE_ANTICIPEE)),
            fin + timedelta(minutes=_parametre(CLE_TOLERANCE_CLOTURE)))


def seances_du_jour(user, date=None, *, inclure_toutes=False):
    """Séances du jour lisibles par `user` (les siennes + toutes pour DFRC/secrétariat)."""
    from edts.models import AffectationCreneau

    if date is None:
        date = timezone.localdate()
    roles = {'ADMIN', 'CPFAE_ADMIN', 'CHEF_CPFAE_ADMIN', 'SECRETARIAT', 'CHEF_SECRETARIAT',
             'DIRECTION'}
    peut_voir_tout = inclure_toutes or (user.role or '').upper() in roles
    qs = (AffectationCreneau.objects
          .filter(actif=True, emploi_du_temps__statut__in=('VALIDE', 'PUBLIE'))
          .select_related('creneau_template', 'emploi_du_temps', 'emploi_du_temps__annee_academique',
                          'groupe', 'formation')
          .order_by('creneau_template__heure_debut'))
    resultat = []
    for affectation in qs:
        if not est_seance_du_jour(affectation, date):
            continue
        if not peut_voir_tout and affectation.enseignant_id != user.id:
            continue
        debut, fin = horodatages(affectation, date)
        resultat.append({
            'id': affectation.id,
            'date': date.isoformat(),
            'intitule': affectation.intitule or str(affectation.creneau_template),
            'nature': affectation.nature,
            'salle': affectation.salle_nom,
            'groupe': affectation.groupe_id,
            'groupe_libelle': (getattr(affectation.groupe, 'nom', '')
                               or getattr(affectation.groupe, 'libelle', ''))
            if affectation.groupe_id else '',
            'formation': affectation.formation_id,
            'formation_libelle': getattr(affectation.formation, 'intitule', '') if affectation.formation_id else '',
            'enseignant_nom': affectation.enseignant_nom,
            'debut': debut.isoformat(),
            'fin': fin.isoformat(),
            'peut_gerer': peut_gerer_seance(user, affectation),
        })
    return resultat


# ---------------------------------------------------------------------------
# Droits et effectifs
# ---------------------------------------------------------------------------

def peut_gerer_seance(user, affectation):
    """Enseignant affecté, encadrant, secrétariat ou DFRC — jamais le simple auditeur."""
    role = (getattr(user, 'role', '') or '').upper()
    if role in {'ADMIN', 'CPFAE_ADMIN', 'CHEF_CPFAE_ADMIN', 'SECRETARIAT',
                'CHEF_SECRETARIAT', 'DIRECTION'}:
        return True
    if role in {'ENCADRANT', 'FORMATEUR'} and affectation.enseignant_id == user.id:
        return True
    return False


def membres_groupe(affectation):
    """Participants LMD du groupe de la séance (affectations de groupe actives)."""
    if not affectation.groupe_id:
        return Participant.objects.none()
    from scolarite.models import AffectationGroupe

    ids = (AffectationGroupe.objects
           .filter(groupe_id=affectation.groupe_id, active=True,
                   inscription__etudiant__participant__isnull=False)
           .values_list('inscription__etudiant__participant_id', flat=True))
    return Participant.objects.filter(pk__in=set(ids)).order_by('nom', 'prenom')


def pointages_du_jour(affectation, date):
    return {p.participant_id: p for p in Pointage.objects.filter(
        seance_edt=affectation, date_journee=date, participant__isnull=False)}


# ---------------------------------------------------------------------------
# QR de séance
# ---------------------------------------------------------------------------

def jeton_actif(affectation, date):
    return (QRToken.objects
            .filter(seance_edt=affectation, actif=True, expire_at__gt=timezone.now())
            .order_by('-created_at').first())


@transaction.atomic
def generer_jeton(request, affectation, date):
    """Désactive les jetons du jour et émet un QR valable jusqu'à fin + tolérance."""
    QRToken.objects.filter(seance_edt=affectation, actif=True).update(actif=False)
    _, fin = horodatages(affectation, date)
    expire = fin + timedelta(minutes=_parametre(CLE_TOLERANCE_CLOTURE))
    jeton = QRToken.objects.create(
        seance_edt=affectation, actif=True, expire_at=expire,
        genere_par=request.user if request.user.is_authenticated else None,
    )
    AuditLog.objects.create(
        action=AuditLog.Action.FORMATION_QR_GENERATE,
        acteur=request.user, acteur_label=request.user.get_full_name() or request.user.username,
        cible_type='seance_edt', cible_numero=str(affectation.pk),
        cible_nom=affectation.intitule or str(affectation.creneau_template),
        extra={'date': date.isoformat(), 'token': str(jeton.token), 'canal': 'EDT_LMD'},
    )
    return jeton


# ---------------------------------------------------------------------------
# Badgeage automatique (scan du QR)
# ---------------------------------------------------------------------------

@transaction.atomic
def badger_scan(request, *, participant, affectation, date, device_id='', coords=None,
                type_personne='participant'):
    """Entrée/sortie au scan du QR — anti-fraude : 1 entrée + 1 sortie par séance.

    Retourne (action, pointage, None) ou (None, None, réponse-dict d'erreur).
    """
    now = timezone.now()
    debut, fin = horodatages(affectation, date)
    ouverture, cloture = fenetre_scan(affectation, date)
    if now < ouverture:
        return None, None, {'code': 'TROP_TOT',
                            'detail': 'Le QR de cette séance n’est pas encore actif.'}
    if now > cloture:
        return None, None, {'code': 'HORS_FENETRE',
                            'detail': 'La fenêtre de badgeage de cette séance est fermée.'}

    verrou = (Pointage.objects
              .filter(seance_edt=affectation, date_journee=date, participant=participant)
              .select_for_update())
    termine_existant = verrou.filter(timestamp_sortie__isnull=False).first()
    ouvert = verrou.filter(timestamp_sortie__isnull=True).order_by('-timestamp_entree').first()

    if ouvert is not None:
        ouvert.timestamp_sortie = min(now, cloture)
        ouvert.statut = Pointage.Statut.TERMINE
        ouvert.calculer_duree()
        if ouvert.statut_assiduite == Pointage.StatutAssiduite.NON_RENSEIGNE or not ouvert.statut_assiduite:
            seuil_retard = debut + timedelta(minutes=_parametre(CLE_TOLERANCE_RETARD))
            if ouvert.timestamp_entree <= seuil_retard:
                ouvert.statut_assiduite = Pointage.StatutAssiduite.PRESENT
        ouvert.save()
        _log_scan(AuditLog.Action.SCAN_SECURE_SORTIE, request, participant, affectation,
                  ouvert, device_id, {'duree_minutes': float(ouvert.duree_presence_minutes or 0)})
        return 'SORTIE', ouvert, None

    if termine_existant is not None:
        return None, None, {'code': 'ALREADY_SCANNED',
                            'detail': 'Vous avez déjà pointé (entrée + sortie) pour cette séance.'}

    seuil_retard = debut + timedelta(minutes=_parametre(CLE_TOLERANCE_RETARD))
    pointage = Pointage.objects.create(
        participant=participant,
        seance_edt=affectation,
        session=None,
        date_journee=date,
        timestamp_entree=now,
        statut=Pointage.Statut.EN_COURS,
        statut_assiduite=(Pointage.StatutAssiduite.RETARD if now > seuil_retard
                          else Pointage.StatutAssiduite.PRESENT),
        device_id=(device_id or '')[:255],
        annee_academique_id=affectation.emploi_du_temps.annee_academique_id,
        groupe_lmd_id=affectation.groupe_id,
        **(coords or {}),
    )
    _log_scan(AuditLog.Action.SCAN_SECURE_ENTREE, request, participant, affectation,
              pointage, device_id, {'retard': pointage.statut_assiduite == Pointage.StatutAssiduite.RETARD})
    return 'ENTREE', pointage, None


def _log_scan(action, request, participant, affectation, pointage, device_id, extra):
    AuditLog.objects.create(
        action=action,
        acteur=request.user if request and request.user.is_authenticated else None,
        acteur_label=(request.user.get_full_name() or request.user.username)
        if request and request.user.is_authenticated else 'Mobile',
        cible_type='participant',
        cible_numero=getattr(participant, 'matricule', '') or getattr(participant, 'numero', '') or '',
        cible_nom=f'{getattr(participant, "nom", "")} {getattr(participant, "prenom", "")}'.strip(),
        pointage=pointage,
        device_id=device_id or '',
        extra={'canal': 'EDT_LMD', 'seance_edt': affectation.pk, **(extra or {})},
    )


# ---------------------------------------------------------------------------
# Émargement manuel de masse (cases enseignant / administratif habilité)
# ---------------------------------------------------------------------------

#: Statuts pédagogiques autorisés à l'émargement manuel (modèle 08.4).
STATUTS_EMARGEMENT = {
    'PRESENT': Pointage.StatutAssiduite.PRESENT,
    'RETARD': Pointage.StatutAssiduite.RETARD,
    'ABSENT': Pointage.StatutAssiduite.ABSENT,
    'ABSENCE_JUSTIFIEE': Pointage.StatutAssiduite.ABSENCE_JUSTIFIEE,
    'EXCUSE': Pointage.StatutAssiduite.EXCUSE,
}


class ErreurEmargement(Exception):
    def __init__(self, detail, status_code=400, code='EMARGEMENT_REFUSE'):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.code = code


@transaction.atomic
def emarger(request, affectation, date, entries, *, motif_global=''):
    """Émargement manuel de masse. Règle « forçage contrôlé » (08.14) : toute
    correction d'un pointage existant exige un motif, tracé avant/après."""
    membres_ids = set(membres_groupe(affectation).values_list('id', flat=True))
    existants = pointages_du_jour(affectation, date)
    debut, fin = horodatages(affectation, date)
    journal = []
    lignes_traitees = set()

    for index, entree in enumerate(entries):
        statut_cible = (entree.get('statut') or '').upper()
        if statut_cible not in STATUTS_EMARGEMENT:
            raise ErreurEmargement(
                f"Ligne {index + 1} : statut « {entree.get('statut')} » inconnu "
                f"(attendu : {', '.join(sorted(STATUTS_EMARGEMENT))}).")
        pid = entree.get('participant')
        try:
            pid = int(pid)
        except (TypeError, ValueError):
            raise ErreurEmargement(f'Ligne {index + 1} : identifiant participant invalide.')
        if pid in lignes_traitees:
            raise ErreurEmargement(f'Ligne {index + 1} : participant {pid} dupliqué.')
        lignes_traitees.add(pid)
        if membres_ids and pid not in membres_ids:
            raise ErreurEmargement(
                f'Ligne {index + 1} : ce participant n’est pas inscrit dans le groupe de la séance '
                '(règle 1 — présence réservée aux inscrits).', status_code=403, code='NOT_IN_GROUP')
        participant = Participant.objects.filter(pk=pid).first()
        if participant is None:
            raise ErreurEmargement(f'Ligne {index + 1} : participant {pid} introuvable.')

        motif = (entree.get('motif') or motif_global or '').strip()
        assiduite = STATUTS_EMARGEMENT[statut_cible]
        pointage = existants.get(pid)
        avant = None

        if pointage is None:
            if statut_cible == 'PRESENT':
                pointage = Pointage.objects.create(
                    participant=participant, seance_edt=affectation, date_journee=date,
                    timestamp_entree=debut, statut=Pointage.Statut.TERMINE,
                    statut_assiduite=assiduite, device_id='EMARGEMENT_MANUEL',
                    annee_academique_id=affectation.emploi_du_temps.annee_academique_id,
                    groupe_lmd_id=affectation.groupe_id,
                )
                pointage.timestamp_sortie = fin
                pointage.calculer_duree()
                pointage.save()
            elif statut_cible == 'RETARD':
                seuil = debut + timedelta(minutes=_parametre(CLE_TOLERANCE_RETARD))
                pointage = Pointage.objects.create(
                    participant=participant, seance_edt=affectation, date_journee=date,
                    timestamp_entree=seuil + timedelta(minutes=1), statut=Pointage.Statut.TERMINE,
                    statut_assiduite=assiduite, device_id='EMARGEMENT_MANUEL',
                    annee_academique_id=affectation.emploi_du_temps.annee_academique_id,
                    groupe_lmd_id=affectation.groupe_id,
                )
                pointage.timestamp_sortie = fin
                pointage.calculer_duree()
                pointage.save()
            else:
                # Absence : ligne administrative de durée nulle (aucun badge),
                # pour que l'état nominal soit opposable et traçable.
                pointage = Pointage.objects.create(
                    participant=participant, seance_edt=affectation, date_journee=date,
                    timestamp_entree=debut, timestamp_sortie=debut,
                    statut=Pointage.Statut.FORCE_DFRC, statut_assiduite=assiduite,
                    device_id='EMARGEMENT_MANUEL',
                    annee_academique_id=affectation.emploi_du_temps.annee_academique_id,
                    groupe_lmd_id=affectation.groupe_id,
                )
                pointage.calculer_duree()
                pointage.save()
            action = AuditLog.Action.FORCE_ENTREE
        else:
            # Correction d'un pointage existant → motif OBLIGATOIRE (08.14).
            if not motif:
                raise ErreurEmargement(
                    f'Ligne {index + 1} : motif obligatoire pour corriger un pointage '
                    f'({participant.nom} {participant.prenom} a déjà un badgeage).')
            avant = {
                'statut': pointage.statut,
                'statut_assiduite': pointage.statut_assiduite,
                'entree': pointage.timestamp_entree.isoformat(),
                'sortie': pointage.timestamp_sortie.isoformat() if pointage.timestamp_sortie else None,
            }
            pointage.statut = Pointage.Statut.FORCE_DFRC
            pointage.statut_assiduite = assiduite
            if statut_cible in ('ABSENT', 'ABSENCE_JUSTIFIEE', 'EXCUSE'):
                pointage.timestamp_entree = debut
                pointage.timestamp_sortie = debut
            pointage.save()
            if pointage.timestamp_sortie is None:
                pointage.calculer_duree()
                pointage.save(update_fields=['duree_presence_minutes'])
            action = (AuditLog.Action.FORCE_SORTIE
                      if avant['sortie'] else AuditLog.Action.FORCE_ENTREE)

        nouvelle = {
            'statut': pointage.statut,
            'statut_assiduite': pointage.statut_assiduite,
        }
        AuditLog.objects.create(
            action=action,
            acteur=request.user,
            acteur_label=request.user.get_full_name() or request.user.username,
            cible_type='participant',
            cible_numero=getattr(participant, 'matricule', '') or '',
            cible_nom=f'{participant.nom} {participant.prenom}'.strip(),
            pointage=pointage,
            extra={'canal': 'EDT_LMD', 'seance_edt': affectation.pk, 'date': date.isoformat(),
                   'motif': motif, 'avant': avant, 'apres': nouvelle,
                   'source': 'EMARGEMENT_MANUEL'},
        )
        journal.append({
            'participant': pid,
            'statut': assiduite,
            'pointage_id': pointage.pk,
            'corrige': avant is not None,
        })
    return journal


# ---------------------------------------------------------------------------
# Clôture automatique de séance
# ---------------------------------------------------------------------------

@transaction.atomic
def auto_clore(request, affectation, date):
    """Clôture de séance : ouvertures sans sortie → sortie = fin (+ tolérance) ;
    inscrits sans aucun badge → ligne « absent non badgé »."""
    fin = horodatages(affectation, date)[1]
    cloture = fin + timedelta(minutes=_parametre(CLE_TOLERANCE_CLOTURE))
    ouverts = Pointage.objects.filter(
        seance_edt=affectation, date_journee=date, timestamp_sortie__isnull=True)
    nb_clotures = 0
    for pointage in ouverts:
        pointage.timestamp_sortie = min(timezone.now(), cloture)
        pointage.statut = Pointage.Statut.SORTIE_AUTO
        pointage.calculer_duree()
        pointage.save()
        AuditLog.objects.create(
            action=AuditLog.Action.AUTO_EXIT,
            acteur=request.user if request and request.user.is_authenticated else None,
            acteur_label=(request.user.get_full_name() or request.user.username)
            if request and getattr(request, 'user', None) and request.user.is_authenticated else 'Système',
            cible_type='participant',
            cible_numero=getattr(pointage.participant, 'matricule', '') or '' if pointage.participant else '',
            cible_nom=(f'{pointage.participant.nom} {pointage.participant.prenom}'.strip()
                       if pointage.participant else ''),
            pointage=pointage,
            extra={'canal': 'EDT_LMD', 'seance_edt': affectation.pk, 'date': date.isoformat(),
                   'source': 'AUTOCLOTURE'},
        )
        nb_clotures += 1

    badge = set(Pointage.objects.filter(seance_edt=affectation, date_journee=date)
                .values_list('participant_id', flat=True))
    nb_absents = 0
    for membre in membres_groupe(affectation).exclude(pk__in=badge):
        Pointage.objects.create(
            participant=membre, seance_edt=affectation, date_journee=date,
            timestamp_entree=horodatages(affectation, date)[0],
            timestamp_sortie=horodatages(affectation, date)[0],
            statut=Pointage.Statut.ABSENT_NON_BADGE,
            statut_assiduite=Pointage.StatutAssiduite.ABSENT,
            device_id='AUTOCLOTURE',
            annee_academique_id=affectation.emploi_du_temps.annee_academique_id,
            groupe_lmd_id=affectation.groupe_id,
        )
        nb_absents += 1
    QRToken.objects.filter(seance_edt=affectation, actif=True).update(actif=False)
    AuditLog.objects.create(
        action=AuditLog.Action.CLOSE_SESSION,
        acteur=request.user if request and request.user.is_authenticated else None,
        acteur_label=(request.user.get_full_name() or request.user.username)
        if request and request.user.is_authenticated else 'Système',
        cible_type='seance_edt', cible_numero=str(affectation.pk),
        cible_nom=affectation.intitule or str(affectation.creneau_template),
        extra={'canal': 'EDT_LMD', 'date': date.isoformat(),
               'pointages_clotures': nb_clotures, 'absents_marques': nb_absents},
    )
    return {'pointages_clotures': nb_clotures, 'absents_marques': nb_absents}
