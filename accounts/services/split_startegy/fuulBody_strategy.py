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

class FullBodySplitStrategy(SplitStrategy):
    """
    استراتژی Full Body پیشرفته با ویژگی‌های حرفه‌ای
    این استراتژی به عنوان یک مربی شخصی حرفه‌ای عمل می‌کند و شامل:
    - مدیریت پیشرفته حجم و شدت برای تمرینات تمام بدن
    - پشتیبانی از تمرینات پیشرفته و تکنیک‌های ویژه
    - مدیریت هوشمند خستگی و ریکاوری
    - سازگاری با تیپ بدنی و اهداف مختلف
    - پشتیبانی از تمرینات جایگزین و اصلاحی
    - مدیریت پیشرفت و تنظیم خودکار برنامه
    """
    current_week: int = 1  # مقدار پیش‌فرض

    # نگاشت گروه‌های عضلانی با جزئیات بیشتر
    MUSCLE_GROUPS = {
        'primary': {
            'push': ['chest', 'shoulders', 'triceps'],
            'pull': ['back', 'biceps', 'rear_delts'],
            'legs': ['quadriceps', 'hamstrings', 'glutes'],
            'core': ['abs', 'obliques', 'lower_back']
        },
        'secondary': {
            'accessory': ['calves', 'forearms', 'traps'],
            'stabilizers': ['hip_flexors', 'adductors', 'abductors']
        },
        'exercise_priority': {
            'chest': ['bench_press', 'push_ups', 'dips'],
            'back': ['pull_ups', 'rows', 'lat_pulldowns'],
            'legs': ['squats', 'deadlifts', 'lunges'],
            'shoulders': ['overhead_press', 'lateral_raises', 'face_pulls'],
            'core': ['planks', 'crunches', 'russian_twists']
        },
        'techniques': {
            'compound': ['supersets', 'giant_sets', 'circuits'],
            'isolation': ['drop_sets', 'rest_pause', 'pyramids']
        },
        'volume_multipliers': {
            'primary': 1.2,
            'secondary': 0.8
        }
    }
    
    # تکنیک‌های پیشرفته برای هر سطح تجربه
    ADVANCED_TECHNIQUES = {
        'beginner': ['circuits', 'supersets'],
        'intermediate': ['circuits', 'supersets', 'giant_sets', 'drop_sets'],
        'expert': ['circuits', 'supersets', 'giant_sets', 'drop_sets', 
                  'pyramids', 'rest_pause', 'cluster_sets', 'complexes']
    }
    
    # Warmup and cooldown mappings for DRY base usage
    WARMUP_MAP = {
        'full_body': [{
            'type': 'mobility',
            'content': [
                {'name': 'Dynamic Full Body Warmup', 'sets': 1, 'duration': '5-10min'},
                {'name': 'Joint Mobility', 'sets': 1, 'duration': '3-5min'},
                {'name': 'Light Cardio', 'sets': 1, 'duration': '5min'},
                {'name': 'Bodyweight Squats', 'sets': 2, 'reps': '10-12'},
                {'name': 'Push-ups', 'sets': 2, 'reps': '8-10'},
                {'name': 'Pull-ups/Assisted Pull-ups', 'sets': 2, 'reps': '5-8'}
            ],
            'notes': 'Focus on full body activation and mobility'
        }]
    }
    COOLDOWN_MAP = {
        'full_body': [{
            'type': 'cooldown',
            'content': [
                {'name': 'Full Body Stretch', 'duration': '5-10min', 'notes': 'Include all major muscle groups'},
                {'name': 'Foam Rolling', 'duration': '5-10min', 'notes': 'Focus on tight areas'},
                {'name': 'Deep Breathing', 'duration': '2-3min', 'notes': 'Calm down and relax'},
                {'name': 'Light Walking', 'duration': '5min', 'notes': 'Active recovery'}
            ],
            'notes': 'Emphasize full body recovery and flexibility'
        }]
    }
    DAY_SEQUENCE = ['full_body']

    def generate(self, week: int) -> Dict:
        program = {'weekly_plan': {}}
        for day in self.settings.training_days.keys():
            program['weekly_plan'][day] = self._build_fullbody_day(week)
            self._validate_day_plan(program['weekly_plan'][day])
        self._balance_volume_across_days(program)
        self._add_warmup_cooldown(program, self.WARMUP_MAP, self.COOLDOWN_MAP, self.DAY_SEQUENCE)
        self._validate_volume(program)
        # تبدیل کلیدها به تاریخ
        dated_program = {}
        base_date = datetime.now()
        for day, exercises in program['weekly_plan'].items():
            training_date = convert_day_to_date(day, base_date)
            dated_program[training_date.strftime('%Y-%m-%d')] = exercises
        return dated_program
        
    def _build_fullbody_day(self, week: int) -> List[Exercise]:
        """ساخت برنامه حرفه‌ای برای یک روز تمرین تمام بدن"""
        exercises = []
        
        # تنظیم تعداد تمرینات بر اساس سطح تجربه
        exercise_counts = self._get_exercise_counts()
        
        # تمرینات اصلی با اولویت‌بندی
        for category, muscles in self.MUSCLE_GROUPS['primary'].items():
            for muscle in muscles:
                exercises.extend(self._build_priority_exercises(
                    muscle,
                    self.MUSCLE_GROUPS['exercise_priority'].get(muscle, []),
                    exercise_counts['primary'],
                    week,
                    is_primary=True
                ))
                
        # تمرینات ثانویه
        for category, muscles in self.MUSCLE_GROUPS['secondary'].items():
            for muscle in muscles:
                if random.random() < 0.6:  # 60% شانس اضافه کردن تمرین ثانویه
                    exercises.extend(self._build_muscle_exercises(
                        muscle,
                        exercise_counts['secondary'],
                        week,
                        is_primary=False
                    ))
                    
        # اضافه کردن تکنیک‌های پیشرفته
        exercises = self._apply_advanced_techniques(exercises)
        
        # تنظیم حجم و شدت
        exercises = self._adjust_exercise_volume(exercises)
        
        return exercises
        
    def _get_exercise_counts(self) -> Dict[str, int]:
        """دریافت تعداد تمرینات برای هر نوع"""
        base_counts = {
            'beginner': {'primary': 1, 'secondary': 1},
            'intermediate': {'primary': 2, 'secondary': 1},
            'expert': {'primary': 2, 'secondary': 2}
        }.get(self.settings.experience_level, {'primary': 2, 'secondary': 1})
        
        # تنظیم بر اساس تیپ بدنی
        if self.user.body_type == 'ectomorph':
            base_counts['primary'] = max(1, base_counts['primary'] - 1)
        elif self.user.body_type == 'mesomorph':
            base_counts['primary'] = min(3, base_counts['primary'] + 1)
            
        return base_counts
        
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
        
    def _build_muscle_exercises(self, muscle: str, count: int, week: int, is_primary: bool) -> List[Exercise]:
        available = self.exercise_selector.get_exercises(map_muscle_names([muscle]), week)['main']
        if is_primary:
            filtered = [ex for ex in available if ex.mechanic == 'compound']
        else:
            filtered = [ex for ex in available if ex.mechanic == 'isolation']
        return filtered[:count]
        
    def _apply_advanced_techniques(self, exercises: List[Exercise]) -> List[Exercise]:
        """اعمال تکنیک‌های پیشرفته"""
        if not exercises:
            return exercises
            
        # فیلتر کردن تکنیک‌های مجاز برای سطح تجربه
        allowed_techniques = self.ADVANCED_TECHNIQUES.get(self.settings.experience_level, [])
        
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
            'circuits': 'اجرای 3-4 تمرین پشت سر هم با استراحت کوتاه',
            'supersets': 'اجرای پشت سر هم با تمرین مکمل',
            'giant_sets': 'اجرای 3-4 تمرین پشت سر هم',
            'drop_sets': 'کاهش 20-25% وزن در هر ست',
            'pyramids': 'افزایش تدریجی وزن و کاهش تکرار',
            'rest_pause': 'استراحت 15-20 ثانیه بین ست‌ها',
            'cluster_sets': 'استراحت کوتاه بین تکرارها',
            'complexes': 'ترکیب چند تمرین با یک وزنه'
        }
        return notes.get(technique, '')
        
    def _adjust_exercise_volume(self, exercises: List[Exercise]) -> List[Exercise]:
        """تنظیم حجم تمرینات"""
        for exercise in exercises:
            is_primary = exercise.mechanic == 'compound'
            multiplier = (self.MUSCLE_GROUPS['volume_multipliers']['primary'] 
                        if is_primary else 
                        self.MUSCLE_GROUPS['volume_multipliers']['secondary'])
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
                adjusted_sets = max(2, adjusted_sets - 1)
            elif self.user.body_type == 'mesomorph':
                adjusted_sets = min(6, adjusted_sets + 1)
            exercise.sets = adjusted_sets
            exercise.reps = base_volume['reps']
            exercise.volume_multiplier = multiplier
        return exercises
        
    def _validate_day_plan(self, exercises: List[Exercise]):
        """اعتبارسنجی برنامه روزانه"""
        # بررسی تعداد تمرینات
        if len(exercises) > 8:  # حداکثر 8 تمرین در روز
            exercises = exercises[:8]
            
        # بررسی توزیع گروه‌های عضلانی
        muscle_counts = defaultdict(int)
        for ex in exercises:
            if isinstance(ex, Exercise) and ex.primary_muscles:
                muscle_counts[ex.primary_muscles[0]] += 1
                
        # تنظیم در صورت نیاز
        for muscle, count in muscle_counts.items():
            if count > 2:  # حداکثر 2 تمرین برای هر عضله
                self._adjust_muscle_exercises(exercises, muscle, count)
                
    def _adjust_muscle_exercises(self, exercises: List[Exercise], muscle: str, count: int):
        """تنظیم تمرینات یک عضله خاص"""
        muscle_exercises = [ex for ex in exercises if ex.primary_muscles and ex.primary_muscles[0] == muscle]
        if len(muscle_exercises) > 2:
            # حذف تمرینات اضافی با اولویت تمرینات ایزوله
            to_remove = len(muscle_exercises) - 2
            isolation_exercises = [ex for ex in muscle_exercises if ex.mechanic == 'isolation']
            for ex in isolation_exercises[:to_remove]:
                exercises.remove(ex)
                
    def _balance_volume_across_days(self, program: Dict):
        """تعادل حجم تمرینات در روزهای مختلف"""
        daily_volumes = []
        for day, exercises in program['weekly_plan'].items():
            total = sum(self.volume_manager.calculate_volume(
                ex,
                ex.sets,
                ex.reps
            ) for ex in exercises if isinstance(ex, Exercise))
            daily_volumes.append(total)
            
        avg_volume = sum(daily_volumes) / len(daily_volumes)
        for i, vol in enumerate(daily_volumes):
            if vol < avg_volume * 0.8:
                self._add_exercise(program, list(program['weekly_plan'].keys())[i])
            elif vol > avg_volume * 1.2:
                self._remove_exercise(program, list(program['weekly_plan'].keys())[i])
                
    def _add_exercise(self, program: Dict, day: str):
        """اضافه کردن تمرین به برنامه"""
        # اطمینان از اینکه day تاریخ است
        training_date = convert_day_to_date(day, datetime.now())
        available_muscles = [m for m in self.MUSCLE_GROUPS['primary'].values() 
                           if self.recovery_manager.can_train(m, training_date)]
        if available_muscles:
            muscle = random.choice(available_muscles)
            exercises = self._build_muscle_exercises(muscle, 1, self.current_week, True)
            if exercises:
                program['weekly_plan'][day].extend(exercises)
                
    def _remove_exercise(self, program: Dict, day: str):
        """حذف تمرین از برنامه"""
        if program['weekly_plan'][day]:
            # حذف یک تمرین ایزوله یا با حجم بالا
            exercises = program['weekly_plan'][day]
            isolation_exercises = [ex for ex in exercises if ex.mechanic == 'isolation']
            if isolation_exercises:
                program['weekly_plan'][day].remove(random.choice(isolation_exercises))
            else:
                program['weekly_plan'][day].pop()
                
    def _create_exercise_entry(self, exercise: Exercise, is_primary: bool) -> dict:
        if isinstance(exercise, dict):
            print('[ERROR] Only Exercise model instances are allowed, not dict')
            raise TypeError('Only Exercise model instances are allowed, not dict')
        muscles = exercise.primary_muscles if is_primary else exercise.secondary_muscles
        muscle_group = muscles[0] if muscles else 'full_body'
        print(f'[DEBUG] Creating exercise entry for {exercise.name} (primary={is_primary})')
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
            'rest_seconds': calculate_rest_time(exercise.mechanic, 0.7),
            'technique': getattr(exercise, 'technique', None),
            'technique_notes': getattr(exercise, 'technique_notes', None),
            'notes': get_exercise_notes(self.settings.experience_level, is_primary),
            'progression': get_progression_notes(self.settings.experience_level),
            'alternatives': self.get_exercise_alternatives(exercise)
        }
