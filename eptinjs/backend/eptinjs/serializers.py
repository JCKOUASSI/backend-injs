"""Serializers DRF du module EPT-INJS."""
from __future__ import annotations

from rest_framework import serializers

from .models import (
    GroupeMembre,
    GroupePedagogique,
    JourFerie,
    ParametresPlanification,
    PeriodeFormation,
    PlanningRun,
    Pointage,
    ProgrammePeriode,
    Seance,
    SeanceQRToken,
)


def teacher_name(teacher) -> str | None:
    return teacher.user.get_full_name() if teacher else None


class PeriodeFormationSerializer(serializers.ModelSerializer):
    academic_year_label = serializers.CharField(source='academic_year.label', read_only=True)
    semester_label = serializers.CharField(source='semester.name', read_only=True, default=None)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    rythme_display = serializers.CharField(source='get_rythme_mensuel_display', read_only=True)
    seances_count = serializers.IntegerField(read_only=True)
    programmes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PeriodeFormation
        fields = [
            'id', 'academic_year', 'academic_year_label', 'semester', 'semester_label',
            'code', 'libelle', 'date_debut', 'date_fin', 'ordre', 'rythme_mensuel',
            'rythme_display', 'statut', 'statut_display', 'is_active',
            'seances_count', 'programmes_count', 'created_at',
        ]

    def validate(self, attrs):
        debut = attrs.get('date_debut') or getattr(self.instance, 'date_debut', None)
        fin = attrs.get('date_fin') or getattr(self.instance, 'date_fin', None)
        if debut and fin and fin < debut:
            raise serializers.ValidationError({'date_fin': 'La date de fin précède la date de début.'})
        return attrs


class ParametresPlanificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParametresPlanification
        fields = [
            'id', 'periode', 'jours_actifs',
            'matin_actif', 'matin_debut', 'matin_fin',
            'soir_actif', 'soir_debut', 'soir_fin',
            'duree_seance_minutes', 'max_seances_par_jour', 'tolerance_capacite_pct',
            'verrouiller_salle_par_groupe', 'poids_ecart_capacite',
            'poids_rotation_salle', 'poids_equilibrage_salles',
        ]

    def validate_jours_actifs(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError('Indiquez au moins un jour actif.')
        if any(not isinstance(day, int) or day < 0 or day > 6 for day in value):
            raise serializers.ValidationError('Les jours doivent être des entiers de 0 (lundi) à 6 (dimanche).')
        return sorted(set(value))

    def validate(self, attrs):
        for prefix in ('matin', 'soir'):
            debut = attrs.get(f'{prefix}_debut') or getattr(self.instance, f'{prefix}_debut', None)
            fin = attrs.get(f'{prefix}_fin') or getattr(self.instance, f'{prefix}_fin', None)
            if debut and fin and fin <= debut:
                raise serializers.ValidationError(
                    {f'{prefix}_fin': 'L’heure de fin doit suivre l’heure de début.'},
                )
        return attrs


class JourFerieSerializer(serializers.ModelSerializer):
    class Meta:
        model = JourFerie
        fields = ['id', 'institution', 'date', 'libelle', 'is_active']


class GroupeMembreSerializer(serializers.ModelSerializer):
    matricule = serializers.CharField(source='student.matricule', read_only=True)
    nom = serializers.SerializerMethodField()

    class Meta:
        model = GroupeMembre
        fields = ['id', 'groupe', 'student', 'matricule', 'nom']

    def get_nom(self, obj):
        return obj.student.user.get_full_name()


class GroupePedagogiqueSerializer(serializers.ModelSerializer):
    promotion_name = serializers.CharField(source='promotion.name', read_only=True)
    effectif = serializers.IntegerField(read_only=True)

    class Meta:
        model = GroupePedagogique
        fields = [
            'id', 'promotion', 'promotion_name', 'code', 'name',
            'effectif_max', 'effectif', 'is_active',
        ]


class ProgrammePeriodeSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source='course.code', read_only=True)
    course_name = serializers.CharField(source='course.name', read_only=True)
    teaching_unit_code = serializers.CharField(source='course.teaching_unit.code', read_only=True)
    promotion_name = serializers.CharField(source='promotion.name', read_only=True)
    periode_code = serializers.CharField(source='periode.code', read_only=True)
    periode_libelle = serializers.CharField(source='periode.libelle', read_only=True)
    session_kind_display = serializers.CharField(source='get_session_kind_display', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    supervisor_name = serializers.SerializerMethodField()
    volume_horaire_heures = serializers.FloatField(read_only=True)
    volume_maquette_heures = serializers.SerializerMethodField()
    heures_planifiees = serializers.SerializerMethodField()
    taux_couverture = serializers.SerializerMethodField()
    groupes_codes = serializers.SerializerMethodField()

    class Meta:
        model = ProgrammePeriode
        fields = [
            'id', 'periode', 'periode_code', 'periode_libelle',
            'course', 'course_code', 'course_name', 'teaching_unit_code',
            'promotion', 'promotion_name', 'session_kind', 'session_kind_display',
            'teacher', 'teacher_name', 'supervisor', 'supervisor_name',
            'volume_horaire_minutes', 'volume_horaire_heures', 'volume_maquette_heures',
            'heures_planifiees', 'taux_couverture', 'creneau_mode', 'salle_preferee',
            'groupes', 'groupes_codes', 'date_debut', 'date_fin', 'is_active',
        ]

    def get_teacher_name(self, obj):
        return teacher_name(obj.teacher)

    def get_supervisor_name(self, obj):
        return teacher_name(obj.supervisor)

    def get_volume_maquette_heures(self, obj):
        return round(obj.volume_maquette_minutes() / 60, 2)

    def get_heures_planifiees(self, obj):
        return round(obj.minutes_planifiees() / 60, 2)

    def get_taux_couverture(self, obj):
        cible = obj.volume_horaire_minutes or obj.volume_maquette_minutes()
        if not cible:
            return 0.0
        return round(obj.minutes_planifiees() / cible * 100, 1)

    def get_groupes_codes(self, obj):
        return [groupe.code for groupe in obj.groupes.all()]

    def validate(self, attrs):
        debut = attrs.get('date_debut') or getattr(self.instance, 'date_debut', None)
        fin = attrs.get('date_fin') or getattr(self.instance, 'date_fin', None)
        if debut and fin and fin < debut:
            raise serializers.ValidationError({'date_fin': 'La date de fin précède la date de début.'})
        return attrs


class SeanceSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source='course.code', read_only=True)
    course_name = serializers.CharField(source='course.name', read_only=True)
    promotion_name = serializers.CharField(source='promotion.name', read_only=True)
    periode_code = serializers.CharField(source='periode.code', read_only=True)
    periode_libelle = serializers.CharField(source='periode.libelle', read_only=True)
    groupe_code = serializers.CharField(source='groupe.code', read_only=True, default=None)
    room_code = serializers.CharField(source='room.code', read_only=True, default=None)
    room_name = serializers.CharField(source='room.name', read_only=True, default=None)
    teacher_name = serializers.SerializerMethodField()
    supervisor_name = serializers.SerializerMethodField()
    session_kind_display = serializers.CharField(source='get_session_kind_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    day_of_week = serializers.IntegerField(read_only=True)
    day_display = serializers.SerializerMethodField()
    duree_heures = serializers.FloatField(read_only=True)
    presents_count = serializers.SerializerMethodField()
    attendus_count = serializers.SerializerMethodField()

    class Meta:
        model = Seance
        fields = [
            'id', 'programme', 'periode', 'periode_code', 'periode_libelle',
            'course', 'course_code', 'course_name', 'promotion', 'promotion_name',
            'groupe', 'groupe_code', 'teacher', 'teacher_name', 'supervisor', 'supervisor_name',
            'room', 'room_code', 'room_name', 'session_kind', 'session_kind_display',
            'numero', 'intitule', 'date', 'day_of_week', 'day_display',
            'heure_debut', 'heure_fin', 'duree_minutes', 'duree_heures',
            'statut', 'statut_display', 'origine', 'started_at', 'ended_at', 'notes',
            'presents_count', 'attendus_count',
        ]
        read_only_fields = ['periode', 'course', 'promotion', 'duree_minutes', 'started_at', 'ended_at']

    def get_teacher_name(self, obj):
        return teacher_name(obj.teacher)

    def get_supervisor_name(self, obj):
        return teacher_name(obj.supervisor)

    def get_day_display(self, obj):
        return ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'][obj.date.weekday()]

    def get_presents_count(self, obj):
        cached = getattr(obj, 'presents_count_annotated', None)
        if cached is not None:
            return cached
        return obj.pointages.filter(statut__in=['present', 'retard', 'force']).count()

    def get_attendus_count(self, obj):
        cached = getattr(obj, 'attendus_count_annotated', None)
        if cached is not None:
            return cached
        return obj.pointages.count()

    def validate(self, attrs):
        debut = attrs.get('heure_debut') or getattr(self.instance, 'heure_debut', None)
        fin = attrs.get('heure_fin') or getattr(self.instance, 'heure_fin', None)
        if debut and fin and fin <= debut:
            raise serializers.ValidationError({'heure_fin': 'L’heure de fin doit suivre l’heure de début.'})
        return attrs


class SeanceWriteSerializer(SeanceSerializer):
    """Création manuelle : le programme porte la période, l'ECUE et la promotion."""

    class Meta(SeanceSerializer.Meta):
        read_only_fields = ['periode', 'course', 'promotion', 'duree_minutes', 'started_at', 'ended_at']

    def create(self, validated_data):
        validated_data.setdefault('origine', 'manuelle')
        return super().create(validated_data)


class SeanceQRTokenSerializer(serializers.ModelSerializer):
    est_valide = serializers.BooleanField(read_only=True)
    seance_intitule = serializers.SerializerMethodField()

    class Meta:
        model = SeanceQRToken
        fields = ['id', 'seance', 'seance_intitule', 'token', 'is_active', 'expires_at', 'est_valide', 'created_at']
        read_only_fields = ['token', 'expires_at']

    def get_seance_intitule(self, obj):
        return f'{obj.seance.course.code} — {obj.seance.date} {obj.seance.heure_debut:%H:%M}'


class PointageSerializer(serializers.ModelSerializer):
    personne_nom = serializers.CharField(read_only=True)
    matricule = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    est_present = serializers.BooleanField(read_only=True)

    class Meta:
        model = Pointage
        fields = [
            'id', 'seance', 'role', 'role_display', 'student', 'teacher',
            'personne_nom', 'matricule', 'statut', 'statut_display', 'est_present',
            'source', 'entree_at', 'sortie_at', 'duree_minutes',
            'device_id', 'latitude', 'longitude', 'accuracy_m',
            'last_heartbeat_at', 'outside_geofence_count', 'notes',
        ]
        read_only_fields = ['duree_minutes']

    def get_matricule(self, obj):
        if obj.student_id:
            return obj.student.matricule
        if obj.teacher_id:
            return obj.teacher.employee_id
        return None


class PlanningRunSerializer(serializers.ModelSerializer):
    periode_code = serializers.CharField(source='periode.code', read_only=True)
    started_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PlanningRun
        fields = [
            'id', 'periode', 'periode_code', 'mode', 'statut', 'scope', 'synthese',
            'started_by', 'started_by_name', 'created_at', 'finished_at',
        ]

    def get_started_by_name(self, obj):
        return obj.started_by.get_full_name() if obj.started_by_id else None


class GenerationRequestSerializer(serializers.Serializer):
    """Paramètres d'entrée du moteur de génération."""

    periode = serializers.UUIDField()
    promotions = serializers.ListField(child=serializers.UUIDField(), required=False, allow_empty=True)
    courses = serializers.ListField(child=serializers.UUIDField(), required=False, allow_empty=True)
    mode = serializers.ChoiceField(choices=['strict', 'best_effort'], default='best_effort')
    remplacer = serializers.BooleanField(
        default=True, help_text='Supprime les séances auto existantes du périmètre avant génération.',
    )
    dry_run = serializers.BooleanField(default=False)


class ScanRequestSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    device_id = serializers.CharField(max_length=80, required=False, allow_blank=True)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    accuracy_m = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)


class MarquageSerializer(serializers.Serializer):
    """Marquage manuel en masse depuis la fiche Cours (ECUE)."""

    statut = serializers.ChoiceField(choices=[choice[0] for choice in Pointage.STATUTS])
    students = serializers.ListField(child=serializers.UUIDField(), required=False, allow_empty=True)
    teachers = serializers.ListField(child=serializers.UUIDField(), required=False, allow_empty=True)
    notes = serializers.CharField(max_length=255, required=False, allow_blank=True)
