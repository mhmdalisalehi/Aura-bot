from typing import Dict, List
from datetime import datetime
from accounts.models import UserProfile, TrainingSettings
from exercises.models import Exercise
from .exercise_selector import ExerciseSelector
from .volume_manager import WorkoutVolumeManager
from .recovery_manager import RecoveryManager
from .mobility_manager import MobilityManager
from .workout_utils import (
    calculate_rest_time,
    calculate_intensity,
    get_exercise_notes
)
from .workout_validator import WorkoutValidator

class WorkoutGenerator:
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
            raise ValueError(f"Error in initializing managers: {str(e)}")
            
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
            
    def generate_workout(self, target_muscles: List[str], week: int) -> Dict:
        """تولید یک جلسه تمرین با مدیریت خطا و همگام‌سازی"""
        try:
            # بررسی امکان تمرین
            if not self.recovery_manager.can_train(target_muscles, datetime.now()):
                raise ValueError("Target muscles need rest")
                
            # دریافت تمرینات مناسب
            exercises = self.exercise_selector.get_exercises(
                target_muscles,
                week,
                include_warmup=True,
                include_cooldown=True
            )
            
            # تولید برنامه تمرین
            workout = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'target_muscles': target_muscles,
                'exercises': []
            }
            
            # اضافه کردن تمرینات با همگام‌سازی
            for exercise_tuple in exercises.get('main', []):
                exercise = exercise_tuple[0] if isinstance(exercise_tuple, tuple) else exercise_tuple
                exercise_data = self._prepare_exercise_data(exercise, week)
                workout['exercises'].append(exercise_data)
                if hasattr(exercise, 'id'):
                    self.exercise_selector.update_history(exercise.id, week)
            # اضافه کردن تمرینات گرم کردن و سرد کردن
            workout['warmup'] = self._format_mobility_exercises(
                [item[0] if isinstance(item, tuple) else item for item in exercises.get('warmup', [])],
                'warmup'
            )
            workout['cooldown'] = self._format_mobility_exercises(
                [item[0] if isinstance(item, tuple) else item for item in exercises.get('cooldown', [])],
                'cooldown'
            )
            
            # اعتبارسنجی برنامه
            is_valid, errors = self.validator.validate_workout(workout)
            if not is_valid:
                raise ValueError(f"Workout is not valid: {', '.join(errors)}")
                
            return workout
            
        except Exception as e:
            raise ValueError(f"Error in generating workout: {str(e)}")
            
    def _prepare_exercise_data(self, exercise: Exercise, week: int) -> Dict:
        """آماده‌سازی داده‌های تمرین با همگام‌سازی"""
        try:
            # تنظیم حجم تمرین
            volume = self.volume_manager.adjust_volume(
                exercise.primary_muscles[0],
                week
            )
            
            # محاسبه زمان استراحت
            rest_time = calculate_rest_time(exercise, self.settings.experience_level)
            
            # محاسبه شدت
            intensity = calculate_intensity(exercise, volume['sets'], volume['reps'])
            
            # دریافت نکات
            notes = get_exercise_notes(exercise, self.settings.experience_level)
            
            return {
                'exercise_id': exercise.id,
                'exercise_name': exercise.name,
                'type': exercise.type,
                'muscle_group': exercise.primary_muscles[0],
                'sets': volume['sets'],
                'reps': volume['reps'],
                'rest_seconds': rest_time,
                'intensity': intensity,
                'notes': notes
            }
        except Exception as e:
            raise ValueError(f"Error in preparing exercise data: {str(e)}")
            
    def _format_mobility_exercises(self, exercises: List, exercise_type: str) -> List[Dict]:
        """فرمت‌بندی تمرینات موبیلیتی با مدیریت خطا"""
        try:
            formatted = []
            for item in exercises:
                exercise = item[0] if isinstance(item, tuple) else item
                formatted.append({
                    'exercise_id': exercise.id,
                    'exercise_name': exercise.name,
                    'type': exercise_type,
                    'duration_seconds': self._get_mobility_duration(exercise_type),
                    'notes': self._get_mobility_notes(exercise_type)
                })
            return formatted
        except Exception as e:
            raise ValueError(f"Error in formatting mobility exercises: {str(e)}")
            
    def _get_mobility_duration(self, exercise_type: str) -> int:
        """دریافت مدت زمان تمرینات موبیلیتی"""
        return 60 if exercise_type == 'warmup' else 45
        
    def _get_mobility_notes(self, exercise_type: str) -> str:
        """دریافت نکات تمرینات موبیلیتی"""
        return "روی فرم صحیح تمرکز کنید" if exercise_type == 'warmup' else "کشش ملایم و آرام"
        
    def adjust_workout(self, workout: Dict, feedback: Dict) -> Dict:
        """تنظیم تمرین بر اساس بازخورد"""
        # تنظیم حجم تمرینات
        if 'volume_feedback' in feedback:
            self._adjust_volume(workout, feedback['volume_feedback'])
            
        # تنظیم شدت تمرینات
        if 'intensity_feedback' in feedback:
            self._adjust_intensity(workout, feedback['intensity_feedback'])
            
        # تنظیم توالی تمرینات
        if 'sequence_feedback' in feedback:
            self._adjust_sequence(workout, feedback['sequence_feedback'])
            
        return workout
        
    def _adjust_volume(self, workout: Dict, feedback: Dict):
        """تنظیم حجم تمرینات"""
        for exercise in workout['exercises']:
            muscle = exercise['muscle_group']
            if muscle in feedback:
                # تنظیم تعداد ست‌ها
                if 'sets' in feedback[muscle]:
                    exercise['sets'] = feedback[muscle]['sets']
                    
                # تنظیم تعداد تکرارها
                if 'reps' in feedback[muscle]:
                    exercise['reps'] = feedback[muscle]['reps']
                    
    def _adjust_intensity(self, workout: Dict, feedback: Dict):
        """تنظیم شدت تمرینات"""
        for exercise in workout['exercises']:
            if exercise['exercise_id'] in feedback:
                # تنظیم زمان استراحت
                if 'rest_seconds' in feedback[exercise['exercise_id']]:
                    exercise['rest_seconds'] = feedback[exercise['exercise_id']]['rest_seconds']
                    
    def _adjust_sequence(self, workout: Dict, feedback: Dict):
        """تنظیم توالی تمرینات"""
        if 'new_sequence' in feedback:
            # جابجایی تمرینات
            workout['exercises'] = [
                workout['exercises'][i] for i in feedback['new_sequence']
            ] 