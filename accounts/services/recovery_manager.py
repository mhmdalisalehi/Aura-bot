from typing import List, Dict
from django.utils import timezone
from datetime import timedelta
from accounts.models import UserProfile, TrainingSettings

class RecoveryManager:
    MIN_RECOVERY_DAYS = {
        'chest': 2,
        'back': 2,
        'shoulders': 2,
        'biceps': 2,
        'triceps': 2,
        'quadriceps': 3,
        'hamstrings': 3,
        'glutes': 2,
        'calves': 2,
        'abs': 1
    }
    
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        self.last_trained = {}
        
    def can_train(self, muscles: List[str], current_time: timezone.datetime) -> bool:
        """بررسی امکان تمرین برای عضلات مشخص"""
        for muscle in muscles:
            if not self._check_recovery(muscle, current_time):
                return False
        return True
    
    def _check_recovery(self, muscle: str, current_time: timezone.datetime) -> bool:
        """بررسی وضعیت ریکاوری یک عضله"""
        if muscle not in self.last_trained:
            return True
            
        last_training = self.last_trained[muscle][-1]
        min_recovery = self.MIN_RECOVERY_DAYS.get(muscle, 2)
        
        recovery_time = current_time - last_training
        return recovery_time.days >= min_recovery
    
    def get_recovery_status(self, muscle: str) -> Dict:
        """دریافت وضعیت ریکاوری یک عضله"""
        if muscle not in self.last_trained:
            return {
                'can_train': True,
                'days_since_last_training': None,
                'min_recovery_days': self.MIN_RECOVERY_DAYS.get(muscle, 2)
            }
            
        last_training = self.last_trained[muscle][-1]
        days_since = (timezone.now() - last_training).days
        min_recovery = self.MIN_RECOVERY_DAYS.get(muscle, 2)
        
        return {
            'can_train': days_since >= min_recovery,
            'days_since_last_training': days_since,
            'min_recovery_days': min_recovery
        }
    
    def adjust_recovery_time(self, muscle: str, intensity: float):
        """تنظیم زمان ریکاوری بر اساس شدت تمرین"""
        if intensity > 0.8:  # شدت بالا
            self.MIN_RECOVERY_DAYS[muscle] = min(
                self.MIN_RECOVERY_DAYS.get(muscle, 2) + 1,
                4
            )
        elif intensity < 0.5:  # شدت پایین
            self.MIN_RECOVERY_DAYS[muscle] = max(
                self.MIN_RECOVERY_DAYS.get(muscle, 2) - 1,
                1
            )
    
    def reset_recovery_times(self):
        """بازنشانی زمان‌های ریکاوری"""
        self.last_trained = {} 