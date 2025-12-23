from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError

User = get_user_model()

# Constants to avoid duplication
BRANCH_CHOICES = [
    ('COMPS', 'Computer Engineering'),
    ('IT', 'Information Technology'),
    ('AIML', 'CSE Artificial Intelligence and Machine Learning'),
    ('DS', 'CSE Data Science'),
    ('MECH', 'Mechanical Engineering'),
    ('CIVIL', 'Civil Engineering'),
]

YEAR_CHOICES = [
    ('FE', 'First Year (FE)'),
    ('SE', 'Second Year (SE)'),
    ('TE', 'Third Year (TE)'),
    ('BE', 'Fourth Year (BE)'),
]
class Sport(models.Model):
    slug = models.SlugField(unique=True, blank=True, max_length=255)
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    isTeamBased = models.BooleanField(default=False)
    primary = models.ManyToManyField(User, related_name='primary_sports')
    secondary = models.ManyToManyField(User, related_name='secondary_sports', blank=True)
    venue = models.CharField(max_length=50, default="")
    is_finalized = models.BooleanField(default=False)
    teamSize = models.IntegerField(default=0)
    day = models.IntegerField(default=1)
    time = models.CharField(max_length=5, default="")
    img = models.URLField(default="")


    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class Registration(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE)
    year = models.CharField(max_length=2, choices=YEAR_CHOICES, default="FE")
    branch = models.CharField(max_length=6, choices=BRANCH_CHOICES, default="COMPS")
    registered_on = models.DateTimeField(auto_now_add=True)
    registration_modified = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ['student', 'sport']  # Prevent duplicate registrations
        indexes = [
            models.Index(fields=['student', 'sport']),
        ]
    def __str__(self):
        return f"{self.student.username} - {self.sport.name}"

class Team(models.Model):
    BRANCH_CHOICES = [
        ('COMPS', 'Computer Engineering'),
        ('IT', 'Information Technology'),
        ('AIML', 'CSE Artificial Intelligence and Machine Learning'),
        ('DS', 'CSE Data Science'),
        ('MECH', 'Mechanical Engineering'),
        ('CIVIL', 'Civil Engineering'),
    ]

    YEAR_CHOICES = [
        ('FE', 'First Year (FE)'),
        ('SE', 'Second Year (SE)'),
        ('TE', 'Third Year (TE)'),
        ('BE', 'Fourth Year (BE)'),
    ]
    name = models.CharField(max_length=50)
    branch = models.CharField(max_length=6, choices=BRANCH_CHOICES, default="COMPS")
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='managed_teams')
    captain = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='captain_teams')
    members = models.ManyToManyField(User, related_name="team_members", blank=True)
    teamSize = models.IntegerField(default=0)
    class Meta:
        indexes = [
            models.Index(fields=['sport', 'branch']),
        ]
    def __str__(self):
        return f"{self.name} ({self.branch})"


class Results(models.Model):
    player = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="result_player")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True, related_name="result_team")
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="result_sport")
    branch = models.CharField(max_length=6, choices=BRANCH_CHOICES, blank=True)
    position = models.PositiveIntegerField(help_text="1 for 1st, 2 for 2nd, 3 for 3rd")
    score = models.PositiveIntegerField(default=0, help_text="Points earned in the match/game itself")
    points = models.PositiveIntegerField(default=0, editable=False,
                                         help_text="Auto-calculated: 3 for 1st, 2 for 2nd, 1 for 3rd")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position']
        constraints = [
            models.CheckConstraint(
                check=models.Q(team__isnull=False) | models.Q(player__isnull=False),
                name='team_or_player_required'
            ),
            models.UniqueConstraint(
                fields=['sport', 'team'],
                condition=models.Q(team__isnull=False),
                name='unique_team_per_sport'
            ),
            models.UniqueConstraint(
                fields=['sport', 'player'],
                condition=models.Q(player__isnull=False),
                name='unique_player_per_sport'
            ),
        ]
        indexes = [
            models.Index(fields=['sport', 'position']),
            models.Index(fields=['sport', 'branch']),
        ]

    def clean(self):
        if not self.team and not self.player:
            raise ValidationError("You must select either a Team or a Player.")
        if self.team and self.player:
            raise ValidationError("Please select only one: Team OR Player, not both.")
        if self.team and self.team.sport != self.sport:
            raise ValidationError(
                f"The selected team '{self.team.name}' is registered for {self.team.sport.name}, not {self.sport.name}."
            )

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
        try:
            # Note: Ensure Registration is imported/available in this file scope
            registration = Registration.objects.filter(
                student=instance.player,
                sport=instance.sport
            ).first()
            if registration:
                instance.branch = registration.branch
        except Exception:
            pass
        registration = Registration.objects.filter(
            student=instance.player,
            sport=instance.sport
        ).first()

        if registration:
            instance.branch = registration.branch

class TeamRequest(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    registeration = models.ForeignKey(Registration, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    accepted = models.BooleanField(default=False)
    denied = models.BooleanField(default=False)
    time =  models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['registeration', 'team'], name='unique_registration_team_request')
        ]

