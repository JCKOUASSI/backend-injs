from rest_framework import serializers, viewsets
from apps.documents.models import DocumentCategory, Document


class DocumentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentCategory
        fields = '__all__'


class DocumentSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Document
        fields = '__all__'
        read_only_fields = ['owner', 'signature_hash']


class DocumentCategoryViewSet(viewsets.ModelViewSet):
    queryset = DocumentCategory.objects.all()
    serializer_class = DocumentCategorySerializer
    permission_module = 'documents'


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.select_related('owner', 'category').all()
    serializer_class = DocumentSerializer
    permission_module = 'documents'

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
