from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from accounts.models import UserProfile, TrainingSettings
from exercises.models import Exercise
import logging

class WorkoutValidator:
    """
    اعتبارسنجی حرفه‌ای برنامه تمرینی
    - بررسی تعادل و توالی تمرینات
    - بررسی سازگاری با محدودیت‌های فیزیکی
    - همگام‌سازی با سایر بخش‌های برنامه
    - بررسی پیشرفت و ریکاوری
    """
    
    # محدودیت‌های حجمی برای هر عضله (مجموع ست‌ها در هفته)
    VOLUME_LIMITS = {
        'chest': {'min': 8, 'max': 20},
        'back': {'min': 8, 'max': 20},
        'shoulders': {'min': 6, 'max': 15},
        'biceps': {'min': 4, 'max': 12},
        'triceps': {'min': 4, 'max': 12},
        'quadriceps': {'min': 8, 'max': 20},
        'hamstrings': {'min': 6, 'max': 15},
        'calves': {'min': 4, 'max': 12},
        'abs': {'min': 4, 'max': 12}
    }
    
    # محدودیت‌های شدت برای هر نوع تمرین
    INTENSITY_LIMITS = {
        'compound': {'min': 3, 'max': 8},    # ست‌ها
        'isolation': {'min': 2, 'max': 4},   # ست‌ها
        'accessory': {'min': 2, 'max': 3}    # ست‌ها
    }
    
    # محدوده تکرار برای هر هدف
    REP_RANGES = {
        'muscle_gain': {'min': 6, 'max': 12},
        'strength': {'min': 3, 'max': 6},
        'weight_loss': {'min': 12, 'max': 20},
        'endurance': {'min': 15, 'max': 30}
    }
    
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        self.volume_manager = None
        self.recovery_manager = None
        self.mobility_manager = None
        self.exercise_selector = None
        self._validate_initialization()
        
    def _validate_initialization(self):
        """اعتبارسنجی مقداردهی اولیه"""
        if not self.user or not self.settings:
            raise ValueError("User and settings must be provided")
            
    def set_managers(self, volume_manager, recovery_manager, mobility_manager, exercise_selector):
        """تنظیم مدیران مورد نیاز برای اعتبارسنجی
        
        Args:
            volume_manager: مدیر حجم تمرین
            recovery_manager: مدیر ریکاوری
            mobility_manager: مدیر موبایلیتی
            exercise_selector: انتخاب‌گر تمرینات
        """
        self.volume_manager = volume_manager
        self.recovery_manager = recovery_manager
        self.mobility_manager = mobility_manager
        self.exercise_selector = exercise_selector
        
    def validate_program(self, program: Dict) -> Tuple[bool, List[str]]:
        logging.info(f"validate_program called with program: {program}")
        try:
            errors = []
            
            # بررسی ساختار برنامه
            if not self._validate_structure(program):
                logging.warning("Program structure is not valid")
                errors.append("Program structure is not valid")
                return False, errors
                
            # بررسی تعادل تمرینات
            balance_errors = self._validate_exercise_balance(program)
            logging.info(f"balance_errors: {balance_errors}")
            errors.extend(balance_errors)
            
            # بررسی حجم تمرینات
            volume_errors = self._validate_volume(program)
            logging.info(f"volume_errors: {volume_errors}")
            errors.extend(volume_errors)
            
            # بررسی توالی تمرینات
            sequence_errors = self._validate_sequence(program)
            logging.info(f"sequence_errors: {sequence_errors}")
            errors.extend(sequence_errors)
            
            # بررسی محدودیت‌های فیزیکی
            limitation_errors = self._validate_limitations(program)
            logging.info(f"limitation_errors: {limitation_errors}")
            errors.extend(limitation_errors)
            
            # بررسی ریکاوری
            if self.recovery_manager:
                recovery_errors = self._validate_recovery(program)
                logging.info(f"recovery_errors: {recovery_errors}")
                errors.extend(recovery_errors)
            else:
                logging.warning("Recovery manager is not set")
                errors.append("Recovery manager is not set")
                
            # بررسی موبیلیتی
            if self.mobility_manager:
                mobility_errors = self._validate_mobility(program)
                logging.info(f"mobility_errors: {mobility_errors}")
                errors.extend(mobility_errors)
            else:
                logging.warning("Mobility manager is not set")
                errors.append("Mobility manager is not set")
                
            logging.info(f"validate_program result: {len(errors) == 0}, errors: {errors}")
            return len(errors) == 0, errors
            
        except Exception as e:
            logging.error(f"Exception in validate_program: {str(e)}")
            return False, [f"Error in program validation: {str(e)}"]
            
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
    
    def _validate_exercise_structure(self, exercise) -> bool:
        """اعتبارسنجی ساختار یک تمرین"""
        required_fields = [
            'exercise_id', 'exercise_name', 'type', 
            'muscle_group', 'sets', 'reps', 'rest_seconds'
        ]
        if isinstance(exercise, dict):
            return all(field in exercise for field in required_fields)
        return all(hasattr(exercise, field) for field in required_fields)
    
    def _validate_exercise_balance(self, program: Dict) -> List[str]:
        """بررسی تعادل تمرینات"""
        errors = []
        exercise_counts = {}
        muscle_counts = {}
        for day, exercises in program['weekly_plan'].items():
            # شمارش تمرینات هر نوع
            for exercise in exercises:
                ex_type = exercise['type'] if isinstance(exercise, dict) else exercise.type
                muscle = exercise['muscle_group'] if isinstance(exercise, dict) else exercise.muscle_group
                exercise_counts[ex_type] = exercise_counts.get(ex_type, 0) + 1
                muscle_counts[muscle] = muscle_counts.get(muscle, 0) + 1
        # بررسی تعادل نوع تمرینات
        for ex_type, count in exercise_counts.items():
            limits = self.INTENSITY_LIMITS.get(ex_type, {'min': 2, 'max': 5})
            if count < limits['min']:
                errors.append(f"Number of {ex_type} exercises is less than allowed")
            elif count > limits['max']:
                errors.append(f"Number of {ex_type} exercises is more than allowed")
        # بررسی تعادل عضلات
        for muscle, count in muscle_counts.items():
            limits = self.VOLUME_LIMITS.get(muscle, {'min': 4, 'max': 12})
            if count < limits['min']:
                errors.append(f"Number of {muscle} exercises is less than allowed")
            elif count > limits['max']:
                errors.append(f"Number of {muscle} exercises is more than allowed")
        return errors
    
    def _validate_volume(self, program: Dict) -> List[str]:
        """اعتبارسنجی حجم تمرینات"""
        errors = []
        muscle_volume = {}
        
        for day, exercises in program['weekly_plan'].items():
            for exercise in exercises:
                muscle = exercise.muscle_group
                if muscle not in muscle_volume:
                    muscle_volume[muscle] = 0
                    
                volume = self._calculate_exercise_volume(exercise)
                muscle_volume[muscle] += volume
                
                # بررسی حجم هر تمرین
                if not self._is_valid_exercise_volume(exercise):
                    errors.append(f"Volume of exercise {exercise.exercise_name} is not valid")
        
        # بررسی حجم کل هر عضله
        for muscle, volume in muscle_volume.items():
            if not self._is_valid_muscle_volume(muscle, volume):
                errors.append(f"Total volume for {muscle} is not valid")
                
        return errors
    
    def _calculate_exercise_volume(self, exercise: Exercise) -> int:
        """محاسبه حجم یک تمرین"""
        sets = exercise.sets
        reps = exercise.reps
        if isinstance(reps, str):
            reps = int(reps.split('-')[0])
        return sets * reps
    
    def _is_valid_exercise_volume(self, exercise: Exercise) -> bool:
        """بررسی اعتبار حجم یک تمرین"""
        sets = exercise.sets
        reps = exercise.reps
        
        # بررسی تعداد ست‌ها
        if not isinstance(sets, int) or sets < 1 or sets > 10:
            return False
            
        # بررسی تعداد تکرارها
        if isinstance(reps, str):
            try:
                min_reps, max_reps = map(int, reps.split('-'))
                rep_range = self.REP_RANGES.get(self.user.goal, {'min': 8, 'max': 12})
                if min_reps < rep_range['min'] or max_reps > rep_range['max']:
                    return False
            except:
                return False
                
        return True
    
    def _is_valid_muscle_volume(self, muscle: str, volume: int) -> bool:
        """بررسی اعتبار حجم کل یک عضله"""
        limits = self.VOLUME_LIMITS.get(muscle, {'min': 4, 'max': 12})
        return limits['min'] <= volume <= limits['max']
    
    def _validate_sequence(self, program: Dict) -> List[str]:
        """اعتبارسنجی توالی تمرینات"""
        errors = []
        trained_muscles = {}
        
        # بررسی توالی روزها
        days = sorted(program['weekly_plan'].keys())
        for i in range(1, len(days)):
            prev_day = datetime.strptime(days[i-1], '%Y-%m-%d')
            curr_day = datetime.strptime(days[i], '%Y-%m-%d')
            if (curr_day - prev_day).days < 1:
                errors.append("Training days must be at least one day apart")
        
        # بررسی توالی عضلات
        for day, exercises in program['weekly_plan'].items():
            for exercise in exercises:
                muscle = exercise.muscle_group
                if muscle not in trained_muscles:
                    trained_muscles[muscle] = []
                trained_muscles[muscle].append(day)
                
        for muscle, days in trained_muscles.items():
            if len(days) > 1:
                for i in range(1, len(days)):
                    prev_day = datetime.strptime(days[i-1], '%Y-%m-%d')
                    curr_day = datetime.strptime(days[i], '%Y-%m-%d')
                    min_recovery = self._get_min_recovery_days(muscle)
                    if (curr_day - prev_day).days < min_recovery:
                        errors.append(f"Rest time for {muscle} is not enough")
        
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
                    errors.append(f"Exercise {exercise.exercise_name} is not compatible with physical limitations")
                    
        return errors
    
    def _is_exercise_safe(self, exercise: Exercise) -> bool:
        """بررسی امنیت تمرین با توجه به محدودیت‌های فیزیکی
        
        Args:
            exercise: اطلاعات تمرین
            
        Returns:
            آیا تمرین امن است یا خیر
        """
        # بررسی محدودیت‌های فیزیکی
        if hasattr(self.user, 'physical_limitations'):
            for limitation in self.user.physical_limitations:
                if limitation in exercise.muscle_group:
                    return False
                    
        # بررسی سطح دشواری
        if exercise.difficulty not in ['beginner', 'intermediate']:
            return False
            
        return True
    
    def _validate_recovery(self, program: Dict) -> List[str]:
        """اعتبارسنجی ریکاوری"""
        errors = []
        
        if not self.recovery_manager:
            return errors
            
        for day, exercises in program['weekly_plan'].items():
            target_muscles = [ex.muscle_group for ex in exercises]
            if not self.recovery_manager.can_train(target_muscles, datetime.strptime(day, '%Y-%m-%d')):
                errors.append(f"Muscles in {day} need rest")
                
        return errors
    
    def _validate_mobility(self, program: Dict) -> List[str]:
        """اعتبارسنجی موبیلیتی"""
        errors = []
        
        if not self.mobility_manager:
            return errors
            
        for day, day_exercises in program['weekly_plan'].items():
            # بررسی وجود تمرینات گرم کردن
            if 'warmup' not in day_exercises or not day_exercises['warmup']:
                errors.append(f"Warmup exercises are missing on {day}")
                
            # بررسی وجود تمرینات سرد کردن
            if 'cooldown' not in day_exercises or not day_exercises['cooldown']:
                errors.append(f"Cooldown exercises are missing on {day}")
                
        return errors
    
    def validate_workout(self, workout: Dict) -> Tuple[bool, List[str]]:
        """اعتبارسنجی یک جلسه تمرین با مدیریت خطا"""
        try:
            errors = []
            
            # بررسی ساختار
            if not self._validate_workout_structure(workout):
                errors.append("Workout structure is not valid")
                return False, errors
                
            # بررسی تمرینات اصلی
            if 'exercises' in workout:
                exercise_errors = self._validate_workout_exercises(workout['exercises'])
                errors.extend(exercise_errors)
                
            # بررسی تمرینات گرم کردن
            if 'warmup' in workout:
                warmup_errors = self._validate_mobility_exercises(workout['warmup'], 'warmup')
                errors.extend(warmup_errors)
                
            # بررسی تمرینات سرد کردن
            if 'cooldown' in workout:
                cooldown_errors = self._validate_mobility_exercises(workout['cooldown'], 'cooldown')
                errors.extend(cooldown_errors)
                
            # بررسی ریکاوری
            if self.recovery_manager:
                target_muscles = [ex.muscle_group for ex in workout.get('exercises', [])]
                if not self.recovery_manager.can_train(target_muscles, datetime.strptime(workout['date'], '%Y-%m-%d')):
                    errors.append("Muscles in target need rest")
            else:
                errors.append("Recovery manager is not set")
                
            return len(errors) == 0, errors
            
        except Exception as e:
            return False, [f"Error in workout validation: {str(e)}"]
            
    def _validate_workout_structure(self, workout: Dict) -> bool:
        """اعتبارسنجی ساختار جلسه تمرین با جزئیات بیشتر"""
        required_keys = ['date', 'target_muscles']
        optional_keys = ['exercises', 'warmup', 'cooldown']
        
        # بررسی کلیدهای اجباری
        if not all(key in workout for key in required_keys):
            return False
            
        # بررسی نوع داده‌ها
        if not isinstance(workout['date'], str):
            return False
        if not isinstance(workout['target_muscles'], list):
            return False
            
        # بررسی تاریخ
        try:
            datetime.strptime(workout['date'], '%Y-%m-%d')
        except ValueError:
            return False
            
        # بررسی کلیدهای اختیاری
        for key in optional_keys:
            if key in workout and not isinstance(workout[key], list):
                return False
                
        return True
        
    def _validate_workout_exercises(self, exercises: List[Exercise]) -> List[str]:
        """اعتبارسنجی تمرینات اصلی با جزئیات بیشتر"""
        errors = []
        
        if not exercises:
            errors.append("Exercise list is empty")
            return errors
            
        for i, exercise in enumerate(exercises, 1):
            # بررسی ساختار
            if not self._validate_exercise_structure(exercise):
                errors.append(f"Exercise structure {i} is not valid")
                continue
                
            # بررسی حجم
            if not self._is_valid_exercise_volume(exercise):
                errors.append(f"Volume of exercise {i} ({exercise.exercise_name}) is not valid")
                
            # بررسی محدودیت‌ها
            if not self._is_exercise_safe(exercise):
                errors.append(f"Exercise {i} ({exercise.exercise_name}) is not compatible with physical limitations")
                
            # بررسی توالی
            if i > 1:
                prev_exercise = exercises[i-2]
                if not self._is_valid_exercise_sequence(prev_exercise, exercise):
                    errors.append(f"Exercise sequence {i-1} and {i} is not appropriate")
                    
        return errors
        
    def _is_valid_exercise_sequence(self, prev_exercise: Exercise, curr_exercise: Exercise) -> bool:
        """بررسی توالی مناسب تمرینات"""
        # تمرینات ترکیبی قبل از ایزوله
        if (prev_exercise.type == 'isolation' and 
            curr_exercise.type == 'compound'):
            return False
            
        # تمرینات بزرگ قبل از کوچک
        if (prev_exercise.muscle_group in ['biceps', 'triceps'] and 
            curr_exercise.muscle_group in ['chest', 'back']):
            return False
            
        return True
        
    def _validate_mobility_exercises(self, exercises: List[Exercise], exercise_type: str) -> List[str]:
        """اعتبارسنجی تمرینات موبیلیتی با جزئیات بیشتر"""
        errors = []
        
        if not exercises:
            errors.append(f"{exercise_type} exercises are missing")
            return errors
            
        for i, exercise in enumerate(exercises, 1):
            # بررسی ساختار
            if not all(hasattr(exercise, field) for field in ['exercise_id', 'exercise_name', 'duration_seconds']):
                errors.append(f"{exercise_type} exercise structure {i} is not valid")
                continue
                
            # بررسی مدت زمان
            duration = exercise.duration_seconds
            if exercise_type == 'warmup':
                if duration < 30 or duration > 300:
                    errors.append(f"Warmup duration for exercise {i} is not valid")
            else:  # cooldown
                if duration < 20 or duration > 180:
                    errors.append(f"Cooldown duration for exercise {i} is not valid")
                    
            # بررسی نوع تمرین
            if not self._is_valid_mobility_exercise(exercise, exercise_type):
                errors.append(f"{exercise_type} exercise type {i} is not valid")
                
        return errors
        
    def _is_valid_mobility_exercise(self, exercise: Exercise, exercise_type: str) -> bool:
        """بررسی اعتبار نوع تمرین موبیلیتی"""
        try:
            ex = Exercise.objects.get(id=exercise.exercise_id)
            
            if exercise_type == 'warmup':
                return ex.category in ['cardio', 'plyometrics', 'stretching']
            else:  # cooldown
                return ex.category in ['stretching', 'mobility']
                
        except Exercise.DoesNotExist:
            return False