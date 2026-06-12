import logging

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q

from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    UserSelfProfileSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
)
from .permissions import IsDFRC, IsSecretariatOrDFRC, ROLE_HIERARCHY, get_creatable_roles
from .role_groups import ALLOWED_WEB_ROLES, user_role_context
from .throttles import LoginRateThrottle
from .emails import send_welcome_email
from presences.models import DeviceBinding, AuditLog, _log_audit

User = get_user_model()

logger = logging.getLogger(__name__)


def _login_client_ip(request) -> str:
    xff = (request.META.get('HTTP_X_FORWARDED_FOR') or '').strip()
    if xff:
        return xff.split(',')[0].strip()
    return (request.META.get('REMOTE_ADDR') or '').strip()


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login_view(request):
    """Connexion — retourne access + refresh tokens.
    Si device_id est fourni (app mobile), vérifie le verrouillage appareil."""
    client_ip = _login_client_ip(request)
    user_agent = (request.META.get('HTTP_USER_AGENT') or '')[:200]

    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(
            'login_payload_invalid ip=%s ua=%r errors=%s',
            client_ip,
            user_agent,
            serializer.errors,
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    username_try = serializer.validated_data['username']
    user = authenticate(
        username=username_try,
        password=serializer.validated_data['password'],
    )
    if user is None:
        logger.warning(
            'login_failed_bad_credentials username=%r ip=%s ua=%r',
            username_try,
            client_ip,
            user_agent,
        )
        return Response(
            {'detail': 'Identifiants invalides.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    device_id = request.data.get('device_id', '').strip()

    if not device_id and user.role not in ALLOWED_WEB_ROLES:
        if user.role == User.Role.AUDITEUR:
            detail = 'Les comptes auditeur sont réservés à l\'application mobile.'
        elif user.role == User.Role.FORMATEUR:
            detail = 'Les comptes formateur sont réservés à l\'application mobile.'
        else:
            detail = 'Ce compte n\'a pas accès à la plateforme web.'
        logger.warning(
            'login_web_forbidden role=%s username=%r ip=%s',
            user.role,
            user.username,
            client_ip,
        )
        return Response({'detail': detail}, status=status.HTTP_403_FORBIDDEN)

    if user.role in ('AUDITEUR', 'FORMATEUR', 'ENCADRANT'):
        from .profile_sync import sync_user_profile_links
        sync_user_profile_links(user)

    # ── Verrouillage appareil (auditeurs / formateurs uniquement) ──
    if device_id and user.role in ('AUDITEUR', 'FORMATEUR'):
        existing = DeviceBinding.objects.filter(
            device_id=device_id, is_active=True
        ).select_related('user').first()

        if existing and existing.user_id != user.id:
            logger.warning(
                'login_device_locked device_id=%r attempted_user_id=%s bound_user_id=%s ip=%s',
                device_id,
                user.pk,
                existing.user_id,
                client_ip,
            )
            return Response({
                'code': 'DEVICE_LOCKED',
                'detail': (
                    f'Cet appareil est déjà lié au compte de '
                    f'{existing.user.get_full_name()}. '
                    f'Contactez votre encadrant pour le débloquer.'
                ),
            }, status=status.HTTP_403_FORBIDDEN)

        # Bind device to this user if not already bound
        if not existing:
            DeviceBinding.objects.update_or_create(
                device_id=device_id,
                defaults={
                    'user': user,
                    'device_info': request.data.get('device_info', ''),
                    'is_active': True,
                },
            )

    logger.info(
        'login_ok user_id=%s username=%r role=%s ip=%s device_id=%r',
        user.pk,
        user.username,
        user.role,
        client_ip,
        device_id[:16] + '…' if len(device_id) > 16 else device_id,
    )

    refresh = RefreshToken.for_user(user)
    refresh['role'] = user.role
    refresh['full_name'] = user.get_full_name()
    refresh['must_change_password'] = bool(getattr(user, 'must_change_password', False))
    _log_audit(
        action=AuditLog.Action.USER_LOGIN,
        request=request,
        cible_type='user',
        cible_numero=user.username,
        cible_nom=user.get_full_name() or user.username,
        extra={'role': user.role, 'device_id': bool(device_id)},
    )
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'must_change_password': bool(getattr(user, 'must_change_password', False)),
        'user': UserSerializer(user).data,
        'role_context': user_role_context(user),
    })


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """Profil de l'utilisateur connecté : lecture ou mise à jour partielle des données personnelles."""
    user = request.user
    if request.method == 'GET':
        data = UserSerializer(user).data
        data['role_context'] = user_role_context(user)
        return Response(data)
    serializer = UserSelfProfileSerializer(user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    _log_audit(
        action=AuditLog.Action.USER_UPDATE,
        request=request,
        cible_type='user',
        cible_numero=user.username,
        cible_nom=user.get_full_name() or user.username,
        extra={'self_profile': True, 'champs_modifies': list(request.data.keys())},
    )
    data = UserSerializer(user).data
    data['role_context'] = user_role_context(user)
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def roles_view(request):
    """Hiérarchie et périmètre de gestion des rôles pour l'utilisateur connecté."""
    return Response(user_role_context(request.user))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """Permet à l'utilisateur connecté de changer son propre mot de passe."""
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    was_forced_change = bool(getattr(request.user, 'must_change_password', False))
    request.user.set_password(serializer.validated_data['new_password'])
    if getattr(request.user, 'must_change_password', False):
        request.user.must_change_password = False
    request.user.save()
    _log_audit(
        action=AuditLog.Action.USER_PASSWORD_CHANGE,
        request=request,
        cible_type='user',
        cible_numero=request.user.username,
        cible_nom=request.user.get_full_name() or request.user.username,
        extra={'first_login_change': was_forced_change},
    )
    return Response({'detail': 'Mot de passe modifié avec succès.'})


class UserListCreateView(generics.ListCreateAPIView):
    """DFRC/Secrétariat : lister et créer des utilisateurs."""
    permission_classes = [IsSecretariatOrDFRC]

    def get_queryset(self):
        user = self.request.user
        subordinates = get_creatable_roles(user.role)
        qs = User.objects.filter(role__in=subordinates).order_by('last_name', 'first_name')
        if user.role in ('SECRETARIAT', 'CHEF_SECRETARIAT'):
            qs = qs.filter(secretariat=user.secretariat)
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search) |
                Q(matricule__icontains=search)
            )
        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)
        exclude_role = self.request.query_params.get('exclude_role')
        if exclude_role:
            for role_code in exclude_role.split(','):
                role_code = role_code.strip()
                if role_code in ROLE_HIERARCHY:
                    qs = qs.exclude(role=role_code)
        if user.role == 'DIRECTION':
            qs = qs.exclude(role__in=['AUDITEUR', 'FORMATEUR'])
        return qs

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        user = self.request.user
        plain_password = serializer.validated_data.get('password', '')
        if user.role in ('SECRETARIAT', 'CHEF_SECRETARIAT') and user.secretariat:
            new_user = serializer.save(secretariat=user.secretariat)
        else:
            new_user = serializer.save()
        send_welcome_email(new_user, plain_password)
        _log_audit(
            action=AuditLog.Action.USER_CREATE,
            request=self.request,
            cible_type='user',
            cible_numero=new_user.username,
            cible_nom=new_user.get_full_name() or new_user.username,
            extra={'role': new_user.role, 'secretariat': str(new_user.secretariat) if new_user.secretariat else None},
        )


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """DFRC/Secrétariat : détail / modifier / supprimer un utilisateur."""
    permission_classes = [IsSecretariatOrDFRC]

    def get_queryset(self):
        user = self.request.user
        subordinates = get_creatable_roles(user.role)
        qs = User.objects.filter(role__in=subordinates)
        if user.role in ('SECRETARIAT', 'CHEF_SECRETARIAT'):
            qs = qs.filter(secretariat=user.secretariat)
        if user.role == 'DIRECTION':
            qs = qs.exclude(role__in=['AUDITEUR', 'FORMATEUR'])
        return qs

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return UserUpdateSerializer
        return UserSerializer

    def perform_update(self, serializer):
        instance = serializer.save()
        _log_audit(
            action=AuditLog.Action.USER_UPDATE,
            request=self.request,
            cible_type='user',
            cible_numero=instance.username,
            cible_nom=instance.get_full_name() or instance.username,
            extra={'role': instance.role, 'secretariat': str(instance.secretariat) if instance.secretariat else None},
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.pk == request.user.pk:
            return Response(
                {'detail': 'Impossible de supprimer votre propre compte.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        _log_audit(
            action=AuditLog.Action.USER_DELETE,
            request=request,
            cible_type='user',
            cible_numero=instance.username,
            cible_nom=instance.get_full_name() or instance.username,
            extra={'role': instance.role, 'secretariat': str(instance.secretariat) if instance.secretariat else None},
        )
        return super().destroy(request, *args, **kwargs)
