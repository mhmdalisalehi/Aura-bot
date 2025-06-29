from django.contrib import admin
from .models import  UserProfile,InjuryExerciseClassification,BotUser
from .models import WorkoutPlan, WorkoutDay, WorkoutExercise,TrainingSettings

# Register models in the admin panel
admin.site.register(UserProfile)
admin.site.register(InjuryExerciseClassification)

admin.site.register(BotUser)
admin.site.register(TrainingSettings)
admin.site.register(WorkoutPlan)
admin.site.register(WorkoutDay)
admin.site.register(WorkoutExercise)
