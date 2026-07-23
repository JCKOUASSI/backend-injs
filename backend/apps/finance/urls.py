from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.finance.views import (
    FeeTypeViewSet, StudentFeeViewSet, PaymentViewSet, PaymentProviderViewSet,
    orange_webhook, mtn_webhook, wave_webhook,
)

router = DefaultRouter()
router.register('fee-types', FeeTypeViewSet)
router.register('student-fees', StudentFeeViewSet)
router.register('payments', PaymentViewSet, basename='payment')
router.register('providers', PaymentProviderViewSet, basename='payment-provider')

urlpatterns = [
    path('', include(router.urls)),
    path('webhooks/orange/', orange_webhook, name='webhook-orange'),
    path('webhooks/mtn/', mtn_webhook, name='webhook-mtn'),
    path('webhooks/wave/', wave_webhook, name='webhook-wave'),
]
