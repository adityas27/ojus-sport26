from rest_framework import status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, Max
from rest_framework.views import APIView
from authentication.models import Student
from .models import Sport, Registration, Team, Results, TeamRequest
from .serializers import SportSerializer, RegistrationSerializer, TeamSerializer, TeamCreateSerializer, TeamRequestSerializer
from .serializers import (
    ResultsSerializer,
    ResultUpdateSerializer,
    ResultScoreAdjustSerializer,
    DepartmentLeaderboardSerializer
)
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
            return Response(serializer.data, status=status.HTTP_200_OK)
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_team(request, sport_slug):
    sport = get_object_or_404(Sport, slug=sport_slug)
    if not sport.isTeamBased:
        return Response({"error": "This sport does not support teams"}, status=status.HTTP_400_BAD_REQUEST)

    # validate registration
    if not Registration.objects.filter(student=request.user, sport=sport).exists():
        return Response({"error": "You must register for the sport before creating a team."}, status=status.HTTP_403_FORBIDDEN)

    serializer = TeamCreateSerializer(data=request.data, context={'request': request, 'sport': sport})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # create team: manager and captain default to current user unless captain_moodleID provided and valid
    name = serializer.validated_data.get('name')
    branch = request.user.branch
    captain_moodle = serializer.validated_data.get('captain_moodleID', None)

    captain_user = request.user
    if captain_moodle:
        possible = request.user.__class__.objects.filter(moodleID=captain_moodle).first()
        if possible and Registration.objects.filter(student=possible, sport=sport).exists():
            captain_user = possible

    team = Team.objects.create(name=name, branch=branch, sport=sport, manager=request.user, captain=captain_user)
    # Add the captain as a member of the team as well
    
    if captain_user:
        team.members.add(captain_user)

    resp = TeamSerializer(team, context={'request': request})
    return Response(resp.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_team(request, team_id):
    team = get_object_or_404(Team, pk=team_id)

    # Ensure user is registered for the same sport
    try:
        registration = Registration.objects.get(student=request.user, sport=team.sport)
    except Registration.DoesNotExist:
        return Response({"error": "You must register for this sport before joining a team."}, status=status.HTTP_403_FORBIDDEN)

    # Prevent duplicate requests
    if TeamRequest.objects.filter(registeration=registration, team=team).exists():
        return Response({"error": "You have already requested to join this team."}, status=status.HTTP_400_BAD_REQUEST)

    treq = TeamRequest.objects.create(student=request.user, registeration=registration, team=team)
    serializer = TeamRequestSerializer(treq, context={'request': request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_team_requests(request, team_id):
    team = get_object_or_404(Team, pk=team_id)

    # Only manager (or admins/coordinators) can view requests
    is_manager = request.user == team.manager
    is_coordinator = request.user == team.sport.primary or team.sport.secondary.filter(pk=request.user.pk).exists()
    if not (is_manager or is_coordinator or request.user.is_staff or request.user.is_superuser):
        return Response(status=status.HTTP_403_FORBIDDEN)

    requests_qs = TeamRequest.objects.filter(team=team, accepted=False, denied=False).order_by('-time')
    serializer = TeamRequestSerializer(requests_qs, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def respond_to_request(request, request_id):
    action = request.data.get('action')  # 'accept' or 'decline'
    treq = get_object_or_404(TeamRequest, pk=request_id)
    team = treq.team

    # Only team manager can accept/decline
    if request.user != team.manager:
        return Response({"error": "Only the team manager can respond to requests."}, status=status.HTTP_403_FORBIDDEN)

    if treq.accepted or treq.denied:
        return Response({"error": "This request has already been handled."}, status=status.HTTP_400_BAD_REQUEST)

    if action == 'accept':
        treq.accepted = True
        treq.denied = False
        treq.save()
        team.members.add(treq.student)
        return Response({"status": "accepted"}, status=status.HTTP_200_OK)
    elif action == 'decline':
        treq.denied = True
        treq.accepted = False
        treq.save()
        return Response({"status": "declined"}, status=status.HTTP_200_OK)
    else:
        return Response({"error": "Invalid action. Use 'accept' or 'decline'."}, status=status.HTTP_400_BAD_REQUEST)


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
    """
    Get leaderboard for a specific sport with auto-sync logic.
    Automatically creates Results entries for any new teams/players.
    """
    sport = get_object_or_404(Sport, slug=sport_slug)

    # Auto-sync logic: Add missing teams/players to Results
    if sport.isTeamBased:
        # Get all teams for this sport that don't have results yet
        existing_team_ids = Results.objects.filter(sport=sport).values_list('team_id', flat=True)
        missing_teams = Team.objects.filter(sport=sport).exclude(id__in=existing_team_ids)

        if missing_teams.exists():
            # Calculate next position (count existing results + 1)
            next_position = Results.objects.filter(sport=sport).count() + 1

            # Use get_or_create to avoid race conditions
            for team in missing_teams:
                Results.objects.get_or_create(
                    sport=sport,
                    team=team,
                    defaults={
                        'branch': team.branch,
                        'position': next_position,
                        'points': 0,
                        'score': 0
                    }
                )
                next_position += 1
    else:
        # Individual sport - sync with registrations
        existing_player_ids = Results.objects.filter(sport=sport).values_list('player_id', flat=True)
        missing_registrations = Registration.objects.filter(
            sport=sport
        ).exclude(student_id__in=existing_player_ids).select_related('student')

        if missing_registrations.exists():
            # Calculate next position
            next_position = Results.objects.filter(sport=sport).count() + 1

            # Use get_or_create to avoid race conditions
            for reg in missing_registrations:
                Results.objects.get_or_create(
                    sport=sport,
                    player=reg.student,
                    defaults={
                        'branch': reg.branch,
                        'position': next_position,
                        'points': 0,
                        'score': 0
                    }
                )
                next_position += 1

    # ✅ FIX: Sort by position (rank), NOT by score
    results = Results.objects.filter(
        sport=sport
    ).select_related('team', 'player', 'sport').order_by('position')  # ← Changed from order_by('-score')

    serializer = ResultsSerializer(results, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([IsAdminUser])
def update_sport_leaderboard(request, sport_slug):

    if not isinstance(request.data, list):
        return Response(
            {"error": "Data must be a list of results."},
            status=status.HTTP_400_BAD_REQUEST
        )

    sport = get_object_or_404(Sport, slug=sport_slug)

    # Check if sport is already finalized
    if sport.is_finalized:
        return Response(
            {"error": "Cannot update leaderboard. Sport standings are already finalized."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate incoming data
    serializer = ResultUpdateSerializer(data=request.data, many=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Create position updates mapping
    rank_updates = {item['id']: item['position'] for item in serializer.validated_data}
    result_ids = list(rank_updates.keys())

    # Fetch results to update
    results_to_update = list(
        Results.objects.filter(id__in=result_ids, sport=sport).select_for_update()
    )

    # Verify all IDs exist for this sport
    if len(results_to_update) != len(rank_updates):
        return Response(
            {"error": "Some result IDs are invalid or don't belong to this sport."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Helper function to calculate department points
    def calculate_dept_points(position):
        """Calculate department points: 3 for 1st, 2 for 2nd, 1 for 3rd"""
        if position == 1:
            return 3
        elif position == 2:
            return 2
        elif position == 3:
            return 1
        return 0

    try:
        with transaction.atomic():
            # Update positions and recalculate points
            for result in results_to_update:
                new_position = rank_updates[result.id]
                result.position = new_position
                result.points = calculate_dept_points(new_position)

            # Bulk update for better performance
            Results.objects.bulk_update(results_to_update, ['position', 'points'])

        # Return updated results
        updated_results = Results.objects.filter(
            sport=sport
        ).select_related('team', 'player', 'sport').order_by('position')

        response_serializer = ResultsSerializer(updated_results, many=True)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": f"Failed to update leaderboard: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def adjust_result_score(request, result_id):
    """
    Adjust the score of a single result entry by +1 or -1.
    Expects: {"action": "add"} or {"action": "subtract"}
    """
    try:
        result = Results.objects.select_related('sport').get(id=result_id)
    except Results.DoesNotExist:
        return Response(
            {"error": "Result not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check if sport is finalized
    if result.sport.is_finalized:
        return Response(
            {"error": "Cannot adjust score. Sport standings are finalized."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate action using serializer
    serializer = ResultScoreAdjustSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    action = serializer.validated_data['action']

    # Apply score adjustment with validation
    if action == 'add':
        if result.score >= 9999:  # Set reasonable upper limit
            return Response(
                {"error": "Score has reached maximum limit"},
                status=status.HTTP_400_BAD_REQUEST
            )
        result.score += 1
    elif action == 'subtract':
        if result.score <= 0:
            return Response(
                {"error": "Score cannot be negative"},
                status=status.HTTP_400_BAD_REQUEST
            )
        result.score -= 1

    result.save()

    return Response(
        {
            'id': result.id,
            'score': result.score,
            'message': f'Score {"increased" if action == "add" else "decreased"} successfully'
        },
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def finalize_sport_standings(request, sport_slug):
    """
    Finalize standings for a sport. Once finalized, rankings cannot be changed.
    """
    sport = get_object_or_404(Sport, slug=sport_slug)

    # Check if already finalized
    if sport.is_finalized:
        return Response(
            {"error": "Sport standings are already finalized."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if there are any results to finalize
    results_count = Results.objects.filter(sport=sport).count()
    if results_count == 0:
        return Response(
            {"error": "Cannot finalize. No results exist for this sport."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        with transaction.atomic():
            sport.is_finalized = True
            sport.save()

        return Response(
            {
                'message': f'{sport.name} standings finalized successfully.',
                'sport': sport.name,
                'is_finalized': True,
                'results_count': results_count
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to finalize standings: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def department_leaderboard(request):
    """
    Get overall department leaderboard aggregated from all finalized sports.
    Only counts points from sports that have been finalized.
    """
    # Get all finalized sports
    finalized_sport_ids = Sport.objects.filter(is_finalized=True).values_list('id', flat=True)

    if not finalized_sport_ids:
        return Response(
            {
                "message": "No sports have been finalized yet.",
                "leaderboard": []
            },
            status=status.HTTP_200_OK
        )

    # Aggregate points by branch
    leaderboard_data = Results.objects.filter(
        sport_id__in=finalized_sport_ids,
        branch__isnull=False
    ).values('branch').annotate(
        total_points=Sum('points')
    ).order_by('-total_points')

    # Add rank to each entry
    formatted_data = []
    current_rank = 1
    for entry in leaderboard_data:
        if entry['branch']:  # Skip null branches
            formatted_data.append({
                "rank": current_rank,
                "branch": entry['branch'],
                "total_points": entry['total_points'] or 0
            })
            current_rank += 1

    # Use serializer for consistent output
    serializer = DepartmentLeaderboardSerializer(formatted_data, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def reset_sport_leaderboard(request, sport_slug):
    """
    Reset all standings for a sport (only if not finalized).
    This will reset all positions to sequential order and scores to 0.
    """
    sport = get_object_or_404(Sport, slug=sport_slug)

    # Prevent reset if sport is finalized
    if sport.is_finalized:
        return Response(
            {"error": "Cannot reset. Sport standings are finalized. Unfinalize first."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        with transaction.atomic():
            # Get all results for this sport
            results = Results.objects.filter(sport=sport).order_by('id')

            # Reset positions sequentially and scores to 0
            for index, result in enumerate(results, start=1):
                result.position = index
                result.score = 0
                result.points = 0  # Will be recalculated by signal if position is 1-3

            # Bulk update
            Results.objects.bulk_update(results, ['position', 'score', 'points'])

        return Response(
            {
                "message": f"Leaderboard for {sport.name} reset successfully.",
                "sport": sport.name,
                "results_reset": results.count()
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to reset leaderboard: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def unfinalize_sport_standings(request, sport_slug):
    """
    Unfinalize a sport to allow editing rankings again.
    """
    sport = get_object_or_404(Sport, slug=sport_slug)

    if not sport.is_finalized:
        return Response(
            {"error": "Sport is not finalized."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        with transaction.atomic():
            sport.is_finalized = False
            sport.save()

        return Response(
            {
                'message': f'{sport.name} standings unfinalized. Rankings can now be edited.',
                'sport': sport.name,
                'is_finalized': False
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to unfinalize standings: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_user_admin_status(request):
    return Response({
        "is_staff": request.user.is_staff,
        "is_superuser": request.user.is_superuser
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_team_status(request, sport_slug):
    sport = get_object_or_404(Sport, slug=sport_slug)
    team = Team.objects.filter(sport=sport, members=request.user).first()
    if team:
        return Response({"in_team": True, "team": {"id": team.id, "name": team.name}})
    return Response({"in_team": False, "team": None})