from django.contrib import admin
from .models import  UserProfile,InjuryExerciseClassification,BotUser

# Register models in the admin panel
admin.site.register(UserProfile)
admin.site.register(InjuryExerciseClassification)

admin.site.register(BotUser)
