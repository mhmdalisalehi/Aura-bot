import os
import django
import json
from datetime import datetime

# تنظیم محیط جنگو
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aura.settings')
django.setup()

from accounts.models import BotUser, UserProfile, TrainingSettings
from accounts.services.workout_plan_generator import WorkoutPlanGenerator
from accounts.services.workout_exporter import WorkoutExporter

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
        
        print(f"در حال تولید برنامه تمرینی برای کاربر {user_profile.user}...")
        
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
        print(f"برنامه تمرینی در فایل {filename} ذخیره شد.")
        
        # نمایش نسخه متنی برنامه
        text_output = exporter.export_to_text(plan)
        text_filename = f"workout_plan_{telegram_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(text_filename, 'w', encoding='utf-8') as f:
            f.write(text_output)
        print(f"نسخه متنی برنامه در فایل {text_filename} ذخیره شد.")
        
    except BotUser.DoesNotExist:
        print(f"کاربر با شناسه تلگرام {telegram_id} یافت نشد.")
    except UserProfile.DoesNotExist:
        print(f"پروفایل کاربر با شناسه تلگرام {telegram_id} یافت نشد.")
    except TrainingSettings.DoesNotExist:
        print(f"تنظیمات تمرین برای کاربر با شناسه تلگرام {telegram_id} یافت نشد.")
    except Exception as e:
        print(f"خطا در تولید برنامه تمرینی: {str(e)}")

if __name__ == '__main__':
    # تولید برنامه تمرینی برای کاربر مورد نظر
    generate_workout_plan('mhmdalislhi', duration_weeks=4) 