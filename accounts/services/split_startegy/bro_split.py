from typing import Dict, List, Optional, Tuple
import random
import math
from accounts.services.split_startegy.base import SplitStrategy
from accounts.models import Exercise, UserProfile, TrainingSettings
from accounts.services.recovery_manager import RecoveryManager
from accounts.services.volume_manager import WorkoutVolumeManager
from accounts.services.exercise_selector import ExerciseSelector
from accounts.services.mobility_manager import MobilityManager
from datetime import datetime
from accounts.services.date_converter import convert_day_to_date

current_date = datetime.now()

class BroSplitStrategy(SplitStrategy):
    """
    استراتژی Bro Split پیشرفته با ویژگی‌های حرفه‌ای
    این استراتژی به عنوان یک مربی شخصی حرفه‌ای عمل می‌کند و شامل:
    - مدیریت پیشرفته حجم و شدت برای هر گروه عضلانی
    - پشتیبانی از تمرینات پیشرفته و تکنیک‌های ویژه
    - مدیریت هوشمند خستگی و ریکاوری
    - سازگاری با تیپ بدنی و اهداف مختلف
    - پشتیبانی از تمرینات جایگزین و اصلاحی
    - مدیریت پیشرفت و تنظیم خودکار برنامه
    """
    current_week: int = 1  # مقدار پیش‌فرض
    
    # نگاشت عضلات برای هر روز تمرین با جزئیات بیشتر
    MUSCLE_DAY_MAPPING = {
        'chest': {
            'primary': ['chest'],
            'secondary': ['triceps', 'front_delts'],
            'synergists': ['core'],
            'techniques': ['drop_sets', 'rest_pause'],
            'volume_multiplier': 1.2
        },
        'back': {
            'primary': ['back'],
            'secondary': ['biceps', 'rear_delts'],
            'synergists': ['core', 'forearms'],
            'techniques': ['supersets', 'giant_sets'],
            'volume_multiplier': 1.2
        },
        'legs': {
            'primary': ['quadriceps', 'hamstrings'],
            'secondary': ['glutes', 'calves'],
            'synergists': ['core', 'lower_back'],
            'techniques': ['pyramids', 'rest_pause'],
            'volume_multiplier': 1.3
        },
        'shoulders': {
            'primary': ['shoulders'],
            'secondary': ['traps', 'rear_delts'],
            'synergists': ['triceps', 'core'],
            'techniques': ['drop_sets', 'supersets'],
            'volume_multiplier': 1.1
        },
        'arms': {
            'primary': ['biceps', 'triceps'],
            'secondary': ['forearms'],
            'synergists': ['shoulders'],
            'techniques': ['supersets', 'giant_sets'],
            'volume_multiplier': 1.0
        },
        'core': {
            'primary': ['abs', 'obliques'],
            'secondary': ['lower_back'],
            'synergists': ['hip_flexors'],
            'techniques': ['circuits', 'timed_sets'],
            'volume_multiplier': 0.9
        }
    }
    
    # اولویت‌بندی روزها با در نظر گرفتن ریکاوری
    DAY_PRIORITY = ['chest', 'back', 'legs', 'shoulders', 'arms', 'core']
    
    # تکنیک‌های پیشرفته برای هر سطح تجربه
    ADVANCED_TECHNIQUES = {
        'beginner': ['drop_sets', 'rest_pause'],
        'intermediate': ['drop_sets', 'rest_pause', 'supersets', 'giant_sets'],
        'expert': ['drop_sets', 'rest_pause', 'supersets', 'giant_sets', 
                  'pyramids', 'negatives', 'forced_reps']
    }
    
    def _generate_base_program(self, week: int) -> Dict:
        """
        تولید برنامه پایه با ویژگی‌های حرفه‌ای
        
        Args:
            week: شماره هفته
            
        Returns:
            Dict: برنامه تمرینی تولید شده
        """
        program = {}
        available_days = list(self.settings.training_days.keys())
        
        # تنظیم اولویت‌بندی روزها بر اساس ریکاوری
        prioritized_days = self._prioritize_days_by_recovery(available_days)
        
        # تولید برنامه برای هر روز
        for i, (day_name, muscle_day) in enumerate(zip(prioritized_days, self.DAY_PRIORITY)):
            if i >= len(prioritized_days):
                break
                
            # بررسی ریکاوری قبل از تولید برنامه
            if not self._check_recovery_for_day(muscle_day, day_name):
                # تنظیم مجدد روز در صورت نیاز به استراحت
                day_name = self._find_next_available_day(prioritized_days[i:], muscle_day)
                
            program[day_name] = self._build_muscle_day(muscle_day, week)
            
        # اضافه کردن روزهای تکمیلی
        if len(available_days) > len(self.DAY_PRIORITY):
            extra_days = available_days[len(self.DAY_PRIORITY):]
            for day in extra_days:
                program[day] = self._build_hybrid_day(week)
        # تبدیل کلیدها به تاریخ
        dated_program = {}
        base_date = datetime.now()
        for day, exercises in program.items():
            training_date = convert_day_to_date(day, base_date)
            dated_program[training_date.strftime('%Y-%m-%d')] = exercises
        return dated_program
        
    def _prioritize_days_by_recovery(self, available_days: List[str]) -> List[str]:
        """اولویت‌بندی روزها بر اساس ریکاوری"""
        prioritized = []
        remaining_days = available_days.copy()
        
        while remaining_days:
            best_day = None
            best_recovery_score = -1
            
            for day in remaining_days:
                score = self._calculate_recovery_score(day)
                if score > best_recovery_score:
                    best_recovery_score = score
                    best_day = day
                    
            if best_day:
                prioritized.append(best_day)
                remaining_days.remove(best_day)
                
        return prioritized
        
    def _calculate_recovery_score(self, day: str) -> float:
        """محاسبه امتیاز ریکاوری برای یک روز"""
        training_date = convert_day_to_date(day, datetime.now())
        score = 1.0
        
        # کاهش امتیاز برای روزهای پشت سر هم
        if self.user.last_training_date:
            days_since_last = (training_date - self.user.last_training_date).days
            score *= min(1.0, days_since_last / 2)
            
        # تنظیم بر اساس تیپ بدنی
        if self.user.body_type == 'ectomorph':
            score *= 1.2  # نیاز به ریکاوری بیشتر
        elif self.user.body_type == 'mesomorph':
            score *= 0.9  # ریکاوری سریع‌تر
            
        return score
        
    def _check_recovery_for_day(self, muscle_day: str, day: str) -> bool:
        """بررسی ریکاوری برای یک روز تمرین"""
        training_date = convert_day_to_date(day, datetime.now())
        muscles = self.MUSCLE_DAY_MAPPING[muscle_day]['primary']
        return all(self.recovery_manager.can_train(muscle, training_date) for muscle in muscles)
        
    def _find_next_available_day(self, available_days: List[str], muscle_day: str) -> str:
        """یافتن روز بعدی مناسب برای تمرین"""
        for day in available_days:
            if self._check_recovery_for_day(muscle_day, day):
                return day
        return available_days[0]  # اگر روز مناسب پیدا نشد
        
    def _build_muscle_day(self, muscle_day: str, week: int) -> List[Exercise]:
        """ساخت برنامه حرفه‌ای برای یک روز تمرین"""
        exercises = []
        muscle_config = self.MUSCLE_DAY_MAPPING[muscle_day]
        
        # تنظیم تعداد تمرینات بر اساس سطح تجربه
        exercise_counts = self._get_exercise_counts(muscle_day)
        
        # تمرینات اصلی
        for muscle in muscle_config['primary']:
            exercises.extend(self._build_muscle_exercises(
                muscle, 
                exercise_counts['primary'],
                week,
                is_primary=True
            ))
            
        # تمرینات ثانویه
        for muscle in muscle_config['secondary']:
            if random.random() < 0.8:  # 80% شانس اضافه کردن تمرین ثانویه
                exercises.extend(self._build_muscle_exercises(
                    muscle,
                    exercise_counts['secondary'],
                    week,
                    is_primary=False
                ))
                
        # اضافه کردن تکنیک‌های پیشرفته
        exercises = self._apply_advanced_techniques(exercises, muscle_config['techniques'])
        
        # تنظیم حجم و شدت
        exercises = self._adjust_exercise_volume(exercises, muscle_config['volume_multiplier'])
        
        return exercises
        
    def _get_exercise_counts(self, muscle_day: str) -> Dict[str, int]:
        """دریافت تعداد تمرینات برای هر نوع"""
        base_counts = {
            'beginner': {'primary': 3, 'secondary': 1},
            'intermediate': {'primary': 4, 'secondary': 2},
            'expert': {'primary': 5, 'secondary': 2}
        }.get(self.settings.experience_level, {'primary': 4, 'secondary': 2})
        
        # تنظیم بر اساس تیپ بدنی
        if self.user.body_type == 'ectomorph':
            base_counts['primary'] = max(3, base_counts['primary'] - 1)
        elif self.user.body_type == 'mesomorph':
            base_counts['primary'] = min(6, base_counts['primary'] + 1)
            
        return base_counts
        
    def _build_muscle_exercises(self, muscle: str, count: int, week: int, is_primary: bool) -> List[Exercise]:
        available = self.exercise_selector.get_exercises([muscle], week)['main']
        if is_primary:
            filtered = [ex for ex in available if ex.mechanic == 'compound']
        else:
            filtered = [ex for ex in available if ex.mechanic == 'isolation']
        return filtered[:count]
        
    def _apply_advanced_techniques(self, exercises: List[Exercise], 
                                 available_techniques: List[str]) -> List[Exercise]:
        """اعمال تکنیک‌های پیشرفته"""
        if not exercises:
            return exercises
            
        # فیلتر کردن تکنیک‌های مجاز برای سطح تجربه
        allowed_techniques = [
            tech for tech in available_techniques
            if tech in self.ADVANCED_TECHNIQUES.get(self.settings.experience_level, [])
        ]
        
        if not allowed_techniques:
            return exercises
            
        # اعمال تکنیک‌ها به صورت تصادفی
        for i in range(len(exercises)):
            if random.random() < 0.3:  # 30% شانس اعمال تکنیک
                technique = random.choice(allowed_techniques)
                exercises[i].technique = technique
                exercises[i].technique_notes = self._get_technique_notes(technique)
                
        return exercises
        
    def _get_technique_notes(self, technique: str) -> str:
        """دریافت نکات مربوط به تکنیک"""
        notes = {
            'drop_sets': 'کاهش 20-25% وزن در هر ست',
            'rest_pause': 'استراحت 15-20 ثانیه بین ست‌ها',
            'supersets': 'اجرای پشت سر هم با تمرین مکمل',
            'giant_sets': 'اجرای 3-4 تمرین پشت سر هم',
            'pyramids': 'افزایش تدریجی وزن و کاهش تکرار',
            'negatives': 'تمرکز روی فاز منفی حرکت',
            'forced_reps': 'تکرارهای اجباری با کمک'
        }
        return notes.get(technique, '')
        
    def _adjust_exercise_volume(self, exercises: List[Exercise], multiplier: float) -> List[Exercise]:
        """تنظیم حجم تمرینات"""
        for exercise in exercises:
            muscle_group = (exercise.primary_muscles[0] if exercise.primary_muscles else
                            (exercise.secondary_muscles[0] if exercise.secondary_muscles else 'full_body'))
            base_volume = self.volume_manager.adjust_volume(
                muscle_group,
                self.current_week
            )
            # تنظیم حجم بر اساس ضریب
            adjusted_sets = math.ceil(base_volume['sets'] * multiplier)
            # تنظیم بر اساس تیپ بدنی
            if self.user.body_type == 'ectomorph':
                adjusted_sets = max(3, adjusted_sets - 1)
            elif self.user.body_type == 'mesomorph':
                adjusted_sets = min(8, adjusted_sets + 1)
            exercise.sets = adjusted_sets
            exercise.reps = base_volume['reps']
            exercise.volume_multiplier = multiplier
        return exercises
        
    def _build_hybrid_day(self, week: int) -> List[Exercise]:
        """ساخت روزهای ترکیبی پیشرفته"""
        focus_areas = self._determine_hybrid_focus()
        exercises = []
        
        for area in focus_areas:
            if area['type'] == 'weak_point':
                exercises.extend(self._build_weak_point_exercises(area['muscles'], week))
            elif area['type'] == 'core':
                exercises.extend(self._build_core_exercises(week))
            elif area['type'] == 'cardio':
                exercises.extend(self._build_cardio_protocol())
                
        return exercises
        
    def _determine_hybrid_focus(self) -> List[Dict]:
        """تعیین تمرکز روزهای ترکیبی"""
        focus_areas = []
        
        # اضافه کردن نقاط ضعف
        weak_points = self._get_user_weak_points()
        if weak_points:
            focus_areas.append({
                'type': 'weak_point',
                'muscles': weak_points,
                'priority': 1
            })
            
        # اضافه کردن تمرینات مرکزی
        if self.user.goal in ['muscle_gain', 'strength']:
            focus_areas.append({
                'type': 'core',
                'priority': 2
            })
            
        # اضافه کردن کاردیو
        if self.user.goal == 'weight_loss':
            focus_areas.append({
                'type': 'cardio',
                'priority': 3
            })
            
        # مرتب‌سازی بر اساس اولویت
        focus_areas.sort(key=lambda x: x['priority'])
        return focus_areas
        
    def _build_weak_point_exercises(self, muscles: List[str], week: int) -> List[Exercise]:
        exercises = []
        for muscle in muscles:
            available = self.exercise_selector.get_exercises([muscle], week)['main']
            compound = [ex for ex in available if ex.mechanic == 'compound']
            isolation = [ex for ex in available if ex.mechanic == 'isolation']
            exercises.extend(compound[:1])
            exercises.extend(isolation[:2])
        return exercises
        
    def _build_core_exercises(self, week: int) -> List[Exercise]:
        core_muscles = ['abs', 'obliques', 'lower_back']
        exercises = []
        for muscle in core_muscles:
            available = self.exercise_selector.get_exercises([muscle], week)['main']
            if available:
                exercises.extend(available[:2])
        return exercises
        
    def _build_cardio_protocol(self) -> List[Exercise]:
        """ساخت پروتکل کاردیو"""
        if self.user.goal == 'weight_loss':
            return [{
                'type': 'cardio',
                'protocol': 'HIIT',
                'duration': '30-45 minutes',
                'intervals': [
                    {'type': 'sprint', 'duration': '30s', 'intensity': 'high'},
                    {'type': 'walk', 'duration': '60s', 'intensity': 'low'}
                ],
                'rounds': 8,
                'notes': 'Adjust intensity based on fitness level'
            }]
        else:
            return [{
                'type': 'cardio',
                'protocol': 'Steady State',
                'duration': '30-45 minutes',
                'intensity': 'moderate',
                'notes': 'Maintain heart rate at 60-70% of max'
            }]
            
    def _create_exercise_entry(self, exercise: Exercise, is_primary: bool) -> dict:
        if isinstance(exercise, dict):
            raise TypeError('Only Exercise model instances are allowed, not dict')
        muscles = exercise.primary_muscles if is_primary else exercise.secondary_muscles
        muscle_group = muscles[0] if muscles else 'full_body'
        return {
            'exercise_id': exercise.id,
            'exercise_name': exercise.name,
            'type': 'compound' if is_primary else 'isolation',
            'muscle_group': muscle_group,
            'secondary_muscles': exercise.secondary_muscles if not is_primary else [],
            'mechanic': exercise.mechanic,
            'equipment': exercise.equipment,
            'difficulty': getattr(exercise, 'difficulty', ''),
            'sets': getattr(exercise, 'sets', 4) if is_primary else 3,
            'reps': getattr(exercise, 'reps', '8-12'),
            'rest_seconds': self._calculate_rest_time(exercise, is_primary),
            'technique': getattr(exercise, 'technique', None),
            'technique_notes': getattr(exercise, 'technique_notes', None),
            'notes': self._generate_exercise_notes(exercise, is_primary),
            'progression': self._get_progression_notes(),
            'alternatives': self.get_exercise_alternatives(exercise)
        }
        
    def _get_progression_notes(self) -> str:
        """دریافت نکات پیشرفت"""
        if self.settings.experience_level == 'beginner':
            return "Focus on form and technique. Increase weight when 12 reps become easy."
        elif self.settings.experience_level == 'intermediate':
            return "Progressive overload: Increase weight or reps each week."
        else:
            return "Advanced progression: Use various techniques and periodization."
