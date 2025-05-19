from django.db import models
from django.contrib.auth.models import User

from exercises.models import Exercise


class BotUser(models.Model):
    telegram_id = models.CharField(max_length=50, unique=True)
    username = models.CharField(max_length=150, blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True, null=True)
    phone = models.CharField(max_length=15, unique=True, blank=True, null=True)
    last_name = models.CharField(max_length=150, blank=True, null=True)
    # Add any other fields you want to store for bot users

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username or str(self.telegram_id)

class UserProfile(models.Model):
    user = models.OneToOneField(BotUser, on_delete=models.CASCADE)
    gender = models.CharField(max_length=10, choices=[("male" , ' Male'),("female","Female")])
    height_cm = models.FloatField()
    weight_kg = models.FloatField()
    age = models.PositiveIntegerField()
    goal = models.CharField(max_length=30,choices=[
        ('weight_loss', 'Weight Loss'),
        ('muscle_gain', 'Muscle Gain'),
        ('strength', 'Strength'),
        ('aesthetics', 'Aesthetics'),
        ('endurance', 'Endurance'),])
    body_fat_percentage = models.FloatField(null=True, blank=True)
    body_fat_percentage_interd_by_user = models.FloatField(null=True, blank=True)
    
    body_type = models.CharField(max_length=20, choices=[('ectomorph', 'Ectomorph'), ('mesomorph', 'Mesomorph'), ('endomorph', 'Endomorph')], null=True, blank=True)
    daily_activity_level = models.CharField(max_length=10, choices=[
        ('low', 'Low (Sedentary)'),
        ('moderate', 'Moderate'),
        ('high', 'Active)'),
    ])
    aura = models.PositiveBigIntegerField(default=0) #point
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def bmi(self):
        return self.weight_kg / ((self.height_cm / 100) ** 2)
    
    
class TrainingSettings(models.Model):
    user = models.OneToOneField(BotUser, on_delete=models.CASCADE)
    experience_level = models.CharField(max_length=15, choices=[('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('expert', 'Expert')])
    training_days_per_week = models.PositiveIntegerField()
    training_days = models.JSONField()
    training_duration_minutes = models.PositiveIntegerField()
    available_equipment = models.JSONField()
    preferred_location = models.CharField(max_length=20, choices=[('home', 'Home'), ('gym', 'Gym')])
    injuries = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class InjuryExerciseClassification(models.Model):
    INJURY_CHOICES = [
        ('lower_back', 'Lower Back Injury'),
        ('knee', 'Knee Injury'),
        ('shoulder', 'Shoulder Injury'),
        ('neck', 'Neck Injury'),
        ('wrist', 'Wrist Injury'),
        ('elbow', 'Elbow Injury'),
        ('hip', 'Hip Injury'),
        ('chest', 'Chest Injury'),
    ]

    CLASSIFICATION_CHOICES = [
        ('avoid', 'Avoid'),
        ('safe', 'Safe Alternative'),
    ]

    injury = models.CharField(max_length=20, choices=INJURY_CHOICES)
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='injury_classifications')
    classification = models.CharField(max_length=10, choices=CLASSIFICATION_CHOICES)

    class Meta:
        unique_together = ('injury', 'exercise')

    def __str__(self):
        return f"{self.exercise.name} - {self.injury} - {self.classification}"


