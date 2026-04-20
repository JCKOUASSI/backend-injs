from django.contrib import admin
from django.utils.html import format_html
from .models import Pointage, AuditLog


class TypePersonneFilter(admin.SimpleListFilter):
    title = "Type de personne"
    parameter_name = "type_personne"

    def lookups(self, request, model_admin):
        return (
            ("participant", "Participant"),
            ("formateur", "Formateur"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "participant":
            return queryset.filter(participant__isnull=False)
        if value == "formateur":
            return queryset.filter(formateur__isnull=False)
        return queryset


@admin.register(Pointage)
class PointageAdmin(admin.ModelAdmin):
    list_display = [
        'date_journee', 'personne_nom', 'personne_numero', 'type_personne_display',
        'formation_label', 'module_label', 'session_label',
        'timestamp_entree', 'timestamp_sortie', 'duree_presence_minutes', 'statut_badge',
    ]
    list_display_links = ['personne_nom']
    list_filter = [
        'statut', 'date_journee', TypePersonneFilter,
        'session__module__formation', 'session__module',
    ]
    search_fields = [
        'participant__matricule', 'participant__nom', 'participant__prenom',
        'formateur__numerobadge', 'formateur__nom', 'formateur__prenom',
        'session__intitule', 'session__module__intitule', 'session__module__formation__formation',
    ]
    date_hierarchy = 'date_journee'
    ordering = ['-date_journee', '-timestamp_entree']
    list_select_related = [
        'participant', 'participant__secretariat',
        'formateur',
        'session', 'session__module', 'session__module__formation',
    ]
    autocomplete_fields = ['participant', 'formateur', 'session']
    list_per_page = 50
    fieldsets = (
        ("Personne", {
            'fields': ('participant', 'formateur'),
            'description': "Un pointage concerne soit un participant, soit un formateur.",
        }),
        ("Séance", {
            'fields': ('session', 'date_journee'),
        }),
        ("Horodatage", {
            'fields': ('timestamp_entree', 'timestamp_sortie', 'duree_presence_minutes', 'statut'),
        }),
        ("Contexte technique", {
            'classes': ('collapse',),
            'fields': ('device_id', 'created_at', 'updated_at'),
        }),
    )
    readonly_fields = ['duree_presence_minutes', 'created_at', 'updated_at']

    @admin.display(description="Nom")
    def personne_nom(self, obj):
        personne = obj.personne
        if not personne:
            return "—"
        nom = getattr(personne, 'nom', '')
        prenom = getattr(personne, 'prenom', '')
        return f"{nom} {prenom}".strip() or str(personne)

    @admin.display(description="Identifiant")
    def personne_numero(self, obj):
        if obj.participant_id:
            return obj.participant.matricule or "—"
        if obj.formateur_id:
            return obj.formateur.numerobadge or "—"
        return "—"

    @admin.display(description="Type")
    def type_personne_display(self, obj):
        return "Formateur" if obj.formateur_id else "Participant"

    @admin.display(description="Formation")
    def formation_label(self, obj):
        return obj.session.module.formation

    @admin.display(description="Module")
    def module_label(self, obj):
        return obj.session.module.intitule

    @admin.display(description="Séance")
    def session_label(self, obj):
        return obj.session.intitule or f"Session {obj.session.numero}"

    @admin.display(description="Statut")
    def statut_badge(self, obj):
        colors = {
            Pointage.Statut.EN_COURS: ("#e8f6f1", "#13624e"),
            Pointage.Statut.TERMINE: ("#eef6fc", "#0f4c81"),
            Pointage.Statut.FORCE_DFRC: ("#fff7e8", "#9a6700"),
            Pointage.Statut.ABSENT_NON_BADGE: ("#fdecec", "#b42318"),
        }
        bg, fg = colors.get(obj.statut, ("#f3f4f6", "#374151"))
        return format_html(
            '<span style="background:{};color:{};padding:3px 8px;border-radius:999px;font-weight:600;">{}</span>',
            bg, fg, obj.get_statut_display()
        )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp', 'action', 'acteur_label', 'cible_type',
        'cible_numero', 'cible_nom', 'formation_titre', 'ip_address',
    ]
    list_filter = ['action', 'cible_type', 'formation']
    search_fields = [
        'acteur_label', 'cible_numero', 'cible_nom',
        'formation_titre', 'ip_address', 'device_id',
    ]
    readonly_fields = [
        'timestamp', 'action', 'acteur', 'acteur_label',
        'cible_type', 'cible_numero', 'cible_nom',
        'formation', 'formation_titre', 'pointage',
        'ip_address', 'device_id', 'extra',
    ]
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
