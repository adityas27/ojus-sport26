from django.urls import path
from . import views

urlpatterns = [
    path('book/', views.book_seat, name='book-seat'),
    path('cancel/', views.cancel_booking, name='cancel-booking'),
    path('remaining/', views.get_remaining, name='remaining-seats'),
    path('my-booking/', views.my_booking, name='my-booking'),
    path('booking/<int:moodleID>/', views.get_booking_by_moodle, name='booking-by-moodle'),
    path('mark-present/<int:moodleID>/', views.mark_present, name='mark-present'),
]
