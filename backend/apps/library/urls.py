from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.library.views import LibraryResourceViewSet

router = DefaultRouter()
router.register('', LibraryResourceViewSet, basename='library-resource')

urlpatterns = [path('', include(router.urls))]
