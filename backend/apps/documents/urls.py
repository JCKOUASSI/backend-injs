from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.documents.views import DocumentCategoryViewSet, DocumentViewSet

router = DefaultRouter()
router.register('categories', DocumentCategoryViewSet)
router.register('', DocumentViewSet, basename='document')

urlpatterns = [path('', include(router.urls))]
