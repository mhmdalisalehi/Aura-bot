import datetime
from typing import Optional
from accounts.models import TrainingSettings, UserProfile

from logger_util import get_logger
logger = get_logger('split_rotation_manager', 'logs/split_rotation_manager.log')

def get_optimal_split(user_profile: UserProfile, settings: TrainingSettings) -> str:
    """
    انتخاب هوشمند split بر اساس تجربه، هدف، تعداد روزهای تمرین، تیپ بدنی و محدودیت‌ها (مثلا آسیب‌ها) به عنوان یک مربی حرفه‌ای.
    """
    exp = settings.experience_level
    days = settings.training_days_per_week
    goal = user_profile.goal
    body_type = user_profile.body_type
    injuries = settings.injuries

    logger.info(f"Evaluating optimal split for user {user_profile.id}: exp={exp}, days={days}, goal={goal}, body_type={body_type}, injuries={injuries}")

    if injuries:
        logger.info("User has injuries, forcing split to 'full_body'")
        return "full_body"

    if exp == "beginner" and (days <= 3):
        logger.info("Beginner with <=3 days: split='full_body'")
        return "full_body"
    elif exp == "intermediate" and (3 <= days <= 4):
        logger.info("Intermediate with 3-4 days: split='upper_lower'")
        return "upper_lower"
    elif exp == "expert" and (days >= 4):
        if (body_type == "mesomorph" or (goal == "muscle_gain")):
            logger.info("Expert, mesomorph or muscle_gain: split='bro_split'")
            return "bro_split"
        else:
            logger.info("Expert, not mesomorph/muscle_gain: split='ppl'")
            return "ppl"
    else:
        logger.info(f"Defaulting to current split: {settings.split_type}")
        return settings.split_type

def update_split_if_needed(settings: TrainingSettings) -> Optional[str]:
    """
    بررسی می‌کند که آیا split_rotation_weeks هفته از آخرین به‌روزرسانی split گذشته است یا خیر؛ اگر بله، تابع get_optimal_split را فراخوانی می‌کند و مقدار split_type را به‌روز می‌کند و split_last_updated را نیز به‌روز می‌کند.
    """
    delta = datetime.datetime.now(datetime.timezone.utc) - settings.split_last_updated
    logger.info(f"Checking if split update is needed. Days since last update: {delta.days}, rotation period: {settings.split_rotation_weeks * 7} days")
    if delta.days >= (settings.split_rotation_weeks * 7):
        new_split = get_optimal_split(settings.user.userprofile, settings)
        if new_split != settings.split_type:
            logger.info(f"Updating split_type from {settings.split_type} to {new_split}")
            settings.split_type = new_split
            settings.split_last_updated = datetime.datetime.now(datetime.timezone.utc)
            settings.save(update_fields=["split_type", "split_last_updated"])
            return new_split
        else:
            logger.info("Optimal split is the same as current. No update needed.")
    else:
        logger.info("Split rotation period not reached. No update performed.")