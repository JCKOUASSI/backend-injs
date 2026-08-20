"""Administration Django du module EPT-INJS."""
from django.contrib import admin

from .models import (
    GroupeMembre,
    GroupePedagogique,
    JourFerie,
    ParametresPlanification,
    PeriodeFormation,
    PlanningAuditLog,
    PlanningRun,
    Pointage,
    ProgrammePeriode,
    Seance,
    SeanceQRToken,
)


@admin.register(PeriodeFormation)
class PeriodeFormationAdmin(admin.ModelAdmin):
    list_display = ['code', 'libelle', 'academic_year', 'date_debut', 'date_fin', 'statut', 'is_active']
    list_filter = ['academic_year', 'statut', 'is_active']
    search_fields = ['code', 'libelle']
    ordering = ['-date_debut']


@admin.register(ParametresPlanification)
class ParametresPlanificationAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'duree_seance_minutes', 'max_seances_par_jour', 'tolerance_capacite_pct']


@admin.register(JourFerie)
class JourFerieAdmin(admin.ModelAdmin):
    list_display = ['date', 'libelle', 'institution', 'is_active']
    list_filter = ['institution', 'is_active']
    search_fields = ['libelle']


class GroupeMembreInline(admin.TabularInline):
    model = GroupeMembre
    extra = 0
    raw_id_fields = ['student']


@admin.register(GroupePedagogique)
class GroupePedagogiqueAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'promotion', 'effectif', 'effectif_max', 'is_active']
    list_filter = ['promotion', 'is_active']
    search_fields = ['code', 'name']
    inlines = [GroupeMembreInline]


@admin.register(ProgrammePeriode)
class ProgrammePeriodeAdmin(admin.ModelAdmin):
    list_display = [
        'course', 'promotion', 'periode', 'session_kind',
        'volume_horaire_heures', 'teacher', 'is_active',
    ]
    list_filter = ['periode', 'session_kind', 'is_active']
    search_fields = ['course__code', 'course__name', 'promotion__name']
    raw_id_fields = ['course', 'promotion']
    filter_horizontal = ['groupes']


@admin.register(Seance)
class SeanceAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'heure_debut', 'heure_fin', 'course', 'promotion',
        'groupe', 'room', 'teacher', 'statut',
    ]
    list_filter = ['periode', 'statut', 'session_kind', 'date']
    search_fields = ['course__code', 'course__name', 'intitule']
    date_hierarchy = 'date'
    ordering = ['-date', 'heure_debut']


@admin.register(SeanceQRToken)
class SeanceQRTokenAdmin(admin.ModelAdmin):
    list_display = ['token', 'seance', 'is_active', 'expires_at', 'created_at']
    list_filter = ['is_active']


@admin.register(Pointage)
class PointageAdmin(admin.ModelAdmin):
    list_display = ['seance', 'role', 'personne_nom', 'statut', 'entree_at', 'sortie_at', 'duree_minutes']
    list_filter = ['role', 'statut', 'source']
    search_fields = ['student__matricule', 'teacher__employee_id']


@admin.register(PlanningRun)
class PlanningRunAdmin(admin.ModelAdmin):
    list_display = ['periode', 'mode', 'statut', 'created_at', 'finished_at']
    list_filter = ['statut', 'mode']


@admin.register(PlanningAuditLog)
class PlanningAuditLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'action', 'periode', 'seance', 'actor']
    list_filter = ['action']
    ordering = ['-created_at']
