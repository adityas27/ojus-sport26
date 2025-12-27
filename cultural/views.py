from django.shortcuts import render, get_object_or_404
from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Registration, Event
from .serializers import RegistrationSerializer

# Create your views here.

class RegistrationCreateView(generics.CreateAPIView):
    queryset = Registration.objects.all()
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

# List all registrations for the authenticated user
class RegistrationListView(generics.ListAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Registration.objects.filter(student=self.request.user)

# Registration detail view (retrieve, update, delete)
class RegistrationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Registration.objects.all()
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only allow users to access their own registrations
        return Registration.objects.filter(student=self.request.user)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_registration(request):
    serializer = RegistrationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(student=request.user)
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def registration_list(request):
    registrations = Registration.objects.filter(student=request.user)
    serializer = RegistrationSerializer(registrations, many=True)
    return Response(serializer.data)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def registration_detail(request, pk):
    registration = get_object_or_404(Registration, pk=pk, student=request.user)
    if request.method == 'GET':
        serializer = RegistrationSerializer(registration)
        return Response(serializer.data)
    elif request.method == 'PUT':
        serializer = RegistrationSerializer(registration, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(student=request.user)
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    elif request.method == 'DELETE':
        registration.delete()
        return Response(status=204)
