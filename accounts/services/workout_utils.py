from typing import Dict, List, Union, Optional
from datetime import datetime, timedelta
from exercises.models import Exercise
from accounts.models import TrainingSettings
from .date_converter import convert_persian_to_english_weekday, convert_day_to_date, get_next_training_day

# تابع محاسبه زمان استراحت (به ثانیه) بر اساس نوع تمرین و سطح تجربه کاربر
def calculate_rest_time(exercise_type: str, intensity: float) -> int:
    """
    محاسبه زمان استراحت بین ست‌ها بر اساس نوع تمرین و شدت
    """
    base_rest = {
        'compound': 180,  # 3 دقیقه برای تمرینات ترکیبی
        'isolation': 90,  # 1.5 دقیقه برای تمرینات ایزوله
        'cardio': 60,    # 1 دقیقه برای تمرینات هوازی
        'mobility': 30   # 30 ثانیه برای تمرینات حرکتی
    }
    
    # تنظیم زمان استراحت بر اساس شدت
    rest_time = base_rest.get(exercise_type, 90)
    if intensity > 0.8:  # شدت بالا
        rest_time *= 1.2
    elif intensity < 0.6:  # شدت پایین
        rest_time *= 0.8
        
    return int(rest_time)


# تابع محاسبه شدت تمرین (به صورت عددی بین 0 تا 1) بر اساس نوع تمرین، تعداد ست و تکرارها
def calculate_intensity(goal: str, experience: str, week: int) -> float:
    """
    محاسبه شدت تمرین بر اساس هدف، تجربه و هفته
    """
    base_intensity = {
        'muscle_gain': 0.7,
        'strength': 0.8,
        'weight_loss': 0.6,
        'endurance': 0.5
    }
    
    # تنظیم شدت بر اساس تجربه
    experience_multiplier = {
        'beginner': 0.8,
        'intermediate': 1.0,
        'expert': 1.2
    }
    
    # تنظیم شدت بر اساس هفته
    week_multiplier = 1.0 + (week * 0.05)  # افزایش تدریجی شدت
    
    intensity = base_intensity.get(goal, 0.7)
    intensity *= experience_multiplier.get(experience, 1.0)
    intensity *= week_multiplier
    
    # محدود کردن شدت بین 0.4 و 0.9
    return max(0.4, min(0.9, intensity))


def convert_persian_to_english_weekday(persian_day: str) -> str:
    """
    تبدیل نام روز هفته از فارسی به انگلیسی
    
    Args:
        persian_day: نام روز هفته به فارسی
        
    Returns:
        str: نام روز هفته به انگلیسی
    """
    persian_to_english = {
        'شنبه': 'saturday',
        'یکشنبه': 'sunday',
        'دوشنبه': 'monday',
        'سه‌شنبه': 'tuesday',
        'چهارشنبه': 'wednesday',
        'پنج‌شنبه': 'thursday',
        'جمعه': 'friday'
    }
    return persian_to_english.get(persian_day.lower(), persian_day.lower())


# تابع محاسبه تاریخ روز تمرین بعدی بر اساس تاریخ فعلی و روزهای مجاز تمرین (به صورت لیست نام روزها)
def get_next_training_day(current_date: datetime, training_days: List[str]) -> datetime:
    """
    محاسبه تاریخ روز تمرین بعدی بر اساس تاریخ فعلی و روزهای مجاز تمرین (به صورت لیست نام روزها).
    به عنوان یک مربی حرفه‌ای، این تابع تضمین می‌کند که برنامه تمرین در روزهای مجاز قرار می‌گیرد.
    """
    # تبدیل نام روزها به انگلیسی
    training_days = [convert_persian_to_english_weekday(day) for day in training_days]
    
    # تبدیل نام روزها به عدد (0 تا 6)؛ مثلا "monday" به 0 تبدیل می‌شود.
    day_map = { "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6 }
    training_day_nums = [day_map.get(day.lower(), 0) for day in training_days]

    # اگر لیست خالی باشد، روز بعد را برمی‌گردانیم.
    if not training_day_nums:
         return current_date + timedelta(days=1)

    # محاسبه روز هفته فعلی (به صورت عدد 0 تا 6)
    current_weekday = current_date.weekday()
    # محاسبه روز هفته بعدی مجاز (به صورت عدد)
    next_day_num = min((d for d in training_day_nums if d > current_weekday), default=training_day_nums[0])
    # محاسبه تعداد روزهای اضافی برای رسیدن به روز بعدی مجاز
    delta = (next_day_num - current_weekday) % 7
    return current_date + timedelta(days=delta)


def convert_day_to_date(day_name: str, base_date: datetime) -> datetime:
    """
    تبدیل نام روز هفته به تاریخ
    
    Args:
        day_name: نام روز هفته (فارسی یا انگلیسی)
        base_date: تاریخ پایه برای محاسبه
        
    Returns:
        datetime: تاریخ متناظر با روز هفته
    """
    # تبدیل نام روز به انگلیسی
    english_day = convert_persian_to_english_weekday(day_name)
    
    # تبدیل نام روز به عدد (0 تا 6)
    day_map = { "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6 }
    target_weekday = day_map.get(english_day.lower(), 0)
    
    # محاسبه روز هفته فعلی
    current_weekday = base_date.weekday()
    
    # محاسبه تعداد روزهای اضافی برای رسیدن به روز هدف
    delta = (target_weekday - current_weekday) % 7
    
    return base_date + timedelta(days=delta)


# تابع محاسبه گروه‌های عضلانی مورد تمرین بر اساس نوع split (مثلا "bro_split", "ppl", "upper_lower", "full_body")
def get_muscle_groups_for_split(split_type: str) -> Dict[str, List[str]]:
    """
    دریافت گروه‌های عضلانی مورد تمرین بر اساس نوع split
    """
    muscle_groups = {
        'bro_split': {
            'chest': ['chest', 'triceps', 'shoulders'],
            'back': ['back', 'biceps', 'rear_deltoids'],
            'legs': ['quadriceps', 'hamstrings', 'calves', 'glutes'],
            'shoulders': ['shoulders', 'traps', 'triceps'],
            'arms': ['biceps', 'triceps', 'forearms']
        },
        'ppl': {
            'push': ['chest', 'shoulders', 'triceps'],
            'pull': ['back', 'biceps', 'rear_deltoids'],
            'legs': ['quadriceps', 'hamstrings', 'calves', 'glutes']
        },
        'upper_lower': {
            'upper': ['chest', 'back', 'shoulders', 'biceps', 'triceps'],
            'lower': ['quadriceps', 'hamstrings', 'calves', 'glutes']
        },
        'full_body': {
            'full': ['chest', 'back', 'shoulders', 'biceps', 'triceps', 
                    'quadriceps', 'hamstrings', 'calves', 'glutes']
        }
    }
    
    return muscle_groups.get(split_type, muscle_groups['full_body'])


# تابع تولید نکات و راهنمایی‌های تمرینی برای هر حرکت
def get_exercise_notes(exercise: Exercise, experience_level: str) -> List[str]:
    """
    تولید نکات و راهنمایی‌های تمرینی برای هر حرکت بر اساس نوع حرکت و سطح تجربه کاربر.
    به عنوان یک مربی حرفه‌ای، نکات را طوری تنظیم می‌کنیم که به کاربر در اجرای صحیح حرکت کمک کند.
    """
    notes = []
    
    # نکات عمومی برای همه سطوح
    general_notes = [
        "قبل از شروع ست اصلی، حتماً یک ست گرم کردنی با وزنه سبک انجام دهید",
        "در طول حرکت نفس‌کشی منظم داشته باشید",
        "حرکت را با کنترل کامل انجام دهید و از حرکت‌های ناگهانی خودداری کنید"
    ]
    notes.extend(general_notes)
    
    # نکات مخصوص مبتدیان
    if experience_level == "beginner":
        beginner_notes = [
            "روی فرم صحیح حرکت تمرکز کنید، نه روی وزنه",
            "از یک نفر بخواهید فرم شما را چک کند",
            "اگر احساس درد یا ناراحتی کردید، حرکت را متوقف کنید",
            "بین ست‌ها استراحت کافی داشته باشید"
        ]
        notes.extend(beginner_notes)
    
    # نکات مخصوص سطح متوسط
    elif experience_level == "intermediate":
        intermediate_notes = [
            "روی افزایش تدریجی وزنه تمرکز کنید",
            "تکنیک‌های پیشرفته مثل drop set یا rest-pause را امتحان کنید",
            "به احساس عضله در طول حرکت توجه کنید",
            "سعی کنید در هر جلسه پیشرفت داشته باشید"
        ]
        notes.extend(intermediate_notes)
    
    # نکات مخصوص حرفه‌ای‌ها
    elif experience_level == "expert":
        expert_notes = [
            "از تکنیک‌های پیشرفته مثل superset و giant set استفاده کنید",
            "روی نقاط ضعف خود تمرکز کنید",
            "از تکنیک‌های افزایش شدت مثل forced reps استفاده کنید",
            "برنامه‌ریزی دوره‌ای را رعایت کنید"
        ]
        notes.extend(expert_notes)
    
    # نکات مخصوص نوع حرکت
    if exercise.mechanic == "compound":
        compound_notes = [
            "روی هماهنگی بین عضلات مختلف تمرکز کنید",
            "از تکنیک bracing (سفت کردن عضلات مرکزی) استفاده کنید",
            "حرکت را از مفصل اصلی شروع کنید"
        ]
        notes.extend(compound_notes)
    elif exercise.mechanic == "isolation":
        isolation_notes = [
            "روی انقباض کامل عضله هدف تمرکز کنید",
            "از momentum (تکانه) استفاده نکنید",
            "دامنه حرکت را کامل اجرا کنید"
        ]
        notes.extend(isolation_notes)
    
    # نکات مخصوص تجهیزات مورد نیاز
    if exercise.equipment:
        equipment_notes = [
            f"از تجهیزات {exercise.equipment} به درستی استفاده کنید",
            "قبل از استفاده از تجهیزات، نحوه تنظیم آن‌ها را یاد بگیرید",
            "از سالم بودن تجهیزات اطمینان حاصل کنید"
        ]
        notes.extend(equipment_notes)
    
    return notes 