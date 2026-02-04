from rest_framework import serializers
from .models import Registration, Event, Team, TEAM_EVENTS
from django.contrib.auth import get_user_model

User = get_user_model()

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


class TeamCreateSerializer(serializers.Serializer):
    event_slug = serializers.CharField(write_only=True)
    name = serializers.CharField(max_length=100)
    member_moodle_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    secondary_contact_number = serializers.CharField(max_length=10, required=False, allow_blank=True)

    def validate_event_slug(self, value):
        try:
            event = Event.objects.get(slug=value)
        except Event.DoesNotExist:
            raise serializers.ValidationError("Invalid event slug")
        if value not in TEAM_EVENTS:
            raise serializers.ValidationError("Team registration is not allowed for this event")
        return value

    def validate_member_moodle_ids(self, value):
        # remove duplicates while preserving order
        seen = set()
        ids = []
        for v in value:
            if v in seen:
                continue
            seen.add(v)
            ids.append(v)
        return ids

    def create(self, validated_data):
        event = Event.objects.get(slug=validated_data.pop('event_slug'))
        name = validated_data.pop('name')
        member_ids = validated_data.pop('member_moodle_ids', [])
        secondary_contact = validated_data.pop('secondary_contact_number', '')

        leader = self.context['request'].user

        # resolve members
        members = []
        for mid in member_ids:
            try:
                user = User.objects.get(moodleID=mid)
            except User.DoesNotExist:
                raise serializers.ValidationError({"member_moodle_ids": f"Moodle ID {mid} not found"})
            members.append(user)

        # include leader as a member implicitly
        if leader not in members:
            members.append(leader)

        # ensure no member is in another team for the same event
        from django.db.models import Q
        for member in members:
            conflict = Team.objects.filter(event=event).filter(Q(members=member) | Q(leader=member)).exists()
            if conflict:
                raise serializers.ValidationError({"member_moodle_ids": f"Moodle ID {member.moodleID} is already in another team for this event"})
            # also ensure the member does not have an individual registration for this event
            if Registration.objects.filter(event=event, student=member).exists():
                raise serializers.ValidationError({"member_moodle_ids": f"Moodle ID {member.moodleID} already has an individual registration for this event"})

        # ensure leader doesn't have an individual registration
        if Registration.objects.filter(event=event, student=leader).exists():
            raise serializers.ValidationError({"non_field_errors": "You already have an individual registration for this event"})

        team = Team.objects.create(event=event, name=name, leader=leader, secondary_contact_number=secondary_contact)
        team.members.set(members)
        return team


class TeamSerializer(serializers.ModelSerializer):
    event_slug = serializers.CharField(source='event.slug', read_only=True)
    leader = serializers.IntegerField(source='leader.moodleID', read_only=True)
    members = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ['id', 'event_slug', 'name', 'leader', 'members', 'secondary_contact_number', 'created_on']

    def get_members(self, obj):
        return [u.moodleID for u in obj.members.all()]
        