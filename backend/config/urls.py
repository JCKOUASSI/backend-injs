from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # API endpoints
    path('api/auth/', include('authentication.urls')),
    path('api/formations/', include('formations.urls')),
    path('api/', include('presences.urls')),
    path('api/exports/', include('exports.urls')),

    # Web dashboard CPFAE
    path('dashboard/', include('dashboard.urls')),

    # QR code images publiques (hors préfixe /api/) — routes minimales uniquement
    path('formations/', include('formations.qr_urls')),
]
