from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from exercises.models import Exercise
from accounts.models import UserProfile, TrainingSettings

def calculate_rest_time(exercise: Exercise, user_level: str) -> int:
    """محاسبه زمان استراحت بین ست‌ها"""
    base_rest = {
        'compound': 90,
        'isolation': 60,
        'cardio': 30,
        'mobility': 15
    }.get(exercise.type, 60)
    
    # تنظیم بر اساس سطح تجربه
    if user_level == 'beginner':
        base_rest += 30
    elif user_level == 'expert':
        base_rest -= 15
        
    return base_rest

def calculate_intensity(exercise: Exercise, sets: int, reps: str) -> float:
    """محاسبه شدت تمرین"""
    if isinstance(reps, str):
        min_reps = int(reps.split('-')[0])
    else:
        min_reps = reps
        
    # شدت بر اساس تعداد ست‌ها و تکرارها
    volume_factor = (sets * min_reps) / 100
    
    # شدت بر اساس نوع تمرین
    type_factor = {
        'compound': 1.2,
        'isolation': 1.0,
        'cardio': 0.8,
        'mobility': 0.5
    }.get(exercise.type, 1.0)
    
    return min(volume_factor * type_factor, 1.0)

def get_next_training_day(current_day: datetime, training_days: List[str]) -> datetime:
    """محاسبه روز تمرین بعدی"""
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    current_weekday = current_day.strftime('%A').lower()
    
    # پیدا کردن ایندکس روز فعلی
    current_index = days.index(current_weekday)
    
    # پیدا کردن نزدیک‌ترین روز تمرین بعدی
    for i in range(1, 8):
        next_index = (current_index + i) % 7
        if days[next_index] in training_days:
            return current_day + timedelta(days=i)
            
    return current_day + timedelta(days=7)

def format_exercise_name(exercise: Exercise) -> str:
    """فرمت‌بندی نام تمرین"""
    return f"{exercise.name} ({exercise.type})"

def get_muscle_groups_for_split(split_type: str) -> Dict[str, List[str]]:
    """دریافت گروه‌های عضلانی برای هر نوع split"""
    return {
        'bro_split': {
            'chest': ['chest', 'triceps'],
            'back': ['back', 'biceps'],
            'shoulders': ['shoulders', 'traps'],
            'legs': ['quadriceps', 'hamstrings', 'calves'],
            'arms': ['biceps', 'triceps'],
            'abs': ['abs', 'obliques']
        },
        'push_pull_legs': {
            'push': ['chest', 'shoulders', 'triceps'],
            'pull': ['back', 'biceps', 'traps'],
            'legs': ['quadriceps', 'hamstrings', 'calves', 'glutes']
        },
        'upper_lower': {
            'upper': ['chest', 'back', 'shoulders', 'biceps', 'triceps'],
            'lower': ['quadriceps', 'hamstrings', 'calves', 'glutes']
        },
        'full_body': {
            'full': ['chest', 'back', 'shoulders', 'biceps', 'triceps', 
                    'quadriceps', 'hamstrings', 'calves', 'abs']
        }
    }.get(split_type, {})

def calculate_weekly_volume(program: Dict) -> Dict[str, int]:
    """محاسبه حجم هفتگی برای هر عضله"""
    volume = {}
    
    for day, exercises in program['weekly_plan'].items():
        for exercise in exercises:
            muscle = exercise['muscle_group']
            if muscle not in volume:
                volume[muscle] = 0
                
            sets = exercise['sets']
            reps = exercise['reps']
            if isinstance(reps, str):
                reps = int(reps.split('-')[0])
                
            volume[muscle] += sets * reps
            
    return volume

def validate_rest_periods(program: Dict) -> List[str]:
    """اعتبارسنجی دوره‌های استراحت بین تمرینات"""
    errors = []
    last_trained = {}
    
    for day, exercises in program['weekly_plan'].items():
        for exercise in exercises:
            muscle = exercise['muscle_group']
            if muscle in last_trained:
                days_since = (datetime.strptime(day, '%Y-%m-%d') - 
                            datetime.strptime(last_trained[muscle], '%Y-%m-%d')).days
                
                if days_since < 1:
                    errors.append(f"زمان استراحت ناکافی برای {muscle} در {day}")
                    
            last_trained[muscle] = day
            
    return errors

def get_exercise_notes(exercise: Exercise, user_level: str) -> str:
    """دریافت نکات تمرین بر اساس سطح کاربر"""
    notes = []
    
    if user_level == 'beginner':
        notes.append("روی فرم صحیح تمرکز کنید")
        notes.append("وزن را به تدریج افزایش دهید")
    elif user_level == 'intermediate':
        notes.append("تغییر در تکنیک‌ها را امتحان کنید")
        notes.append("پیشرفت تدریجی را حفظ کنید")
    else:  # expert
        notes.append("تکنیک‌های پیشرفته را اعمال کنید")
        notes.append("شدت را به حداکثر برسانید")
        
    return " | ".join(notes) 