from typing import Dict, List
from django.utils import timezone
from accounts.models import UserProfile, TrainingSettings
from exercises.models import Exercise
from ..exercise_selector import ExerciseSelector
from ..volume_manager import WorkoutVolumeManager
from ..recovery_manager import RecoveryManager

class SplitStrategy:
    def __init__(self, user: UserProfile, settings: TrainingSettings, 
                 exercise_selector: ExerciseSelector, 
                 volume_manager: WorkoutVolumeManager,
                 recovery_manager: RecoveryManager):
        self.user = user
        self.settings = settings
        self.exercise_selector = exercise_selector
        self.volume_manager = volume_manager
        self.recovery_manager = recovery_manager
        self.split_map = {}
        
    def generate(self, week: int) -> Dict:
        """متد اصلی برای تولید برنامه"""
        raise NotImplementedError("Subclasses must implement generate method")
        
    def _add_warmup_cooldown(self, program: Dict):
        """افزودن گرم کردن و سرد کردن به برنامه"""
        for day, exercises in program['weekly_plan'].items():
            split_type = self.split_map.get(day)
            if split_type:
                warmup = self._get_warmup(split_type)
                cooldown = self._get_cooldown(split_type)
                program['weekly_plan'][day] = warmup + exercises + cooldown
                
    def _get_warmup(self, split_type: str) -> List[Dict]:
        """دریافت تمرینات گرم کردن"""
        return []
        
    def _get_cooldown(self, split_type: str) -> List[Dict]:
        """دریافت تمرینات سرد کردن"""
        return []
        
    def _validate_volume(self, program: Dict):
        """اعتبارسنجی حجم برنامه"""
        pass
        
    def _update_tracking(self, muscle: str, exercise: Exercise, volume: Dict):
        """به‌روزرسانی تاریخچه تمرین"""
        self.recovery_manager.last_trained[muscle].append(timezone.now())
        self.volume_manager.muscle_volume[muscle] += (
            self.volume_manager.calculate_volume(
                exercise, 
                volume['sets'], 
                volume['reps']
            )
        ) 