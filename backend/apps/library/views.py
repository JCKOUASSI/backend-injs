from rest_framework import serializers, viewsets
from django_filters.rest_framework import DjangoFilterBackend
from apps.library.models import LibraryResource


class LibraryResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LibraryResource
        fields = '__all__'


class LibraryResourceViewSet(viewsets.ModelViewSet):
    queryset = LibraryResource.objects.all()
    serializer_class = LibraryResourceSerializer
    permission_module = 'library'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['resource_type', 'department', 'is_public']
    search_fields = ['title', 'author', 'isbn']
