from typing import Dict, List, Optional, Tuple
import random
import math
from collections import defaultdict
from datetime import datetime, timedelta
from accounts.services.split_startegy.base import SplitStrategy
from accounts.models import Exercise, UserProfile, TrainingSettings
from accounts.services.recovery_manager import RecoveryManager
from accounts.services.volume_manager import WorkoutVolumeManager
from accounts.services.exercise_selector import ExerciseSelector
from accounts.services.mobility_manager import MobilityManager

current_date = datetime.now()

class UpperLowerSplitStrategy(SplitStrategy):
    """
    استراتژی Upper/Lower پیشرفته با ویژگی‌های حرفه‌ای
    این استراتژی به عنوان یک مربی شخصی حرفه‌ای عمل می‌کند و شامل:
    - مدیریت پیشرفته حجم و شدت برای هر گروه حرکتی
    - پشتیبانی از تمرینات پیشرفته و تکنیک‌های ویژه
    - مدیریت هوشمند خستگی و ریکاوری
    - سازگاری با تیپ بدنی و اهداف مختلف
    - پشتیبانی از تمرینات جایگزین و اصلاحی
    - مدیریت پیشرفت و تنظیم خودکار برنامه
    """
    
    # نگاشت گروه‌های عضلانی با جزئیات بیشتر
    MUSCLE_GROUPS = {
        'upper': {
            'primary': ['chest', 'back', 'shoulders'],
            'secondary': ['biceps', 'triceps', 'forearms'],
            'synergists': ['core', 'upper_back', 'traps'],
            'techniques': ['drop_sets', 'rest_pause', 'supersets', 'giant_sets'],
            'volume_multiplier': 1.2,
            'focus_areas': ['upper_chest', 'lats', 'lateral_delts', 'rear_delts'],
            'exercise_priority': {
                'chest': ['bench_press', 'incline_press', 'dips'],
                'back': ['pull_ups', 'rows', 'lat_pulldowns'],
                'shoulders': ['overhead_press', 'lateral_raises', 'face_pulls']
            }
        },
        'lower': {
            'primary': ['quadriceps', 'hamstrings', 'glutes'],
            'secondary': ['calves', 'adductors', 'abductors'],
            'synergists': ['core', 'lower_back', 'hip_flexors'],
            'techniques': ['pyramids', 'rest_pause', 'drop_sets', 'cluster_sets'],
            'volume_multiplier': 1.3,
            'focus_areas': ['outer_quads', 'hamstring_insertion', 'glute_medius', 'calves'],
            'exercise_priority': {
                'quadriceps': ['squats', 'lunges', 'leg_press'],
                'hamstrings': ['deadlifts', 'romanian_deadlifts', 'leg_curls'],
                'glutes': ['hip_thrusts', 'glute_bridges', 'step_ups']
            }
        }
    }
    
    # تکنیک‌های پیشرفته برای هر سطح تجربه
    ADVANCED_TECHNIQUES = {
        'beginner': ['drop_sets', 'rest_pause'],
        'intermediate': ['drop_sets', 'rest_pause', 'supersets', 'giant_sets'],
        'expert': ['drop_sets', 'rest_pause', 'supersets', 'giant_sets', 
                  'pyramids', 'negatives', 'forced_reps', 'cluster_sets']
    }
    
    def generate(self, week: int) -> Dict:
        """تولید برنامه تمرینی با ویژگی‌های حرفه‌ای"""
        program = {'weekly_plan': {}}
        day_counter = 0
        
        # اولویت‌بندی روزها بر اساس ریکاوری
        prioritized_days = self._prioritize_days_by_recovery(list(self.settings.training_days.keys()))
        
        for day in prioritized_days:
            split_type = 'upper' if day_counter % 2 == 0 else 'lower'
            
            # بررسی ریکاوری قبل از تولید برنامه
            if not self._check_recovery_for_day(split_type, day):
                # تنظیم مجدد روز در صورت نیاز به استراحت
                day = self._find_next_available_day(prioritized_days[day_counter:], split_type)
                
            program['weekly_plan'][day] = self._build_day_plan(split_type, week)
            self.split_map[day] = split_type
            day_counter += 1
        
        self._validate_split_schedule(program)
        self._add_warmup_cooldown(program)
        self._validate_volume(program)
        return program
    
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
        score = 1.0
        
        # کاهش امتیاز برای روزهای پشت سر هم
        if self.user.last_training_date:
            days_since_last = (datetime.strptime(day, '%Y-%m-%d') - self.user.last_training_date).days
            score *= min(1.0, days_since_last / 2)
            
        # تنظیم بر اساس تیپ بدنی
        if self.user.body_type == 'ectomorph':
            score *= 1.2  # نیاز به ریکاوری بیشتر
        elif self.user.body_type == 'mesomorph':
            score *= 0.9  # ریکاوری سریع‌تر
            
        return score
        
    def _check_recovery_for_day(self, split_type: str, day: str) -> bool:
        """بررسی ریکاوری برای یک روز تمرین"""
        muscles = self.MUSCLE_GROUPS[split_type]['primary']
        return all(self.recovery_manager.can_train(muscle, datetime.strptime(day, '%Y-%m-%d')) 
                  for muscle in muscles)
        
    def _find_next_available_day(self, available_days: List[str], split_type: str) -> str:
        """یافتن روز بعدی مناسب برای تمرین"""
        for day in available_days:
            if self._check_recovery_for_day(split_type, day):
                return day
        return available_days[0]  # اگر روز مناسب پیدا نشد
        
    def _build_day_plan(self, split_type: str, week: int) -> List[Dict]:
        """ساخت برنامه حرفه‌ای برای یک روز تمرین"""
        exercises = []
        muscle_config = self.MUSCLE_GROUPS[split_type]
        
        # تنظیم تعداد تمرینات بر اساس سطح تجربه
        exercise_counts = self._get_exercise_counts(split_type)
        
        # تمرینات اصلی با اولویت‌بندی
        for muscle, priority_exercises in muscle_config['exercise_priority'].items():
            exercises.extend(self._build_priority_exercises(
                muscle,
                priority_exercises,
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
                
        # اضافه کردن تمرینات برای نقاط تمرکز
        focus_exercises = self._build_focus_area_exercises(
            muscle_config['focus_areas'],
            week
        )
        exercises.extend(focus_exercises)
        
        # اضافه کردن تکنیک‌های پیشرفته
        exercises = self._apply_advanced_techniques(exercises, muscle_config['techniques'])
        
        # تنظیم حجم و شدت
        exercises = self._adjust_exercise_volume(exercises, muscle_config['volume_multiplier'])
        
        # اضافه کردن گرم کردن و سرد کردن
        exercises = self._get_warmup(split_type) + exercises + self._get_cooldown(split_type)
                
        return exercises
    
    def _build_priority_exercises(self, muscle: str, priority_exercises: List[str], 
                                count: int, week: int, is_primary: bool) -> List[Dict]:
        """ساخت تمرینات با اولویت‌بندی"""
        exercises = []
        
        # تلاش برای استفاده از تمرینات اولویت‌دار
        for exercise_name in priority_exercises:
            if len(exercises) >= count:
                break
                
            available = self.exercise_selector.get_exercises(
                [muscle],
                week,
                name_pattern=exercise_name
            )
            
            if available:
                exercises.extend(available[:1])
                
        # تکمیل با تمرینات دیگر در صورت نیاز
        if len(exercises) < count:
            remaining = self._build_muscle_exercises(
                muscle,
                count - len(exercises),
                week,
                is_primary
            )
            exercises.extend(remaining)
            
        return [self._create_exercise_entry(ex, is_primary) for ex in exercises]
        
    def _get_exercise_counts(self, split_type: str) -> Dict[str, int]:
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
        
    def _build_muscle_exercises(self, muscle: str, count: int, week: int, 
                              is_primary: bool) -> List[Dict]:
        """ساخت لیست تمرینات برای یک عضله"""
        exercises = []
        
        # انتخاب تمرینات ترکیبی
        compound_exercises = self.exercise_selector.get_exercises(
            [muscle],
            week,
            mechanic='compound'
        )
        
        # انتخاب تمرینات ایزوله
        isolation_exercises = self.exercise_selector.get_exercises(
            [muscle],
            week,
            mechanic='isolation'
        )
        
        # ترکیب تمرینات
        if is_primary:
            # اولویت با تمرینات ترکیبی برای عضلات اصلی
            exercises.extend(compound_exercises[:min(2, len(compound_exercises))])
            remaining = count - len(exercises)
            exercises.extend(isolation_exercises[:remaining])
        else:
            # تمرکز روی تمرینات ایزوله برای عضلات ثانویه
            exercises.extend(isolation_exercises[:count])
            
        return [self._create_exercise_entry(ex, is_primary) for ex in exercises]
        
    def _build_focus_area_exercises(self, focus_areas: List[str], week: int) -> List[Dict]:
        """ساخت تمرینات برای نقاط تمرکز"""
        exercises = []
        
        for area in focus_areas:
            if random.random() < 0.6:  # 60% شانس اضافه کردن تمرین تمرکزی
                available = self.exercise_selector.get_exercises(
                    [area],
                    week,
                    mechanic='isolation'
                )
                if available:
                    exercises.extend(available[:1])
                    
        return [self._create_exercise_entry(ex, False) for ex in exercises]
        
    def _apply_advanced_techniques(self, exercises: List[Dict], 
                                 available_techniques: List[str]) -> List[Dict]:
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
                exercises[i]['technique'] = technique
                exercises[i]['technique_notes'] = self._get_technique_notes(technique)
                
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
            'forced_reps': 'تکرارهای اجباری با کمک',
            'cluster_sets': 'استراحت کوتاه بین تکرارها'
        }
        return notes.get(technique, '')
        
    def _adjust_exercise_volume(self, exercises: List[Dict], 
                              multiplier: float) -> List[Dict]:
        """تنظیم حجم تمرینات"""
        for exercise in exercises:
            base_volume = self.volume_manager.adjust_volume(
                exercise['muscle_group'],
                self.current_week
            )
            
            # تنظیم حجم بر اساس ضریب
            adjusted_sets = math.ceil(base_volume['sets'] * multiplier)
            
            # تنظیم بر اساس تیپ بدنی
            if self.user.body_type == 'ectomorph':
                adjusted_sets = max(3, adjusted_sets - 1)
            elif self.user.body_type == 'mesomorph':
                adjusted_sets = min(8, adjusted_sets + 1)
                
            exercise.update({
                'sets': adjusted_sets,
                'reps': base_volume['reps'],
                'volume_multiplier': multiplier
            })
            
        return exercises
            
    def _get_warmup(self, split_type: str) -> List[Dict]:
        """انتخاب گرم کردن اختصاصی برای هر نوع جلسه"""
        warmups = {
            'upper': [{
                'type': 'mobility',
                'content': [
                    {'name': 'Band Shoulder Dislocates', 'sets': 2, 'reps': '10-12'},
                    {'name': 'Scapular Wall Slides', 'sets': 2, 'reps': '12-15'},
                    {'name': 'Dynamic Chest Stretch', 'sets': 2, 'duration': '30s'},
                    {'name': 'Band Pull-Aparts', 'sets': 2, 'reps': '15-20'},
                    {'name': 'Cat-Cow Stretch', 'sets': 2, 'reps': '10-12'}
                ],
                'notes': 'Focus on shoulder mobility and upper body activation'
            }],
            'lower': [{
                'type': 'mobility',
                'content': [
                    {'name': 'Hip Circle Walks', 'sets': 2, 'reps': '10 each direction'},
                    {'name': 'Bodyweight Squats with Pause', 'sets': 2, 'reps': '12-15'},
                    {'name': 'Dynamic Hamstring Stretch', 'sets': 2, 'duration': '30s'},
                    {'name': 'Ankle Mobility', 'sets': 2, 'reps': '10 each side'},
                    {'name': 'Hip Flexor Stretch', 'sets': 2, 'duration': '30s each side'}
                ],
                'notes': 'Focus on hip and ankle mobility for lower body'
            }]
        }
        return warmups.get(split_type, [])
        
    def _get_cooldown(self, split_type: str) -> List[Dict]:
        """انتخاب سرد کردن اختصاصی برای هر نوع جلسه"""
        cooldowns = {
            'upper': [{
                'type': 'cooldown',
                'content': [
                    {'name': 'Chest Stretch', 'duration': '60s', 'notes': 'Focus on pec minor'},
                    {'name': 'Shoulder Stretch', 'duration': '45s each side', 'notes': 'Include internal rotation'},
                    {'name': 'Lat Stretch', 'duration': '60s each side', 'notes': 'Include overhead reach'},
                    {'name': 'Foam Roll Upper Back', 'duration': '90s', 'notes': 'Focus on tight spots'},
                    {'name': 'Biceps/Triceps Stretch', 'duration': '45s each arm', 'notes': 'Include shoulder extension'}
                ],
                'notes': 'Emphasize upper body recovery and mobility'
            }],
            'lower': [{
                'type': 'cooldown',
                'content': [
                    {'name': 'Quad Stretch', 'duration': '60s each leg', 'notes': 'Include hip flexor'},
                    {'name': 'Hamstring Stretch', 'duration': '45s each leg', 'notes': 'Include sciatic nerve glides'},
                    {'name': 'Calf Stretch', 'duration': '60s each leg', 'notes': 'Include both gastrocnemius and soleus'},
                    {'name': 'Hip Flexor Stretch', 'duration': '45s each side', 'notes': 'Include psoas'},
                    {'name': 'Foam Roll Legs', 'duration': '90s each leg', 'notes': 'Focus on IT band and quads'}
                ],
                'notes': 'Emphasize lower body recovery and flexibility'
            }]
        }
        return cooldowns.get(split_type, [])
        
    def _create_exercise_entry(self, exercise: Exercise, is_primary: bool) -> Dict:
        """ساخت ورودی استاندارد برای تمرین با جزئیات بیشتر"""
        return {
            'exercise_id': exercise.id,
            'exercise_name': exercise.name,
            'type': 'compound' if is_primary else 'isolation',
            'muscle_group': exercise.primary_muscles[0],
            'secondary_muscles': exercise.secondary_muscles,
            'mechanic': exercise.mechanic,
            'equipment': exercise.equipment,
            'difficulty': exercise.difficulty,
            'sets': self._get_default_sets(is_primary),
            'reps': self._get_default_reps(),
            'rest_seconds': self._calculate_rest_time(exercise, is_primary),
            'technique': None,
            'technique_notes': None,
            'notes': self._generate_exercise_notes(exercise, is_primary),
            'progression': self._get_progression_notes(),
            'alternatives': self.get_exercise_alternatives(exercise)
        }
        
    def _get_default_sets(self, is_primary: bool) -> int:
        """دریافت تعداد ست‌های پیش‌فرض"""
        base_sets = 4 if is_primary else 3
        
        # تنظیم بر اساس سطح تجربه
        if self.settings.experience_level == 'beginner':
            base_sets = max(3, base_sets - 1)
        elif self.settings.experience_level == 'expert':
            base_sets = min(6, base_sets + 1)
            
        return base_sets
        
    def _get_default_reps(self) -> str:
        """دریافت تعداد تکرارهای پیش‌فرض"""
        ranges = self.REP_RANGES.get(self.user.goal, {'min': 8, 'max': 12})
        return f"{ranges['min']}-{ranges['max']}"
        
    def _get_progression_notes(self) -> str:
        """دریافت نکات پیشرفت"""
        if self.settings.experience_level == 'beginner':
            return "Focus on form and technique. Increase weight when 12 reps become easy."
        elif self.settings.experience_level == 'intermediate':
            return "Progressive overload: Increase weight or reps each week."
        else:
            return "Advanced progression: Use various techniques and periodization."
            
    def _validate_split_schedule(self, program: Dict):
        """اعتبارسنجی برنامه هفتگی"""
        trained_muscles = defaultdict(list)
        for day, exercises in program['weekly_plan'].items():
            for ex in exercises:
                if isinstance(ex, dict) and 'muscle_group' in ex:
                    muscle = ex['muscle_group']
                    trained_muscles[muscle].append(day)
                    
        for muscle, days in trained_muscles.items():
            min_recovery = RecoveryManager.MIN_RECOVERY_DAYS.get(muscle, 2)
            for i in range(1, len(days)):
                if (datetime.strptime(days[i], '%Y-%m-%d') - 
                    datetime.strptime(days[i-1], '%Y-%m-%d')).days < min_recovery:
                    self._adjust_exercise_scheduling(program, muscle)
                    
    def _adjust_exercise_scheduling(self, program: Dict, muscle: str):
        """تنظیم زمان‌بندی تمرینات برای ریکاوری بهتر"""
        for day, exercises in program['weekly_plan'].items():
            for ex in exercises:
                if isinstance(ex, dict) and ex.get('muscle_group') == muscle:
                    # کاهش حجم یا تغییر تمرین
                    if random.random() < 0.5:
                        ex['sets'] = max(2, ex['sets'] - 1)
                    else:
                        alternatives = self.get_exercise_alternatives(
                            Exercise.objects.get(id=ex['exercise_id'])
                        )
                        if alternatives:
                            alt = random.choice(alternatives)
                            ex.update(self._create_exercise_entry(alt, ex['type'] == 'compound'))
