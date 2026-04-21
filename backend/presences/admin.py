from django.contrib import admin
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from .models import Pointage, AuditLog


class TypePersonneFilter(admin.SimpleListFilter):
    title = "Type de personne"
    parameter_name = "type_personne"

    def lookups(self, request, model_admin):
        return (
            ("participant", "Participant"),
            ("formateur", "Formateur"),
            ("encadrant", "Encadrant"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "participant":
            return queryset.filter(participant__isnull=False)
        if value == "formateur":
            return queryset.filter(formateur__isnull=False)
        if value == "encadrant":
            return queryset.filter(encadrant__isnull=False)
        return queryset


@admin.register(Pointage)
class PointageAdmin(admin.ModelAdmin):
    list_display = [
        'remettre_en_cours_action',
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
        'encadrant__matricule', 'encadrant__first_name', 'encadrant__last_name', 'encadrant__username',
        'session__intitule', 'session__module__intitule', 'session__module__formation__formation',
    ]
    date_hierarchy = 'date_journee'
    ordering = ['-date_journee', '-timestamp_entree']
    list_select_related = [
        'participant', 'participant__secretariat',
        'formateur',
        'encadrant',
        'session', 'session__module', 'session__module__formation',
    ]
    autocomplete_fields = ['participant', 'formateur', 'encadrant', 'session']
    list_per_page = 50
    actions = ['remettre_selection_en_cours']
    fieldsets = (
        ("Personne", {
            'fields': ('participant', 'formateur', 'encadrant'),
            'description': "Un pointage concerne soit un participant, un formateur ou un encadrant.",
        }),
        ("Séance", {
            'fields': ('session', 'date_journee'),
        }),
        ("Horodatage", {
            'fields': ('timestamp_entree', 'timestamp_sortie', 'duree_presence_minutes', 'statut', 'remettre_en_cours_depuis_fiche'),
        }),
        ("Contexte technique", {
            'classes': ('collapse',),
            'fields': ('device_id', 'created_at', 'updated_at'),
        }),
    )
    readonly_fields = ['duree_presence_minutes', 'remettre_en_cours_depuis_fiche', 'created_at', 'updated_at']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:pointage_id>/remettre-en-cours/',
                self.admin_site.admin_view(self.remettre_en_cours_view),
                name='presences_pointage_remettre_en_cours',
            ),
        ]
        return custom_urls + urls

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
        if obj.encadrant_id:
            return obj.encadrant.matricule or "—"
        return "—"

    @admin.display(description="Type")
    def type_personne_display(self, obj):
        if obj.formateur_id:
            return "Formateur"
        if obj.encadrant_id:
            return "Encadrant"
        return "Participant"

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

    @admin.display(description="Action")
    def remettre_en_cours_action(self, obj):
        if not obj.timestamp_sortie:
            return "—"
        url = reverse('admin:presences_pointage_remettre_en_cours', args=[obj.pk])
        return format_html(
            '<a href="{}" style="font-weight:600;" onclick="return confirm(\'Confirmer la remise en cours de cet auditeur ?\')">Remettre en cours</a>',
            url,
        )

    @admin.display(description="Remise en cours")
    def remettre_en_cours_depuis_fiche(self, obj):
        if not obj or not obj.pk:
            return "Enregistrez d'abord le pointage."
        if not obj.timestamp_sortie:
            return "Ce pointage est deja en cours."
        url = reverse('admin:presences_pointage_remettre_en_cours', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" onclick="return confirm(\'Confirmer la remise en cours de cet auditeur ?\')">Remettre en cours</a>',
            url,
        )

    @admin.action(description="Remettre en cours les pointages selectionnes")
    def remettre_selection_en_cours(self, request, queryset):
        a_traiter = queryset.filter(timestamp_sortie__isnull=False)
        count = 0
        for pointage in a_traiter:
            pointage.timestamp_sortie = None
            pointage.duree_presence_minutes = None
            pointage.statut = Pointage.Statut.EN_COURS
            pointage.save(update_fields=['timestamp_sortie', 'duree_presence_minutes', 'statut', 'updated_at'])
            count += 1

        if count == 0:
            self.message_user(
                request,
                "Aucun pointage termine selectionne.",
                level=messages.WARNING,
            )
            return

        self.message_user(
            request,
            f"{count} pointage(s) remis en cours.",
            level=messages.SUCCESS,
        )

    def remettre_en_cours_view(self, request, pointage_id):
        pointage = self.get_object(request, pointage_id)
        if pointage is None:
            self.message_user(request, "Pointage introuvable.", level=messages.ERROR)
            return HttpResponseRedirect(reverse('admin:presences_pointage_changelist'))

        if not pointage.timestamp_sortie:
            self.message_user(
                request,
                "Ce pointage est deja en cours.",
                level=messages.WARNING,
            )
            return HttpResponseRedirect(reverse('admin:presences_pointage_changelist'))

        with transaction.atomic():
            pointage.timestamp_sortie = None
            pointage.duree_presence_minutes = None
            pointage.statut = Pointage.Statut.EN_COURS
            pointage.save(update_fields=['timestamp_sortie', 'duree_presence_minutes', 'statut', 'updated_at'])

        self.message_user(
            request,
            f"{self.personne_nom(pointage)} a ete remis(e) en cours.",
            level=messages.SUCCESS,
        )
        return HttpResponseRedirect(reverse('admin:presences_pointage_changelist'))


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
