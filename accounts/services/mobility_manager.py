from typing import List, Dict
from exercises.models import Exercise
from accounts.models import UserProfile, TrainingSettings

class MobilityManager:
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        self.mobility_history = {}
        
    def get_mobility_exercises(self, target_areas: List[str] = None) -> List[Exercise]:
        """دریافت تمرینات موبیلیتی مناسب"""
        exercises = Exercise.objects.filter(
            type='mobility',
            difficulty__lte=self._get_max_difficulty()
        )
        
        if target_areas:
            exercises = exercises.filter(
                target_areas__overlap=target_areas
            )
            
        # فیلتر بر اساس محدودیت‌های فیزیکی
        exercises = self._filter_by_limitations(exercises)
        
        # اولویت‌بندی بر اساس تاریخچه
        exercises = self._prioritize_by_history(exercises)
        
        return list(exercises)
    
    def _get_max_difficulty(self) -> int:
        """تعیین حداکثر سختی تمرین موبیلیتی"""
        return {
            'beginner': 1,
            'intermediate': 2,
            'expert': 3
        }.get(self.settings.experience_level, 1)
    
    def _filter_by_limitations(self, exercises: List[Exercise]) -> List[Exercise]:
        """فیلتر تمرینات بر اساس محدودیت‌های فیزیکی"""
        if not self.user.physical_limitations:
            return exercises
            
        return exercises.exclude(
            contraindications__overlap=self.user.physical_limitations
        )
    
    def _prioritize_by_history(self, exercises: List[Exercise]) -> List[Exercise]:
        """اولویت‌بندی تمرینات بر اساس تاریخچه"""
        if not self.mobility_history:
            return exercises
            
        for exercise in exercises:
            last_trained = self.mobility_history.get(exercise.id, 0)
            exercise.priority = 7 - last_trained  # اولویت بیشتر برای تمرینات قدیمی‌تر
            
        return sorted(exercises, key=lambda x: x.priority, reverse=True)
    
    def update_history(self, exercise_id: int):
        """به‌روزرسانی تاریخچه تمرینات موبیلیتی"""
        self.mobility_history[exercise_id] = 0  # بازنشانی به 0
        
        # افزایش شمارنده برای سایر تمرینات
        for ex_id in self.mobility_history:
            if ex_id != exercise_id:
                self.mobility_history[ex_id] += 1
    
    def get_warmup_exercises(self, split_type: str) -> List[Exercise]:
        """دریافت تمرینات گرم کردن مناسب برای نوع split"""
        target_areas = {
            'push': ['shoulders', 'chest', 'triceps'],
            'pull': ['back', 'biceps', 'shoulders'],
            'legs': ['hips', 'knees', 'ankles'],
            'full_body': ['shoulders', 'hips', 'spine']
        }.get(split_type, ['shoulders', 'hips', 'spine'])
        
        return self.get_mobility_exercises(target_areas)
    
    def get_cooldown_exercises(self, split_type: str) -> List[Exercise]:
        """دریافت تمرینات سرد کردن مناسب برای نوع split"""
        target_areas = {
            'push': ['chest', 'shoulders'],
            'pull': ['back', 'shoulders'],
            'legs': ['quadriceps', 'hamstrings'],
            'full_body': ['major_muscle_groups']
        }.get(split_type, ['major_muscle_groups'])
        
        return self.get_mobility_exercises(target_areas) 