from typing import Dict, List
from datetime import datetime, timedelta
from accounts.models import UserProfile, TrainingSettings
from exercises.models import Exercise
from .split_strategies import (
    BroSplitStrategy,
    PushPullLegsSplitStrategy,
    UpperLowerSplitStrategy,
    FullBodySplitStrategy
)
from .exercise_selector import ExerciseSelector
from .volume_manager import WorkoutVolumeManager
from .recovery_manager import RecoveryManager
from .mobility_manager import MobilityManager
from .workout_validator import WorkoutValidator
from .workout_utils import (
    calculate_rest_time,
    calculate_intensity,
    get_next_training_day,
    get_muscle_groups_for_split
)

class WorkoutPlanGenerator:
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        self.exercise_selector = ExerciseSelector(user, settings)
        self.volume_manager = WorkoutVolumeManager(user, settings)
        self.recovery_manager = RecoveryManager(user, settings)
        self.mobility_manager = MobilityManager(user, settings)
        self.validator = WorkoutValidator(user, settings)
        
    def generate_plan(self, weeks: int = 4) -> Dict:
        """تولید برنامه تمرینی برای تعداد هفته‌های مشخص"""
        # انتخاب استراتژی مناسب
        strategy = self._get_split_strategy()
        
        # تولید برنامه هفتگی
        weekly_plan = {}
        current_date = datetime.now()
        
        for week in range(weeks):
            # تولید برنامه برای هر هفته
            week_plan = strategy.generate(week + 1)
            
            # اضافه کردن تاریخ‌ها
            for day, exercises in week_plan.items():
                training_date = get_next_training_day(
                    current_date,
                    list(self.settings.training_days.keys())
                )
                weekly_plan[training_date.strftime('%Y-%m-%d')] = exercises
                current_date = training_date + timedelta(days=1)
                
        # اعتبارسنجی برنامه
        is_valid, errors = self.validator.validate_program({'weekly_plan': weekly_plan})
        if not is_valid:
            raise ValueError(f"برنامه نامعتبر است: {', '.join(errors)}")
            
        return {
            'weekly_plan': weekly_plan,
            'metadata': self._get_plan_metadata(weeks)
        }
        
    def _get_split_strategy(self):
        """انتخاب استراتژی مناسب بر اساس تنظیمات"""
        strategies = {
            'bro_split': BroSplitStrategy,
            'push_pull_legs': PushPullLegsSplitStrategy,
            'upper_lower': UpperLowerSplitStrategy,
            'full_body': FullBodySplitStrategy
        }
        
        strategy_class = strategies.get(self.settings.split_type)
        if not strategy_class:
            raise ValueError(f"نوع split نامعتبر است: {self.settings.split_type}")
            
        return strategy_class(
            self.user,
            self.settings,
            self.exercise_selector,
            self.volume_manager,
            self.recovery_manager
        )
        
    def _get_plan_metadata(self, weeks: int) -> Dict:
        """دریافت متادیتای برنامه"""
        return {
            'user_id': self.user.id,
            'created_at': datetime.now().isoformat(),
            'weeks': weeks,
            'split_type': self.settings.split_type,
            'experience_level': self.settings.experience_level,
            'goal': self.user.goal,
            'available_equipment': self.settings.available_equipment,
            'training_days': list(self.settings.training_days.keys())
        }
        
    def adjust_plan(self, plan: Dict, feedback: Dict) -> Dict:
        """تنظیم برنامه بر اساس بازخورد"""
        # تنظیم حجم تمرینات
        if 'volume_feedback' in feedback:
            self._adjust_volume(plan, feedback['volume_feedback'])
            
        # تنظیم شدت تمرینات
        if 'intensity_feedback' in feedback:
            self._adjust_intensity(plan, feedback['intensity_feedback'])
            
        # تنظیم توالی تمرینات
        if 'sequence_feedback' in feedback:
            self._adjust_sequence(plan, feedback['sequence_feedback'])
            
        # اعتبارسنجی مجدد
        is_valid, errors = self.validator.validate_program(plan)
        if not is_valid:
            raise ValueError(f"برنامه تنظیم شده نامعتبر است: {', '.join(errors)}")
            
        return plan
        
    def _adjust_volume(self, plan: Dict, feedback: Dict):
        """تنظیم حجم تمرینات"""
        for day, exercises in plan['weekly_plan'].items():
            for exercise in exercises:
                muscle = exercise['muscle_group']
                if muscle in feedback:
                    # تنظیم تعداد ست‌ها
                    if 'sets' in feedback[muscle]:
                        exercise['sets'] = feedback[muscle]['sets']
                        
                    # تنظیم تعداد تکرارها
                    if 'reps' in feedback[muscle]:
                        exercise['reps'] = feedback[muscle]['reps']
                        
    def _adjust_intensity(self, plan: Dict, feedback: Dict):
        """تنظیم شدت تمرینات"""
        for day, exercises in plan['weekly_plan'].items():
            for exercise in exercises:
                if exercise['exercise_id'] in feedback:
                    # تنظیم زمان استراحت
                    if 'rest_seconds' in feedback[exercise['exercise_id']]:
                        exercise['rest_seconds'] = feedback[exercise['exercise_id']]['rest_seconds']
                        
    def _adjust_sequence(self, plan: Dict, feedback: Dict):
        """تنظیم توالی تمرینات"""
        for day, exercises in plan['weekly_plan'].items():
            if day in feedback:
                # جابجایی تمرینات
                new_sequence = feedback[day]
                plan['weekly_plan'][day] = [exercises[i] for i in new_sequence] 