from typing import List, Dict, Optional
from exercises.models import Exercise
from accounts.models import UserProfile, TrainingSettings
from django.db.models import Q

class MobilityManager:
    """
    مدیریت حرفه‌ای موبیلیتی و انعطاف‌پذیری
    - تنظیم تمرینات بر اساس نوع (گرم کردن، سرد کردن، ریکاوری فعال)
    - مدیریت محدودیت‌های فیزیکی و آسیب‌ها
    - همگام‌سازی با سایر بخش‌های برنامه
    """
    
    # دسته‌بندی تمرینات موبیلیتی
    MOBILITY_CATEGORIES = {
        'warmup': ['dynamic_stretching', 'mobility', 'activation'],
        'cooldown': ['static_stretching', 'foam_rolling', 'mobility'],
        'active_recovery': ['light_cardio', 'mobility', 'dynamic_stretching']
    }
    
    # تمرینات اختصاصی برای هر نوع split
    SPLIT_SPECIFIC_EXERCISES = {
        'push': {
            'warmup': ['shoulder_mobility', 'chest_opening', 'wrist_mobility'],
            'cooldown': ['chest_stretch', 'shoulder_stretch', 'tricep_stretch']
        },
        'pull': {
            'warmup': ['back_mobility', 'lat_activation', 'scapular_mobility'],
            'cooldown': ['back_stretch', 'lat_stretch', 'bicep_stretch']
        },
        'legs': {
            'warmup': ['hip_mobility', 'ankle_mobility', 'glute_activation'],
            'cooldown': ['quad_stretch', 'hamstring_stretch', 'calf_stretch']
        },
        'full_body': {
            'warmup': ['full_body_mobility', 'joint_mobility', 'core_activation'],
            'cooldown': ['full_body_stretch', 'foam_rolling', 'breathing']
        }
    }
    
    # ضریب‌های تعدیل برای سن
    AGE_MULTIPLIERS = {
        '18-25': 1.2,    # موبیلیتی بیشتر
        '26-35': 1.0,    # موبیلیتی استاندارد
        '36-45': 0.8,    # موبیلیتی کمتر
        '46+': 0.6       # موبیلیتی بسیار کمتر
    }
    
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        self.mobility_history = {}  # تاریخچه تمرینات موبیلیتی
        self.mobility_status = {}   # وضعیت موبیلیتی هر ناحیه
        self.recovery_needs = {}    # نیازهای ریکاوری هر ناحیه
        
    def get_mobility_exercises(self, 
                             target_areas: List[str] = None,
                             exercise_type: str = 'warmup',
                             split_type: str = None) -> List[Exercise]:
        """
        دریافت تمرینات موبیلیتی مناسب
        - تنظیم بر اساس نوع تمرین (گرم کردن، سرد کردن، ریکاوری فعال)
        - تنظیم بر اساس نوع split
        - تنظیم بر اساس محدودیت‌های فیزیکی
        """
        # دریافت دسته‌بندی‌های مناسب
        categories = self.MOBILITY_CATEGORIES.get(exercise_type, ['mobility'])
        
        # ساخت کوئری پایه
        query = Q(category__in=categories)
        
        # اضافه کردن تمرینات اختصاصی split
        if split_type and split_type in self.SPLIT_SPECIFIC_EXERCISES:
            specific_exercises = self.SPLIT_SPECIFIC_EXERCISES[split_type][exercise_type]
            query |= Q(name__in=specific_exercises)
        
        # فیلتر بر اساس نواحی هدف
        if target_areas:
            query &= (
                Q(primary_muscles__overlap=target_areas) |
                Q(secondary_muscles__overlap=target_areas)
            )
        
        # فیلتر بر اساس سطح تجربه
        query &= Q(level__lte=self._get_max_difficulty())
        
        # دریافت تمرینات
        exercises = Exercise.objects.filter(query)
        
        # فیلتر بر اساس محدودیت‌های فیزیکی
        exercises = self._filter_by_limitations(exercises)
        
        # تنظیم بر اساس سن و جنسیت
        exercises = self._adjust_for_demographics(exercises)
        
        # اولویت‌بندی بر اساس تاریخچه و نیازهای ریکاوری
        exercises = self._prioritize_exercises(exercises, target_areas)
        
        return list(exercises)
    
    def get_warmup_exercises(self, split_type: str) -> List[Exercise]:
        """دریافت تمرینات گرم کردن مناسب برای نوع split"""
        target_areas = self._get_target_areas_for_split(split_type)
        return self.get_mobility_exercises(
            target_areas=target_areas,
            exercise_type='warmup',
            split_type=split_type
        )
    
    def get_cooldown_exercises(self, split_type: str) -> List[Exercise]:
        """دریافت تمرینات سرد کردن مناسب برای نوع split"""
        target_areas = self._get_target_areas_for_split(split_type)
        return self.get_mobility_exercises(
            target_areas=target_areas,
            exercise_type='cooldown',
            split_type=split_type
        )
    
    def get_active_recovery_exercises(self, target_areas: List[str]) -> List[Exercise]:
        """دریافت تمرینات ریکاوری فعال مناسب"""
        return self.get_mobility_exercises(
            target_areas=target_areas,
            exercise_type='active_recovery'
        )
    
    def _get_target_areas_for_split(self, split_type: str) -> List[str]:
        """دریافت نواحی هدف برای نوع split"""
        target_areas = {
            'push': ['shoulders', 'chest', 'triceps'],
            'pull': ['back', 'biceps', 'shoulders'],
            'legs': ['quadriceps', 'hamstrings', 'glutes', 'calves'],
            'full_body': ['shoulders', 'hips', 'spine', 'core']
        }
        return target_areas.get(split_type, ['shoulders', 'hips', 'spine'])
    
    def _get_max_difficulty(self) -> str:
        """تعیین حداکثر سختی تمرین موبیلیتی"""
        return {
            'beginner': 'beginner',
            'intermediate': 'intermediate',
            'expert': 'expert'
        }.get(self.settings.experience_level, 'beginner')
    
    def _filter_by_limitations(self, exercises: List[Exercise]) -> List[Exercise]:
        """فیلتر تمرینات بر اساس محدودیت‌های فیزیکی"""
        if not self.user.physical_limitations:
            return exercises
            
        return exercises.exclude(
            contraindications__overlap=self.user.physical_limitations
        )
    
    def _adjust_for_demographics(self, exercises: List[Exercise]) -> List[Exercise]:
        """تنظیم تمرینات بر اساس سن و جنسیت"""
        age_multiplier = self._get_age_multiplier()
        
        # تنظیم بر اساس سن
        if age_multiplier < 1.0:  # سن بالا
            exercises = exercises.exclude(
                category__in=['plyometrics', 'dynamic_stretching']
            )
        
        # تنظیم بر اساس جنسیت
        if self.user.gender == 'female':
            exercises = exercises.filter(
                Q(category__in=['mobility', 'stretching']) |
                Q(level='beginner')
            )
        
        return exercises
    
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
    
    def _prioritize_exercises(self, exercises: List[Exercise], target_areas: List[str]) -> List[Exercise]:
        """اولویت‌بندی تمرینات بر اساس تاریخچه و نیازهای ریکاوری"""
        if not exercises:
            return []
            
        # محاسبه امتیاز برای هر تمرین
        for exercise in exercises:
            score = 1.0
            
            # امتیاز بر اساس تاریخچه
            if exercise.id in self.mobility_history:
                days_since = self.mobility_history[exercise.id]
                score *= (1 + days_since * 0.1)  # افزایش امتیاز برای تمرینات قدیمی‌تر
            
            # امتیاز بر اساس نیازهای ریکاوری
            for muscle in exercise.primary_muscles:
                if muscle in self.recovery_needs:
                    score *= (1 + self.recovery_needs[muscle] * 0.2)
            
            # امتیاز بر اساس نواحی هدف
            if target_areas:
                overlap = len(set(exercise.primary_muscles) & set(target_areas))
                score *= (1 + overlap * 0.3)
            
            exercise.priority_score = score
        
        # مرتب‌سازی بر اساس امتیاز
        return sorted(exercises, key=lambda x: x.priority_score, reverse=True)
    
    def update_mobility_status(self, exercise_id: int, target_areas: List[str]):
        """به‌روزرسانی وضعیت موبیلیتی"""
        # به‌روزرسانی تاریخچه
        self.mobility_history[exercise_id] = 0
        
        # افزایش شمارنده برای سایر تمرینات
        for ex_id in self.mobility_history:
            if ex_id != exercise_id:
                self.mobility_history[ex_id] += 1
        
        # به‌روزرسانی وضعیت نواحی هدف
        for area in target_areas:
            if area in self.mobility_status:
                self.mobility_status[area] = min(1.0, self.mobility_status[area] + 0.1)
            else:
                self.mobility_status[area] = 0.1
    
    def update_recovery_needs(self, muscle: str, need_level: float):
        """به‌روزرسانی نیازهای ریکاوری"""
        self.recovery_needs[muscle] = min(1.0, need_level)
    
    def reset_mobility_status(self):
        """بازنشانی وضعیت موبیلیتی"""
        self.mobility_history = {}
        self.mobility_status = {}
        self.recovery_needs = {} 