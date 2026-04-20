from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

admin.site.site_header = "CPFAE Administration"
admin.site.site_title = "CPFAE Admin"
admin.site.index_title = "Gestion des formations et presences"

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

    # Formations web (for QR code images, etc.)
    path('formations/', include('formations.urls')),
]
