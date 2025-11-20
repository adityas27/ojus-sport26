from django.urls import path
from . import views

app_name = 'sports'

urlpatterns = [
    # Sport URLs
    path('sports/', views.sport_list, name='sport-list'), # will be handled in frontend
    path('sports/<int:pk>/', views.sport_detail, name='sport-detail'), # will be handled in frontend
    
    # Registration URLs
    path('registrations/', views.registration_list, name='registration-list'), # Post feature is implemented, GET is to be worked up on
    path('registrations/<int:pk>/', views.registration_detail, name='registration-detail'),
    path('registrations/sport/<slug:sport_slug>/', views.registration_by_sport, name='registration-by-sport'),
    path('user-registration-info/', views.user_registration_info, name='user-registration-info'),
    path("registration-search/<int:moodleID>/", views.admin_registration_search_by_moodle, name="admin-registration-search-moodle"),

    # Team URLs
    path('teams/', views.team_list, name='team-list'),
    path('teams/<int:pk>/', views.team_detail, name='team-detail'),

    # Leaderboard URLS
    path('leaderboard/department/', views.department_leaderboard, name='department-leaderboard'),
    path('leaderboard/sport/<slug:sport_slug>/', views.sport_leaderboard, name='sport-leaderboard'),
    path('leaderboard/sport/<slug:sport_slug>/update/', views.update_sport_leaderboard,
         name='update-sport-leaderboard'),
    path('leaderboard/result/<int:result_id>/adjust/', views.adjust_result_points, name='adjust-result-points'),
    path('leaderboard/sport/<slug:sport_slug>/finalize/', views.finalize_sport_standings, name='finalize-sport'),
]