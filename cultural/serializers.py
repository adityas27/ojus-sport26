from rest_framework import serializers
from .models import Registration, Event

class RegistrationSerializer(serializers.ModelSerializer):
    # Accept event_slug from client and derive event & student server-side
    # Also expose event.slug in responses as `event_slug_display` and event name as `event_name`
    event_slug = serializers.CharField(write_only=True, required=True)
    event_slug_display = serializers.CharField(source='event.slug', read_only=True)
    event_name = serializers.CharField(source='event.name', read_only=True)
    student = serializers.PrimaryKeyRelatedField(read_only=True)
    event = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Registration
        fields = ['id', 'student', 'event', 'year', 'registered_on', 'event_slug', 'event_slug_display', 'event_name']
        read_only_fields = ('id', 'student', 'event', 'registered_on', 'event_slug_display', 'event_name')
    
    def create(self, validated_data):
        event_slug = validated_data.pop('event_slug')
        user = self.context['request'].user
        try:
            event = Event.objects.get(slug=event_slug)
        except Event.DoesNotExist:
            raise serializers.ValidationError({"event_slug": "Invalid event slug"})

        registration = Registration.objects.create(
            student=user,
            year=user.year,
            event=event,
            **validated_data
        )
        return registration
        