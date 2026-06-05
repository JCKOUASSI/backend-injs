"""Résolution du périmètre Participant pour un compte auditeur."""

from django.db.models import Count

from formations.models import Participant


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
