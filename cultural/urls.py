from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.create_registration, name='cultural-register'),
    path('registrations/', views.registration_list, name='cultural-registration-list'),
    path('registrations/<int:pk>/', views.registration_detail, name='cultural-registration-detail'),

    # Teams
    path('teams/create/', views.create_team, name='cultural-team-create'),
    path('teams/my/', views.my_teams, name='cultural-my-teams'),
    path('teams/event/<slug:slug>/', views.event_teams, name='cultural-event-teams'),
]