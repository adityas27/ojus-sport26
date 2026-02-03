import json
import os
from django.db import transaction, IntegrityError, connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from .models import Bookings
from .utils import get_remaining_seats, TOTAL_CAPACITY, set_remaining_cache
from django.contrib.auth import get_user_model

User = get_user_model()

def _broadcast_remaining(remaining):
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)('booking_updates', {
            'type': 'count.update',
            'remaining': remaining,
        })
    except Exception:
        # Swallow channel errors; booking correctness relies on DB
        pass
    # update redis cache if possible (best-effort)
    try:
        set_remaining_cache(remaining)
    except Exception:
        pass


def _acquire_db_lock():
    """Acquire a transactional advisory lock on Postgres to serialize booking operations.

    Falls back to no-op on non-Postgres DBs.
    """
    try:
        with connection.cursor() as cursor:
            # use a constant key; this call blocks until lock acquired for transaction
            cursor.execute('SELECT pg_advisory_xact_lock(%s);', [42])
    except Exception:
        # Non-Postgres DB or advisory locks unavailable: continue without crash.
        pass


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def book_seat(request):
    student = request.user
    year = request.data.get('year')

    with transaction.atomic():
        # serialize critical section
        _acquire_db_lock()

        # ensure student hasn't already booked
        if Bookings.objects.filter(student=student).exists():
            return JsonResponse({'detail': 'Student already booked.'}, status=status.HTTP_400_BAD_REQUEST)

        # compute remaining from DB truth
        current_count = Bookings.objects.count()
        remaining = TOTAL_CAPACITY - current_count
        if remaining <= 0:
            return JsonResponse({'detail': 'Capacity full.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking = Bookings.objects.create(student=student, year=year or '')
        except IntegrityError:
            return JsonResponse({'detail': 'Booking conflict.'}, status=status.HTTP_400_BAD_REQUEST)

        # new remaining
        new_remaining = TOTAL_CAPACITY - Bookings.objects.count()

    # broadcast outside transaction
    _broadcast_remaining(new_remaining)

    return JsonResponse({'success': True, 'remaining': new_remaining}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_booking(request):
    student = request.user

    with transaction.atomic():
        _acquire_db_lock()
        booking = Bookings.objects.filter(student=student).first()
        if not booking:
            return JsonResponse({'detail': 'No booking found.'}, status=status.HTTP_404_NOT_FOUND)
        booking.delete()
        new_remaining = TOTAL_CAPACITY - Bookings.objects.count()

    _broadcast_remaining(new_remaining)
    return JsonResponse({'success': True, 'remaining': new_remaining}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_remaining(request):
    try:
        remaining = get_remaining_seats()
    except Exception:
        # fallback to DB
        remaining = TOTAL_CAPACITY - Bookings.objects.count()
    return JsonResponse({'remaining': remaining})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_booking(request):
    student = request.user
    print(request)
    booking = Bookings.objects.filter(student=student).first()
    if not booking:
        return JsonResponse({'booking': None}, status=status.HTTP_404_NOT_FOUND)
    url = "127.0.0.1:8000"
    data = {
        'moodleID': student.moodleID,
        'first_name': student.first_name,
        'last_name': student.last_name,
        'year': student.year,
        'registered_on': booking.registered_on.isoformat(),
        "url":f"https://{url}/booking/mark-present/{student.moodleID}",
    }
    return JsonResponse({'booking': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_booking_by_moodle(request, moodleID):
    """Return booking details for a given student's moodleID.

    Anyone authenticated can view the ticket; response includes a `can_mark`
    flag indicating whether the current user can mark attendance (is_staff/superuser).
    """
    User = get_user_model()
    student = get_object_or_404(User, pk=moodleID)
    booking = Bookings.objects.filter(student=student).first()
    if not booking:
        return JsonResponse({'detail': 'No booking found.'}, status=status.HTTP_404_NOT_FOUND)

    data = {
        'student': {
            'username': student.username,
            'moodleID': student.moodleID,
            'year': student.year,
            'branch': getattr(student, 'branch', None),
        },
        'registered_on': booking.registered_on.isoformat(),
        'attended': booking.attended,
        'can_mark': bool(request.user.is_staff or request.user.is_superuser),
    }
    return JsonResponse(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_present(request, moodleID):
    """Mark a booking as attended. Only users with staff/superuser may do this."""
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

    User = get_user_model()
    student = get_object_or_404(User, pk=moodleID)
    booking = Bookings.objects.filter(student=student).first()
    if not booking:
        return JsonResponse({'detail': 'No booking found.'}, status=status.HTTP_404_NOT_FOUND)

    booking.attended = True
    booking.save()

    return JsonResponse({'success': True, 'attended': True})
