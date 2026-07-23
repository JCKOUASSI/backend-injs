import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group
from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel
from apps.accounts.rbac import ACTIONS, GROUP_LEVELS, MODULES, make_perm, parse_codename


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email obligatoire')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)


class ModulePermissionRegistry(models.Model):
    """Ancre ContentType pour les permissions métier module.action."""

    class Meta:
        verbose_name = 'Registre permissions INJS'
        verbose_name_plural = 'Registre permissions INJS'
        default_permissions = ()


class GroupProfile(models.Model):
    """Métadonnées INJS pour un groupe Django (rôle institutionnel)."""

    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='profile')
    code = models.CharField(max_length=50, unique=True, db_index=True)
    level = models.PositiveSmallIntegerField(choices=GROUP_LEVELS, db_index=True, default=4)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    parent = models.ForeignKey(
        Group, null=True, blank=True, on_delete=models.SET_NULL, related_name='child_profiles'
    )

    class Meta:
        ordering = ['level', 'group__name']

    def __str__(self):
        return f'{self.group.name} (N{self.level})'


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='users/photos/', null=True, blank=True)
    institution = models.ForeignKey(
        'academics.Institution', on_delete=models.SET_NULL, null=True, blank=True, related_name='users'
    )
    department = models.ForeignKey(
        'academics.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='users'
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=32, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    must_change_password = models.BooleanField(default=False)
    locale = models.CharField(max_length=10, default='fr')

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f'{self.get_full_name()} <{self.email}>'

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def get_short_name(self):
        return self.first_name

    def get_group_level(self) -> int:
        levels = [
            g.profile.level
            for g in self.groups.select_related('profile').all()
            if hasattr(g, 'profile') and g.profile.is_active
        ]
        return min(levels) if levels else 4

    def get_permission_codes(self) -> set[str]:
        if self.is_superuser:
            return {f'{module}.{action}' for module in MODULES for action in ACTIONS}
        codes = set()
        for perm in self.get_all_permissions():
            if not perm.startswith('accounts.'):
                continue
            module, action = parse_codename(perm.split('.', 1)[1])
            if module and action:
                codes.add(f'{module}.{action}')
        return codes

    def has_module_permission(self, module: str, action: str, context: dict | None = None) -> bool:
        if self.is_superuser:
            return True
        if self.has_perm(make_perm(module, action)):
            return True
        if context:
            return self._check_contextual_permission(module, action, context)
        return False

    def _check_contextual_permission(self, module, action, context):
        """Contextuel : enseignant → ses cours ; étudiant → ses données."""
        level = self.get_group_level()
        if level == 3 and module == 'exams' and action in ('create', 'update'):
            teacher_id = context.get('teacher_id')
            if teacher_id and hasattr(self, 'teacher_profile'):
                return str(self.teacher_profile.id) == str(teacher_id)
        if level == 4 and module in ('students', 'exams', 'finance'):
            student_id = context.get('student_id')
            if student_id and hasattr(self, 'student_profile'):
                return str(self.student_profile.id) == str(student_id)
        return False


class AuditLog(models.Model):
    """Immutable audit trail."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=50, db_index=True)
    module = models.CharField(max_length=50, db_index=True)
    object_type = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['module', 'action', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
        ]

    def __str__(self):
        return f'{self.action} {self.object_type} by {self.user}'
