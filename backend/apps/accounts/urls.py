from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from apps.accounts.views import (
    CustomTokenObtainPairView, MFAVerifyView, MeView,
    UserViewSet, GroupViewSet, PermissionViewSet, AuditLogViewSet,
)

router = DefaultRouter()
router.register('users', UserViewSet, basename='user')
router.register('groups', GroupViewSet, basename='group')
router.register('permissions', PermissionViewSet, basename='permission')
router.register('audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('mfa/verify/', MFAVerifyView.as_view(), name='mfa_verify'),
    path('me/', MeView.as_view(), name='me'),
    path('', include(router.urls)),
]
