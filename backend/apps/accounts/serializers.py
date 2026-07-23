from django.contrib.auth.models import Group, Permission
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from apps.accounts.models import User, GroupProfile, AuditLog
from apps.accounts.rbac import parse_codename, to_display_codename


class ModulePermissionSerializer(serializers.ModelSerializer):
    module = serializers.SerializerMethodField()
    action = serializers.SerializerMethodField()
    codename_display = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ['id', 'codename', 'codename_display', 'module', 'action', 'name']

    def get_module(self, obj):
        module, _ = parse_codename(obj.codename)
        return module

    def get_action(self, obj):
        _, action = parse_codename(obj.codename)
        return action

    def get_codename_display(self, obj):
        return to_display_codename(obj.codename)


class GroupProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupProfile
        fields = ['code', 'level', 'description', 'is_active', 'parent']


class GroupSerializer(serializers.ModelSerializer):
    profile = GroupProfileSerializer(read_only=True)
    code = serializers.CharField(write_only=True, required=False)
    level = serializers.IntegerField(write_only=True, required=False, default=4)
    description = serializers.CharField(write_only=True, required=False, allow_blank=True)
    is_active = serializers.BooleanField(write_only=True, required=False, default=True)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), write_only=True, required=False, allow_null=True
    )
    permissions = ModulePermissionSerializer(source='permissions.all', many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.all(), write_only=True, source='permissions', required=False
    )

    class Meta:
        model = Group
        fields = [
            'id', 'name', 'profile', 'code', 'level', 'description', 'is_active', 'parent',
            'permissions', 'permission_ids',
        ]

    def _profile_defaults(self, validated_data):
        return {
            'code': validated_data.pop('code', None),
            'level': validated_data.pop('level', 4),
            'description': validated_data.pop('description', ''),
            'is_active': validated_data.pop('is_active', True),
            'parent': validated_data.pop('parent', None),
        }

    def create(self, validated_data):
        profile_data = self._profile_defaults(validated_data)
        permissions = validated_data.pop('permissions', [])
        if not profile_data['code']:
            profile_data['code'] = validated_data['name'].lower().replace(' ', '_')
        group = Group.objects.create(**validated_data)
        GroupProfile.objects.create(group=group, **profile_data)
        if permissions:
            group.permissions.set(permissions)
        return group

    def update(self, instance, validated_data):
        profile_data = self._profile_defaults(validated_data)
        permissions = validated_data.pop('permissions', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        profile, _ = GroupProfile.objects.get_or_create(
            group=instance,
            defaults={'code': instance.name.lower().replace(' ', '_'), 'level': 4},
        )
        for attr, value in profile_data.items():
            if value is not None:
                setattr(profile, attr, value)
        profile.save()
        if permissions is not None:
            instance.permissions.set(permissions)
        return instance


class UserSerializer(serializers.ModelSerializer):
    groups_detail = GroupSerializer(source='groups', many=True, read_only=True)
    group_level = serializers.IntegerField(source='get_group_level', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    photo_url = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'phone', 'photo', 'photo_url',
            'groups', 'groups_detail', 'group_level', 'institution', 'department', 'is_active',
            'mfa_enabled', 'locale', 'permissions', 'created_at', 'last_login',
        ]
        read_only_fields = ['id', 'created_at', 'last_login']

    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None

    def get_permissions(self, obj):
        return sorted(obj.get_permission_codes())


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    group_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Group.objects.all(), source='groups', required=False
    )

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'phone', 'group_ids', 'institution', 'department']

    def create(self, validated_data):
        groups = validated_data.pop('groups', [])
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        if groups:
            user.groups.set(groups)
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_email', 'action', 'module', 'object_type',
            'object_id', 'object_repr', 'changes', 'ip_address', 'timestamp',
        ]
