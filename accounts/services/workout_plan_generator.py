from typing import Dict, List
from datetime import datetime, timedelta
from accounts.models import UserProfile, TrainingSettings
from exercises.models import Exercise
from .split_startegy.bro_split import BroSplitStrategy
from .split_startegy.ppl_strategy import PushPullLegsSplitStrategy
from .split_startegy.uperlower_strategy import UpperLowerSplitStrategy
from .split_startegy.fuulBody_strategy import FullBodySplitStrategy
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
from accounts.services.split_rotation_manager import update_split_if_needed
from accounts.services.date_converter import convert_day_to_date, convert_persian_to_english_weekday
import logging

def get_field(obj, field):
    if isinstance(obj, dict):
        return obj.get(field)
    return getattr(obj, field, None)

class WorkoutPlanGenerator:
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        self._initialize_managers()
        self._validate_managers()
        
    def _initialize_managers(self):
        """مقداردهی اولیه مدیران با مدیریت خطا"""
        try:
            self.exercise_selector = ExerciseSelector(self.user, self.settings)
            self.volume_manager = WorkoutVolumeManager(self.user, self.settings)
            self.recovery_manager = RecoveryManager(self.user, self.settings)
            self.mobility_manager = MobilityManager(self.user, self.settings)
            self.validator = WorkoutValidator(self.user, self.settings)
            
            # تنظیم مدیران در validator
            self.validator.set_managers(
                self.volume_manager,
                self.recovery_manager,
                self.mobility_manager,
                self.exercise_selector
            )
        except Exception as e:
            raise ValueError("Some managers are not initialized")
            
    def _validate_managers(self):
        """اعتبارسنجی مدیران"""
        if not all([
            self.exercise_selector,
            self.volume_manager,
            self.recovery_manager,
            self.mobility_manager,
            self.validator
        ]):
            raise ValueError("Some managers are not initialized")
            
    def generate_plan(self, weeks: int = 4) -> Dict:
        """تولید برنامه تمرینی با مدیریت خطا و همگام‌سازی"""
        try:
            # انتخاب استراتژی مناسب
            strategy = self._get_split_strategy()
            
            # تولید برنامه هفتگی
            weekly_plan = {}
            current_date = datetime.now()
            
            for week in range(weeks):
                # بررسی نیاز به کاهش بار
                if self.volume_manager._should_deload(week + 1):
                    weekly_plan.update(self._generate_deload_week(current_date, week + 1))
                    continue
                    
                # تولید برنامه برای هر هفته
                week_plan = strategy.generate(week + 1)
                
                # تبدیل نام روزهای هفته به تاریخ و اضافه کردن تاریخ‌ها و همگام‌سازی
                weekly_plan.update(self._add_dates_to_plan(week_plan, current_date))
                
                # فقط کلیدهایی که واقعا تاریخ هستند را در نظر بگیر
                date_keys = [day for day in weekly_plan.keys() if len(day) == 10 and day[4] == '-' and day[7] == '-']
                if date_keys:
                    current_date = max(
                        datetime.strptime(day, '%Y-%m-%d')
                        for day in date_keys
                    ) + timedelta(days=1)
            
            # تبدیل ساختار برنامه به فرمت مورد نیاز validator
            plain_weekly_plan = {}
            for day, day_plan in weekly_plan.items():
                # ترکیب همه تمرینات در یک لیست
                all_exercises = []
                if isinstance(day_plan, dict):
                    if 'warmup' in day_plan:
                        all_exercises.extend(day_plan['warmup'])
                    if 'main' in day_plan:
                        all_exercises.extend(day_plan['main'])
                    if 'cooldown' in day_plan:
                        all_exercises.extend(day_plan['cooldown'])
                else:
                    # اگر day_plan یک لیست است (مثلاً در حالت deload)
                    all_exercises.extend(day_plan)
                plain_weekly_plan[day] = all_exercises
            
            # اعتبارسنجی برنامه با ساختار مسطح
            is_valid, errors = self.validator.validate_program({'weekly_plan': plain_weekly_plan})
            if not is_valid:
                raise ValueError(f"Program is not valid: {', '.join(errors)}")
                
            # برگرداندن برنامه اصلی با ساختار کامل
            return {'weekly_plan': weekly_plan}
            
        except Exception as e:
            raise ValueError(f"Error in generating workout plan: {str(e)}")
            
    def _generate_deload_week(self, current_date: datetime, week: int) -> Dict:
        """تولید هفته کاهش بار"""
        deload_plan = {}
        strategy = self._get_split_strategy()
        # تولید برنامه با حجم کمتر
        base_plan = strategy.generate(week)
        for day, exercises in base_plan.items():
            deload_exercises = []
            for exercise in exercises:
                if not isinstance(exercise, dict):
                    continue  # فقط دیکشنری تمرین را قبول کن
                deload_exercise = exercise.copy()
                deload_exercise['sets'] = max(1, exercise['sets'] - 2)
                deload_exercise['reps'] = '12-15'  # تکرارهای سبک‌تر
                deload_exercises.append(deload_exercise)
            # تبدیل روزهای هفته از فارسی به انگلیسی
            training_days = [convert_persian_to_english_weekday(day) for day in self.settings.training_days.keys()]
            # اضافه کردن به برنامه
            training_date = get_next_training_day(
                current_date,
                training_days
            )
            deload_plan[training_date.strftime('%Y-%m-%d')] = deload_exercises
            current_date = training_date + timedelta(days=1)
        return deload_plan
        
    def _add_dates_to_plan(self, week_plan: Dict, current_date: datetime) -> Dict:
        dated_plan = {}
        for day, exercises in week_plan.items():
            if not exercises:
                logging.warning(f"No exercises generated for day {day}!")
            training_date = convert_day_to_date(day, current_date)
            target_muscles = []
            formatted_exercises = []
            warmups = []
            cooldowns = []
            for exercise in exercises:
                # فقط در این نقطه مدل را به dict تبدیل کن
                if hasattr(exercise, 'id'):
                    formatted_exercise = {
                        'exercise_id': exercise.id,
                        'exercise_name': exercise.name,
                        'type': getattr(exercise, 'type', 'compound'),
                        'muscle_group': exercise.primary_muscles[0] if exercise.primary_muscles else 'full_body',
                        'sets': getattr(exercise, 'sets', 3),
                        'reps': getattr(exercise, 'reps', '8-12'),
                        'rest_seconds': getattr(exercise, 'rest_seconds', 60),
                        'intensity': getattr(exercise, 'intensity', 0.7),
                        'notes': getattr(exercise, 'notes', '')
                    }
                    formatted_exercises.append(formatted_exercise)
                    if not target_muscles and exercise.primary_muscles:
                        target_muscles.extend(exercise.primary_muscles)
            if not target_muscles:
                target_muscles = ['full_body']
            if not self.recovery_manager.can_train(target_muscles, training_date):
                training_date = self._find_next_available_date(training_date, target_muscles)
            # اطمینان از وجود حداقل یک تمرین گرم کردن و سرد کردن
            if not warmups:
                warmups = [{
                    'exercise_id': 0,
                    'exercise_name': 'General Warmup',
                    'type': 'warmup',
                    'muscle_group': 'full_body',
                    'sets': 2,
                    'reps': '10-12',
                    'rest_seconds': 30,
                    'duration_seconds': 300,
                    'notes': 'General warmup for the workout'
                }]
            if not cooldowns:
                cooldowns = [{
                    'exercise_id': 0,
                    'exercise_name': 'General Cooldown',
                    'type': 'cooldown',
                    'muscle_group': 'full_body',
                    'sets': 2,
                    'reps': '30-45',
                    'rest_seconds': 45,
                    'duration_seconds': 300,
                    'notes': 'General cooldown for the workout'
                }]
            dated_plan[training_date.strftime('%Y-%m-%d')] = {
                'main': formatted_exercises,
                'warmup': warmups[:3],
                'cooldown': cooldowns[:3]
            }
            current_date = training_date + timedelta(days=1)
        return dated_plan
        
    def _find_next_available_date(self, start_date: datetime, target_muscles: List[str]) -> datetime:
        """یافتن تاریخ بعدی مناسب برای تمرین"""
        current_date = start_date
        max_attempts = 14  # حداکثر 2 هفته جلو می‌رویم
        
        for _ in range(max_attempts):
            if self.recovery_manager.can_train(target_muscles, current_date):
                return current_date
            current_date += timedelta(days=1)
            
        raise ValueError("Cannot find a suitable date for training")
        
    def _get_split_strategy(self):
        """انتخاب استراتژی مناسب با مدیریت خطا"""
        try:
            strategies = {
                'bro_split':   BroSplitStrategy,
                'ppl': PushPullLegsSplitStrategy,
                'upper_lower': UpperLowerSplitStrategy,
                'full_body': FullBodySplitStrategy
            }
            
            strategy_class = strategies.get(self.settings.split_type)
            if not strategy_class:
                raise ValueError(f"Invalid split type: {self.settings.split_type}")
                
            return strategy_class(
                self.user,
                self.settings,
                self.exercise_selector,
                self.volume_manager,
                self.recovery_manager
            )
        except Exception as e:
            raise ValueError(f"Error in selecting strategy: {str(e)}")
        
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
            raise ValueError(f"Program is not valid: {', '.join(errors)}")
            
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
        
    def _parse_duration(self, duration_str: str) -> int:
        """تبدیل رشته مدت زمان به ثانیه"""
        try:
            if 'min' in duration_str:
                minutes = int(duration_str.split('min')[0].strip())
                return minutes * 60
            elif 's' in duration_str:
                seconds = int(duration_str.split('s')[0].strip())
                return seconds
            else:
                return 60  # مقدار پیش‌فرض
        except (ValueError, AttributeError):
            return 60  # مقدار پیش‌فرض در صورت خطا 