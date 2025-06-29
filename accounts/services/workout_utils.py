from typing import Dict, List, Union, Optional
from datetime import datetime, timedelta
from exercises.models import Exercise
from accounts.models import TrainingSettings
from .date_converter import convert_persian_to_english_weekday, convert_day_to_date, get_next_training_day

from logger_util import get_logger
logger = get_logger('workout_utils', 'logs/workout_utils.log')

def calculate_rest_time(exercise_type: str, intensity: float) -> int:
    """
    محاسبه زمان استراحت بین ست‌ها بر اساس نوع تمرین و شدت
    """
    base_rest = {
        'compound': 180,
        'isolation': 90,
        'cardio': 60,
        'mobility': 30
    }
    rest_time = base_rest.get(exercise_type, 90)
    if intensity > 0.8:
        rest_time *= 1.2
    elif intensity < 0.6:
        rest_time *= 0.8
    logger.debug(f"Rest time for {exercise_type} with intensity {intensity}: {rest_time}")
    return int(rest_time)

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
    experience_multiplier = {
        'beginner': 0.8,
        'intermediate': 1.0,
        'expert': 1.2
    }
    week_multiplier = 1.0 + (week * 0.05)
    intensity = base_intensity.get(goal, 0.7)
    intensity *= experience_multiplier.get(experience, 1.0)
    intensity *= week_multiplier
    result = max(0.4, min(0.9, intensity))
    logger.debug(f"Calculated intensity for goal={goal}, experience={experience}, week={week}: {result}")
    return result

def convert_persian_to_english_weekday(persian_day: str) -> str:
    """
    تبدیل نام روز هفته از فارسی به انگلیسی
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
    result = persian_to_english.get(persian_day.lower(), persian_day.lower())
    logger.debug(f"Converted Persian day '{persian_day}' to English '{result}'")
    return result

def get_next_training_day(current_date: datetime, training_days: List[str]) -> datetime:
    """
    محاسبه تاریخ روز تمرین بعدی بر اساس تاریخ فعلی و روزهای مجاز تمرین (به صورت لیست نام روزها).
    """
    training_days = [convert_persian_to_english_weekday(day) for day in training_days]
    day_map = { "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6 }
    training_day_nums = [day_map.get(day.lower(), 0) for day in training_days]
    if not training_day_nums:
        logger.warning("No training days provided, returning next day.")
        return current_date + timedelta(days=1)
    current_weekday = current_date.weekday()
    next_day_num = min((d for d in training_day_nums if d > current_weekday), default=training_day_nums[0])
    delta = (next_day_num - current_weekday) % 7
    result_date = current_date + timedelta(days=delta)
    logger.debug(f"Next training day from {current_date} with allowed days {training_days}: {result_date}")
    return result_date

def convert_day_to_date(day_name: str, base_date: datetime) -> datetime:
    """
    تبدیل نام روز هفته به تاریخ
    """
    english_day = convert_persian_to_english_weekday(day_name)
    day_map = { "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6 }
    target_weekday = day_map.get(english_day.lower(), 0)
    current_weekday = base_date.weekday()
    delta = (target_weekday - current_weekday) % 7
    result_date = base_date + timedelta(days=delta)
    logger.debug(f"Converted day '{day_name}' to date '{result_date}' based on base date '{base_date}'")
    return result_date

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
    result = muscle_groups.get(split_type, muscle_groups['full_body'])
    logger.debug(f"Muscle groups for split '{split_type}': {result}")
    return result

def get_progression_notes(experience_level: str) -> str:
    """Get progression notes based on experience level."""
    if experience_level == 'beginner':
        note = "Focus on form and technique. Increase weight when 12 reps become easy."
    elif experience_level == 'intermediate':
        note = "Progressive overload: Increase weight or reps each week."
    else:
        note = "Advanced progression: Use various techniques and periodization."
    logger.debug(f"Progression notes for experience level '{experience_level}': {note}")
    return note

def get_exercise_notes(exercise: Exercise, experience_level: str) -> List[str]:
    """
    Generate notes for an exercise based on type and experience.
    """
    notes = []
    is_primary = getattr(exercise, 'is_primary', False)
    if is_primary:
        if experience_level == 'beginner':
            notes.append("روی فرم صحیح حرکت تمرکز کنید و با وزنه سبک شروع کنید.")
        elif experience_level == 'intermediate':
            notes.append("وزنه را به تدریج افزایش دهید و روی کنترل حرکت تمرکز کنید.")
        else:
            notes.append("از تکنیک‌های پیشرفته مانند drop set یا rest-pause استفاده کنید.")
    else:
        notes.append("حرکت را با کنترل کامل و دامنه حرکتی مناسب انجام دهید.")
    logger.debug(f"Exercise notes for '{getattr(exercise, 'name', str(exercise))}', experience '{experience_level}': {notes}")
    return notes