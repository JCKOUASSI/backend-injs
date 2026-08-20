"""INJS-LMD URL Configuration."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from apps.core.views import RootView

urlpatterns = [
    path('', RootView.as_view(), name='root'),
    path('health/', RedirectView.as_view(url='/api/v1/core/health/', permanent=False)),
    path('admin/', admin.site.urls),
    path('metrics/', include('django_prometheus.urls')),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('api/v1/', include('injs_lmd.api_urls')),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = 'INJS-LMD Administration'
admin.site.site_title = 'INJS-LMD'
admin.site.index_title = 'Gestion académique LMD'
