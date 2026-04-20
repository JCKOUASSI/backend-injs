from rest_framework import serializers
from django.contrib.auth import get_user_model
from .permissions import get_subordinate_roles, get_creatable_roles

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    secretariat_nom = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'grade', 'telephone', 'organisation', 'is_active',
            'secretariat', 'secretariat_nom',
        ]
        read_only_fields = ['id', 'secretariat_nom']

    def get_secretariat_nom(self, obj):
        if obj.secretariat:
            return obj.secretariat.nom
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'password', 'role', 'grade', 'telephone', 'organisation', 'secretariat',
        ]

    def validate_role(self, value):
        request = self.context.get('request')
        requester_role = getattr(getattr(request, 'user', None), 'role', None)
        allowed = get_creatable_roles(requester_role)
        if value not in allowed:
            raise serializers.ValidationError(
                f"Vous ne pouvez pas attribuer le rôle « {value} »."
            )
        return value

    def validate_secretariat(self, value):
        request = self.context.get('request')
        requester = getattr(request, 'user', None)
        if getattr(requester, 'role', None) in ('SECRETARIAT', 'CHEF_SECRETARIAT'):
            if value is not None and value != requester.secretariat:
                raise serializers.ValidationError(
                    "Vous ne pouvez créer des utilisateurs que pour votre propre secrétariat."
                )
        return value

    def validate(self, attrs):
        role = attrs.get('role')
        secretariat = attrs.get('secretariat')
        if role in ('CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN'):
            attrs['secretariat'] = None
        if role == 'CHEF_CPFAE_ADMIN':
            if User.objects.filter(role='CHEF_CPFAE_ADMIN').exists():
                raise serializers.ValidationError(
                    {'role': "Un Chef CPFAE Admin existe déjà. Ce rôle est unique sur toute la plateforme."}
                )
        if role == 'CHEF_SECRETARIAT' and secretariat:
            already_exists = User.objects.filter(
                role='CHEF_SECRETARIAT', secretariat=secretariat
            ).exists()
            if already_exists:
                raise serializers.ValidationError(
                    {'role': "Ce secrétariat a déjà un Chef Secrétariat. Un seul Chef Secrétariat est autorisé par secrétariat."}
                )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'password', 'role', 'grade', 'telephone', 'organisation', 'is_active',
            'secretariat',
        ]
        read_only_fields = ['id']

    def validate_role(self, value):
        request = self.context.get('request')
        requester_role = getattr(getattr(request, 'user', None), 'role', None)
        allowed = get_creatable_roles(requester_role)
        if value not in allowed:
            raise serializers.ValidationError(
                f"Vous ne pouvez pas attribuer le rôle « {value} »."
            )
        return value

    def validate_secretariat(self, value):
        request = self.context.get('request')
        requester = getattr(request, 'user', None)
        if getattr(requester, 'role', None) in ('SECRETARIAT', 'CHEF_SECRETARIAT'):
            if value is not None and value != requester.secretariat:
                raise serializers.ValidationError(
                    "Vous ne pouvez modifier que les utilisateurs de votre propre secrétariat."
                )
        return value

    def validate(self, attrs):
        role = attrs.get('role', self.instance.role if self.instance else None)
        secretariat = attrs.get('secretariat', self.instance.secretariat if self.instance else None)
        if role in ('CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN'):
            attrs['secretariat'] = None
        if role == 'CHEF_CPFAE_ADMIN':
            already_exists = User.objects.filter(role='CHEF_CPFAE_ADMIN').exclude(
                pk=self.instance.pk if self.instance else None
            ).exists()
            if already_exists:
                raise serializers.ValidationError(
                    {'role': "Un Chef CPFAE Admin existe déjà. Ce rôle est unique sur toute la plateforme."}
                )
        if role == 'CHEF_SECRETARIAT' and secretariat:
            already_exists = User.objects.filter(
                role='CHEF_SECRETARIAT', secretariat=secretariat
            ).exclude(pk=self.instance.pk if self.instance else None).exists()
            if already_exists:
                raise serializers.ValidationError(
                    {'role': "Ce secrétariat a déjà un Chef Secrétariat. Un seul Chef Secrétariat est autorisé par secrétariat."}
                )
        return attrs

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Mot de passe actuel incorrect.")
        return value

    def validate_new_password(self, value):
        old = self.initial_data.get('old_password', '')
        if value == old:
            raise serializers.ValidationError("Le nouveau mot de passe doit être différent de l'ancien.")
        return value
