from typing import Dict, List, Tuple
from exercises.models import Exercise
from accounts.models import UserProfile, TrainingSettings

class WorkoutVolumeManager:
    """
    مدیریت حرفه‌ای حجم تمرینات
    - تنظیم حجم بر اساس هدف، تجربه و وضعیت فیزیکی
    - مدیریت پیشرفت تدریجی
    - تنظیم حجم بر اساس نوع تمرین
    - مدیریت ریکاوری و خستگی
    """
    
    # اهداف حجمی برای هر هدف و سطح تجربه (مجموع ست‌ها در هفته)
    VOLUME_TARGETS = {
        'muscle_gain': {
            'beginner': (10, 12),    # 10-12 ست در هفته
            'intermediate': (12, 16), # 12-16 ست در هفته
            'expert': (14, 20)       # 14-20 ست در هفته
        },
        'strength': {
            'beginner': (8, 10),     # 8-10 ست در هفته
            'intermediate': (10, 14), # 10-14 ست در هفته
            'expert': (12, 16)       # 12-16 ست در هفته
        },
        'weight_loss': {
            'beginner': (12, 15),    # 12-15 ست در هفته
            'intermediate': (15, 18), # 15-18 ست در هفته
            'expert': (18, 22)       # 18-22 ست در هفته
        },
        'endurance': {
            'beginner': (15, 18),    # 15-18 ست در هفته
            'intermediate': (18, 22), # 18-22 ست در هفته
            'expert': (20, 25)       # 20-25 ست در هفته
        }
    }
    
    # محدوده تکرار برای هر هدف و نوع تمرین
    REP_RANGES = {
        'muscle_gain': {
            'compound': '6-8',    # تمرینات ترکیبی
            'isolation': '8-12',  # تمرینات ایزوله
            'accessory': '12-15'  # تمرینات تکمیلی
        },
        'strength': {
            'compound': '3-5',    # تمرینات ترکیبی
            'isolation': '6-8',   # تمرینات ایزوله
            'accessory': '8-10'   # تمرینات تکمیلی
        },
        'weight_loss': {
            'compound': '8-12',   # تمرینات ترکیبی
            'isolation': '12-15', # تمرینات ایزوله
            'accessory': '15-20'  # تمرینات تکمیلی
        },
        'endurance': {
            'compound': '12-15',  # تمرینات ترکیبی
            'isolation': '15-20', # تمرینات ایزوله
            'accessory': '20-25'  # تمرینات تکمیلی
        }
    }
    
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        self.muscle_volume = {}  # حجم فعلی هر عضله
        self.weekly_volume = {}  # حجم هفتگی هر عضله
        self.progression_week = 1  # هفته پیشرفت
        self.deload_week = False  # هفته کاهش بار
        
    def adjust_volume(self, muscle: str, week: int, exercise_type: str = 'compound') -> Dict:
        """
        تنظیم حجم تمرین برای یک عضله در هفته مشخص
        - تنظیم بر اساس هدف و تجربه
        - تنظیم بر اساس نوع تمرین
        - تنظیم بر اساس پیشرفت
        - تنظیم بر اساس ریکاوری
        """
        # بررسی نیاز به کاهش بار
        if self._should_deload(week):
            return self._get_deload_volume(muscle, exercise_type)
        
        # دریافت حجم پایه
        base_volume = self._get_base_volume(muscle, exercise_type)
        
        # تنظیم‌های متوالی
        adjusted_volume = self._adjust_for_experience(base_volume)
        adjusted_volume = self._adjust_for_recovery(adjusted_volume, muscle)
        adjusted_volume = self._adjust_for_progression(adjusted_volume, week)
        adjusted_volume = self._adjust_for_exercise_type(adjusted_volume, exercise_type)
        adjusted_volume = self._adjust_for_goal(adjusted_volume, exercise_type)
        
        # به‌روزرسانی تاریخچه
        self._update_volume_history(muscle, adjusted_volume)
        
        return adjusted_volume
    
    def _get_base_volume(self, muscle: str, exercise_type: str) -> Dict:
        """دریافت حجم پایه برای یک عضله و نوع تمرین"""
        base_volumes = {
            'chest': {'compound': 4, 'isolation': 3, 'accessory': 2},
            'back': {'compound': 4, 'isolation': 3, 'accessory': 2},
            'shoulders': {'compound': 3, 'isolation': 2, 'accessory': 2},
            'biceps': {'compound': 2, 'isolation': 3, 'accessory': 2},
            'triceps': {'compound': 2, 'isolation': 3, 'accessory': 2},
            'quadriceps': {'compound': 4, 'isolation': 3, 'accessory': 2},
            'hamstrings': {'compound': 3, 'isolation': 2, 'accessory': 2},
            'calves': {'compound': 2, 'isolation': 3, 'accessory': 1},
            'abs': {'compound': 2, 'isolation': 3, 'accessory': 2}
        }
        
        # تنظیم بر اساس نوع تمرین
        sets = base_volumes.get(muscle, {'compound': 3, 'isolation': 2, 'accessory': 2})[exercise_type]
        
        # تنظیم بر اساس هدف
        if self.user.goal == 'strength':
            sets = int(sets * 0.8)  # کاهش تعداد ست‌ها برای تمرینات قدرتی
        elif self.user.goal == 'endurance':
            sets = int(sets * 1.2)  # افزایش تعداد ست‌ها برای تمرینات استقامتی
        
        return {
            'sets': sets,
            'reps': self.REP_RANGES[self.user.goal][exercise_type]
        }
    
    def _adjust_for_experience(self, volume: Dict) -> Dict:
        """تنظیم حجم بر اساس تجربه کاربر"""
        experience_multiplier = {
            'beginner': 0.7,    # کاهش حجم برای مبتدیان
            'intermediate': 1.0, # حجم استاندارد
            'expert': 1.2       # افزایش حجم برای حرفه‌ای‌ها
        }.get(self.settings.experience_level, 1.0)
        
        return {
            'sets': int(volume['sets'] * experience_multiplier),
            'reps': volume['reps']
        }
    
    def _adjust_for_recovery(self, volume: Dict, muscle: str) -> Dict:
        """تنظیم حجم بر اساس وضعیت ریکاوری"""
        if muscle in self.muscle_volume:
            current_volume = self.muscle_volume[muscle]
            threshold = self._get_volume_threshold(muscle)
            
            if current_volume > threshold * 1.2:  # حجم خیلی بالا
                return {
                    'sets': int(volume['sets'] * 0.7),  # کاهش 30%
                    'reps': volume['reps']
                }
            elif current_volume > threshold:  # حجم بالا
                return {
                    'sets': int(volume['sets'] * 0.8),  # کاهش 20%
                    'reps': volume['reps']
                }
        
        return volume
    
    def _adjust_for_progression(self, volume: Dict, week: int) -> Dict:
        """تنظیم حجم بر اساس پیشرفت"""
        if week > self.progression_week:
            self.progression_week = week
            
            # افزایش حجم هر 4 هفته
            if week % 4 == 0:
                return {
                    'sets': volume['sets'] + 1,
                    'reps': volume['reps']
                }
            # افزایش شدت هر 2 هفته
            elif week % 2 == 0:
                return {
                    'sets': volume['sets'],
                    'reps': self._increase_intensity(volume['reps'])
                }
        
        return volume
    
    def _adjust_for_exercise_type(self, volume: Dict, exercise_type: str) -> Dict:
        """تنظیم حجم بر اساس نوع تمرین"""
        type_multiplier = {
            'compound': 1.2,    # افزایش حجم برای تمرینات ترکیبی
            'isolation': 1.0,   # حجم استاندارد برای تمرینات ایزوله
            'accessory': 0.8    # کاهش حجم برای تمرینات تکمیلی
        }.get(exercise_type, 1.0)
        
        return {
            'sets': int(volume['sets'] * type_multiplier),
            'reps': volume['reps']
        }
    
    def _adjust_for_goal(self, volume: Dict, exercise_type: str) -> Dict:
        """تنظیم حجم بر اساس هدف کاربر"""
        goal_adjustments = {
            'muscle_gain': {
                'compound': {'sets': 1.1, 'reps': '8-12'},
                'isolation': {'sets': 1.0, 'reps': '10-15'},
                'accessory': {'sets': 0.9, 'reps': '12-15'}
            },
            'strength': {
                'compound': {'sets': 1.2, 'reps': '4-6'},
                'isolation': {'sets': 0.8, 'reps': '6-8'},
                'accessory': {'sets': 0.7, 'reps': '8-10'}
            },
            'weight_loss': {
                'compound': {'sets': 1.0, 'reps': '12-15'},
                'isolation': {'sets': 0.9, 'reps': '15-20'},
                'accessory': {'sets': 0.8, 'reps': '20-25'}
            },
            'endurance': {
                'compound': {'sets': 0.9, 'reps': '15-20'},
                'isolation': {'sets': 0.8, 'reps': '20-25'},
                'accessory': {'sets': 0.7, 'reps': '25-30'}
            }
        }
        
        adjustment = goal_adjustments.get(self.user.goal, {}).get(exercise_type, {})
        return {
            'sets': int(volume['sets'] * adjustment.get('sets', 1.0)),
            'reps': adjustment.get('reps', volume['reps'])
        }
    
    def _should_deload(self, week: int) -> bool:
        """بررسی نیاز به کاهش بار"""
        # کاهش بار هر 8 هفته
        if week % 8 == 0:
            self.deload_week = True
            return True
        
        # کاهش بار بر اساس خستگی
        if self._check_fatigue():
            self.deload_week = True
            return True
            
        self.deload_week = False
        return False
    
    def _get_deload_volume(self, muscle: str, exercise_type: str) -> Dict:
        """دریافت حجم کاهش بار"""
        base_volume = self._get_base_volume(muscle, exercise_type)
        return {
            'sets': int(base_volume['sets'] * 0.5),  # کاهش 50% حجم
            'reps': self._decrease_intensity(base_volume['reps'])
        }
    
    def _check_fatigue(self) -> bool:
        """بررسی سطح خستگی"""
        if not self.muscle_volume:
            return False
            
        # بررسی حجم کلی در هفته
        total_volume = sum(self.muscle_volume.values())
        max_volume = sum(
            self.VOLUME_TARGETS[self.user.goal][self.settings.experience_level]
        ) * 1.2  # 20% بیشتر از هدف
        
        return total_volume > max_volume
    
    def _get_volume_threshold(self, muscle: str) -> int:
        """دریافت آستانه حجم برای یک عضله"""
        thresholds = {
            'chest': 20,
            'back': 20,
            'shoulders': 15,
            'biceps': 12,
            'triceps': 12,
            'quadriceps': 20,
            'hamstrings': 15,
            'calves': 12,
            'abs': 12
        }
        return thresholds.get(muscle, 15)
    
    def _increase_intensity(self, rep_range: str) -> str:
        """افزایش شدت با تغییر محدوده تکرار"""
        if '-' in rep_range:
            min_rep, max_rep = map(int, rep_range.split('-'))
            return f"{min_rep-1}-{max_rep-1}"
        return rep_range
    
    def _decrease_intensity(self, rep_range: str) -> str:
        """کاهش شدت با تغییر محدوده تکرار"""
        if '-' in rep_range:
            min_rep, max_rep = map(int, rep_range.split('-'))
            return f"{min_rep+2}-{max_rep+2}"
        return rep_range
    
    def _update_volume_history(self, muscle: str, volume: Dict):
        """به‌روزرسانی تاریخچه حجم"""
        if muscle not in self.muscle_volume:
            self.muscle_volume[muscle] = 0
            
        # محاسبه حجم جدید
        if isinstance(volume['reps'], str) and '-' in volume['reps']:
            min_rep, max_rep = map(int, volume['reps'].split('-'))
            avg_reps = (min_rep + max_rep) / 2
        else:
            avg_reps = int(volume['reps'])
            
        self.muscle_volume[muscle] += volume['sets'] * avg_reps
    
    def reset_weekly_volume(self):
        """بازنشانی حجم هفتگی"""
        self.weekly_volume = {}
        if self.deload_week:
            self.muscle_volume = {k: v * 0.5 for k, v in self.muscle_volume.items()}
            self.deload_week = False 