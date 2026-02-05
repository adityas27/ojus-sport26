from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Registration, Event, Team, TEAM_EVENTS
from .serializers import RegistrationSerializer, TeamCreateSerializer, TeamSerializer


# Create Registration
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_registration(request):

    serializer = RegistrationSerializer(data=request.data, context={'request': request})
    event_slug = request.data.get('event_slug')
    event = get_object_or_404(Event, slug=event_slug)

    # preventing duplicate entry
    existing_registration = Registration.objects.filter(
        student=request.user, event=event
    ).first()

    if existing_registration:
        return Response(
            {"error": "You have already registered for this event."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # disallow individual registration if user is already part of a team for this event
    from django.db.models import Q
    if Team.objects.filter(event=event).filter(Q(members=request.user) | Q(leader=request.user)).exists():
        return Response({"error": "You are part of a team for this event; individual registration is not allowed."}, status=status.HTTP_400_BAD_REQUEST)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




# List Registrations for Authenticated User
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def registration_list(request):
    registrations = Registration.objects.filter(student=request.user)
    serializer = RegistrationSerializer(registrations, many=True)
    return Response(serializer.data)


# Create Team (only for TEAM_EVENTS)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_team(request):
    serializer = TeamCreateSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        team = serializer.save()
        out = TeamSerializer(team)
        return Response(out.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# List teams for authenticated user (leader or member)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_teams(request):
    from django.db.models import Q
    teams = Team.objects.filter(Q(leader=request.user) | Q(members=request.user)).distinct()
    serializer = TeamSerializer(teams, many=True)
    return Response(serializer.data)


# List teams for an event (public)
@api_view(['GET'])
def event_teams(request, slug):
    event = get_object_or_404(Event, slug=slug)
    teams = Team.objects.filter(event=event)
    serializer = TeamSerializer(teams, many=True)
    return Response(serializer.data)


# Retrieve, Update, Delete Registration
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def registration_detail(request, pk):
    registration = get_object_or_404(
        Registration,
        pk=pk,
        student=request.user
    )

    # Retrieve
    if request.method == 'GET':
        serializer = RegistrationSerializer(registration)
        return Response(serializer.data)

    # Update
    elif request.method == 'PUT':
        serializer = RegistrationSerializer(
            registration,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save(student=request.user)
            return Response(serializer.data)

        return Response(serializer.errors, status=400)

    # Delete
    elif request.method == 'DELETE':
        registration.delete()
        return Response(status=204)


# Mark team as attended (only for is_managing users, paintball only)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_team_attended(request):
    # verify user is managing
    if not request.user.is_managing:
        return Response({"error": "Only managing volunteers can access this"}, status=status.HTTP_403_FORBIDDEN)

    leader_moodle_id = request.data.get('leader_moodle_id')
    if not leader_moodle_id:
        return Response({"error": "leader_moodle_id required"}, status=status.HTTP_400_BAD_REQUEST)

    # get paintball event
    paintball_event = get_object_or_404(Event, slug='paintball')

    # find team where leader has that moodle id
    try:
        leader = get_user_model().objects.get(moodleID=leader_moodle_id)
    except get_user_model().DoesNotExist:
        return Response({"error": f"User with Moodle ID {leader_moodle_id} not found"}, status=status.HTTP_404_NOT_FOUND)

    # find team
    team = get_object_or_404(Team, event=paintball_event, leader=leader)

    # mark team as attended
    team.attended = True
    team.save()

    # also mark all team members' individual registrations as attended (if any)
    for member in team.members.all():
        reg = Registration.objects.filter(student=member, event=paintball_event).first()
        if reg:
            reg.attended = True
            reg.save()

    return Response({"message": f"Team '{team.name}' marked as attended"}, status=status.HTTP_200_OK)


# Get teams for paintball (for attendance management)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def paintball_teams_attendance(request):
    # verify user is managing
    if not request.user.is_managing:
        return Response({"error": "Only managing volunteers can access this"}, status=status.HTTP_403_FORBIDDEN)

    try:
        paintball_event = Event.objects.get(slug='paintball')
    except Event.DoesNotExist:
        return Response({"error": "Paintball event not found"}, status=status.HTTP_404_NOT_FOUND)
    
    teams = Team.objects.filter(event=paintball_event)
    serializer = TeamSerializer(teams, many=True)
    return Response(serializer.data)
