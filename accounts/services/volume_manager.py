from typing import Dict, List
from exercises.models import Exercise
from accounts.models import UserProfile, TrainingSettings

class WorkoutVolumeManager:
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        self.muscle_volume = {}
        self.weekly_volume = {}
        
    def adjust_volume(self, muscle: str, week: int) -> Dict:
        """تنظیم حجم تمرین برای یک عضله در هفته مشخص"""
        base_volume = self._get_base_volume(muscle)
        adjusted_volume = self._adjust_for_experience(base_volume)
        adjusted_volume = self._adjust_for_recovery(adjusted_volume, muscle)
        adjusted_volume = self._adjust_for_progression(adjusted_volume, week)
        
        return adjusted_volume
    
    def _get_base_volume(self, muscle: str) -> Dict:
        """دریافت حجم پایه برای یک عضله"""
        base_volumes = {
            'chest': {'sets': 12, 'reps': '8-12'},
            'back': {'sets': 12, 'reps': '8-12'},
            'shoulders': {'sets': 9, 'reps': '8-12'},
            'biceps': {'sets': 6, 'reps': '10-12'},
            'triceps': {'sets': 6, 'reps': '10-12'},
            'quadriceps': {'sets': 12, 'reps': '8-12'},
            'hamstrings': {'sets': 9, 'reps': '8-12'},
            'calves': {'sets': 6, 'reps': '12-15'},
            'abs': {'sets': 6, 'reps': '12-15'}
        }
        return base_volumes.get(muscle, {'sets': 6, 'reps': '8-12'})
    
    def _adjust_for_experience(self, volume: Dict) -> Dict:
        """تنظیم حجم بر اساس تجربه کاربر"""
        experience_multiplier = {
            'beginner': 0.7,
            'intermediate': 1.0,
            'expert': 1.3
        }.get(self.settings.experience_level, 1.0)
        
        return {
            'sets': int(volume['sets'] * experience_multiplier),
            'reps': volume['reps']
        }
    
    def _adjust_for_recovery(self, volume: Dict, muscle: str) -> Dict:
        """تنظیم حجم بر اساس وضعیت ریکاوری"""
        if muscle in self.muscle_volume:
            current_volume = self.muscle_volume[muscle]
            if current_volume > self._get_volume_threshold(muscle):
                return {
                    'sets': int(volume['sets'] * 0.8),
                    'reps': volume['reps']
                }
        return volume
    
    def _adjust_for_progression(self, volume: Dict, week: int) -> Dict:
        """تنظیم حجم بر اساس پیشرفت"""
        if week > 1 and week % 4 == 0:  # افزایش حجم هر 4 هفته
            return {
                'sets': volume['sets'] + 1,
                'reps': volume['reps']
            }
        return volume
    
    def _get_volume_threshold(self, muscle: str) -> int:
        """دریافت آستانه حجم برای یک عضله"""
        thresholds = {
            'chest': 20,
            'back': 20,
            'shoulders': 15,
            'biceps': 10,
            'triceps': 10,
            'quadriceps': 20,
            'hamstrings': 15,
            'calves': 10,
            'abs': 10
        }
        return thresholds.get(muscle, 15)
    
    def calculate_volume(self, exercise: Exercise, sets: int, reps: str) -> int:
        """محاسبه حجم کل یک تمرین"""
        if isinstance(reps, str):
            reps = int(reps.split('-')[0])  # استفاده از حداقل تکرار
        return sets * reps
    
    def reset_weekly_volume(self):
        """بازنشانی حجم هفتگی"""
        self.weekly_volume = {} 