"""
Session management views for the React frontend.
"""
from datetime import time, timedelta
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from authentication.permissions import IsDFRC, IsDFRCOrEncadrant, IsSecretariatOrEncadrantOrDFRC, IsSecretariatOrDFRC
from .models import Formation, Module, SessionModule, QRToken
from .serializers import SessionSerializer, ModuleSerializer


REACTIVATION_GRACE_HOURS = 4


def reactiver_session_et_qr(session):
    """
    Réouvre une séance terminée, prolonge la fin prévue pour éviter une
    re-clôture immédiate par _auto_manage_sessions / auto_close_sessions,
    et réactive le QR associé.
    """
    formation = session.module.formation
    now = timezone.now()
    local_now = timezone.localtime(now)
    today = local_now.date()

    SessionModule.objects.filter(
        module__formation=formation,
        demarree_le__isnull=False,
        terminee_le__isnull=True,
    ).exclude(pk=session.pk).update(terminee_le=now)

    update_fields = ['terminee_le']
    session.terminee_le = None

    if session.date_journee < today:
        session.date_journee = today
        update_fields.append('date_journee')

    fin_est_future = (
        session.heure_fin_prevue is not None
        and session.date_journee == today
        and session.heure_fin_prevue > local_now.time()
    )
    if not fin_est_future:
        grace_end = local_now + timedelta(hours=REACTIVATION_GRACE_HOURS)
        new_fin = grace_end.time()
        if new_fin > time(23, 59):
            new_fin = time(23, 59)
        session.heure_fin_prevue = new_fin
        update_fields.append('heure_fin_prevue')

    session.save(update_fields=update_fields)

    module = session.module
    if module.statut in ('TERMINEE', 'SUSPENDUE', 'PLANIFIEE'):
        module.statut = 'EN_COURS'
        module.save(update_fields=['statut'])

    qr = QRToken.objects.filter(session=session).order_by('-created_at').first()
    if qr:
        qr_updates = []
        if not qr.actif:
            qr.actif = True
            qr_updates.append('actif')
        if qr.is_expired:
            qr.expire_at = now + timedelta(hours=24)
            qr_updates.append('expire_at')
        if qr_updates:
            qr.save(update_fields=qr_updates)


def _has_unfinished_previous_session(session):
    """
    Retourne True si une séance précédente (même module, même date) n'est pas terminée.
    La précédence est définie par le numéro de séance.
    """
    return SessionModule.objects.filter(
        module=session.module,
        date_journee=session.date_journee,
        numero__lt=session.numero,
        terminee_le__isnull=True,
    ).exists()


def _auto_manage_sessions(formation):
    """
    Auto-start sessions with auto_demarrage=True when heure_debut_prevue is reached.
    Auto-close sessions when heure_fin_prevue is passed.
    Called lazily whenever the session list is loaded.
    """
    now = timezone.now()
    local_now = timezone.localtime(now)
    today = local_now.date()
    current_time = local_now.time()

    sessions = SessionModule.objects.filter(module__formation=formation)
    changed_formation = False

    modules_updated = set()

    for session in sessions:
        module = session.module
        # Auto-start
        if (
            session.auto_demarrage
            and session.demarree_le is None
            and session.heure_debut_prevue is not None
            and session.date_journee == today
            and session.heure_debut_prevue <= current_time
            and not _has_unfinished_previous_session(session)
        ):
            session.demarree_le = now
            session.save(update_fields=['demarree_le'])
            if module.statut == 'PLANIFIEE':
                module.statut = 'EN_COURS'
                module.save(update_fields=['statut'])
                modules_updated.add(module.pk)

        # Auto-close. ``terminee_le`` est borné à la fin prévue de la séance
        # (combinaison ``date_journee`` + ``heure_fin_prevue``) pour éviter qu'une
        # clôture tardive (chargement plusieurs heures après la fin) ne gonfle
        # la durée effective utilisée par les statistiques de volume horaire.
        if (
            session.demarree_le is not None
            and session.terminee_le is None
            and session.heure_fin_prevue is not None
            and (
                session.date_journee < today
                or (session.date_journee == today and session.heure_fin_prevue <= current_time)
            )
        ):
            from datetime import datetime as _dt
            from zoneinfo import ZoneInfo as _ZI
            _tz = _ZI('Africa/Abidjan')
            fin_prevue_local = _dt.combine(
                session.date_journee, session.heure_fin_prevue, tzinfo=_tz,
            )
            session.terminee_le = fin_prevue_local
            session.save(update_fields=['terminee_le'])
            QRToken.objects.filter(session=session, actif=True).update(actif=False)

    # If all sessions of a module are terminated → mark module TERMINEE
    for module in formation.modules.all():
        if (
            module.statut != 'TERMINEE'
            and module.sessions.exists()
            and not module.sessions.filter(terminee_le__isnull=True).exists()
        ):
            module.statut = 'TERMINEE'
            module.save(update_fields=['statut'])


@api_view(['POST'])
@permission_classes([IsSecretariatOrEncadrantOrDFRC])
def session_start(request, formation_pk, session_pk):
    """Start a session."""
    try:
        formation = Formation.objects.get(pk=formation_pk)
        session = SessionModule.objects.get(pk=session_pk, module__formation=formation)
    except (Formation.DoesNotExist, SessionModule.DoesNotExist):
        return Response({'detail': 'Formation ou séance introuvable.'}, status=404)
    
    # Check permission
    user = request.user
    module = session.module
    if user.role == 'ENCADRANT' and module.superviseur is not None and module.superviseur != user:
        return Response({'detail': 'Non autorisé.'}, status=403)
    
    if session.demarree_le and session.terminee_le is None:
        return Response({'detail': 'Cette séance est déjà démarrée.'}, status=400)

    if session.terminee_le is not None:
        reactiver_session_et_qr(session)
        session.refresh_from_db()
        return Response({
            'detail': 'Séance réactivée.',
            'session': SessionSerializer(session).data,
        })

    if _has_unfinished_previous_session(session):
        return Response(
            {'detail': 'Impossible de démarrer cette séance tant que la précédente du même jour n’est pas terminée.'},
            status=400,
        )
    
    session.demarree_le = timezone.now()
    session.demarree_par = user
    session.save()
    
    # Update module status if needed
    if module.statut == 'PLANIFIEE':
        module.statut = 'EN_COURS'
        module.save(update_fields=['statut'])
    
    return Response({
        'detail': 'Séance démarrée.',
        'session': SessionSerializer(session).data,
    })


@api_view(['POST'])
@permission_classes([IsSecretariatOrEncadrantOrDFRC])
def session_stop(request, formation_pk, session_pk):
    """Stop (terminate) a session."""
    try:
        formation = Formation.objects.get(pk=formation_pk)
        session = SessionModule.objects.get(pk=session_pk, module__formation=formation)
    except (Formation.DoesNotExist, SessionModule.DoesNotExist):
        return Response({'detail': 'Formation ou séance introuvable.'}, status=404)
    
    if not session.demarree_le:
        return Response({'detail': 'Cette séance n\'a pas été démarrée.'}, status=400)
    
    if session.terminee_le:
        return Response({'detail': 'Cette séance est déjà terminée.'}, status=400)
    
    session.terminee_le = timezone.now()
    session.save()
    QRToken.objects.filter(session=session, actif=True).update(actif=False)
    
    # Check if all sessions of the module are terminated
    module = session.module
    remaining = module.sessions.filter(terminee_le__isnull=True).exclude(pk=session.pk).count()

    if remaining == 0:
        module.statut = 'TERMINEE'
        module.save(update_fields=['statut'])
    
    return Response({
        'detail': 'Séance terminée.',
        'session': SessionSerializer(session).data,
    })


@api_view(['POST'])
@permission_classes([IsSecretariatOrDFRC])
def session_create(request, formation_pk, module_pk):
    """Create a new session for a module of a formation."""
    try:
        formation = Formation.objects.get(pk=formation_pk)
        module = Module.objects.get(pk=module_pk, formation=formation)
    except Formation.DoesNotExist:
        return Response({'detail': 'Formation introuvable.'}, status=404)
    except Module.DoesNotExist:
        return Response({'detail': 'Module introuvable pour cette formation.'}, status=404)

    date_journee = request.data.get('date_journee')
    heure_debut = request.data.get('heure_debut_prevue')
    heure_fin = request.data.get('heure_fin_prevue')
    intitule = request.data.get('intitule', '')

    if not date_journee:
        return Response({'detail': 'date_journee est requis.'}, status=400)

    # Auto-calcul du numéro si non fourni
    if 'numero' in request.data:
        numero = int(request.data['numero'])
    else:
        last = SessionModule.objects.filter(
            module=module, date_journee=date_journee
        ).order_by('-numero').first()
        numero = (last.numero + 1) if last else 1

    from django.db import IntegrityError
    try:
        session = SessionModule.objects.create(
            module=module,
            date_journee=date_journee,
            numero=numero,
            heure_debut_prevue=heure_debut,
            heure_fin_prevue=heure_fin,
            intitule=intitule,
        )
    except IntegrityError:
        return Response(
            {'detail': f'Une séance n°{numero} existe déjà pour ce module à cette date.'},
            status=400,
        )

    return Response({
        'detail': 'Séance créée.',
        'session': SessionSerializer(session).data,
    }, status=201)


@api_view(['DELETE'])
@permission_classes([IsDFRC])
def session_delete(request, formation_pk, session_pk):
    """Delete a session (only if not started)."""
    try:
        formation = Formation.objects.get(pk=formation_pk)
        session = SessionModule.objects.get(pk=session_pk, module__formation=formation)
    except (Formation.DoesNotExist, SessionModule.DoesNotExist):
        return Response({'detail': 'Formation ou séance introuvable.'}, status=404)
    
    if session.demarree_le:
        return Response({'detail': 'Impossible de supprimer une séance démarrée.'}, status=400)
    
    session.delete()
    
    return Response({'detail': 'Séance supprimée.'}, status=204)


@api_view(['PATCH'])
@permission_classes([IsSecretariatOrDFRC])
def session_update(request, formation_pk, session_pk):
    """Update a session (intitule, date, heures). Not allowed if already terminated."""
    try:
        formation = Formation.objects.get(pk=formation_pk)
        session = SessionModule.objects.get(pk=session_pk, module__formation=formation)
    except (Formation.DoesNotExist, SessionModule.DoesNotExist):
        return Response({'detail': 'Formation ou séance introuvable.'}, status=404)

    if session.terminee_le:
        return Response({'detail': 'Impossible de modifier une séance terminée.'}, status=400)

    if 'intitule' in request.data:
        session.intitule = request.data['intitule']
    if 'date_journee' in request.data:
        val = request.data['date_journee']
        if not val:
            return Response({'detail': 'La date de la séance est obligatoire.'}, status=400)
        session.date_journee = val
    if 'heure_debut_prevue' in request.data:
        session.heure_debut_prevue = request.data['heure_debut_prevue'] or None
    if 'heure_fin_prevue' in request.data:
        session.heure_fin_prevue = request.data['heure_fin_prevue'] or None

    try:
        session.full_clean()
        session.save()
    except Exception as e:
        return Response({'detail': str(e)}, status=400)
    return Response({
        'detail': 'Séance mise à jour.',
        'session': SessionSerializer(session).data,
    })


@api_view(['GET'])
@permission_classes([IsSecretariatOrEncadrantOrDFRC])
def session_list(request, formation_pk):
    """List all sessions for a formation, grouped by module."""
    from .access import formation_accessible
    formation = formation_accessible(request.user, formation_pk)
    if not formation:
        return Response({'detail': 'Formation introuvable ou non autorisée.'}, status=404)

    _auto_manage_sessions(formation)

    # If module_id filter provided, return only that module's sessions
    module_id = request.query_params.get('module_id')
    if module_id:
        sessions = SessionModule.objects.filter(module_id=module_id).select_related('module')
        return Response(SessionSerializer(sessions, many=True).data)

    # Otherwise return modules with their sessions (filtered by secretariat scope if applicable)
    user = request.user
    if user.role in ('SECRETARIAT', 'CHEF_SECRETARIAT') and user.secretariat:
        modules = formation.modules.filter(secretariat=user.secretariat).prefetch_related('sessions')
    elif user.role == 'ENCADRANT':
        modules = formation.modules.filter(superviseur=user).prefetch_related('sessions')
    else:
        modules = formation.modules.prefetch_related('sessions').all()

    return Response(ModuleSerializer(modules, many=True).data)
