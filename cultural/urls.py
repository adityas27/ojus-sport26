from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.create_registration, name='cultural-register'),
    path('registrations/', views.registration_list, name='cultural-registration-list'),
    path('registrations/<int:pk>/', views.registration_detail, name='cultural-registration-detail'),
]