from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Registration
from .serializers import RegistrationSerializer


# Create Registration
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_registration(request):
    serializer = RegistrationSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(student=request.user)
        return Response(serializer.data, status=201)

    return Response(serializer.errors, status=400)


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
