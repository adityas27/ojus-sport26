from django.urls import path
from .consumers import BookingConsumer

websocket_urlpatterns = [
    path('ws/bookings/', BookingConsumer.as_asgi()),
]
