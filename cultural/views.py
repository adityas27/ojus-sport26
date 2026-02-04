from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
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
