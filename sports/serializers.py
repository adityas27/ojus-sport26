from rest_framework import serializers
from .models import Sport, Registration, Team, Results
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['moodleID', 'username', 'email']


class SportSerializer(serializers.ModelSerializer):
    primary = UserSerializer(read_only=True)
    secondary = UserSerializer(many=True, read_only=True)
    participants_count = serializers.SerializerMethodField()

    class Meta:
        model = Sport
        fields = ['slug','id', 'name', 'description', 'isTeamBased', 'primary', 'secondary', 'participants_count']

    def get_participants_count(self, obj):
        return obj.registration_set.count()


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
        fields = [
            'id', 'name', 'branch', 'sport', 'sport_id',
            'members', 'member_ids', 'manager', 'manager_id',
            'captain', 'captain_id'
        ]

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

        team = Team.objects.create(
            sport=sport,
            manager=manager,
            captain=captain,
            **validated_data
        )

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


# ========================================
# LEADERBOARD SERIALIZERS
# ========================================

class ResultsSerializer(serializers.ModelSerializer):
    """Serializer for displaying leaderboard results"""
    display_name = serializers.SerializerMethodField()
    sport_name = serializers.CharField(source='sport.name', read_only=True)
    sport_slug = serializers.CharField(source='sport.slug', read_only=True)
    sport_is_finalized = serializers.BooleanField(source='sport.is_finalized', read_only=True)
    team_id = serializers.IntegerField(source='team.id', read_only=True, allow_null=True)
    player_id = serializers.IntegerField(source='player.id', read_only=True, allow_null=True)

    class Meta:
        model = Results
        fields = [
            'id', 'position', 'score', 'points', 'branch',
            'display_name', 'sport_name', 'sport_slug', 'sport_is_finalized',
            'team_id', 'player_id', 'created_at', 'updated_at'
        ]
        read_only_fields = ['points', 'created_at', 'updated_at']

    def get_display_name(self, obj):
        """Get the display name for the result (team or player)"""
        if obj.team:
            return obj.team.name
        elif obj.player:
            return obj.player.username
        return "Unknown"


class ResultUpdateSerializer(serializers.Serializer):
    """Serializer for bulk updating result positions"""
    id = serializers.IntegerField()
    position = serializers.IntegerField(min_value=1)

    def validate_position(self, value):
        """Ensure position is a positive integer"""
        if value < 1:
            raise serializers.ValidationError("Position must be at least 1")
        return value


class ResultScoreAdjustSerializer(serializers.Serializer):
    """Serializer for adjusting individual result scores (+1 or -1)"""
    action = serializers.ChoiceField(choices=['add', 'subtract'])

    def validate_action(self, value):
        """Validate action is either 'add' or 'subtract'"""
        if value not in ['add', 'subtract']:
            raise serializers.ValidationError("Action must be 'add' or 'subtract'")
        return value


class DepartmentLeaderboardSerializer(serializers.Serializer):
    """Serializer for department-level leaderboard aggregation"""
    branch = serializers.CharField()
    branch_display = serializers.SerializerMethodField()
    total_points = serializers.IntegerField()
    rank = serializers.IntegerField(required=False)

    def get_branch_display(self, obj):
        """Get the full branch name for display"""
        from .models import BRANCH_CHOICES
        branch_dict = dict(BRANCH_CHOICES)
        return branch_dict.get(obj['branch'], obj['branch'])

class ResultCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new results (admin only)"""
    sport_slug = serializers.SlugRelatedField(
        source='sport',
        slug_field='slug',
        queryset=Sport.objects.all(),
        write_only=True
    )
    team_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    player_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Results
        fields = [
            'id', 'sport_slug', 'team_id', 'player_id',
            'position', 'score', 'branch'
        ]
        read_only_fields = ['points']

    def validate(self, data):
        """Validate that either team or player is provided, but not both"""
        team_id = data.get('team_id')
        player_id = data.get('player_id')

        if not team_id and not player_id:
            raise serializers.ValidationError("You must provide either team_id or player_id")

        if team_id and player_id:
            raise serializers.ValidationError("Provide only one: team_id OR player_id, not both")

        # Validate sport type matches team/player
        sport = data.get('sport')
        if team_id and not sport.isTeamBased:
            raise serializers.ValidationError("This sport does not support teams")
        if player_id and sport.isTeamBased:
            raise serializers.ValidationError("This sport requires teams, not individual players")

        return data

    def create(self, validated_data):
        """Create a new result entry"""
        team_id = validated_data.pop('team_id', None)
        player_id = validated_data.pop('player_id', None)

        team = None
        player = None

        if team_id:
            try:
                team = Team.objects.get(pk=team_id)
            except Team.DoesNotExist:
                raise serializers.ValidationError({"team_id": "Invalid team id"})

        if player_id:
            try:
                player = User.objects.get(pk=player_id)
            except User.DoesNotExist:
                raise serializers.ValidationError({"player_id": "Invalid player id"})

        result = Results.objects.create(
            team=team,
            player=player,
            **validated_data
        )
        return result