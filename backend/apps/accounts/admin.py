from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group
from apps.accounts.models import User, GroupProfile, ModulePermissionRegistry, AuditLog


class GroupProfileInline(admin.StackedInline):
    model = GroupProfile
    fk_name = 'group'
    can_delete = False
    extra = 0


class GroupAdmin(BaseGroupAdmin):
    inlines = [GroupProfileInline]
    list_display = ['name', 'profile_code', 'profile_level', 'profile_active']
    list_filter = ['profile__level', 'profile__is_active']

    @admin.display(description='Code')
    def profile_code(self, obj):
        return obj.profile.code if hasattr(obj, 'profile') else '—'

    @admin.display(description='Niveau')
    def profile_level(self, obj):
        return f'N{obj.profile.level}' if hasattr(obj, 'profile') else '—'

    @admin.display(description='Actif', boolean=True)
    def profile_active(self, obj):
        return obj.profile.is_active if hasattr(obj, 'profile') else False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'display_groups', 'is_active', 'is_staff']
    list_filter = ['groups', 'is_active', 'is_staff', 'mfa_enabled']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['email']
    filter_horizontal = ['groups', 'user_permissions']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informations personnelles', {'fields': ('first_name', 'last_name', 'phone', 'photo')}),
        ('Institution', {'fields': ('institution', 'department')}),
        ('Sécurité', {'fields': ('mfa_enabled', 'mfa_secret', 'must_change_password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'password1', 'password2', 'first_name', 'last_name')}),
    )

    @admin.display(description='Groupes')
    def display_groups(self, obj):
        return ', '.join(g.name for g in obj.groups.all())


@admin.register(ModulePermissionRegistry)
class ModulePermissionRegistryAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'module', 'object_type']
    list_filter = ['module', 'action']
    readonly_fields = [f.name for f in AuditLog._meta.fields]


admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)
