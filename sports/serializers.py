from rest_framework import serializers
from .models import Sport, Registration, Team
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['moodleID', 'username', 'email']

class SportSerializer(serializers.ModelSerializer):
    primary = UserSerializer(read_only=True)
    secondary = UserSerializer(many=True, read_only=True)
    
    class Meta:
        model = Sport
        fields = ['id', 'name', 'description', 'isTeamBased', 'primary', 'secondary']

class RegistrationSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    sport = SportSerializer(read_only=True)
    sport_slug = serializers.SlugField(write_only=True)

    class Meta:
        model = Registration
        fields = [
            'id', 'student', 'sport', 'sport_slug',
            'year', 'branch', 'registered_on', 'registration_modified'
        ]
        read_only_fields = ['registered_on', 'registration_modified']

    def create(self, validated_data):
        sport_slug = validated_data.pop('sport_slug')
        try:
            sport = Sport.objects.get(slug=sport_slug)
        except Sport.DoesNotExist:
            raise serializers.ValidationError({"sport_slug": "Invalid sport slug"})
        print(self.context['request'].user)
        registration = Registration.objects.create(
            student=self.context['request'].user,
            sport=sport,
            **validated_data
        )
        return registration
class TeamSerializer(serializers.ModelSerializer):
    members = UserSerializer(many=True, read_only=True)
    sport = SportSerializer(read_only=True)
    sport_id = serializers.IntegerField(write_only=True)
    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    manager = UserSerializer(read_only=True)
    manager_id = serializers.IntegerField(write_only=True, required=False)
    captain = UserSerializer(read_only=True)
    captain_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Team
        fields = ['id', 'name', 'branch', 'sport', 'sport_id', 'members', 'member_ids', 'manager', 'manager_id', 'captain', 'captain_id']

    def create(self, validated_data):
        member_ids = validated_data.pop('member_ids', [])
        sport_id = validated_data.pop('sport_id')
        manager_id = validated_data.pop('manager_id', None)
        captain_id = validated_data.pop('captain_id', None)

        try:
            sport = Sport.objects.get(pk=sport_id)
        except Sport.DoesNotExist:
            raise serializers.ValidationError({"sport_id": "Invalid sport id"})

        request_user = None
        if self.context and self.context.get('request'):
            request_user = self.context['request'].user

        manager = None
        if manager_id:
            manager = User.objects.filter(pk=manager_id).first()
        elif request_user:
            manager = request_user

        captain = None
        if captain_id:
            captain = User.objects.filter(pk=captain_id).first()
        else:
            captain = manager

        team = Team.objects.create(sport=sport, manager=manager, captain=captain, **validated_data)

        if member_ids:
            team.members.set(User.objects.filter(pk__in=member_ids))
        return team

    def update(self, instance, validated_data):
        member_ids = validated_data.pop('member_ids', None)
        sport_id = validated_data.pop('sport_id', None)
        manager_id = validated_data.pop('manager_id', None)
        captain_id = validated_data.pop('captain_id', None)

        if sport_id is not None:
            try:
                sport = Sport.objects.get(pk=sport_id)
                instance.sport = sport
            except Sport.DoesNotExist:
                raise serializers.ValidationError({"sport_id": "Invalid sport id"})

        if manager_id is not None:
            instance.manager = User.objects.filter(pk=manager_id).first()

        if captain_id is not None:
            instance.captain = User.objects.filter(pk=captain_id).first()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if member_ids is not None:
            instance.members.set(User.objects.filter(pk__in=member_ids))
        return instance