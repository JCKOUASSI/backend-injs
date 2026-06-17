"""
Services de calcul — évaluation académique :
- Moyennes pondérées par coefficients
- Taux de présence (à partir des pointages)
- Décisions pédagogiques automatiques
- Génération des fiches auditeur / formateur
"""
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from formations.models import Module, Participant, Formateur, Formation
from presences.models import Pointage



def _get_parametres(formation):
    """Retourne les paramètres d'évaluation de la formation ou les valeurs par défaut."""
    params = ParametresEvaluation.objects.filter(formation=formation, actif=True).first()
    if params:
        return {
            'seuil_admission': float(params.seuil_admission),
            'taux_presence_min': float(params.taux_presence_min),
            'seuil_mention_bien': float(params.seuil_mention_bien),
            'seuil_mention_tres_bien': float(params.seuil_mention_tres_bien),
        }
    return {
        'seuil_admission': 12.0,
        'taux_presence_min': 80.0,
        'seuil_mention_bien': 14.0,
        'seuil_mention_tres_bien': 16.0,
    }


# ─────────────────────────────────────────────────────────────
# MOYENNES
# ─────────────────────────────────────────────────────────────

def calculer_moyenne_module(module, participant):
    """
    Calcule la moyenne pondérée d'un participant sur un module
    à partir des notes d'épreuves (hors absents/exclus sans note).
    Retourne l'objet MoyenneModule mis à jour.
    """
    notes = NoteEpreuve.objects.filter(
        epreuve__module=module,
        participant=participant,
        note__isnull=False,
    ).select_related('epreuve')

    somme_notes_coeff = Decimal('0')
    total_coefficients = Decimal('0')
    nb_epreuves = 0

    for ne in notes:
        coeff = ne.epreuve.coefficient or Decimal('0')
        somme_notes_coeff += ne.note * coeff
        total_coefficients += coeff
        nb_epreuves += 1

    moyenne = None
    if total_coefficients > 0:
        moyenne = round(somme_notes_coeff / total_coefficients, 2)

    obj, _ = MoyenneModule.objects.update_or_create(
        module=module,
        participant=participant,
        defaults={
            'moyenne': moyenne,
            'total_coefficients': total_coefficients,
            'somme_notes_coeff': somme_notes_coeff,
            'nb_epreuves': nb_epreuves,
        },
    )
    return obj


def calculer_moyennes_module_tous(module):
    """Recalcule les moyennes de tous les participants ayant une note sur le module."""
    participant_ids = NoteEpreuve.objects.filter(
        epreuve__module=module
    ).values_list('participant_id', flat=True).distinct()
    resultats = []
    for pid in participant_ids:
        participant = Participant.objects.get(pk=pid)
        resultats.append(calculer_moyenne_module(module, participant))
    return resultats


def calculer_moyenne_generale(participant, formation):
    """
    Moyenne générale d'un participant sur une formation =
    moyenne des moyennes de modules (pondérée par durée prévue si disponible).
    """
    modules = Module.objects.filter(formation=formation)
    somme = Decimal('0')
    total_poids = Decimal('0')

    for module in modules:
        mm = MoyenneModule.objects.filter(module=module, participant=participant).first()
        if not mm or mm.moyenne is None:
            continue
        poids = module.duree_prevue_heures or Decimal('1')
        if poids <= 0:
            poids = Decimal('1')
        somme += mm.moyenne * poids
        total_poids += poids

    if total_poids > 0:
        return round(somme / total_poids, 2)
    return None


# ─────────────────────────────────────────────────────────────
# TAUX DE PRÉSENCE
# ─────────────────────────────────────────────────────────────

def _minutes_prevues_module(module):
    """Estime les minutes prévues d'un module (priorité au volume horaire défini)."""
    if module.duree_prevue_heures and module.duree_prevue_heures > 0:
        return float(module.duree_prevue_heures) * 60.0
    total = Decimal('0')
    for s in module.sessions.all():
        if s.heure_debut_prevue and s.heure_fin_prevue:
            debut = s.heure_debut_prevue.hour * 60 + s.heure_debut_prevue.minute
            fin = s.heure_fin_prevue.hour * 60 + s.heure_fin_prevue.minute
            if fin > debut:
                total += Decimal(fin - debut)
    return float(total)


def calculer_presence_module(module, participant):
    """
    Retourne (heures_presence, heures_prevues, taux_presence) pour un
    participant sur un module à partir des pointages terminés.
    """
    agg = Pointage.objects.filter(
        session__module=module,
        participant=participant,
        duree_presence_minutes__isnull=False,
    ).aggregate(total=Sum('duree_presence_minutes'))
    minutes_presence = float(agg['total'] or 0)
    minutes_prevues = _minutes_prevues_module(module)

    heures_presence = round(minutes_presence / 60.0, 2)
    heures_prevues = round(minutes_prevues / 60.0, 2)
    taux = None
    if minutes_prevues > 0:
        taux = round((minutes_presence / minutes_prevues) * 100, 2)
    return heures_presence, heures_prevues, taux


def calculer_presence_formation(participant, formation):
    """Taux de présence global d'un participant sur une formation."""
    modules = Module.objects.filter(formation=formation)
    total_presence = 0.0
    total_prevu = 0.0
    for module in modules:
        hp, hprev, _ = calculer_presence_module(module, participant)
        total_presence += hp
        total_prevu += hprev
    taux = None
    if total_prevu > 0:
        taux = round((total_presence / total_prevu) * 100, 2)
    return round(total_presence, 2), round(total_prevu, 2), taux


# ─────────────────────────────────────────────────────────────
# DÉCISIONS PÉDAGOGIQUES
# ─────────────────────────────────────────────────────────────

def calculer_decision(participant, formation, generer_auto=True):
    """
    Calcule et enregistre la décision pédagogique d'un participant
    sur une formation selon les paramètres (seuils).
    """
    params = _get_parametres(formation)
    moyenne = calculer_moyenne_generale(participant, formation)
    heures_presence, heures_prevues, taux_presence = calculer_presence_formation(
        participant, formation
    )

    decision_obj, _ = DecisionPedagogique.objects.get_or_create(
        participant=participant,
        formation=formation,
        defaults={'generee_auto': generer_auto},
    )

    # Ne pas écraser une décision validée manuellement
    if decision_obj.validee_le and not generer_auto:
        return decision_obj

    decision_obj.moyenne_generale = moyenne
    decision_obj.taux_presence = taux_presence
    decision_obj.total_heures_presence = heures_presence
    decision_obj.total_heures_prevues = heures_prevues
    decision_obj.generee_auto = generer_auto
    decision_obj.criteres_appliques = params

    # Logique de décision avec seuils paramétrés
    if moyenne is None or taux_presence is None:
        decision_obj.decision = DecisionPedagogique.TypeDecision.EN_ATTENTE
    else:
        if moyenne >= params['seuil_admission'] and taux_presence >= params['taux_presence_min']:
            decision_obj.decision = DecisionPedagogique.TypeDecision.ADMIS
            if moyenne >= params['seuil_mention_tres_bien']:
                decision_obj.mention = DecisionPedagogique.Mention.TRES_BIEN
            elif moyenne >= params['seuil_mention_bien']:
                decision_obj.mention = DecisionPedagogique.Mention.BIEN
            elif moyenne >= params['seuil_admission']:
                decision_obj.mention = DecisionPedagogique.Mention.ASSEZ_BIEN
            else:
                decision_obj.mention = DecisionPedagogique.Mention.PASSABLE
        elif moyenne < 8 or taux_presence < 50:
            decision_obj.decision = DecisionPedagogique.TypeDecision.EXCLUSION
            decision_obj.mention = ''
        else:
            decision_obj.decision = DecisionPedagogique.TypeDecision.AJOURNE
            decision_obj.mention = ''

    decision_obj.save()
    return decision_obj


def calculer_decisions_formation(formation):
    """Recalcule les décisions de tous les participants attendus dans une formation."""
    from formations.models import ModuleParticipant
    participant_ids = ModuleParticipant.objects.filter(
        module__formation=formation
    ).values_list('participant_id', flat=True).distinct()
    resultats = []
    for pid in participant_ids:
        participant = Participant.objects.get(pk=pid)
        resultats.append(calculer_decision(participant, formation))
    return resultats


# ─────────────────────────────────────────────────────────────
# FICHES AUDITEUR
# ─────────────────────────────────────────────────────────────

def generer_fiche_auditeur(participant, formation):
    """Génère/met à jour la fiche académique complète d'un auditeur."""
    moyenne_generale = calculer_moyenne_generale(participant, formation)
    decision = calculer_decision(participant, formation)

    fiche, _ = FicheAuditeurAcademique.objects.update_or_create(
        participant=participant,
        formation=formation,
        defaults={
            'moyenne_generale': moyenne_generale,
            'decision_finale': decision,
        },
    )

    # Suivi par module
    modules = Module.objects.filter(formation=formation)
    for module in modules:
        hp, hprev, taux = calculer_presence_module(module, participant)
        mm = MoyenneModule.objects.filter(module=module, participant=participant).first()
        nb_epreuves = mm.nb_epreuves if mm else 0
        moyenne_module = mm.moyenne if mm else None
        SuiviModuleAuditeur.objects.update_or_create(
            fiche=fiche,
            module=module,
            defaults={
                'heures_presence': hp,
                'heures_prevues': hprev,
                'taux_presence': taux,
                'moyenne_module': moyenne_module,
                'nb_epreuves': nb_epreuves,
            },
        )
    return fiche


def calculer_classements(formation):
    """Calcule le classement des auditeurs d'une formation selon leur moyenne générale."""
    fiches = FicheAuditeurAcademique.objects.filter(
        formation=formation, moyenne_generale__isnull=False
    ).order_by('-moyenne_generale')
    rang = 0
    for fiche in fiches:
        rang += 1
        fiche.classement = rang
        fiche.save(update_fields=['classement'])
    return fiches


# ─────────────────────────────────────────────────────────────
# FICHES FORMATEUR
# ─────────────────────────────────────────────────────────────

def _minutes_presence_formateur(formateur, module=None):
    qs = Pointage.objects.filter(formateur=formateur, duree_presence_minutes__isnull=False)
    if module:
        qs = qs.filter(session__module=module)
    agg = qs.aggregate(total=Sum('duree_presence_minutes'))
    return float(agg['total'] or 0)


def generer_fiche_formateur(formateur, module):
    """Génère/met à jour la fiche d'un formateur pour un module."""
    minutes_presence = _minutes_presence_formateur(formateur, module)
    minutes_prevues = _minutes_prevues_module(module)
    heures_effectuees = round(minutes_presence / 60.0, 2)
    heures_prevues = round(minutes_prevues / 60.0, 2)
    taux = round((minutes_presence / minutes_prevues) * 100, 2) if minutes_prevues > 0 else None

    nb_seances = module.sessions.count()
    nb_seances_realisees = module.sessions.filter(terminee_le__isnull=False).count()

    # Satisfaction auditeurs (questionnaires FORMATEUR sur le module)
    satisfaction, nb_eval = _satisfaction_formateur(module)

    fiche, _ = FicheFormateur.objects.update_or_create(
        formateur=formateur,
        module=module,
        defaults={
            'formation': module.formation,
            'heures_prevues': heures_prevues,
            'heures_effectuees': heures_effectuees,
            'taux_presence': taux,
            'nb_seances': nb_seances,
            'nb_seances_realisees': nb_seances_realisees,
            'satisfaction_auditeurs': satisfaction,
            'nb_evaluations': nb_eval,
        },
    )
    return fiche


def _satisfaction_formateur(module):
    """Note moyenne de satisfaction (questions NOTE) des questionnaires FORMATEUR du module."""
    from django.db.models import Avg, Count
    from .models import Questionnaire, ReponseQuestion

    questionnaires = Questionnaire.objects.filter(
        module=module, cible=Questionnaire.Cible.FORMATEUR
    )
    agg = ReponseQuestion.objects.filter(
        question__questionnaire__in=questionnaires,
        question__type_question='NOTE',
        note__isnull=False,
    ).aggregate(moyenne=Avg('note'), total=Count('id'))
    moyenne = round(agg['moyenne'], 2) if agg['moyenne'] else None
    return moyenne, agg['total'] or 0
