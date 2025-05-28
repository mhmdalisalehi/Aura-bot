import os
import django
import json

# تنظیم محیط جنگو - این باید قبل از import کردن مدل‌ها باشد
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aura.settings')
django.setup()

# حالا می‌توانیم مدل‌ها را import کنیم
from accounts.models import BotUser, UserProfile, TrainingSettings
from accounts.services.workout_plan_generator import WorkoutPlanGenerator

try:
    # یافتن کاربر
    bot_user = BotUser.objects.get(telegram_id='mhmdalislhi')
    user_profile = UserProfile.objects.get(user=bot_user)
    training_settings = TrainingSettings.objects.get(user=bot_user)

    # تولید برنامه تمرینی
    generator = WorkoutPlanGenerator(user_profile, training_settings)
    plan = generator.generate_plan(weeks=1)  # برای یک هفته

    # نمایش ساختار برنامه
    print(json.dumps(plan, indent=2, ensure_ascii=False))

except Exception as e:
    print(f"Error: {str(e)}")