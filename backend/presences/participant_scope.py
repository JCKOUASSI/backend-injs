"""Résolution du périmètre Participant pour un compte auditeur."""

from django.db.models import Count

from formations.models import Participant


def _compact_identifier(value):
    """Normalise un identifiant pour comparer les variantes de format (casse, espaces, ponctuation)."""
    return ''.join(ch for ch in (value or '').strip().upper() if ch.isalnum())


def _user_matricule_candidates(user):
    """Variantes compactes du matricule/username du compte."""
    candidates = set()
    for raw in (getattr(user, 'matricule', ''), getattr(user, 'username', '')):
        compact = _compact_identifier(raw)
        if compact:
            candidates.add(compact)
    return candidates


def participant_for_module(user, module):
    """Fiche Participant de l'utilisateur réellement inscrite au module donné.

    Contrairement à ``primary_participant_for_user`` (qui choisit une fiche
    « principale » indépendamment du module), cette résolution s'appuie sur les
    inscriptions du module et tolère les écarts de format de matricule. Elle
    évite les faux négatifs « pas inscrit à ce module » lorsque le compte est
    rattaché à une autre fiche (ou à une fiche vide) que celle inscrite.

    Priorité : lien de compte (``user_id``) puis correspondance de matricule.
    Retourne ``None`` si aucune fiche inscrite ne correspond au compte.
    """
    from formations.models import ModuleParticipant

    candidates = _user_matricule_candidates(user)
    inscriptions = (
        ModuleParticipant.objects
        .filter(module=module)
        .select_related('participant')
    )
    fallback = None
    for insc in inscriptions:
        p = insc.participant
        if p is None:
            continue
        if p.user_id == user.pk:
            return p
        if candidates and _compact_identifier(p.matricule) in candidates:
            fallback = fallback or p
    return fallback


def participant_ids_for_user(user):
    """IDs des fiches Participant dont les pointages concernent cet auditeur."""
    ids = set()
    for pk in Participant.objects.filter(user_id=user.pk).values_list('pk', flat=True):
        ids.add(pk)
    for matricule in {(user.matricule or '').strip(), (user.username or '').strip()}:
        if not matricule:
            continue
        for pk in Participant.objects.filter(matricule__iexact=matricule).values_list('pk', flat=True):
            ids.add(pk)
    return ids


def primary_participant_for_user(user):
    """Fiche Participant principale (liée au compte ou la plus badgeée)."""
    ids = participant_ids_for_user(user)
    if not ids:
        return None
    return (
        Participant.objects.filter(pk__in=ids)
        .annotate(nb_pt=Count('pointages'))
        .order_by('-user_id', '-nb_pt', 'pk')
        .first()
    )


def link_user_to_primary_participant(user):
    """Lie le compte à la fiche matricule existante si possible."""
    participant = primary_participant_for_user(user)
    if participant is None:
        return None
    updates = []
    if participant.user_id is None:
        participant.user = user
        updates.append('user')
    if updates:
        participant.save(update_fields=updates)
    matricule = (participant.matricule or '').strip()
    if matricule and (user.matricule or '').strip() != matricule:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        User.objects.filter(pk=user.pk).update(matricule=matricule)
        user.matricule = matricule
    return participant
