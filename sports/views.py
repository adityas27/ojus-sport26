from rest_framework import status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, Max
from rest_framework.views import APIView
from authentication.models import Student
from .models import Sport, Registration, Team, Results
from .serializers import SportSerializer, RegistrationSerializer, TeamSerializer, ResultsSerializer, \
    ResultUpdateSerializer
from django.db import transaction


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

        # Determine if the user is a coordinator/manager
        coordinated_sports_query = Sport.objects.filter(
            Q(primary=request.user) | Q(secondary=request.user)
        )

        # Base: Start by fetching the current user's own registrations
        user_registrations = Registration.objects.filter(student=request.user)

        if coordinated_sports_query.exists() or request.user.is_staff or request.user.is_superuser:
            # If manager/admin, combine user's registrations with all registrations they coordinate

            # Get IDs of all registrations related to managed sports
            managed_registration_ids = Registration.objects.filter(
                sport__in=coordinated_sports_query
            ).values_list('id', flat=True)

            # Combine the user's registration IDs with the managed registration IDs
            all_relevant_ids = set(user_registrations.values_list('id', flat=True)) | set(managed_registration_ids)

            registrations = Registration.objects.filter(id__in=all_relevant_ids)
        else:
            # If regular user, registrations is already set to user_registrations
            registrations = user_registrations

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


# Filter out the registrations by selecting sport
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def registration_by_sport(request, sport_slug):
    # --- PERMISSION CHECK ---
    sport = get_object_or_404(Sport, slug=sport_slug)
    is_coordinator = (
            request.user == sport.primary or
            sport.secondary.filter(pk=request.user.pk).exists()
    )
    is_admin = request.user.is_staff or request.user.is_superuser

    if not is_coordinator and not is_admin:
        # If the user is not a coordinator or an admin, deny access.
        return Response(
            {"detail": "Permission denied. You must be a coordinator or admin to view all registrations for a sport."},
            status=status.HTTP_403_FORBIDDEN
        )
    # --- END PERMISSION CHECK ---

    registrations = Registration.objects.filter(sport=sport)
    serializer = RegistrationSerializer(registrations, many=True, context={'request': request})
    return Response(serializer.data)


# Gives a user specefic registration information(self-only)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_registration_info(request):
    try:
        # NOTE: Your user model should be used directly for filtering
        registrations = Registration.objects.filter(student=request.user)
    except Exception:
        # Added a generic exception handler in case the query fails unexpectedly
        return Response({"error": "Failed to fetch user registrations."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    serializer = RegistrationSerializer(registrations, many=True)
    return Response({
        "username": request.user.username,
        "moodleID": request.user.moodleID,
        "registrations": serializer.data
    })


# For Admin User to list all registrations
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


# Leaderboard Views(It consists of sport level as well as department level leaderboard and only Admin can change the standings)
@api_view(['GET'])
@permission_classes([AllowAny])
def sport_leaderboard(request, sport_slug):
    sport = get_object_or_404(Sport, slug=sport_slug)
    ''' It uses auto-sync logic, whenever a participant or team registered for a
        sport then they are automatically listed in the leaderboards '''
    if sport.isTeamBased:
        existing_team_ids = Results.objects.filter(sport=sport).values_list('team_id', flat=True)
        missing_teams = Team.objects.filter(sport=sport).exclude(id__in=existing_team_ids)
        if missing_teams.exists():
            last_pos = Results.objects.filter(sport=sport).aggregate(Max('position'))['position__max'] or 0
            new_results = []
            for i, team in enumerate(missing_teams):
                new_results.append(Results(
                    sport=sport, team=team, branch=team.branch,
                    position=last_pos + i + 1, points=0, score=0
                ))
            Results.objects.bulk_create(new_results)
    else:
        existing_player_ids = Results.objects.filter(sport=sport).values_list('player_id', flat=True)
        missing_registrations = Registration.objects.filter(sport=sport).exclude(student__in=existing_player_ids)
        if missing_registrations.exists():
            last_pos = Results.objects.filter(sport=sport).aggregate(Max('position'))['position__max'] or 0
            new_results = []
            for i, reg in enumerate(missing_registrations):
                new_results.append(Results(
                    sport=sport, player=reg.student, branch=reg.branch,
                    position=last_pos + i + 1, points=0, score=0
                ))
            Results.objects.bulk_create(new_results)

    results = Results.objects.filter(
        sport=sport,
    ).select_related('team', 'player', 'sport').order_by('position')
    serializer = ResultsSerializer(results, many=True)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([IsAdminUser])
def update_sport_leaderboard(request, sport_slug):
    if not isinstance(request.data, list):
        return Response(
            {"error": "Data must be a list of results."},
            status=status.HTTP_400_BAD_REQUEST
        )
    sport = get_object_or_404(Sport, slug=sport_slug)
    serializer = ResultUpdateSerializer(data=request.data, many=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    rank_updates = {item['id']: item['position'] for item in serializer.validated_data}
    result_ids = list(rank_updates.keys())
    results_to_update = list(Results.objects.filter(id__in=result_ids, sport=sport))
    if len(results_to_update) != len(rank_updates):
        return Response(
            {"error": "Mismatched or invalid result IDs for this sport."},
            status=status.HTTP_400_BAD_REQUEST
        )
    def calculate_dept_points(position):
        if position == 1:
            return 3
        elif position == 2:
            return 2
        elif position == 3:
            return 1
        return 0
    try:
        with transaction.atomic():
            for result in results_to_update:
                new_position = rank_updates[result.id]
                result.position = new_position
                result.points = calculate_dept_points(new_position)

            Results.objects.bulk_update(results_to_update, ['position', 'points'])

        updated_results = Results.objects.filter(sport=sport).order_by('position')
        response_serializer = ResultsSerializer(updated_results, many=True)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAdminUser])
def adjust_result_points(request, result_id):
    try:
        result = Results.objects.get(id=result_id)
    except Results.DoesNotExist:
        return Response({"error": "Result not found"}, status=status.HTTP_404_NOT_FOUND)

    action = request.data.get('action')
    if action == 'add':
        result.score += 1
    elif action == 'subtract' and result.score > 0:
        result.score -= 1
    else:
        return Response(
            {"error": "Invalid action. Use 'add' or 'subtract'."},
            status=status.HTTP_400_BAD_REQUEST
        )
    result.save()
    return Response({'id': result.id, 'score': result.score}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def finalize_sport_standings(request, sport_slug):
    sport = get_object_or_404(Sport, slug=sport_slug)
    sport.is_finalized = True
    sport.save()
    return Response({
        'message': f'{sport.name} rankings finalized.',
        'is_finalized': True
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def department_leaderboard(request):
    finalized_sport_ids = Sport.objects.filter(is_finalized=True).values_list('id', flat=True)

    leaderboard_data = Results.objects.filter(
        sport_id__in=finalized_sport_ids
    ).values('branch').annotate(
        total_points=Sum('points')
    ).order_by('-total_points')
    formatted_data = [
        {
            "branch": entry['branch'],
            "total_points": entry['total_points'] or 0
        }
        for entry in leaderboard_data if entry['branch']
    ]
    return Response(formatted_data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_user_admin_status(request):
    return Response({"is_staff": request.user.is_staff}, status=status.HTTP_200_OK)