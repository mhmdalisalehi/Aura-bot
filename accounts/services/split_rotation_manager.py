import datetime
from typing import Optional
from accounts.models import TrainingSettings, UserProfile


def get_optimal_split(user_profile: UserProfile, settings: TrainingSettings) -> str:
    """
    انتخاب هوشمند split بر اساس تجربه، هدف، تعداد روزهای تمرین، تیپ بدنی و محدودیت‌ها (مثلا آسیب‌ها) به عنوان یک مربی حرفه‌ای.
    """
    exp = settings.experience_level
    days = settings.training_days_per_week
    goal = user_profile.goal
    body_type = user_profile.body_type
    injuries = settings.injuries

    # اگر محدودیت‌های فیزیکی (مثلا آسیب‌ها) وجود داشته باشد، split را به full_body تغییر می‌دهیم.
    if injuries:
         return "full_body"

    if exp == "beginner" and (days <= 3):
         return "full_body"
    elif exp == "intermediate" and (3 <= days <= 4):
         return "upper_lower"
    elif exp == "expert" and (days >= 4):
         if (body_type == "mesomorph" or (goal == "muscle_gain")):
             return "bro_split"
         else:
             return "ppl"
    else:
         # در غیر این صورت، مقدار پیش‌فرض (یا مقدار فعلی) را برمی‌گردانیم.
         return settings.split_type


def update_split_if_needed(settings: TrainingSettings) -> Optional[str]:
    """
    بررسی می‌کند که آیا split_rotation_weeks هفته از آخرین به‌روزرسانی split گذشته است یا خیر؛ اگر بله، تابع get_optimal_split را فراخوانی می‌کند و مقدار split_type را به‌روز می‌کند و split_last_updated را نیز به‌روز می‌کند.
    """
    delta = datetime.datetime.now(datetime.timezone.utc) - settings.split_last_updated
    if delta.days >= (settings.split_rotation_weeks * 7):
         new_split = get_optimal_split(settings.user.userprofile, settings)
         if new_split != settings.split_type:
             settings.split_type = new_split
             settings.split_last_updated = datetime.datetime.now(datetime.timezone.utc)
             settings.save(update_fields=["split_type", "split_last_updated"])
             return new_split
    return None 