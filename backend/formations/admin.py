from django.contrib import admin
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html
from .models import Formation, Participant, Secretariat, ModuleParticipant, ModuleFormateur, Formateur, QRToken, RefFormation, RefModule, RefSite, RefBatiment, RefSalle, RefCategorie, RefGrade, Module, SessionModule
from presences.models import AuditLog, _log_audit
FormationFormateur = ModuleFormateur


class AuditLogAdminMixin:
    """Mixin à ajouter à tout ModelAdmin pour tracer les actions dans l'AuditLog."""
    audit_action_create = None
    audit_action_update = None
    audit_action_delete = None

    def _audit_cible(self, obj):
        """Retourne (cible_type, cible_numero, cible_nom) selon le modèle."""
        return ('', str(obj.pk), str(obj))

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        action = self.audit_action_update if change else self.audit_action_create
        if action:
            cible_type, cible_numero, cible_nom = self._audit_cible(obj)
            extra = {'via_admin': True}
            if change and form and hasattr(form, 'changed_data'):
                extra['champs_modifies'] = form.changed_data
            _log_audit(
                action=action,
                request=request,
                cible_type=cible_type,
                cible_numero=cible_numero,
                cible_nom=cible_nom,
                extra=extra,
            )

    def delete_model(self, request, obj):
        if self.audit_action_delete:
            cible_type, cible_numero, cible_nom = self._audit_cible(obj)
            _log_audit(
                action=self.audit_action_delete,
                request=request,
                cible_type=cible_type,
                cible_numero=cible_numero,
                cible_nom=cible_nom,
                extra={'via_admin': True},
            )
        super().delete_model(request, obj)


def _reactiver_session_et_qr(session):
    session.terminee_le = None
    session.save(update_fields=['terminee_le'])

    module = session.module
    if module.statut in ('TERMINEE', 'SUSPENDUE', 'PLANIFIEE'):
        module.statut = 'EN_COURS'
        module.save(update_fields=['statut'])

    qr = QRToken.objects.filter(session=session).order_by('-created_at').first()
    if qr and not qr.actif:
        qr.actif = True
        qr.save(update_fields=['actif'])


@admin.register(Secretariat)
class SecretariatAdmin(admin.ModelAdmin):
    list_display = ['numero', 'nom', 'responsable', 'nb_participants']
    search_fields = ['numero', 'nom']
    list_filter = ['responsable']


class ModuleParticipantInline(admin.TabularInline):
    model = ModuleParticipant
    extra = 1
    autocomplete_fields = ['participant']


class ModuleFormateurInline(admin.TabularInline):
    model = ModuleFormateur
    extra = 1
    autocomplete_fields = ['formateur']


@admin.register(Formation)
class FormationAdmin(admin.ModelAdmin):
    list_display = ['formation', 'numero_formation', 'created_at']
    list_filter = []
    search_fields = ['formation']
    inlines = []


@admin.register(Participant)
class ParticipantAdmin(AuditLogAdminMixin, admin.ModelAdmin):
    audit_action_create = AuditLog.Action.PARTICIPANT_CREATE
    audit_action_update = AuditLog.Action.PARTICIPANT_UPDATE
    audit_action_delete = AuditLog.Action.PARTICIPANT_DELETE
    list_display = ['matricule', 'nom', 'prenom', 'email', 'categorie', 'grade', 'secretariat']
    search_fields = ['matricule', 'nom', 'prenom', 'email']
    list_filter = ['categorie', 'secretariat']
    autocomplete_fields = ['secretariat']

    def _audit_cible(self, obj):
        return ('participant', obj.matricule or str(obj.pk), f"{obj.nom} {obj.prenom}".strip())


@admin.register(ModuleParticipant)
class ModuleParticipantAdmin(admin.ModelAdmin):
    list_display = ['module', 'participant', 'inscrit_le']
    list_filter = ['module__formation']


@admin.register(Module)
class ModuleAdmin(AuditLogAdminMixin, admin.ModelAdmin):
    audit_action_create = AuditLog.Action.FORMATION_CREATE
    audit_action_update = AuditLog.Action.FORMATION_UPDATE
    audit_action_delete = AuditLog.Action.FORMATION_DELETE
    list_display = ['intitule', 'formation', 'grade', 'groupe', 'statut', 'formateur', 'secretariat', 'date_debut', 'date_fin', 'sessions_button', 'reactiver_derniere_seance_button']
    search_fields = ['intitule', 'formation__formation', 'grade', 'groupe']
    list_filter = ['statut', 'secretariat', 'formation']
    autocomplete_fields = ['formateur', 'secretariat', 'site']
    inlines = [ModuleParticipantInline, ModuleFormateurInline]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/sessions/',
                self.admin_site.admin_view(self.sessions_module_view),
                name='formations_module_sessions',
            ),
            path(
                '<path:object_id>/reactiver-derniere-seance/',
                self.admin_site.admin_view(self.reactiver_derniere_seance_view),
                name='formations_module_reactiver_derniere_seance',
            ),
        ]
        return custom_urls + urls

    @admin.display(description='Séances')
    def sessions_button(self, obj):
        count = obj.sessions.count()
        url = reverse('admin:formations_module_sessions', args=[obj.pk])
        label = f'Voir {count} séance(s)'
        return format_html('<a class="button" href="{}">{}</a>', url, label)

    def sessions_module_view(self, request, object_id):
        module = self.get_object(request, object_id)
        if module is None:
            self.message_user(request, "Module introuvable.", level='error')
            return HttpResponseRedirect(reverse('admin:formations_module_changelist'))

        sessions = list(
            module.sessions.select_related('module')
            .order_by('-date_journee', '-numero')
        )
        sessions_rows = []
        for session in sessions:
            etat = 'Planifiée'
            if session.est_en_cours:
                etat = 'En cours'
            elif session.est_terminee:
                etat = 'Terminée'
            sessions_rows.append({
                'id': session.id,
                'date_journee': session.date_journee,
                'numero': session.numero,
                'intitule': session.intitule or f"Séance {session.numero}",
                'etat': etat,
                'demarree_le': session.demarree_le,
                'terminee_le': session.terminee_le,
                'change_url': reverse('admin:formations_sessionmodule_change', args=[session.pk]),
                'reactiver_url': (
                    reverse('admin:formations_sessionmodule_reactiver', args=[session.pk])
                    if session.demarree_le and session.terminee_le
                    else None
                ),
            })

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'title': f"Séances du module : {module.intitule}",
            'module_obj': module,
            'sessions_rows': sessions_rows,
            'back_url': reverse('admin:formations_module_changelist'),
        }
        return render(request, 'admin/formations/module/sessions_list.html', context)

    @admin.display(description='Réactiver séance')
    def reactiver_derniere_seance_button(self, obj):
        has_terminated = obj.sessions.filter(
            demarree_le__isnull=False,
            terminee_le__isnull=False,
        ).exists()
        if not has_terminated:
            return '-'
        url = reverse('admin:formations_module_reactiver_derniere_seance', args=[obj.pk])
        return format_html('<a class="button" href="{}">Réactiver dernière séance</a>', url)

    def reactiver_derniere_seance_view(self, request, object_id):
        module = self.get_object(request, object_id)
        if module is None:
            self.message_user(request, "Module introuvable.", level='error')
            return HttpResponseRedirect(reverse('admin:formations_module_changelist'))

        session = module.sessions.filter(
            demarree_le__isnull=False,
            terminee_le__isnull=False,
        ).order_by('-terminee_le').first()
        if session is None:
            self.message_user(request, "Aucune séance terminée à réactiver pour ce module.", level='warning')
            return HttpResponseRedirect(reverse('admin:formations_module_changelist'))

        _reactiver_session_et_qr(session)
        self.message_user(
            request,
            f"Dernière séance réactivée pour le module « {module.intitule} ».",
        )
        return HttpResponseRedirect(reverse('admin:formations_module_changelist'))


@admin.register(SessionModule)
class SessionModuleAdmin(AuditLogAdminMixin, admin.ModelAdmin):
    audit_action_create = AuditLog.Action.SEANCE_CREATE
    audit_action_update = AuditLog.Action.SEANCE_CREATE  # pas d'action UPDATE spécifique
    audit_action_delete = AuditLog.Action.SEANCE_DELETE
    list_display = ['date_journee', 'numero', 'intitule', 'module', 'formation', 'heure_debut_prevue', 'heure_fin_prevue', 'demarree_le', 'terminee_le', 'reactiver_button']
    list_filter = ['date_journee', 'module__formation', 'module']
    search_fields = ['intitule', 'module__intitule', 'module__formation__formation']
    autocomplete_fields = ['module', 'demarree_par']
    actions = ['reactiver_sessions']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/reactiver/',
                self.admin_site.admin_view(self.reactiver_view),
                name='formations_sessionmodule_reactiver',
            ),
        ]
        return custom_urls + urls

    @admin.display(description='Formation')
    def formation(self, obj):
        return obj.module.formation

    @admin.display(description='Action')
    def reactiver_button(self, obj):
        if not obj.demarree_le or not obj.terminee_le:
            return '-'
        url = reverse('admin:formations_sessionmodule_reactiver', args=[obj.pk])
        return format_html('<a class="button" href="{}">Réactiver</a>', url)

    def reactiver_view(self, request, object_id):
        session = self.get_object(request, object_id)
        if session is None:
            self.message_user(request, "Séance introuvable.", level='error')
            return HttpResponseRedirect(reverse('admin:formations_sessionmodule_changelist'))

        if not session.demarree_le or not session.terminee_le:
            self.message_user(
                request,
                "Cette séance n'est pas terminée, aucune réactivation nécessaire.",
                level='warning',
            )
            return HttpResponseRedirect(reverse('admin:formations_sessionmodule_changelist'))

        self._reactiver_une_session(session)
        self.message_user(request, "Séance réactivée avec succès.")
        return HttpResponseRedirect(reverse('admin:formations_sessionmodule_changelist'))

    def _reactiver_une_session(self, session):
        _reactiver_session_et_qr(session)

    @admin.action(description='Réactiver les séances sélectionnées')
    def reactiver_sessions(self, request, queryset):
        reactivated = 0
        skipped = 0

        for session in queryset.select_related('module'):
            # On ne réactive que des séances déjà démarrées puis terminées.
            if not session.demarree_le or not session.terminee_le:
                skipped += 1
                continue

            self._reactiver_une_session(session)
            reactivated += 1

        if reactivated:
            self.message_user(
                request,
                f"{reactivated} séance(s) réactivée(s).",
            )
        if skipped:
            self.message_user(
                request,
                f"{skipped} séance(s) ignorée(s) (non terminées ou jamais démarrées).",
                level='warning',
            )


@admin.register(Formateur)
class FormateurAdmin(AuditLogAdminMixin, admin.ModelAdmin):
    audit_action_create = AuditLog.Action.FORMATEUR_CREATE
    audit_action_update = AuditLog.Action.FORMATEUR_UPDATE
    audit_action_delete = AuditLog.Action.FORMATEUR_DELETE
    list_display = ['numerobadge', 'nom', 'prenom', 'specialite', 'email', 'organisation']
    search_fields = ['numerobadge', 'nom', 'prenom', 'email']
    list_filter = ['organisation', 'secretariats']
    filter_horizontal = ['secretariats']

    def _audit_cible(self, obj):
        return ('formateur', obj.numerobadge or str(obj.pk), f"{obj.nom} {obj.prenom}".strip())


@admin.register(ModuleFormateur)
class ModuleFormateurAdmin(admin.ModelAdmin):
    list_display = ['module', 'formateur', 'inscrit_le']
    list_filter = ['module__formation']


@admin.register(QRToken)
class QRTokenAdmin(admin.ModelAdmin):
    list_display = ['session', 'token', 'actif', 'expire_at', 'genere_par']
    list_filter = ['actif', 'session__module__formation']
    readonly_fields = ['token']


@admin.register(RefCategorie)
class RefCategorieAdmin(admin.ModelAdmin):
    list_display = ['libelle', 'actif']
    search_fields = ['libelle']
    list_filter = ['actif']


@admin.register(RefGrade)
class RefGradeAdmin(admin.ModelAdmin):
    list_display = ['libelle', 'categorie', 'actif']
    search_fields = ['libelle']
    list_filter = ['categorie', 'actif']


@admin.register(RefFormation)
class RefFormationAdmin(admin.ModelAdmin):
    list_display = ['intitule', 'actif']
    search_fields = ['intitule']
    list_filter = ['actif']


@admin.register(RefModule)
class RefModuleAdmin(admin.ModelAdmin):
    list_display = ['intitule', 'formation', 'volume_horaire', 'actif']
    search_fields = ['intitule']
    list_filter = ['actif', 'formation']
    autocomplete_fields = ['formation']


class RefBatimentInline(admin.TabularInline):
    model = RefBatiment
    extra = 1


class RefSalleInline(admin.TabularInline):
    model = RefSalle
    extra = 1


@admin.register(RefSite)
class RefSiteAdmin(admin.ModelAdmin):
    list_display = ['nom', 'actif', 'geofence_latitude', 'geofence_longitude', 'geofence_rayon_m']
    search_fields = ['nom']
    list_filter = ['actif']
    fields = [
        'nom', 'actif',
        'geofence_latitude', 'geofence_longitude', 'geofence_rayon_m',
    ]
    inlines = [RefBatimentInline, RefSalleInline]


@admin.register(RefBatiment)
class RefBatimentAdmin(admin.ModelAdmin):
    list_display = ['nom', 'site', 'actif']
    search_fields = ['nom']
    list_filter = ['site', 'actif']


@admin.register(RefSalle)
class RefSalleAdmin(admin.ModelAdmin):
    list_display = ['nom', 'site', 'batiment', 'actif']
    search_fields = ['nom']
    list_filter = ['site', 'batiment', 'actif']
