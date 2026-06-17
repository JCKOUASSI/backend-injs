import uuid
from django.db import models
from django.db.models.functions import Lower
from django.conf import settings
from django.utils import timezone


class Secretariat(models.Model):
    """Secrétariat qui gère ses participants."""

    numero = models.CharField(max_length=50, unique=True, blank=True)
    nom = models.CharField(max_length=255, help_text="Nom du secrétariat")
    type = models.ForeignKey(
        'RefTypeSecretariat',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='secretariats',
        help_text="Type de secrétariat",
    )
    description = models.TextField(blank=True, default='')
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='secretariats_resp',
        limit_choices_to={'role': 'CHEF_SECRETARIAT'},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nom']
        verbose_name = 'Secrétariat'
        verbose_name_plural = 'Secrétariats'

    def save(self, *args, **kwargs):
        if not self.numero:
            from django.db import transaction
            with transaction.atomic():
                last = Secretariat.objects.select_for_update().order_by('-id').first()
                next_id = (last.id + 1) if last else 1
                self.numero = f'S{next_id:04d}'
                while Secretariat.objects.filter(numero=self.numero).exists():
                    next_id += 1
                    self.numero = f'S{next_id:04d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nom} ({self.numero})"

    @property
    def nb_participants(self):
        return self.participants.count()

    @property
    def nb_formations(self):
        return self.modules_secretariat.values('formation_id').distinct().count()

    @property
    def nb_modules(self):
        return self.modules_secretariat.count()


class RefTypeSecretariat(models.Model):
    """Types de secrétariat (référentiel configurable)."""
    libelle = models.CharField(max_length=100, unique=True)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ['libelle']
        verbose_name = 'Référentiel – Type de secrétariat'
        verbose_name_plural = 'Référentiel – Types de secrétariat'

    def __str__(self):
        return self.libelle


class RefCategorie(models.Model):
    """Catégories prédéfinies."""
    libelle = models.CharField(max_length=100, unique=True)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ['libelle']
        verbose_name = 'Référentiel – Catégorie'
        verbose_name_plural = 'Référentiel – Catégories'

    def __str__(self):
        return self.libelle


class RefGrade(models.Model):
    """Grades prédéfinis, liés à une catégorie."""
    categorie = models.ForeignKey(
        RefCategorie, on_delete=models.CASCADE, related_name='grades',
        null=True, blank=True,
    )
    libelle = models.CharField(max_length=100)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ['libelle']
        unique_together = ('categorie', 'libelle')
        verbose_name = 'Référentiel – Grade'
        verbose_name_plural = 'Référentiel – Grades'

    def __str__(self):
        return self.libelle


class RefVague(models.Model):
    """Vagues prédéfinies (ex: PREMIERE VAGUE, DEUXIEME VAGUE…)."""
    libelle = models.CharField(max_length=100, unique=True)
    ordre = models.PositiveSmallIntegerField(default=1, help_text="Ordre d'affichage")
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ['ordre', 'libelle']
        verbose_name = 'Référentiel – Vague'
        verbose_name_plural = 'Référentiel – Vagues'

    def __str__(self):
        return self.libelle


class RefFormation(models.Model):
    """Cycles de formation prédéfinis (ex: FORMATION EN ADMINISTRATION DE BASE)."""
    intitule = models.CharField(max_length=255, unique=True)
    actif = models.BooleanField(default=True)
    prix_heure_realisee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Prix pour 1 heure réalisée',
        help_text='Tarif horaire spécifique. Si non renseigné, le tarif par défaut des paramètres finance s\'applique.',
    )

    class Meta:
        ordering = ['intitule']
        verbose_name = 'Référentiel – Formation (cycle)'
        verbose_name_plural = 'Référentiel – Formations (cycles)'

    def __str__(self):
        return self.intitule


class RefModule(models.Model):
    """Modules/cours prédéfinis (ex: Déontologie de la Fonction Publique)."""
    formation = models.ForeignKey(
        RefFormation,
        on_delete=models.CASCADE,
        related_name='modules',
        null=True,
        blank=True,
        help_text="Formation (cycle) auquel appartient ce module",
    )
    intitule = models.CharField(max_length=255)
    volume_horaire = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ['intitule']
        verbose_name = 'Référentiel – Module'
        verbose_name_plural = 'Référentiel – Modules'
        constraints = [
            models.UniqueConstraint(Lower('intitule'), name='uniq_refmodule_intitule_ci'),
        ]

    @staticmethod
    def normalize_intitule(value):
        """Normalise un intitulé : trim, espaces multiples → un seul, majuscules."""
        if value is None:
            return ''
        return ' '.join(str(value).split()).upper()

    def save(self, *args, **kwargs):
        self.intitule = RefModule.normalize_intitule(self.intitule)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.intitule}" + (f" ({self.formation.intitule})" if self.formation_id else "")

    def get_volume_horaire_for_categorie(self, categorie_code):
        """Retourne le volume horaire spécifique à une catégorie, ou le volume global si non défini."""
        if not categorie_code:
            return self.volume_horaire
        try:
            volume_par_cat = self.volumes_horaires.filter(categorie__libelle__iexact=categorie_code).first()
            if volume_par_cat and volume_par_cat.volume_horaire is not None:
                return volume_par_cat.volume_horaire
        except Exception:
            pass
        return self.volume_horaire


class RefModuleVolumeHoraire(models.Model):
    """Volume horaire d'un module du référentiel spécifique à une catégorie."""

    module = models.ForeignKey(
        RefModule,
        on_delete=models.CASCADE,
        related_name='volumes_horaires',
        help_text="Module du référentiel",
    )
    categorie = models.ForeignKey(
        RefCategorie,
        on_delete=models.CASCADE,
        related_name='volumes_horaires_modules',
        help_text="Catégorie concernée (A, B, C, D...)",
    )
    volume_horaire = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Volume horaire pour cette catégorie (en heures)",
    )

    class Meta:
        ordering = ['module', 'categorie__libelle']
        verbose_name = 'Référentiel – Volume horaire par catégorie'
        verbose_name_plural = 'Référentiel – Volumes horaires par catégorie'
        unique_together = ('module', 'categorie')

    def __str__(self):
        return f"{self.module.intitule} – {self.categorie.libelle} : {self.volume_horaire}h"


class RefSite(models.Model):
    """Sites/centres de formation prédéfinis."""
    nom = models.CharField(max_length=255, unique=True)
    actif = models.BooleanField(default=True)
    geofence_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Latitude du centre de formation (contrôle de présence mobile)",
    )
    geofence_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Longitude du centre de formation",
    )
    geofence_rayon_m = models.PositiveIntegerField(
        default=200,
        help_text="Rayon autorisé en mètres pour le badgeage mobile",
    )

    class Meta:
        ordering = ['nom']
        verbose_name = 'Référentiel – Site'
        verbose_name_plural = 'Référentiel – Sites'

    def __str__(self):
        return self.nom


class RefBatiment(models.Model):
    """Bâtiments rattachés à un site."""
    site = models.ForeignKey(RefSite, on_delete=models.CASCADE, related_name='batiments')
    nom = models.CharField(max_length=255)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ['nom']
        unique_together = ('site', 'nom')
        verbose_name = 'Référentiel – Bâtiment'
        verbose_name_plural = 'Référentiel – Bâtiments'

    def __str__(self):
        return f"{self.nom} ({self.site.nom})"


class RefSalle(models.Model):
    """Salles rattachées à un bâtiment (ou directement à un site)."""
    site = models.ForeignKey(RefSite, on_delete=models.CASCADE, related_name='salles')
    batiment = models.ForeignKey(RefBatiment, on_delete=models.SET_NULL, null=True, blank=True, related_name='salles')
    nom = models.CharField(max_length=100)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ['nom']
        unique_together = ('site', 'batiment', 'nom')
        verbose_name = 'Référentiel – Salle'
        verbose_name_plural = 'Référentiel – Salles'

    def __str__(self):
        return f"{self.nom} – {self.site.nom}"


class Formation(models.Model):

    numero_formation = models.PositiveSmallIntegerField(null=True, blank=True, help_text="N° de la formation dans le cycle")
    formation = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['formation']
        verbose_name = 'Formation'
        verbose_name_plural = 'Formations'

    def __str__(self):
        return f"{self.formation}"


class Participant(models.Model):
    class Sexe(models.TextChoices):
        MASCULIN = 'MASCULIN', 'Masculin'
        FEMININ = 'FEMININ', 'Féminin'

    matricule = models.CharField(max_length=50, unique=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    sexe = models.CharField(max_length=10, choices=Sexe.choices, blank=True, default='')
    date_naissance = models.DateField(null=True, blank=True)
    lieu_naissance = models.CharField(max_length=255, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    telephone = models.CharField(max_length=20, blank=True, default='')
    telephone2 = models.CharField(max_length=20, blank=True, default='')
    type_concours = models.CharField(max_length=100, blank=True, default='')
    libelle_concours = models.CharField(max_length=255, blank=True, default='')
    categorie = models.CharField(max_length=10, blank=True, default='')
    grade = models.CharField(max_length=20, blank=True, default='')
    groupe = models.CharField(max_length=50, blank=True, default='')
    grade_groupe = models.CharField(max_length=50, blank=True, default='')
    vague = models.CharField(max_length=50, blank=True, default='', help_text="Vague (PREMIERE VAGUE, DEUXIEME VAGUE…)")
    site = models.CharField(max_length=255, blank=True, default='')
    salle = models.CharField(max_length=100, blank=True, default='')
    secretariat = models.ForeignKey(
        Secretariat,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='participants',
        help_text="Secrétariat responsable de ce participant",
    )
    motif_notoire = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Motif de notoriété du participant',
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='participant_profile',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nom', 'prenom']
        verbose_name = 'Auditeur'
        verbose_name_plural = 'Auditeurs'

    def save(self, *args, **kwargs):
        if not self.matricule:
            raise ValueError('Le matricule est obligatoire pour un participant.')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nom} {self.prenom} ({self.matricule})"


class ModuleParticipant(models.Model):
    """Liste des participants ATTENDUS pour un module."""
    module = models.ForeignKey(
        'Module',
        on_delete=models.CASCADE,
        related_name='module_participants',
    )
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='modules_inscrits',
    )
    inscrit_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('module', 'participant')
        verbose_name = 'Inscription module'
        verbose_name_plural = 'Inscriptions modules'

    def __str__(self):
        return f"{self.participant} → {self.module.intitule}"

    @property
    def formation(self):
        """Accès rapide à la formation via le module."""
        return self.module.formation


FormationParticipant = ModuleParticipant


class Formateur(models.Model):
    numerobadge = models.CharField(max_length=50, unique=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(blank=True, default='')
    telephone = models.CharField(max_length=20, blank=True, default='')
    specialite = models.CharField(max_length=255, blank=True, default='')
    organisation = models.CharField(max_length=255, blank=True, default='')
    numero_piece_identite = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name="N° pièce d'identité",
    )
    numero_compte_bancaire = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='N° de compte bancaire',
    )
    secretariats = models.ManyToManyField(
        Secretariat,
        blank=True,
        related_name='formateurs',
        help_text="Secrétariats auxquels appartient ce formateur",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='formateur_profile',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nom', 'prenom']
        verbose_name = 'Formateur'
        verbose_name_plural = 'Formateurs'

    def save(self, *args, **kwargs):
        if not self.numerobadge:
            from django.db import transaction
            with transaction.atomic():
                last = Formateur.objects.select_for_update().order_by('-id').first()
                next_id = (last.id + 1) if last else 1
                candidate = f'F{next_id:04d}'
                while Formateur.objects.filter(numerobadge=candidate).exists():
                    next_id += 1
                    candidate = f'F{next_id:04d}'
                self.numerobadge = candidate
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nom} {self.prenom} ({self.numerobadge})"


class ModuleFormateur(models.Model):
    """Liste des formateurs assignés à un module."""
    module = models.ForeignKey(
        'Module',
        on_delete=models.CASCADE,
        related_name='module_formateurs',
    )
    formateur = models.ForeignKey(
        Formateur,
        on_delete=models.CASCADE,
        related_name='modules_assignes',
    )
    inscrit_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('module', 'formateur')
        verbose_name = 'Formateur assigné'
        verbose_name_plural = 'Formateurs assignés'

    @property
    def formation(self):
        return self.module.formation

    def __str__(self):
        return f"{self.formateur} → {self.module.intitule}"


FormationFormateur = ModuleFormateur


class Module(models.Model):
    """Module d'une formation (un cours). Une formation peut avoir plusieurs modules."""

    class Statut(models.TextChoices):
        PLANIFIEE  = 'PLANIFIEE',  'Planifiée'
        EN_COURS   = 'EN_COURS',   'En cours'
        SUSPENDUE  = 'SUSPENDUE',  'Suspendue'
        TERMINEE   = 'TERMINEE',   'Terminée'

    formation = models.ForeignKey(
        Formation,
        on_delete=models.CASCADE,
        related_name='modules',
    )
    intitule = models.CharField(max_length=255, help_text="Intitulé du module/cours")
    ref_module = models.ForeignKey(
        RefModule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='modules_instances',
        help_text='Référentiel canonique du module (nomenclature unifiée)',
    )
    # Colonne historique / contrainte SQL (NOT NULL) — alignée sur le titre de formation (cycle).
    cycle = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Libellé du cycle de formation (ex. même valeur que Formation.formation)",
    )
    duree_prevue_heures = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        null=True, blank=True,
        help_text="Volume horaire prévu pour ce module",
    )
    ordre = models.PositiveSmallIntegerField(default=1, help_text="Ordre d'affichage")

    grade    = models.CharField(max_length=20, blank=True, default='', help_text="Grade (A4, A3…)")
    groupe   = models.CharField(max_length=50, blank=True, default='', help_text="Groupe (GROUPE 1, GROUPE 2…)")
    vague    = models.CharField(max_length=50, blank=True, default='', help_text="Vague (PREMIERE VAGUE, DEUXIEME VAGUE…)")
    secretariat = models.ForeignKey(
        Secretariat,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='modules_secretariat',
        help_text="Secrétariat responsable de ce module",
    )
    # NOTE: historiquement un champ texte. On le garde temporairement pour compat/migration.
    site_legacy = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Site (legacy)',
        help_text="Ancien champ texte. Utiliser le champ FK « site » (RefSite) à la place.",
    )
    site = models.ForeignKey(
        RefSite,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='modules',
        verbose_name='Site',
        help_text="Centre de formation (référentiel). Sert à la géolocalisation mobile.",
    )
    batiment = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Bâtiment',
        help_text="Bâtiment ou zone (import Excel : colonne « Bâtiment »).",
    )
    salle = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='Salle',
        help_text="Salle ou lieu précis (import Excel : colonne « Salle »).",
    )
    date_debut = models.DateField(null=True, blank=True, help_text="Date de début du module")
    date_fin   = models.DateField(null=True, blank=True, help_text="Date de fin du module")
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.PLANIFIEE,
    )
    formateur = models.ForeignKey(
        'Formateur',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='modules',
        help_text="Formateur principal du module",
    )
    superviseur = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='modules_supervises',
        help_text="Encadrant responsable du module",
    )
    creee_par = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='modules_crees',
        help_text="Utilisateur ayant créé le module",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ordre', 'intitule']
        verbose_name = 'Module'
        verbose_name_plural = 'Modules'
        unique_together = [('formation', 'intitule', 'grade', 'groupe', 'vague')]

    def __str__(self):
        return f"{self.intitule} ({self.formation.formation})"

    def canonical_intitule(self):
        """Libellé canonique (référentiel matière si renseigné, sinon intitulé module)."""
        if self.ref_module_id and self.ref_module:
            ref_label = (self.ref_module.intitule or '').strip()
            if ref_label:
                return ref_label
        return (self.intitule or '').strip()


class SessionModule(models.Model):
    """Une session (matin, après-midi…) d'un module pour une journée donnée."""
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='sessions',
        help_text="Module auquel appartient cette séance",
    )
    date_journee = models.DateField(default=timezone.localdate)
    numero = models.PositiveSmallIntegerField(
        help_text="Numéro de session dans la journée (1, 2, 3…)",
    )
    intitule = models.CharField(
        max_length=100, blank=True, default='',
        help_text="Intitulé libre (ex: Matin, Après-midi, Module 3…)",
    )
    heure_debut_prevue = models.TimeField(
        null=True, blank=True,
        help_text="Heure de début prévue",
    )
    heure_fin_prevue = models.TimeField(
        null=True, blank=True,
        help_text="Heure de fin prévue",
    )
    auto_demarrage = models.BooleanField(
        default=True,
        help_text="Démarrer automatiquement à l'heure prévue",
    )
    demarree_le = models.DateTimeField(null=True, blank=True)
    terminee_le = models.DateTimeField(null=True, blank=True)
    demarree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions_demarrees',
    )

    class Meta:
        ordering = ['date_journee', 'heure_debut_prevue', 'numero']
        unique_together = ('module', 'date_journee', 'numero')
        verbose_name = 'Séance'
        verbose_name_plural = 'Séances'

    def __str__(self):
        label = self.intitule or f"Session {self.numero}"
        module = self.module
        formation_label = module.formation.formation if module and module.formation_id else ''
        contexte_parts = [p for p in (module.grade, module.groupe, module.vague) if p]
        contexte = " / ".join(contexte_parts)
        prefixe_parts = [p for p in (formation_label, contexte) if p]
        prefixe = " | ".join(prefixe_parts)
        module_label = module.intitule if module else ''
        if self.demarree_le and not self.terminee_le:
            etat = "en cours"
        elif self.terminee_le:
            etat = "terminée"
        else:
            etat = "planifiée"
        core = f"{module_label} — {self.date_journee} {label} ({etat})"
        return f"{prefixe} • {core}" if prefixe else core

    @property
    def formation(self):
        return self.module.formation

    @property
    def est_planifiee(self):
        return self.demarree_le is None

    @property
    def est_en_cours(self):
        return self.demarree_le is not None and self.terminee_le is None

    @property
    def est_terminee(self):
        return self.terminee_le is not None

    @property
    def duree_minutes(self):
        if self.demarree_le and self.terminee_le:
            return round((self.terminee_le - self.demarree_le).total_seconds() / 60, 1)
        return None


class QRToken(models.Model):
    session = models.ForeignKey(
        SessionModule,
        on_delete=models.CASCADE,
        related_name='qr_tokens',
        help_text="Séance liée à ce QR code",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    genere_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='qr_tokens_generes',
    )
    actif = models.BooleanField(default=True)
    expire_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Code QR'
        verbose_name_plural = 'Codes QR'

    @property
    def formation(self):
        return self.session.module.formation

    def __str__(self):
        session_label = self.session.intitule or f"Session {self.session.numero}"
        label = self.session.module.intitule or self.session.module.formation.formation
        return f"QR {label} — {session_label} ({'actif' if self.actif else 'inactif'})"

    @property
    def is_expired(self):
        return timezone.now() > self.expire_at

    @property
    def is_valid(self):
        if not self.actif or self.is_expired:
            return False
        if self.session.est_terminee:
            return False
        return True


class FinanceSettings(models.Model):
    """Paramètres globaux du module finance (singleton pk=1)."""
    prix_heure_realisee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Prix pour 1 heure réalisée',
        help_text='Montant versé par heure de cours effectivement réalisée (badgeage).',
    )
    afficher_montants_exports = models.BooleanField(
        default=True,
        verbose_name='Afficher les montants sur les états financiers',
        help_text='Valeur par défaut lors de l\'export PDF/Excel (modifiable à chaque export).',
    )
    export_titre_document = models.CharField(
        max_length=255,
        blank=True,
        default='ÉTAT FINANCIER FORMATEUR',
        verbose_name='Titre des états financiers',
    )
    export_entete_ligne1 = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='En-tête ligne 1',
        help_text='Ex. République de Côte d\'Ivoire',
    )
    export_entete_ligne2 = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='En-tête ligne 2',
        help_text='Ex. Ministère / Direction',
    )
    export_organisme = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Organisme',
        help_text='Nom affiché sur les états financiers (ex. CPFAE).',
    )
    export_adresse = models.TextField(
        blank=True,
        default='',
        verbose_name='Adresse / coordonnées',
    )
    export_reference_prefix = models.CharField(
        max_length=30,
        blank=True,
        default='EFI',
        verbose_name='Préfixe de référence document',
    )
    export_mention_legale = models.TextField(
        blank=True,
        default='',
        verbose_name='Mention légale / pied de page',
    )
    export_signataire_nom = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Nom du signataire',
    )
    export_signataire_fonction = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Fonction du signataire',
    )
    export_contacts = models.TextField(
        blank=True,
        default='',
        verbose_name='Contacts (fiche récap formateur)',
        help_text='Une ligne par contact ou phrase affichée sous la note NB des exports fiche formateur.',
    )
    export_pied_page_titre = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Titre pied de page (fiche récap)',
        help_text='Ex. DOCUMENT CONFIDENTIEL — affiché en gras en bas de la fiche formateur.',
    )
    export_pied_page_texte = models.TextField(
        blank=True,
        default='',
        verbose_name='Texte pied de page (fiche récap)',
        help_text='Coordonnées institutionnelles affichées sous le titre en bas de la fiche formateur.',
    )
    tolerance_active = models.BooleanField(
        default=False,
        verbose_name='Activer la tolérance horaire',
        help_text='Active la marge de tolérance sur les volumes réalisés inférieurs au planifié.',
    )
    tolerance_minutes = models.PositiveIntegerField(
        default=30,
        verbose_name='Tolérance (minutes)',
        help_text='Marge absolue acceptée (minutes) entre planifié et réalisé.',
    )
    tolerance_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5,
        verbose_name='Tolérance (%)',
        help_text='Marge relative (% du volume planifié). Le seuil retenu est le plus favorable des deux.',
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finance_settings_updates',
    )

    class Meta:
        verbose_name = 'Paramètres finance'
        verbose_name_plural = 'Paramètres finance'

    def __str__(self):
        return f'Paramètres finance (1 h réalisée = {self.prix_heure_realisee})'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                'tolerance_active': False,
                'tolerance_minutes': 30,
                'tolerance_pct': 5,
            },
        )
        return obj


class FinanceAjustement(models.Model):
    """Proposition d'ajustement horaire sur une séance terminée (workflow Finance / Direction)."""

    class Statut(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        VALIDE = 'VALIDE', 'Validé'
        REJETE = 'REJETE', 'Rejeté'

    session = models.ForeignKey(
        SessionModule,
        on_delete=models.CASCADE,
        related_name='finance_ajustements',
    )
    formateur = models.ForeignKey(
        'Formateur',
        on_delete=models.CASCADE,
        related_name='finance_ajustements',
    )
    minutes_delta = models.IntegerField(
        help_text='Minutes à ajouter (positif) ou retirer (négatif) du volume réalisé.',
    )
    motif = models.TextField()
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
        db_index=True,
    )
    realise_avant_minutes = models.FloatField(
        null=True,
        blank=True,
        help_text='Volume réalisé de la séance avant ajustement (snapshot).',
    )
    realise_apres_minutes = models.FloatField(
        null=True,
        blank=True,
        help_text='Volume réalisé attendu après validation.',
    )
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finance_ajustements_proposes',
    )
    proposed_at = models.DateTimeField(auto_now_add=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finance_ajustements_valides',
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finance_ajustements_rejetes',
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_motif = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Ajustement horaire finance'
        verbose_name_plural = 'Ajustements horaires finance'
        ordering = ['-proposed_at']
        indexes = [
            models.Index(fields=['statut', 'proposed_at'], name='formations__statut_8e2f0a_idx'),
            models.Index(fields=['session', 'statut'], name='formations__session_4c1b2d_idx'),
        ]

    def __str__(self):
        return f'Ajustement {self.statut} — séance {self.session_id} ({self.minutes_delta} min)'


class NoteModule(models.Model):
    """Note / mention d'un participant sur un module (saisie secrétariat)."""

    class Mention(models.TextChoices):
        TRES_BIEN = 'TRES_BIEN', 'Très bien'
        BIEN = 'BIEN', 'Bien'
        ASSEZ_BIEN = 'ASSEZ_BIEN', 'Assez bien'
        PASSABLE = 'PASSABLE', 'Passable'
        INSUFFISANT = 'INSUFFISANT', 'Insuffisant'

    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='notes',
    )
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='notes_modules',
    )
    note = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Note numérique (ex : 14.50)',
    )
    mention = models.CharField(
        max_length=20,
        choices=Mention.choices,
        blank=True,
        default='',
        help_text='Mention calculée ou saisie manuellement',
    )
    observations = models.TextField(
        blank=True,
        default='',
        help_text='Observations éventuelles du secrétariat',
    )
    saisie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notes_saisies',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Note module'
        verbose_name_plural = 'Notes modules'
        ordering = ['module', 'participant__nom', 'participant__prenom']
        unique_together = [('module', 'participant')]
