from django.contrib import admin
from .models import Formation, Participant, Secretariat, ModuleParticipant, ModuleFormateur, Formateur, QRToken, RefFormation, RefModule, RefSite, RefBatiment, RefSalle, RefCategorie, RefGrade, Module, SessionModule
FormationFormateur = ModuleFormateur


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
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['matricule', 'nom', 'prenom', 'email', 'categorie', 'grade', 'secretariat']
    search_fields = ['matricule', 'nom', 'prenom', 'email']
    list_filter = ['categorie', 'secretariat']
    autocomplete_fields = ['secretariat']


@admin.register(ModuleParticipant)
class ModuleParticipantAdmin(admin.ModelAdmin):
    list_display = ['module', 'participant', 'inscrit_le']
    list_filter = ['module__formation']


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['intitule', 'formation', 'grade', 'groupe', 'statut', 'formateur', 'secretariat', 'date_debut', 'date_fin']
    search_fields = ['intitule', 'formation__formation', 'grade', 'groupe']
    list_filter = ['statut', 'secretariat', 'formation']
    autocomplete_fields = ['formateur', 'secretariat']
    inlines = [ModuleParticipantInline, ModuleFormateurInline]


@admin.register(SessionModule)
class SessionModuleAdmin(admin.ModelAdmin):
    list_display = ['date_journee', 'numero', 'intitule', 'module', 'formation', 'heure_debut_prevue', 'heure_fin_prevue']
    list_filter = ['date_journee', 'module__formation', 'module']
    search_fields = ['intitule', 'module__intitule', 'module__formation__formation']
    autocomplete_fields = ['module', 'demarree_par']

    @admin.display(description='Formation')
    def formation(self, obj):
        return obj.module.formation


@admin.register(Formateur)
class FormateurAdmin(admin.ModelAdmin):
    list_display = ['numerobadge', 'nom', 'prenom', 'specialite', 'email', 'organisation']
    search_fields = ['numerobadge', 'nom', 'prenom', 'email']
    list_filter = ['organisation', 'secretariats']
    filter_horizontal = ['secretariats']


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
    list_display = ['nom', 'actif']
    search_fields = ['nom']
    list_filter = ['actif']
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
