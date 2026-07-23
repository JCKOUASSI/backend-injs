from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.admissions.views import AdmissionCampaignViewSet, PreRegistrationViewSet

router = DefaultRouter()
router.register('campaigns', AdmissionCampaignViewSet)
router.register('pre-registrations', PreRegistrationViewSet)

urlpatterns = [path('', include(router.urls))]
