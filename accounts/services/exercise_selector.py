from typing import List, Dict
import random
from exercises.models import Exercise
from accounts.models import UserProfile, TrainingSettings

class ExerciseSelector:
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        self.exercise_history = {}
        
    def get_exercises(self, target_muscles: List[str], week: int) -> List[Exercise]:
        """دریافت تمرینات مناسب برای عضلات هدف"""
        exercises = Exercise.objects.filter(
            primary_muscles__overlap=target_muscles,
            difficulty__lte=self._get_max_difficulty(),
            equipment__in=self._get_available_equipment()
        )
        
        # فیلتر بر اساس تجربه کاربر
        exercises = self._filter_by_experience(exercises)
        
        # فیلتر بر اساس محدودیت‌های فیزیکی
        exercises = self._filter_by_limitations(exercises)
        
        # اولویت‌بندی بر اساس تاریخچه
        exercises = self._prioritize_by_history(exercises, week)
        
        return list(exercises)
    
    def _get_max_difficulty(self) -> int:
        """تعیین حداکثر سختی تمرین بر اساس تجربه کاربر"""
        return {
            'beginner': 2,
            'intermediate': 3,
            'expert': 4
        }.get(self.settings.experience_level, 2)
    
    def _get_available_equipment(self) -> List[str]:
        """دریافت تجهیزات در دسترس"""
        return self.settings.available_equipment or ['bodyweight']
    
    def _filter_by_experience(self, exercises: List[Exercise]) -> List[Exercise]:
        """فیلتر تمرینات بر اساس سطح تجربه"""
        if self.settings.experience_level == 'beginner':
            return exercises.filter(is_compound=False)
        return exercises
    
    def _filter_by_limitations(self, exercises: List[Exercise]) -> List[Exercise]:
        """فیلتر تمرینات بر اساس محدودیت‌های فیزیکی"""
        if not self.user.physical_limitations:
            return exercises
            
        return exercises.exclude(
            contraindications__overlap=self.user.physical_limitations
        )
    
    def _prioritize_by_history(self, exercises: List[Exercise], week: int) -> List[Exercise]:
        """اولویت‌بندی تمرینات بر اساس تاریخچه"""
        if not self.exercise_history:
            return exercises
            
        # محاسبه فاصله زمانی از آخرین تمرین
        for exercise in exercises:
            last_trained = self.exercise_history.get(exercise.id, 0)
            exercise.priority = week - last_trained
            
        return sorted(exercises, key=lambda x: x.priority, reverse=True)
    
    def update_history(self, exercise_id: int, week: int):
        """به‌روزرسانی تاریخچه تمرینات"""
        self.exercise_history[exercise_id] = week 