from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError

User = get_user_model()

# Create your models here.
class Sport(models.Model):
    slug = models.SlugField(unique=True, blank=True, max_length=255)
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    isTeamBased = models.BooleanField(default=False)
    primary = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='primary_sports')
    secondary = models.ManyToManyField(User, related_name='secondary_sports')
    venue = models.CharField(max_length=50, default="")
    is_finalized = models.BooleanField(default=False)

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


# Result section for our sports
class Results(models.Model):
    BRANCH_CHOICES = [
        ('COMPS', 'Computer Engineering'),
        ('IT', 'Information Technology'),
        ('AIML', 'CSE Artificial Intelligence and Machine Learning'),
        ('DS', 'CSE Data Science'),
        ('MECH', 'Mechanical Engineering'),
        ('CIVIL', 'Civil Engineering'),
    ]
    player = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="result_player")
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="result_team")
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="result_sport")
    branch = models.CharField(max_length=6, choices=BRANCH_CHOICES, blank=True)
    position = models.IntegerField(help_text="1 for 1st, 2 for 2nd, 3 for 3rd")
    # 1. The Sport-Specific Score (Manually Adjusted by Admin)
    score = models.IntegerField(default=0, help_text="Points earned in the match/game itself")
    # 2. The Department Contribution (Auto-Calculated 3-2-1 based on Position)
    points = models.IntegerField(default=0, editable=False)
    date = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="result_user")

    class Meta:
        ordering = ['position']

    def clean(self):
        if not self.team and not self.player:
            raise ValidationError("You must select either a Team or a Player.")
        if self.team and self.player:
            raise ValidationError("Please select only one: Team OR Player, not both.")
        if self.team and self.team.sport != self.sport:
            raise ValidationError(
                f"The selected team '{self.team.name}' is registered for {self.team.sport.name}, not {self.sport.name}.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        winner = self.team.name if self.team else (self.player.username if self.player else "Unknown")
        return f"{self.sport.name} - #{self.position} {winner} (Score: {self.score} | Dept Pts: {self.points})"

@receiver(pre_save, sender=Results)
def calculate_leaderboard_data(sender, instance, **kwargs):
    if instance.position == 1:
        instance.points = 3
    elif instance.position == 2:
        instance.points = 2
    elif instance.position == 3:
        instance.points = 1
    else:
        instance.points = 0

    if instance.team:
        instance.branch = instance.team.branch
    elif instance.player:
        registration = Registration.objects.filter(
            student=instance.player,
            sport=instance.sport
        ).first()

        if registration:
            instance.branch = registration.branch
