from typing import Dict, List, Tuple
from accounts.models import UserProfile, TrainingSettings
from exercises.models import Exercise

class WorkoutValidator:
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        
    def validate_program(self, program: Dict) -> Tuple[bool, List[str]]:
        """اعتبارسنجی کامل برنامه تمرینی"""
        errors = []
        
        # بررسی ساختار برنامه
        if not self._validate_structure(program):
            errors.append("ساختار برنامه نامعتبر است")
            
        # بررسی حجم تمرینات
        volume_errors = self._validate_volume(program)
        errors.extend(volume_errors)
        
        # بررسی توالی تمرینات
        sequence_errors = self._validate_sequence(program)
        errors.extend(sequence_errors)
        
        # بررسی محدودیت‌های فیزیکی
        limitation_errors = self._validate_limitations(program)
        errors.extend(limitation_errors)
        
        return len(errors) == 0, errors
    
    def _validate_structure(self, program: Dict) -> bool:
        """اعتبارسنجی ساختار برنامه"""
        required_keys = ['weekly_plan']
        if not all(key in program for key in required_keys):
            return False
            
        if not isinstance(program['weekly_plan'], dict):
            return False
            
        for day, exercises in program['weekly_plan'].items():
            if not isinstance(exercises, list):
                return False
                
            for exercise in exercises:
                if not self._validate_exercise_structure(exercise):
                    return False
                    
        return True
    
    def _validate_exercise_structure(self, exercise: Dict) -> bool:
        """اعتبارسنجی ساختار یک تمرین"""
        required_keys = ['exercise_id', 'exercise_name', 'type', 'muscle_group', 'sets', 'reps']
        return all(key in exercise for key in required_keys)
    
    def _validate_volume(self, program: Dict) -> List[str]:
        """اعتبارسنجی حجم تمرینات"""
        errors = []
        muscle_volume = {}
        
        for day, exercises in program['weekly_plan'].items():
            for exercise in exercises:
                muscle = exercise['muscle_group']
                if muscle not in muscle_volume:
                    muscle_volume[muscle] = 0
                    
                volume = self._calculate_exercise_volume(exercise)
                muscle_volume[muscle] += volume
                
                # بررسی حجم هر تمرین
                if not self._is_valid_exercise_volume(exercise):
                    errors.append(f"حجم تمرین {exercise['exercise_name']} نامعتبر است")
        
        # بررسی حجم کل هر عضله
        for muscle, volume in muscle_volume.items():
            if not self._is_valid_muscle_volume(muscle, volume):
                errors.append(f"حجم کل تمرینات برای {muscle} نامعتبر است")
                
        return errors
    
    def _calculate_exercise_volume(self, exercise: Dict) -> int:
        """محاسبه حجم یک تمرین"""
        sets = exercise['sets']
        reps = exercise['reps']
        if isinstance(reps, str):
            reps = int(reps.split('-')[0])
        return sets * reps
    
    def _is_valid_exercise_volume(self, exercise: Dict) -> bool:
        """بررسی اعتبار حجم یک تمرین"""
        sets = exercise['sets']
        reps = exercise['reps']
        
        if not isinstance(sets, int) or sets < 1 or sets > 10:
            return False
            
        if isinstance(reps, str):
            try:
                min_reps, max_reps = map(int, reps.split('-'))
                if min_reps < 1 or max_reps > 30 or min_reps > max_reps:
                    return False
            except:
                return False
                
        return True
    
    def _is_valid_muscle_volume(self, muscle: str, volume: int) -> bool:
        """بررسی اعتبار حجم کل یک عضله"""
        max_volumes = {
            'chest': 100,
            'back': 100,
            'shoulders': 80,
            'biceps': 50,
            'triceps': 50,
            'quadriceps': 100,
            'hamstrings': 80,
            'calves': 50,
            'abs': 50
        }
        return volume <= max_volumes.get(muscle, 80)
    
    def _validate_sequence(self, program: Dict) -> List[str]:
        """اعتبارسنجی توالی تمرینات"""
        errors = []
        trained_muscles = {}
        
        for day, exercises in program['weekly_plan'].items():
            for exercise in exercises:
                muscle = exercise['muscle_group']
                if muscle not in trained_muscles:
                    trained_muscles[muscle] = []
                trained_muscles[muscle].append(day)
                
        for muscle, days in trained_muscles.items():
            if len(days) > 1:
                for i in range(1, len(days)):
                    if (days[i] - days[i-1]).days < self._get_min_recovery_days(muscle):
                        errors.append(f"زمان استراحت برای {muscle} کافی نیست")
                        
        return errors
    
    def _get_min_recovery_days(self, muscle: str) -> int:
        """دریافت حداقل روزهای استراحت برای یک عضله"""
        recovery_days = {
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
        return recovery_days.get(muscle, 2)
    
    def _validate_limitations(self, program: Dict) -> List[str]:
        """اعتبارسنجی محدودیت‌های فیزیکی"""
        errors = []
        
        if not self.user.physical_limitations:
            return errors
            
        for day, exercises in program['weekly_plan'].items():
            for exercise in exercises:
                if not self._is_exercise_safe(exercise):
                    errors.append(f"تمرین {exercise['exercise_name']} با محدودیت‌های فیزیکی سازگار نیست")
                    
        return errors
    
    def _is_exercise_safe(self, exercise: Dict) -> bool:
        """بررسی سازگاری تمرین با محدودیت‌های فیزیکی"""
        try:
            ex = Exercise.objects.get(id=exercise['exercise_id'])
            return not any(
                limitation in ex.contraindications
                for limitation in self.user.physical_limitations
            )
        except Exercise.DoesNotExist:
            return False 