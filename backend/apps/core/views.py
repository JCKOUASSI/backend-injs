from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.conf import settings


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'status': 'ok',
            'service': 'INJS-LMD API',
            'version': '1.0.0',
            'institution': settings.INJS_INSTITUTION_NAME,
        })


class RootView(APIView):
    """Page d'accueil API — liens vers la documentation."""
    permission_classes = [AllowAny]

    def get(self, request):
        base = request.build_absolute_uri('/').rstrip('/')
        return Response({
            'service': 'INJS-LMD API',
            'institution': settings.INJS_INSTITUTION_NAME,
            'version': '1.0.0',
            'documentation': {
                'swagger': f'{base}/api/v1/docs/',
                'redoc': f'{base}/api/v1/redoc/',
                'schema': f'{base}/api/v1/schema/',
            },
            'endpoints': {
                'health': f'{base}/api/v1/core/health/',
                'auth': f'{base}/api/v1/auth/login/',
                'admin': f'{base}/admin/',
            },
        })
