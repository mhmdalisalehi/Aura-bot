from django.db import models
from django.contrib.postgres.fields import ArrayField

class Exercise(models.Model):
    FORCE_CHOICES = [
        ('pull', 'Pull'),
        ('push', 'Push'),
        ('static', 'Static'),
    ]

    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('expert', 'Expert'),
    ]

    MECHANIC_CHOICES = [
        ('compound', 'Compound'),
        ('isolation', 'Isolation'),
    ]

    EQUIPMENT_CHOICES = [
        ('body', 'Body Only'),
        ('machine', 'Machine'),
        ('kettlebells', 'Kettlebells'),
        ('dumbbell', 'Dumbbell'),
        ('cable', 'Cable'),
        ('barbell', 'Barbell'),
        ('bands', 'Bands'),
        ('medicine_ball', 'Medicine Ball'),
        ('exercise_ball', 'Exercise Ball'),
        ('e_z_curl_bar', 'E-Z Curl Bar'),
        ('foam_roll', 'Foam Roll'),
    ]

    CATEGORY_CHOICES = [
        ('strength', 'Strength'),
        ('stretching', 'Stretching'),
        ('plyometrics', 'Plyometrics'),
        ('strongman', 'Strongman'),
        ('powerlifting', 'Powerlifting'),
        ('cardio', 'Cardio'),
        ('olympic_weightlifting', 'Olympic Weightlifting'),
        ('crossfit', 'CrossFit'),
        ('weighted_bodyweight', 'Weighted Bodyweight'),
        ('assisted_bodyweight', 'Assisted Bodyweight'),
    ]

    name = models.CharField(max_length=255)
    aliases = models.JSONField(blank=True, null=True)
    primary_muscles = models.JSONField()
    secondary_muscles = models.JSONField(blank=True, null=True)
    force = models.CharField(max_length=10, choices=FORCE_CHOICES, blank=True, null=True)
    level = models.CharField(max_length=15, choices=LEVEL_CHOICES)
    mechanic = models.CharField(max_length=15, choices=MECHANIC_CHOICES, blank=True, null=True)
    equipment = models.CharField(max_length=20, choices=EQUIPMENT_CHOICES, blank=True, null=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    instructions = models.JSONField()
    description = models.TextField(blank=True, null=True)
    tips = models.JSONField(blank=True, null=True)
    name_in_persian = models.CharField(max_length=255, blank=True, null=True)
    instructions_in_persian = models.JSONField(blank=True, null=True)

    def __str__(self):
        return self.name

class ExerciseImage(models.Model):
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to="exercise_images/",null=True,blank=True)

    def __str__(self):
        return f"Image for {self.exercise.name}"
