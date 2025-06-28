import os
import django
import datetime

# --- Django setup ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aura.settings')
django.setup()

# --- Imports ---
from accounts.models import BotUser, UserProfile, TrainingSettings
from accounts.services.workout_generator_full import WorkoutGenerator, format_workout_plan_for_telegram



# --- Find the user ---
telegram_id = "mhmdalislhi"

try:
    user = BotUser.objects.get(telegram_id=telegram_id)
    profile = UserProfile.objects.get(user=user)
    settings = TrainingSettings.objects.get(user=user)
except BotUser.DoesNotExist:
    print("❌ کاربر پیدا نشد.")
    exit()
except (UserProfile.DoesNotExist, TrainingSettings.DoesNotExist):
    print("❌ پروفایل یا تنظیمات تمرینی برای کاربر وجود ندارد.")
    exit()

# --- Generate the workout plan ---
generator = WorkoutGenerator(profile, settings)

print(f"📋 Split strategy: {settings.split_type}")
print(f"📅 Training days: {list(settings.training_days.keys())}")

# If you want to see which muscles are planned for each day:
from accounts.services.workout_generator_full import BroSplitStrategy, PushPullLegsSplitStrategy, FullBodySplitStrategy, UpperLowerSplitStrategy

split_map = {
    'bro_split': BroSplitStrategy.MUSCLE_DAY_MAPPING,
    'push_pull_legs': PushPullLegsSplitStrategy.MUSCLE_GROUPS,
    'full_body': FullBodySplitStrategy.MUSCLE_GROUPS,
    'upper_lower': UpperLowerSplitStrategy.MUSCLE_GROUPS,
}
print(f"🗓️ Muscle plan per day: {split_map.get(settings.split_type)}")


print("⏳ در حال ساخت برنامه تمرینی برای کاربر:", telegram_id)
program = generator.generate_program(week=1)

from exercises.models import Exercise

print("⚙️ تعداد تمرین‌های موجود در دیتابیس:", Exercise.objects.count())

filtered = Exercise.objects.filter(
    primary_muscles__contains=["chest"],
    level=settings.experience_level,
    equipment__in=settings.available_equipment
)
print("✅ تعداد تمرین‌های قابل انتخاب برای سینه:", filtered.count())


# --- Format the output for Telegram and print ---
message = format_workout_plan_for_telegram(program)
print("✅ برنامه تمرینی تولید شد:\n")
print(message)
print("\n📊 Summary:")
for day, exercises in program['weekly_plan'].items():
    print(f"{day}: {len(exercises)} exercises")
# --- Optional: Save to database (if needed) ---
# از این بخش می‌تونی برای ذخیره به مدل‌های WorkoutPlan / WorkoutDay / WorkoutExercise استفاده کنی
# فعلاً فقط چاپ می‌کنیم
