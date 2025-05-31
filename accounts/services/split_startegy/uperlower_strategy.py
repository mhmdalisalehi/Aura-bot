from typing import Dict, List, Optional, Tuple
import random
import math
from collections import defaultdict
from datetime import datetime, timedelta
from accounts.services.split_startegy.base import SplitStrategy
from accounts.models import Exercise, UserProfile, TrainingSettings
from accounts.services.recovery_manager import RecoveryManager
from accounts.services.volume_manager import WorkoutVolumeManager
from accounts.services.exercise_selector import ExerciseSelector, map_muscle_names
from accounts.services.mobility_manager import MobilityManager
from accounts.services.date_converter import convert_day_to_date
from accounts.services.workout_utils import get_progression_notes, get_exercise_notes, calculate_rest_time

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
    
    current_week: int = 1  # مقدار پیش‌فرض
    
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
    
    DAY_SEQUENCE = ['upper', 'lower', 'upper', 'lower']
    
    # تکنیک‌های پیشرفته برای هر سطح تجربه
    ADVANCED_TECHNIQUES = {
        'beginner': ['drop_sets', 'rest_pause'],
        'intermediate': ['drop_sets', 'rest_pause', 'supersets', 'giant_sets'],
        'expert': ['drop_sets', 'rest_pause', 'supersets', 'giant_sets', 
                  'pyramids', 'negatives', 'forced_reps', 'cluster_sets']
    }
    
    # Warmup and cooldown mappings for DRY base usage
    WARMUP_MAP = {
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
    COOLDOWN_MAP = {
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

    def generate(self, week: int) -> Dict:
        self.current_week = week
        program = {'weekly_plan': {}}
        day_counter = 0
        for day in self.settings.training_days.keys():
            split_type = 'upper' if day_counter % 2 == 0 else 'lower'
            program['weekly_plan'][day] = self._build_day_plan(split_type, week)
            self.split_map[day] = split_type
            day_counter += 1
        self._validate_split_schedule(program)
        self._add_warmup_cooldown(program, self.WARMUP_MAP, self.COOLDOWN_MAP, self.DAY_SEQUENCE)
        self._validate_volume(program)
        return program
    
    def _build_day_plan(self, split_type: str, week: int) -> dict:
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
        
        # Convert to dicts for 'main' section
        main_exercises = [self._create_exercise_entry(ex, is_primary=(ex.mechanic == 'compound')) for ex in exercises]
        # DEBUG: Print all selected exercises before returning main
        print(f"[DEBUG] main_exercises for {split_type} day: {[ex['exercise_name'] for ex in main_exercises]}")
        if not main_exercises:
            print(f"[WARNING] No main exercises generated for {split_type} day! Check exercise selection logic.")
        return {'main': main_exercises}
    
    def _build_priority_exercises(self, muscle: str, priority_exercises: List[str], count: int, week: int, is_primary: bool) -> List[Exercise]:
        exercises = []
        available = self.exercise_selector.get_exercises(map_muscle_names([muscle]), week)['main']
        for exercise_name in priority_exercises:
            if len(exercises) >= count:
                break
            matching_exercises = [ex for ex in available if exercise_name.lower() in ex.name.lower() and (ex.mechanic == 'compound' if is_primary else ex.mechanic == 'isolation')]
            if matching_exercises:
                exercises.extend(matching_exercises[:1])
        if len(exercises) < count:
            remaining = self._build_muscle_exercises(
                muscle,
                count - len(exercises),
                week,
                is_primary
            )
            exercises.extend(remaining)
        return exercises
        
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
        
    def _build_muscle_exercises(self, muscle: str, count: int, week: int, is_primary: bool) -> List[Exercise]:
        available = self.exercise_selector.get_exercises(map_muscle_names([muscle]), week)['main']
        if is_primary:
            filtered = [ex for ex in available if ex.mechanic == 'compound']
        else:
            filtered = [ex for ex in available if ex.mechanic == 'isolation']
        return filtered[:count]
        
    def _build_focus_area_exercises(self, focus_areas: List[str], week: int) -> List[Exercise]:
        exercises = []
        for area in focus_areas:
            if random.random() < 0.6:
                available = self.exercise_selector.get_exercises(map_muscle_names([area]), week)['main']
                filtered = [ex for ex in available if ex.mechanic == 'isolation']
                if filtered:
                    exercises.extend(filtered[:1])
        return exercises
        
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
            'forced_reps': 'تکرارهای اجباری با کمک',
            'cluster_sets': 'استراحت کوتاه بین تکرارها'
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
            'sets': getattr(exercise, 'sets', 4) if is_primary else getattr(exercise, 'sets', 3),
            'reps': getattr(exercise, 'reps', '8-12'),
            'rest_seconds': calculate_rest_time(exercise.mechanic, 0.7),  # Use a default intensity or pass real one if available
            'technique': getattr(exercise, 'technique', None),
            'technique_notes': getattr(exercise, 'technique_notes', None),
            'notes': get_exercise_notes(self.settings.experience_level, is_primary),
            'progression': get_progression_notes(self.settings.experience_level),
            'alternatives': self.get_exercise_alternatives(exercise)
        }
        
    def _adjust_program(self, program: Dict, increase: bool):
        # تنظیم برنامه بر اساس حجم کلی
        adjustment_factor = 1.1 if increase else 0.9
        for day in program['weekly_plan']:
            for exercise in program['weekly_plan'][day]:
                if isinstance(exercise, dict) and 'sets' in exercise:
                    exercise['sets'] = math.ceil(exercise['sets'] * adjustment_factor)

    def _validate_volume(self, program: Dict):
        # اعتبارسنجی حجم کلی برنامه
        total_volume = sum(self.volume_manager.muscle_volume.values())
        volume_range = self.volume_manager.VOLUME_TARGETS[self.user.goal][self.settings.experience_level]
        target = (volume_range[0] + volume_range[1]) / 2  # میانگین محدوده حجم
        if total_volume < target * 0.8:
            self._adjust_program(program, increase=True)
        elif total_volume > target * 1.2:
            self._adjust_program(program, increase=False)
           
    def _validate_split_schedule(self, program: Dict):
        """اعتبارسنجی برنامه هفتگی"""
        trained_muscles = defaultdict(list)
        for day, exercises in program['weekly_plan'].items():
            for ex in exercises:
                if isinstance(ex, dict) and 'muscle_group' in ex:
                    muscle = ex['muscle_group']
                    trained_muscles[muscle].append(day)
                    
        for muscle, days in trained_muscles.items():
            min_recovery = RecoveryManager.BASE_RECOVERY_DAYS.get(muscle, 2)
            for i in range(1, len(days)):
                # اگر مقدار day به فرمت تاریخ نبود، آن را به تاریخ تبدیل کن
                day1 = days[i-1]
                day2 = days[i]
                try:
                    date1 = datetime.strptime(day1, '%Y-%m-%d')
                except ValueError:
                    date1 = convert_day_to_date(day1, datetime.now())
                try:
                    date2 = datetime.strptime(day2, '%Y-%m-%d')
                except ValueError:
                    date2 = convert_day_to_date(day2, datetime.now())
                # حالا مقایسه بر اساس تاریخ انجام می‌شود
                if (date2 - date1).days < min_recovery:
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
                        exercise_id = ex.get('exercise_id') if isinstance(ex, dict) else getattr(ex, 'id', None)
                        if exercise_id:
                            try:
                                exercise_obj = Exercise.objects.get(id=exercise_id)
                                alternatives = self.get_exercise_alternatives(exercise_obj)
                                if alternatives:
                                    alt = random.choice(alternatives)
                                    ex.update(self._create_exercise_entry(alt, ex['type'] == 'compound'))
                            except Exercise.DoesNotExist:
                                print(f'Exercise with id {exercise_id} does not exist.')
                                continue
                        else:
                            
                            continue
