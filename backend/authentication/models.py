from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    # Forward-declare to avoid circular import
    # (Secretariat is in formations app)
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrateur'
        DIRECTION = 'DIRECTION', 'Direction'
        CHEF_CPFAE_ADMIN = 'CHEF_CPFAE_ADMIN', 'Chef CPFAE Admin'
        CPFAE_ADMIN = 'CPFAE_ADMIN', 'CPFAE Admin'
        CHEF_SECRETARIAT = 'CHEF_SECRETARIAT', 'Chef Secrétariat'
        SECRETARIAT = 'SECRETARIAT', 'Secrétariat'
        FINANCE = 'FINANCE', 'Finance'
        ENCADRANT = 'ENCADRANT', 'Encadrant'
        AUDITEUR = 'AUDITEUR', 'Auditeur'

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.AUDITEUR,
    )
    matricule = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text="N° matricule utilisé comme numéro de badgeage",
    )
    telephone = models.CharField(max_length=20, blank=True, default='')
    organisation = models.CharField(max_length=255, blank=True, default='')
    grade = models.CharField(max_length=20, blank=True, default='', help_text="Grade (A4, A3…)")
    secretariat = models.ForeignKey(
        'formations.Secretariat',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='membres',
        help_text="Secrétariat auquel appartient cet utilisateur",
    )
    must_change_password = models.BooleanField(
        default=False,
        help_text="Si vrai, l'utilisateur doit changer son mot de passe avant d'utiliser les fonctions sensibles.",
    )

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"

    @property
    def is_chef_cpfae_admin(self):
        return self.role == self.Role.CHEF_CPFAE_ADMIN

    @property
    def is_dfrc(self):
        return self.role == self.Role.CPFAE_ADMIN

    @property
    def is_chef_secretariat(self):
        return self.role == self.Role.CHEF_SECRETARIAT

    @property
    def is_secretariat(self):
        return self.role == self.Role.SECRETARIAT

    @property
    def is_finance(self):
        return self.role == self.Role.FINANCE

    @property
    def is_encadrant(self):
        return self.role == self.Role.ENCADRANT

    @property
    def is_direction(self):
        return self.role == self.Role.DIRECTION

    @property
    def is_auditeur(self):
        return self.role == self.Role.AUDITEUR
