from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from admin_mixins import AuditLogAdminMixin, UserAdminScopeMixin
from presences.models import AuditLog

from .models import User
from .role_groups import GROUP_NAME_TO_ROLE, ROLE_LABELS

try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


@admin.register(Group)
class RoleGroupAdmin(BaseGroupAdmin, ModelAdmin):
    """Groupes Django ROLE_* — permissions et rôles de l'application."""

    list_display = ['name', 'role_label', 'permissions_count']
    search_fields = ['name']
    filter_horizontal = ['permissions']

    @admin.display(description='Rôle métier')
    def role_label(self, obj):
        role = GROUP_NAME_TO_ROLE.get(obj.name)
        if role:
            return ROLE_LABELS.get(role, role)
        return '—'

    @admin.display(description='Permissions')
    def permissions_count(self, obj):
        return obj.permissions.count()


@admin.register(User)
class UserAdmin(UserAdminScopeMixin, AuditLogAdminMixin, BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    audit_action_create = AuditLog.Action.USER_CREATE
    audit_action_update = AuditLog.Action.USER_UPDATE
    audit_action_delete = AuditLog.Action.USER_DELETE

    list_display = [
        'username', 'matricule', 'last_name', 'first_name',
        'email', 'role_badge', 'grade', 'secretariat',
        'is_active', 'must_change_password',
    ]
    list_filter = [
        'role', 'is_active', 'must_change_password',
        'secretariat', 'is_staff', 'is_superuser',
    ]
    search_fields = [
        'username', 'first_name', 'last_name', 'email',
        'matricule', 'grade', 'telephone', 'organisation',
    ]
    ordering = ['last_name', 'first_name']
    list_select_related = ['secretariat']
    list_per_page = 50
    autocomplete_fields = ['secretariat']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations supplémentaires', {
            'fields': (
                'role', 'matricule', 'grade',
                'telephone', 'organisation',
                'secretariat', 'must_change_password',
            ),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Informations supplémentaires', {
            'fields': (
                'first_name', 'last_name', 'email',
                'role', 'matricule', 'grade',
                'telephone', 'organisation',
                'secretariat',
            ),
        }),
    )

    def _audit_cible(self, obj):
        return (
            'user',
            obj.username,
            obj.get_full_name() or obj.username,
        )

    @admin.display(description='Rôle', ordering='role')
    def role_badge(self, obj):
        colors = {
            User.Role.ADMIN: ('#fdecec', '#b42318'),
            User.Role.DIRECTION: ('#eef6fc', '#0f4c81'),
            User.Role.CHEF_CPFAE_ADMIN: ('#eef6fc', '#0f4c81'),
            User.Role.CPFAE_ADMIN: ('#eef6fc', '#0f4c81'),
            User.Role.CHEF_SECRETARIAT: ('#fff7e8', '#9a6700'),
            User.Role.SECRETARIAT: ('#fff7e8', '#9a6700'),
            User.Role.FINANCE: ('#f0f4ff', '#3949ab'),
            User.Role.ARCHIVE: ('#f5f0ff', '#6b21a8'),
            User.Role.ENCADRANT: ('#e8f6f1', '#13624e'),
            User.Role.SUPERVISEUR: ('#fef3c7', '#92400e'),
            User.Role.AUDITEUR: ('#f3f4f6', '#374151'),
        }
        bg, fg = colors.get(obj.role, ('#f3f4f6', '#374151'))
        return format_html(
            '<span style="background:{};color:{};padding:3px 8px;'
            'border-radius:999px;font-weight:600;font-size:11px;">{}</span>',
            bg, fg, obj.get_role_display(),
        )
