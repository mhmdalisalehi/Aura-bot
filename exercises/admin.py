from django.contrib import admin
from .models import Exercise, ExerciseImage

# Register models in the admin panel
admin.site.register(Exercise)
admin.site.register(ExerciseImage)
