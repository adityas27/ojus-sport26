from django.db import models
from django.utils.text import slugify
from django.contrib.auth import get_user_model

User = get_user_model()


YEAR_CHOICES = [
    ('FE', 'First Year (FE)'),
    ('SE', 'Second Year (SE)'),
    ('TE', 'Third Year (TE)'),
    ('BE', 'Fourth Year (BE)'),
]

# Create your models here.
class Event(models.Model):
    slug = models.SlugField(unique=True, blank=True, max_length=255)
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    registeration = models.BooleanField(default=False)
    primary = models.ManyToManyField(
        User, related_name='cultural_primary_events', blank=True
    )
    secondary = models.ManyToManyField(
        User, related_name='cultural_secondary_events', blank=True
    )
    venue = models.CharField(max_length=50, default="")
    day = models.IntegerField(default=1)
    time = models.CharField(max_length=5, default="")
    img = models.URLField(default="")
    

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    

class  Registration(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cultural_registrations')
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    year = models.CharField(max_length=2, choices=YEAR_CHOICES, default="FE")
    registered_on = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ['student', 'event']
        indexes = [
            models.Index(fields=['student', 'event']),
        ]

    def __str__(self):
        return f"{self.student.username} - {self.event.name}"                          