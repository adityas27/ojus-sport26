from django.db import models
from django.conf import settings


YEAR_CHOICES = [
    ('FE', 'First Year (FE)'),
    ('SE', 'Second Year (SE)'),
    ('TE', 'Third Year (TE)'),
    ('BE', 'Fourth Year (BE)'),
]


class Bookings(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seat_registration")
    year = models.CharField(max_length=2, choices=YEAR_CHOICES)
    registered_on = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(default=False)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['student'], name='unique_booking_per_student')
        ]

    def __str__(self):
        return f"Booking(student={self.student}, year={self.year})"
