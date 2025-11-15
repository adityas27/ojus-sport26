from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.views import APIView
from authentication.models import Student
from .models import Sport, Registration, Team
from .serializers import SportSerializer, RegistrationSerializer, TeamSerializer

# Sport Views
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def sport_list(request):
    if request.method == 'GET':
        sports = Sport.objects.all()
        serializer = SportSerializer(sports, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = SportSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(primary=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def sport_detail(request, pk):
    sport = get_object_or_404(Sport, pk=pk)

    if request.method == 'GET':
        serializer = SportSerializer(sport)
        return Response(serializer.data)

    if request.user != sport.primary and request.user not in sport.secondary.all():
        return Response(status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
        serializer = SportSerializer(sport, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        sport.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Registration Views
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def registration_list(request):
    if request.method == 'GET':
        coordinated_sports = Sport.objects.filter(
            Q(primary=request.user) | Q(secondary=request.user)
        )
        if coordinated_sports.exists():
            registrations = Registration.objects.filter(sport__in=coordinated_sports)
        else:
            registrations = Registration.objects.filter(student=request.user)

        serializer = RegistrationSerializer(registrations, many=True, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = RegistrationSerializer(data=request.data, context={'request': request})
        sport_slug = request.data.get('sport_slug')
        sport = get_object_or_404(Sport, slug=sport_slug)

        # preventing duplicate entry
        existing_registration = Registration.objects.filter(
            student=request.user, sport=sport
        ).first()

        if existing_registration:
            return Response(
                {"error": "You have already registered for this event."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def registration_detail(request, pk):
    registration = get_object_or_404(Registration, pk=pk)

    if (request.user != registration.student and
        request.user != registration.sport.primary and
        request.user not in registration.sport.secondary.all()):
        return Response(status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        serializer = RegistrationSerializer(registration, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = RegistrationSerializer(registration, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        registration.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Team Views
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def team_list(request):
    if request.method == 'GET':
        coordinated_sports = Sport.objects.filter(
            Q(primary=request.user) | Q(secondary=request.user)
        )
        if coordinated_sports.exists():
            teams = Team.objects.filter(sport__in=coordinated_sports)
        else:
            teams = Team.objects.filter(members=request.user)

        serializer = TeamSerializer(teams, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = TeamSerializer(data=request.data, context={'request': request})
        sport_id = request.data.get('sport_id')
        sport = get_object_or_404(Sport, pk=sport_id)
        if not sport.isTeamBased:
            return Response(
                {"error": "This sport does not support teams"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def team_detail(request, pk):
    team = get_object_or_404(Team, pk=pk)

    if (request.user not in team.members.all() and
        request.user != team.sport.primary and
        request.user not in team.sport.secondary.all() and
        request.user != team.manager and
        request.user != team.captain):
        return Response(status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        serializer = TeamSerializer(team)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = TeamSerializer(team, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        if (request.user != team.sport.primary and
            request.user not in team.sport.secondary.all() and
            request.user != team.manager):
            return Response(status=status.HTTP_403_FORBIDDEN)
        team.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

#Filter out the registrations by selecting sport
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def registration_by_sport(request, sport_slug):
    sport = get_object_or_404(Sport, slug=sport_slug)
    registrations = Registration.objects.filter(sport=sport)
    serializer = RegistrationSerializer(registrations, many=True, context={'request': request})
    return Response(serializer.data)

#Gives a user specefic registration information(self-only)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_registration_info(request):
    try:
        student = Student.objects.get(moodleID=request.user.moodleID)
    except Student.DoesNotExist:
        return Response({"error": "Student not found."}, status=404)

    registrations = Registration.objects.filter(student=student)
    serializer = RegistrationSerializer(registrations, many=True)
    return Response({
        "username": student.username,
        "moodleID": student.moodleID,
        "registrations": serializer.data
    })

#For Admin User to list all registrations
@api_view(['GET'])
@permission_classes([IsAdminUser])  # Only admins!
def admin_registration_search_by_moodle(request, moodleID):
    try:
        student = Student.objects.get(moodleID=moodleID)
    except Student.DoesNotExist:
        return Response({"error": "Student not found."}, status=404)

    registrations = Registration.objects.filter(student=student)
    serializer = RegistrationSerializer(registrations, many=True)
    return Response({
        "username": student.username,
        "moodleID": student.moodleID,
        "registrations": serializer.data
    })