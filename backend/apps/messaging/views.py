from rest_framework import serializers, viewsets
from apps.messaging.models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)

    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ['sender']


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    participant_names = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = '__all__'

    def get_participant_names(self, obj):
        return [u.get_full_name() for u in obj.participants.all()]


class ConversationViewSet(viewsets.ModelViewSet):
    queryset = Conversation.objects.prefetch_related('participants', 'messages').all()
    serializer_class = ConversationSerializer
    permission_module = 'messaging'

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user)


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.select_related('sender', 'conversation').all()
    serializer_class = MessageSerializer
    permission_module = 'messaging'

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)
