from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from config.views import api_root
from config.static_views import service_worker, favicon

admin.site.site_header = "SYGEP-CPFAE Administration"
admin.site.site_title = "SYGEP-CPFAE Admin"
admin.site.index_title = "Gestion des formations et présences"

urlpatterns = [
    # Racine → page d'accueil API
    path('', api_root, name='root'),

    # PWA badge + favicon (évite les 404 dans les logs navigateur)
    path('sw.js', service_worker, name='service-worker'),
    path('favicon.ico', favicon, name='favicon'),

    # Admin
    path('admin/', admin.site.urls),

    # API docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # API endpoints
    path('api/', api_root, name='api-root'),
    path('api/auth/', include('authentication.urls')),
    path('api/formations/', include('formations.urls')),
    path('api/', include('presences.urls')),
    path('api/exports/', include('exports.urls')),
    path('api/statistiques/', include('statistiques.urls')),
    path('api/evaluations/', include('suiviEvaluation.urls')),

    # Web dashboard CPFAE
    path('dashboard/', include('dashboard.urls')),

    # QR code images publiques (hors préfixe /api/) — routes minimales uniquement
    path('formations/', include('formations.qr_urls')),
]
