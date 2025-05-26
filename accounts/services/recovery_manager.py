from typing import List, Dict, Optional
from django.utils import timezone
from datetime import timedelta
from accounts.models import UserProfile, TrainingSettings
from exercises.models import Exercise

class RecoveryManager:
    """
    مدیریت حرفه‌ای ریکاوری
    - تنظیم زمان ریکاوری بر اساس شدت، سن، جنسیت و محدودیت‌ها
    - مدیریت ریکاوری فعال و غیرفعال
    - همگام‌سازی با سایر بخش‌های برنامه
    """
    
    # زمان‌های پایه ریکاوری برای هر عضله (به روز)
    BASE_RECOVERY_DAYS = {
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
    
    # ضریب‌های تعدیل برای سن
    AGE_MULTIPLIERS = {
        '18-25': 0.8,    # ریکاوری سریع‌تر
        '26-35': 1.0,    # ریکاوری استاندارد
        '36-45': 1.2,    # ریکاوری کندتر
        '46+': 1.5       # ریکاوری بسیار کندتر
    }
    
    # ضریب‌های تعدیل برای جنسیت
    GENDER_MULTIPLIERS = {
        'male': 1.0,     # ریکاوری استاندارد
        'female': 0.9    # ریکاوری سریع‌تر
    }
    
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        self.last_trained = {}  # تاریخ آخرین تمرین هر عضله
        self.recovery_status = {}  # وضعیت ریکاوری هر عضله
        self.fatigue_level = {}  # سطح خستگی هر عضله
        self.active_recovery_exercises = {}  # تمرینات ریکاوری فعال
        
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
            
        recovery_time = self._calculate_recovery_time(muscle)
        last_training = self.last_trained[muscle][-1]
        
        # بررسی زمان ریکاوری
        if (current_time - last_training).days < recovery_time:
            return False
            
        # بررسی سطح خستگی
        if self.fatigue_level.get(muscle, 0) > 0.8:  # خستگی بالا
            return False
            
        return True
    
    def _calculate_recovery_time(self, muscle: str) -> int:
        """محاسبه زمان ریکاوری مورد نیاز برای یک عضله"""
        base_time = self.BASE_RECOVERY_DAYS.get(muscle, 2)
        
        # تعدیل بر اساس سن
        age_multiplier = self._get_age_multiplier()
        
        # تعدیل بر اساس جنسیت
        gender_multiplier = self.GENDER_MULTIPLIERS.get(self.user.gender, 1.0)
        
        # تعدیل بر اساس شدت آخرین تمرین
        intensity_multiplier = self._get_intensity_multiplier(muscle)
        
        # تعدیل بر اساس آسیب‌ها
        injury_multiplier = self._get_injury_multiplier(muscle)
        
        # محاسبه زمان نهایی
        recovery_time = base_time * age_multiplier * gender_multiplier * intensity_multiplier * injury_multiplier
        
        return max(1, min(int(recovery_time), 7))  # محدود کردن بین 1 تا 7 روز
    
    def _get_age_multiplier(self) -> float:
        """دریافت ضریب تعدیل سن"""
        age = self.user.age
        if age <= 25:
            return self.AGE_MULTIPLIERS['18-25']
        elif age <= 35:
            return self.AGE_MULTIPLIERS['26-35']
        elif age <= 45:
            return self.AGE_MULTIPLIERS['36-45']
        else:
            return self.AGE_MULTIPLIERS['46+']
    
    def _get_intensity_multiplier(self, muscle: str) -> float:
        """دریافت ضریب تعدیل شدت"""
        if muscle not in self.last_trained:
            return 1.0
            
        # بررسی شدت آخرین تمرین
        last_volume = self._get_last_volume(muscle)
        if last_volume > 0.8:  # شدت بالا
            return 1.3
        elif last_volume > 0.5:  # شدت متوسط
            return 1.1
        return 1.0
    
    def _get_injury_multiplier(self, muscle: str) -> float:
        """دریافت ضریب تعدیل آسیب"""
        if not self.user.physical_limitations:
            return 1.0
            
        # بررسی آسیب‌های مرتبط با عضله
        related_injuries = self._get_related_injuries(muscle)
        if related_injuries:
            return 1.5  # افزایش زمان ریکاوری در صورت وجود آسیب
        return 1.0
    
    def _get_related_injuries(self, muscle: str) -> List[str]:
        """دریافت آسیب‌های مرتبط با یک عضله"""
        muscle_injury_map = {
            'chest': ['shoulder_injury', 'chest_injury'],
            'back': ['back_injury', 'spine_injury'],
            'shoulders': ['shoulder_injury', 'rotator_cuff'],
            'quadriceps': ['knee_injury', 'quad_injury'],
            'hamstrings': ['hamstring_injury', 'knee_injury'],
            # ... سایر عضلات
        }
        
        related_injuries = muscle_injury_map.get(muscle, [])
        return [inj for inj in related_injuries if inj in self.user.physical_limitations]
    
    def get_recovery_status(self, muscle: str) -> Dict:
        """دریافت وضعیت کامل ریکاوری یک عضله"""
        if muscle not in self.last_trained:
            return {
                'can_train': True,
                'days_since_last_training': None,
                'recovery_time_needed': self._calculate_recovery_time(muscle),
                'fatigue_level': 0,
                'active_recovery_recommended': False
            }
            
        last_training = self.last_trained[muscle][-1]
        days_since = (timezone.now() - last_training).days
        recovery_time = self._calculate_recovery_time(muscle)
        fatigue = self.fatigue_level.get(muscle, 0)
        
        return {
            'can_train': days_since >= recovery_time and fatigue <= 0.8,
            'days_since_last_training': days_since,
            'recovery_time_needed': recovery_time,
            'fatigue_level': fatigue,
            'active_recovery_recommended': self._should_recommend_active_recovery(muscle)
        }
    
    def _should_recommend_active_recovery(self, muscle: str) -> bool:
        """بررسی نیاز به ریکاوری فعال"""
        if muscle not in self.last_trained:
            return False
            
        days_since = (timezone.now() - self.last_trained[muscle][-1]).days
        fatigue = self.fatigue_level.get(muscle, 0)
        
        # پیشنهاد ریکاوری فعال در روزهای میانی ریکاوری
        return 0.5 <= days_since <= 1.5 and fatigue > 0.3
    
    def get_active_recovery_exercises(self, muscle: str) -> List[Exercise]:
        """دریافت تمرینات ریکاوری فعال مناسب"""
        if not self._should_recommend_active_recovery(muscle):
            return []
            
        # دریافت تمرینات سبک مناسب برای ریکاوری
        return Exercise.objects.filter(
            category__in=['mobility', 'stretching'],
            primary_muscles__contains=[muscle],
            level='beginner'
        ).order_by('?')[:3]  # انتخاب 3 تمرین تصادفی
    
    def update_training_status(self, muscle: str, volume: float, intensity: float):
        """به‌روزرسانی وضعیت تمرین یک عضله"""
        if muscle not in self.last_trained:
            self.last_trained[muscle] = []
            
        self.last_trained[muscle].append(timezone.now())
        
        # به‌روزرسانی سطح خستگی
        self.fatigue_level[muscle] = min(1.0, volume * intensity)
        
        # تنظیم زمان ریکاوری
        self._adjust_recovery_time(muscle, intensity)
    
    def _adjust_recovery_time(self, muscle: str, intensity: float):
        """تنظیم زمان ریکاوری بر اساس شدت تمرین"""
        if intensity > 0.8:  # شدت بالا
            self.BASE_RECOVERY_DAYS[muscle] = min(
                self.BASE_RECOVERY_DAYS.get(muscle, 2) + 1,
                4
            )
        elif intensity < 0.5:  # شدت پایین
            self.BASE_RECOVERY_DAYS[muscle] = max(
                self.BASE_RECOVERY_DAYS.get(muscle, 2) - 1,
                1
            )
    
    def _get_last_volume(self, muscle: str) -> float:
        """دریافت حجم آخرین تمرین یک عضله"""
        if muscle not in self.last_trained:
            return 0.0
            
        # این مقدار باید از VolumeManager دریافت شود
        # فعلاً یک مقدار فرضی برمی‌گردانیم
        return 0.7
    
    def reset_recovery_times(self):
        """بازنشانی زمان‌های ریکاوری"""
        self.last_trained = {}
        self.fatigue_level = {}
        self.recovery_status = {}
        self.active_recovery_exercises = {} 