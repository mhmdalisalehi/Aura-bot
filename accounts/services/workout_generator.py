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

class WorkoutGenerator:
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        self.exercise_selector = ExerciseSelector(user, settings)
        self.volume_manager = WorkoutVolumeManager(user, settings)
        self.recovery_manager = RecoveryManager(user, settings)
        self.mobility_manager = MobilityManager(user, settings)
        
    def generate_workout(self, target_muscles: List[str], week: int) -> Dict:
        """تولید یک جلسه تمرین"""
        # بررسی امکان تمرین
        if not self.recovery_manager.can_train(target_muscles, datetime.now()):
            raise ValueError("عضلات هدف نیاز به استراحت دارند")
            
        # دریافت تمرینات مناسب
        exercises = self.exercise_selector.get_exercises(target_muscles, week)
        
        # تولید برنامه تمرین
        workout = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'target_muscles': target_muscles,
            'exercises': []
        }
        
        # اضافه کردن تمرینات
        for exercise in exercises:
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
            
            # اضافه کردن به برنامه
            workout['exercises'].append({
                'exercise_id': exercise.id,
                'exercise_name': exercise.name,
                'type': exercise.type,
                'muscle_group': exercise.primary_muscles[0],
                'sets': volume['sets'],
                'reps': volume['reps'],
                'rest_seconds': rest_time,
                'intensity': intensity,
                'notes': notes
            })
            
            # به‌روزرسانی تاریخچه
            self.exercise_selector.update_history(exercise.id, week)
            
        # اضافه کردن تمرینات گرم کردن
        warmup_exercises = self.mobility_manager.get_warmup_exercises(
            self.settings.split_type
        )
        workout['warmup'] = self._format_mobility_exercises(warmup_exercises)
        
        # اضافه کردن تمرینات سرد کردن
        cooldown_exercises = self.mobility_manager.get_cooldown_exercises(
            self.settings.split_type
        )
        workout['cooldown'] = self._format_mobility_exercises(cooldown_exercises)
        
        return workout
        
    def _format_mobility_exercises(self, exercises: List[Exercise]) -> List[Dict]:
        """فرمت‌بندی تمرینات موبیلیتی"""
        formatted = []
        
        for exercise in exercises:
            formatted.append({
                'exercise_id': exercise.id,
                'exercise_name': exercise.name,
                'type': 'mobility',
                'duration_seconds': 60,  # مدت زمان پیش‌فرض
                'notes': "روی فرم صحیح تمرکز کنید"
            })
            
        return formatted
        
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