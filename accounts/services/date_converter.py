from datetime import datetime, timedelta
from typing import List

from logger_util import get_logger

logger = get_logger('date_converter', 'logs/date_converter.log')

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
    english_day = persian_to_english.get(persian_day.lower(), persian_day.lower())
    logger.info(f"Converted Persian weekday '{persian_day}' to English '{english_day}'")
    return english_day

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
    logger.info(f"Converted day '{day_name}' (English: '{english_day}') with base date {base_date} to date {result_date}")
    return result_date

def get_next_training_day(current_date: datetime, training_days: List[str]) -> datetime:
    """
    محاسبه تاریخ روز تمرین بعدی بر اساس تاریخ فعلی و روزهای مجاز تمرین
    """
    training_days_english = [convert_persian_to_english_weekday(day) for day in training_days]
    day_map = { "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6 }
    training_day_nums = [day_map.get(day.lower(), 0) for day in training_days_english]

    if not training_day_nums:
        logger.warning("Training days list is empty, returning next day.")
        return current_date + timedelta(days=1)

    current_weekday = current_date.weekday()
    next_day_num = min((d for d in training_day_nums if d > current_weekday), default=training_day_nums[0])
    delta = (next_day_num - current_weekday) % 7
    next_training_date = current_date + timedelta(days=delta)
    logger.info(f"Next training day after {current_date} from {training_days} is {next_training_date}")
    return