from datetime import datetime, timedelta
from typing import List

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

def get_next_training_day(current_date: datetime, training_days: List[str]) -> datetime:
    """
    محاسبه تاریخ روز تمرین بعدی بر اساس تاریخ فعلی و روزهای مجاز تمرین
    
    Args:
        current_date: تاریخ فعلی
        training_days: لیست روزهای مجاز تمرین
        
    Returns:
        datetime: تاریخ روز تمرین بعدی
    """
    # تبدیل نام روزها به انگلیسی
    training_days = [convert_persian_to_english_weekday(day) for day in training_days]
    
    # تبدیل نام روزها به عدد (0 تا 6)
    day_map = { "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6 }
    training_day_nums = [day_map.get(day.lower(), 0) for day in training_days]

    # اگر لیست خالی باشد، روز بعد را برمی‌گردانیم
    if not training_day_nums:
         return current_date + timedelta(days=1)

    # محاسبه روز هفته فعلی
    current_weekday = current_date.weekday()
    
    # محاسبه روز هفته بعدی مجاز
    next_day_num = min((d for d in training_day_nums if d > current_weekday), default=training_day_nums[0])
    
    # محاسبه تعداد روزهای اضافی برای رسیدن به روز بعدی مجاز
    delta = (next_day_num - current_weekday) % 7
    
    return current_date + timedelta(days=delta) 