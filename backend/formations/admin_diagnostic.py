from django.contrib import admin
from django.shortcuts import render

from .volume_horaire import run_organisation_diagnostic


def volume_horaire_diagnostic_view(request):
    """Onglet admin : modules et séances ayant dépassé le volume horaire prévu."""
    depassements_only = request.GET.get('depassements_only') == '1'
    result = run_organisation_diagnostic(request, depassements_only=depassements_only)

    context = {
        **admin.site.each_context(request),
        'title': 'Diagnostique volume horaire',
        'result': result,
        'depassements_only': depassements_only,
    }
    return render(request, 'admin/formations/volume_horaire_diagnostic.html', context)


def attach_volume_diagnostic_admin_urls():
    from django.contrib import admin
    from django.urls import path

    if getattr(admin.site, '_org_volume_diag_urls', False):
        return

    original_get_urls = admin.site.get_urls

    def get_urls():
        custom = [
            path(
                'diagnostique-volume-horaire/',
                admin.site.admin_view(volume_horaire_diagnostic_view),
                name='formations_volume_horaire_diagnostic',
            ),
        ]
        return custom + original_get_urls()

    admin.site.get_urls = get_urls
    admin.site._org_volume_diag_urls = True
