from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Registration, Event
from .serializers import RegistrationSerializer


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
