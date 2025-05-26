from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from accounts.models import UserProfile, TrainingSettings
from exercises.models import Exercise
from ..workout_validator import WorkoutValidator

class SplitStrategy:
    """
    کلاس پایه برای استراتژی‌های تقسیم‌بندی تمرین
    این کلاس به عنوان یک مربی شخصی حرفه‌ای عمل می‌کند و ویژگی‌های زیر را ارائه می‌دهد:
    - مدیریت پیشرفته تمرینات
    - تنظیم هوشمند حجم و شدت
    - پشتیبانی از پیشرفت تدریجی
    - مدیریت خستگی و ریکاوری
    - سازگاری با محدودیت‌های فیزیکی
    - پشتیبانی از تمرینات جایگزین
    """
    
    # محدودیت‌های پیش‌فرض برای هر نوع تمرین
    EXERCISE_LIMITS = {
        'compound': {'min': 3, 'max': 6},    # تعداد تمرینات ترکیبی
        'isolation': {'min': 2, 'max': 4},   # تعداد تمرینات ایزوله
        'accessory': {'min': 1, 'max': 3}    # تعداد تمرینات کمکی
    }
    
    # محدوده تکرار برای هر هدف
    REP_RANGES = {
        'muscle_gain': {'min': 6, 'max': 12},
        'strength': {'min': 3, 'max': 6},
        'weight_loss': {'min': 12, 'max': 20},
        'endurance': {'min': 15, 'max': 30}
    }
    
    def __init__(self, user: UserProfile, settings: TrainingSettings, 
                 exercise_selector, volume_manager, recovery_manager):
        """
        مقداردهی اولیه استراتژی تقسیم‌بندی
        
        Args:
            user: پروفایل کاربر
            settings: تنظیمات تمرین
            exercise_selector: انتخاب‌گر تمرینات
            volume_manager: مدیر حجم تمرین
            recovery_manager: مدیر ریکاوری
        """
        self.user = user
        self.settings = settings
        self.exercise_selector = exercise_selector
        self.volume_manager = volume_manager
        self.recovery_manager = recovery_manager
        self.validator = WorkoutValidator(user, settings)
        self.split_map = {}
        self._validate_initialization()
        
    def _validate_initialization(self):
        """اعتبارسنجی مقداردهی اولیه"""
        if not all([self.user, self.settings, self.exercise_selector, 
                   self.volume_manager, self.recovery_manager]):
            raise ValueError("همه پارامترهای مورد نیاز باید مقداردهی شوند")
            
    def generate(self, week: int) -> Dict:
        """
        تولید برنامه تمرینی برای هفته مشخص
        
        Args:
            week: شماره هفته
            
        Returns:
            Dict: برنامه تمرینی تولید شده
            
        Raises:
            ValueError: در صورت خطا در تولید برنامه
        """
        try:
            # بررسی نیاز به کاهش بار
            if self._should_deload(week):
                return self._generate_deload_week(week)
                
            # تولید برنامه اصلی
            program = self._generate_base_program(week)
            
            # تنظیم حجم و شدت
            program = self._adjust_volume_and_intensity(program, week)
            
            # اضافه کردن تمرینات موبیلیتی
            program = self._add_mobility_exercises(program)
            
            # اعتبارسنجی برنامه
            is_valid, errors = self.validator.validate_program({'weekly_plan': program})
            if not is_valid:
                raise ValueError(f"برنامه نامعتبر است: {', '.join(errors)}")
                
            return program
            
        except Exception as e:
            raise ValueError(f"خطا در تولید برنامه: {str(e)}")
            
    def _should_deload(self, week: int) -> bool:
        """
        بررسی نیاز به کاهش بار
        
        Args:
            week: شماره هفته
            
        Returns:
            bool: آیا نیاز به کاهش بار است
        """
        # کاهش بار هر 4-6 هفته
        return week % 4 == 0 and week > 0
        
    def _generate_deload_week(self, week: int) -> Dict:
        """
        تولید هفته کاهش بار
        
        Args:
            week: شماره هفته
            
        Returns:
            Dict: برنامه کاهش بار
        """
        base_program = self._generate_base_program(week)
        deload_program = {}
        
        for day, exercises in base_program.items():
            deload_exercises = []
            for exercise in exercises:
                deload_exercise = exercise.copy()
                # کاهش حجم به 50-60%
                deload_exercise['sets'] = max(1, int(exercise['sets'] * 0.5))
                # افزایش تکرارها برای تمرکز روی فرم
                deload_exercise['reps'] = '12-15'
                deload_exercises.append(deload_exercise)
            deload_program[day] = deload_exercises
            
        return deload_program
        
    def _generate_base_program(self, week: int) -> Dict:
        """
        تولید برنامه پایه
        
        Args:
            week: شماره هفته
            
        Returns:
            Dict: برنامه پایه
        """
        raise NotImplementedError("این متد باید در کلاس‌های فرزند پیاده‌سازی شود")
        
    def _adjust_volume_and_intensity(self, program: Dict, week: int) -> Dict:
        """
        تنظیم حجم و شدت تمرینات
        
        Args:
            program: برنامه تمرینی
            week: شماره هفته
            
        Returns:
            Dict: برنامه تنظیم شده
        """
        adjusted_program = {}
        
        for day, exercises in program.items():
            adjusted_exercises = []
            for exercise in exercises:
                # تنظیم حجم بر اساس پیشرفت
                adjusted_volume = self.volume_manager.adjust_volume(
                    exercise['muscle_group'],
                    week
                )
                
                # تنظیم شدت بر اساس سطح تجربه
                intensity = self._calculate_intensity(exercise, week)
                
                adjusted_exercise = exercise.copy()
                adjusted_exercise.update({
                    'sets': adjusted_volume['sets'],
                    'reps': adjusted_volume['reps'],
                    'intensity': intensity
                })
                adjusted_exercises.append(adjusted_exercise)
                
            adjusted_program[day] = adjusted_exercises
            
        return adjusted_program
        
    def _calculate_intensity(self, exercise: Dict, week: int) -> float:
        """
        محاسبه شدت تمرین
        
        Args:
            exercise: اطلاعات تمرین
            week: شماره هفته
            
        Returns:
            float: شدت تمرین (0-1)
        """
        base_intensity = 0.7  # شدت پایه
        
        # افزایش تدریجی شدت
        week_factor = min(1.0, 0.7 + (week * 0.05))
        
        # تنظیم بر اساس نوع تمرین
        type_factor = {
            'compound': 1.0,
            'isolation': 0.8,
            'accessory': 0.6
        }.get(exercise['type'], 0.7)
        
        return min(1.0, base_intensity * week_factor * type_factor)
        
    def _add_mobility_exercises(self, program: Dict) -> Dict:
        """
        اضافه کردن تمرینات موبیلیتی
        
        Args:
            program: برنامه تمرینی
            
        Returns:
            Dict: برنامه با تمرینات موبیلیتی
        """
        for day, exercises in program.items():
            # اضافه کردن گرم کردن
            warmup = self.exercise_selector.get_mobility_exercises(
                target_areas=exercises[0]['muscle_group'],
                exercise_type='warmup'
            )
            
            # اضافه کردن سرد کردن
            cooldown = self.exercise_selector.get_mobility_exercises(
                target_areas=exercises[-1]['muscle_group'],
                exercise_type='cooldown'
            )
            
            program[day] = warmup + exercises + cooldown
            
        return program
        
    def get_exercise_alternatives(self, exercise: Dict) -> List[Dict]:
        """
        دریافت تمرینات جایگزین
        
        Args:
            exercise: تمرین اصلی
            
        Returns:
            List[Dict]: لیست تمرینات جایگزین
        """
        return self.exercise_selector.get_alternative_exercises(
            exercise['exercise_id'],
            self.user.physical_limitations
        )
        
    def _validate_exercise_balance(self, exercises: List[Dict]) -> Tuple[bool, List[str]]:
        """
        بررسی تعادل تمرینات
        
        Args:
            exercises: لیست تمرینات
            
        Returns:
            Tuple[bool, List[str]]: (اعتبار, لیست خطاها)
        """
        errors = []
        exercise_counts = {}
        
        # شمارش تمرینات هر نوع
        for exercise in exercises:
            ex_type = exercise['type']
            exercise_counts[ex_type] = exercise_counts.get(ex_type, 0) + 1
            
        # بررسی محدودیت‌ها
        for ex_type, count in exercise_counts.items():
            limits = self.EXERCISE_LIMITS.get(ex_type, {'min': 2, 'max': 5})
            if count < limits['min']:
                errors.append(f"تعداد تمرینات {ex_type} کمتر از حد مجاز است")
            elif count > limits['max']:
                errors.append(f"تعداد تمرینات {ex_type} بیشتر از حد مجاز است")
                
        return len(errors) == 0, errors
