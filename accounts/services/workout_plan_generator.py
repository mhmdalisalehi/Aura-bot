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
    get_muscle_groups_for_split,
    get_exercise_notes
)
from accounts.services.split_rotation_manager import update_split_if_needed
from accounts.services.date_converter import convert_day_to_date, convert_persian_to_english_weekday
import logging
from .base_manager import BaseWorkoutManager

def get_field(obj, field):
    if isinstance(obj, dict):
        return obj.get(field)
    return getattr(obj, field, None)

class WorkoutPlanGenerator(BaseWorkoutManager):
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        super().__init__(user, settings)
        
    def generate_plan(self) -> Dict:
        try:
            strategy = self._get_split_strategy()
            weekly_plan = {}
            current_date = datetime.now()
            week_plan = strategy.generate(1)
            weekly_plan.update(self._add_dates_to_plan(week_plan['weekly_plan'], current_date))
            # Flatten and validate
            plain_weekly_plan = {}
            # Ensure all exercises have required fields for validation
            def ensure_required_fields(ex):
                required_fields = [
                    'exercise_id', 'exercise_name', 'type', 'muscle_group', 'sets', 'reps', 'rest_seconds'
                ]
                defaults = {
                    'exercise_id': 0,
                    'exercise_name': 'Unknown',
                    'type': 'unknown',
                    'muscle_group': 'full_body',
                    'sets': 1,
                    'reps': '8-12',
                    'rest_seconds': 30
                }
                if isinstance(ex, dict):
                    for k in required_fields:
                        if k not in ex:
                            ex[k] = defaults[k]
                return ex

            def expand_and_ensure_fields(ex, ex_type=None):
                # If this is a container (has 'content'), expand it
                if isinstance(ex, dict) and 'content' in ex:
                    expanded = []
                    for idx, item in enumerate(ex['content']):
                        # Map fields from content item to required fields
                        exercise_dict = {
                            'exercise_id': 0,
                            'exercise_name': item.get('name', f'Unknown {ex_type or ex.get("type", "")}{idx+1}') if isinstance(item, dict) else str(item),
                            'type': ex_type or ex.get('type', 'mobility'),
                            'muscle_group': 'full_body',
                            'sets': 1,
                            'reps': '8-12',
                            'rest_seconds': 30,
                            'duration_seconds': 60,
                            'notes': item.get('notes', '') if isinstance(item, dict) else ''
                        }
                        # Try to map duration if present
                        if isinstance(item, dict):
                            dur = item.get('duration')
                            if dur:
                                # Parse duration string (e.g., '60s', '45s each leg')
                                try:
                                    if 'min' in dur:
                                        mins = int(dur.split('min')[0].strip())
                                        exercise_dict['duration_seconds'] = mins * 60
                                    elif 's' in dur:
                                        secs = int(dur.split('s')[0].strip())
                                        exercise_dict['duration_seconds'] = secs
                                except Exception:
                                    pass
                        expanded.append(exercise_dict)
                    return expanded
                else:
                    return [ensure_required_fields(ex)]

            for day, day_plan in weekly_plan.items():
                all_exercises = []
                if isinstance(day_plan, dict):
                    if 'warmup' in day_plan:
                        for e in day_plan['warmup']:
                            all_exercises.extend(expand_and_ensure_fields(e, 'warmup'))
                    if 'main' in day_plan:
                        all_exercises.extend([ensure_required_fields(e) for e in day_plan['main']])
                    if 'cooldown' in day_plan:
                        for e in day_plan['cooldown']:
                            all_exercises.extend(expand_and_ensure_fields(e, 'cooldown'))
                else:
                    all_exercises.extend([ensure_required_fields(e) for e in day_plan])
                # --- Convert all dicts to SimpleNamespace for attribute access ---
                from types import SimpleNamespace
                def dict_to_namespace(d):
                    if isinstance(d, dict):
                        return SimpleNamespace(**d)
                    return d
                all_exercises = [dict_to_namespace(ex) if isinstance(ex, dict) else ex for ex in all_exercises]
                plain_weekly_plan[day] = all_exercises
            is_valid, errors = self.validator.validate_program({'weekly_plan': plain_weekly_plan})
            if not is_valid:
                print("\n[VALIDATION ERROR] Program structure is not valid!")
                print("[VALIDATION ERROR] Validation errors:", errors)
                print("[VALIDATION ERROR] Problematic plan structure:")
                import pprint; pprint.pprint(plain_weekly_plan)
                raise ValueError(f"Program is not valid: {', '.join(errors)}")
            print(f"[INFO] Plan validated successfully.")
            return {'weekly_plan': plain_weekly_plan}
        except Exception as e:
            print(f"[ERROR] Exception in generate_plan: {str(e)}")
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
                # [WARNING] No exercises generated for day {day}!
                pass
            training_date = convert_day_to_date(day, current_date)
            target_muscles = []
            main_exercises = []
            warmups = []
            cooldowns = []
            # Robustly handle both list and dict day plans
            if isinstance(exercises, dict):
                # Already split by keys
                main_items = exercises.get('main', [])
                # If main_items are already dicts, add them directly
                if main_items and all(isinstance(ex, dict) for ex in main_items):
                    main_exercises = main_items
                else:
                    for ex in main_items:
                        if isinstance(ex, dict):
                            main_exercises.append(ex)
                        elif hasattr(ex, 'id') and hasattr(ex, 'name'):
                            main_exercises.append({
                                'exercise_id': ex.id,
                                'exercise_name': ex.name,
                                'type': getattr(ex, 'type', 'compound'),
                                'muscle_group': ex.primary_muscles[0] if hasattr(ex, 'primary_muscles') and ex.primary_muscles else 'full_body',
                                'sets': getattr(ex, 'sets', 3),
                                'reps': getattr(ex, 'reps', '8-12'),
                                'rest_seconds': getattr(ex, 'rest_seconds', 60),
                                'intensity': getattr(ex, 'intensity', 0.7),
                                'notes': getattr(ex, 'notes', '')
                            })
                warmups = exercises.get('warmup', [])
                cooldowns = exercises.get('cooldown', [])
                items = []  # Already handled above
            else:
                items = exercises
            for exercise in items:
                # Convert Exercise model to dict
                if hasattr(exercise, 'id') and hasattr(exercise, 'name'):
                    formatted_exercise = {
                        'exercise_id': exercise.id,
                        'exercise_name': exercise.name,
                        'type': getattr(exercise, 'type', 'compound'),
                        'muscle_group': exercise.primary_muscles[0] if hasattr(exercise, 'primary_muscles') and exercise.primary_muscles else 'full_body',
                        'sets': getattr(exercise, 'sets', 3),
                        'reps': getattr(exercise, 'reps', '8-12'),
                        'rest_seconds': getattr(exercise, 'rest_seconds', 60),
                        'intensity': getattr(exercise, 'intensity', 0.7),
                        'notes': getattr(exercise, 'notes', '')
                    }
                    # Place warmup/cooldown/main by type
                    t = formatted_exercise.get('type', '').lower()
                    if t == 'warmup':
                        warmups.append(formatted_exercise)
                    elif t == 'cooldown':
                        cooldowns.append(formatted_exercise)
                    elif t not in ('warmup', 'cooldown', 'mobility'):
                        main_exercises.append(formatted_exercise)
                    if not target_muscles and hasattr(exercise, 'primary_muscles') and exercise.primary_muscles:
                        target_muscles.extend(exercise.primary_muscles)
                elif isinstance(exercise, dict):
                    t = exercise.get('type', '').lower()
                    if t == 'warmup':
                        warmups.append(exercise)
                    elif t == 'cooldown':
                        cooldowns.append(exercise)
                    elif t not in ('warmup', 'cooldown', 'mobility'):
                        # treat as main exercise dict
                        main_exercises.append(exercise)
            if not target_muscles:
                target_muscles = ['full_body']
            if not self.recovery_manager.can_train(target_muscles, training_date):
                # [WARNING] Recovery manager blocked training for {target_muscles} on {training_date}
                training_date = self._find_next_available_date(training_date, target_muscles)
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
                'main': main_exercises,
                'warmup': warmups[:3],
                'cooldown': cooldowns[:3]
            }
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
    
    def save_plan_to_db(self, plan: Dict, weeks: int = 4):
        """
        Save the generated plan (output of generate_plan) to the normalized database models.
        """
        from accounts.models import WorkoutPlan, WorkoutDay, WorkoutExercise
        # Create WorkoutPlan
        workout_plan = WorkoutPlan.objects.create(
            user=self.user.user,
            settings=self.settings,
            weeks=weeks,
            split_type=self.settings.split_type,
            experience_level=self.settings.experience_level,
            goal=self.user.goal,
            available_equipment=self.settings.available_equipment,
            training_days=self.settings.training_days
        )
        # Save each day
        for day_idx, (date_str, exercises) in enumerate(plan['weekly_plan'].items()):
            workout_day = WorkoutDay.objects.create(
                plan=workout_plan,
                date=date_str,
                order=day_idx
            )
            # Save each exercise
            for ex_idx, exercise in enumerate(exercises):
                ex_obj = None
                if 'exercise_id' in exercise and exercise['exercise_id']:
                    try:
                        ex_obj = Exercise.objects.get(id=exercise['exercise_id'])
                    except Exercise.DoesNotExist:
                        ex_obj = None
                WorkoutExercise.objects.create(
                    day=workout_day,
                    exercise=ex_obj,
                    exercise_name=exercise.get('exercise_name', ''),
                    type=exercise.get('type', ''),
                    muscle_group=exercise.get('muscle_group', ''),
                    sets=exercise.get('sets', 0),
                    reps=exercise.get('reps', ''),
                    rest_seconds=exercise.get('rest_seconds', 60),
                    intensity=exercise.get('intensity', 0.7),
                    notes=exercise.get('notes', ''),
                    order=ex_idx
                )
        return workout_plan