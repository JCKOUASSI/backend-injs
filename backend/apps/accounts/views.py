import pyotp
from django.contrib.auth.models import Group
from rest_framework import viewsets, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.models import User, AuditLog
from apps.accounts.serializers import (
    UserSerializer, UserCreateSerializer, GroupSerializer,
    ModulePermissionSerializer, ChangePasswordSerializer, AuditLogSerializer,
)
from apps.accounts.permissions import HasModulePermission, IsAdminOrReadOnly
from apps.accounts.rbac import module_permissions_queryset
from apps.core.mixins import ExportMixin


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        if user.mfa_enabled:
            data['mfa_required'] = True
            data.pop('access', None)
            data.pop('refresh', None)
        else:
            data['user'] = UserSerializer(user, context=self.context).data
            data['permissions'] = sorted(user.get_permission_codes())
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_scope = 'login'


class MFAVerifyView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return Response({'error': 'Utilisateur invalide'}, status=400)
        if not user.mfa_enabled or not user.mfa_secret:
            return Response({'error': 'MFA non configuré'}, status=400)
        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(code, valid_window=1):
            return Response({'error': 'Code MFA invalide'}, status=400)
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user, context={'request': request}).data,
            'permissions': sorted(user.get_permission_codes()),
        })


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserViewSet(ExportMixin, viewsets.ModelViewSet):
    queryset = User.objects.prefetch_related('groups', 'groups__profile').select_related(
        'institution', 'department'
    ).all()
    permission_module = 'accounts'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['groups', 'institution', 'department', 'is_active']
    search_fields = ['email', 'first_name', 'last_name']
    export_headers = ['Email', 'Nom', 'Prénom', 'Groupes', 'Actif']
    export_title = 'Liste des utilisateurs INJS'
    export_filename = 'utilisateurs_injs'

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAdminOrReadOnly()]
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        user = self.get_object()
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({'error': 'Mot de passe actuel incorrect'}, status=400)
        user.set_password(serializer.validated_data['new_password'])
        user.must_change_password = False
        user.save()
        return Response({'message': 'Mot de passe modifié'})

    @action(detail=True, methods=['post'])
    def enable_mfa(self, request, pk=None):
        user = self.get_object()
        secret = pyotp.random_base32()
        user.mfa_secret = secret
        user.mfa_enabled = True
        user.save(update_fields=['mfa_secret', 'mfa_enabled'])
        totp = pyotp.TOTP(secret)
        return Response({
            'secret': secret,
            'provisioning_uri': totp.provisioning_uri(name=user.email, issuer_name='INJS-LMD'),
        })

    def get_export_rows(self):
        return [
            [
                u.email, u.last_name, u.first_name,
                ', '.join(g.name for g in u.groups.all()),
                'Oui' if u.is_active else 'Non',
            ]
            for u in self.filter_queryset(self.get_queryset())
        ]


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.select_related('profile').prefetch_related('permissions').all()
    serializer_class = GroupSerializer
    permission_module = 'accounts'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['profile__level', 'profile__is_active']


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = module_permissions_queryset()
    serializer_class = ModulePermissionSerializer
    permission_module = 'accounts'


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = AuditLogSerializer
    permission_module = 'accounts'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['module', 'action', 'user']
