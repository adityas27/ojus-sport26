from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()
from django.utils.text import slugify

# Create your models here.
class Sport(models.Model):
    slug = models.SlugField(unique=True, blank=True, max_length=255)
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    isTeamBased = models.BooleanField(default=False)
    primary = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='primary_sports')
    secondary = models.ManyToManyField(User, related_name='secondary_sports')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Registration(models.Model):
    YEAR_CHOICES = [
        ('FE', 'First Year (FE)'),
        ('SE', 'Second Year (SE)'),
        ('TE', 'Third Year (TE)'),
        ('BE', 'Fourth Year (BE)'),
    ]
    BRANCH_CHOICES = [
        ('COMPS', 'Computer Engineering'),
        ('IT', 'Information Technology'),
        ('AIML', 'CSE Artifical Intelligence and Machine Learning'),
        ('DS', 'CSE Data Science'),
        ('MECH', 'Mechanical Engineering'),
        ('CIVIL', 'Civil Engineering'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE)
    year = models.CharField(max_length=2, choices=YEAR_CHOICES, default="FE")
    branch = models.CharField(max_length=6, choices=BRANCH_CHOICES, default="COMPS")
    registered_on = models.DateTimeField(auto_now_add=True)
    registration_modified = models.DateTimeField(auto_now=True)

class Team(models.Model):
    BRANCH_CHOICES = [
        ('COMPS', 'Computer Engineering'),
        ('IT', 'Information Technology'),
        ('AIML', 'CSE Artifical Intelligence and Machine Learning'),
        ('DS', 'CSE Data Science'),
        ('MECH', 'Mechanical Engineering'),
        ('CIVIL', 'Civil Engineering'),
    ]
    name = models.CharField(max_length=50)
    branch = models.CharField(max_length=6, choices=BRANCH_CHOICES, default="COMPS")
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='managed_teams')
    captain = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='captain_teams')
    members = models.ManyToManyField(User, related_name="team_members")
    

