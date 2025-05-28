import os
import django
import json
from datetime import datetime
import traceback
import logging

# تنظیم محیط جنگو
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aura.settings')
django.setup()

from accounts.models import BotUser, UserProfile, TrainingSettings
from accounts.services.workout_plan_generator import WorkoutPlanGenerator
from accounts.services.workout_exporter import WorkoutExporter

logging.basicConfig(level=logging.INFO)

def generate_workout_plan(telegram_id: str, duration_weeks: int = 4) -> None:
    """
    تولید برنامه تمرینی برای کاربر با شناسه تلگرام مشخص شده
    و ذخیره آن در فایل JSON
    """
    try:
        # یافتن کاربر
        bot_user = BotUser.objects.get(telegram_id=telegram_id)
        user_profile = UserProfile.objects.get(user=bot_user)
        training_settings = TrainingSettings.objects.get(user=bot_user)
        
        print(f"In the process of generating a workout plan for user {user_profile.user}...")
        
        # تولید برنامه تمرینی
        generator = WorkoutPlanGenerator(user_profile, training_settings)
        plan = generator.generate_plan(weeks=duration_weeks)
        
        # خروجی گرفتن برنامه
        exporter = WorkoutExporter(user_profile, training_settings)
        
        # ذخیره در فایل JSON
        json_output = exporter.export_to_json(plan)
        filename = f"workout_plan_{telegram_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(json_output)
        print(f"Workout plan saved in file {filename}")
        
        # نمایش نسخه متنی برنامه
        text_output = exporter.export_to_text(plan)
        text_filename = f"workout_plan_{telegram_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(text_filename, 'w', encoding='utf-8') as f:
            f.write(text_output)
        print(f"Text version of the workout plan saved in file {text_filename}")
        
    except BotUser.DoesNotExist:
        print(f"User with telegram id {telegram_id} not found.")
    except UserProfile.DoesNotExist:
        print(f"User profile with telegram id {telegram_id} not found.")
    except TrainingSettings.DoesNotExist:
        print(f"Workout settings for user with telegram id {telegram_id} not found.")
    except Exception as e:
        print("Error:", e)
        traceback.print_exc()

if __name__ == "__main__":
    try:
        # اجرای اصلی برنامه
        generate_workout_plan('mhmdalislhi', duration_weeks=4)
    except Exception as e:
        print("Error:", e)
        traceback.print_exc() 