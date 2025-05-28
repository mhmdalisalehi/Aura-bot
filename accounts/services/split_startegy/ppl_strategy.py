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
from accounts.services.date_converter import convert_day_to_date

current_date = datetime.now()

class PushPullLegsSplitStrategy(SplitStrategy):
    """
    استراتژی Push/Pull/Legs پیشرفته با ویژگی‌های حرفه‌ای
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
        'push': {
            'primary': ['chest', 'shoulders', 'triceps'],
            'secondary': ['front_delts', 'side_delts'],
            'synergists': ['core', 'upper_back'],
            'techniques': ['drop_sets', 'rest_pause', 'supersets'],
            'volume_multiplier': 1.2,
            'focus_areas': ['upper_chest', 'lateral_delts', 'triceps_long_head']
        },
        'pull': {
            'primary': ['back', 'biceps', 'rear_delts'],
            'secondary': ['traps', 'forearms'],
            'synergists': ['core', 'lower_back'],
            'techniques': ['giant_sets', 'rest_pause', 'negatives'],
            'volume_multiplier': 1.2,
            'focus_areas': ['upper_back', 'lats', 'biceps_peak']
        },
        'legs': {
            'primary': ['quadriceps', 'hamstrings', 'glutes'],
            'secondary': ['calves', 'adductors', 'abductors'],
            'synergists': ['core', 'lower_back'],
            'techniques': ['pyramids', 'rest_pause', 'drop_sets'],
            'volume_multiplier': 1.3,
            'focus_areas': ['outer_quads', 'hamstring_insertion', 'glute_medius']
        }
    }
    
    # توالی روزها با در نظر گرفتن ریکاوری
    DAY_SEQUENCE = ['push', 'pull', 'legs', 'push', 'pull', 'legs']
    
    # تکنیک‌های پیشرفته برای هر سطح تجربه
    ADVANCED_TECHNIQUES = {
        'beginner': ['drop_sets', 'rest_pause'],
        'intermediate': ['drop_sets', 'rest_pause', 'supersets', 'giant_sets'],
        'expert': ['drop_sets', 'rest_pause', 'supersets', 'giant_sets', 
                  'pyramids', 'negatives', 'forced_reps', 'cluster_sets']
    }
    
    def generate(self, week: int) -> Dict:
        program = {'weekly_plan': {}}
        sequence_idx = 0
        
        for day in self.settings.training_days:
            if sequence_idx >= len(self.DAY_SEQUENCE):
                sequence_idx = 0
                
            split_type = self.DAY_SEQUENCE[sequence_idx]
            program['weekly_plan'][day] = self._build_day_plan(split_type, week)
            sequence_idx += 1
            
        self._validate_split_schedule(program)
        self._add_warmup_cooldown(program)
        self._validate_volume(program)
        
        # تبدیل کلیدها به تاریخ
        dated_program = {}
        base_date = datetime.now()
        for day, exercises in program['weekly_plan'].items():
            training_date = convert_day_to_date(day, base_date)
            dated_program[training_date.strftime('%Y-%m-%d')] = exercises
        return dated_program
    
    def _build_day_plan(self, split_type: str, week: int) -> List[Exercise]:
        exercises = []
        muscle_config = self.MUSCLE_GROUPS[split_type]
        
        # تنظیم تعداد تمرینات بر اساس سطح تجربه
        exercise_counts = self._get_exercise_counts(split_type)
        
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
        available = self.exercise_selector.get_exercises([muscle], week)['main']
        if is_primary:
            filtered = [ex for ex in available if ex.mechanic == 'compound']
        else:
            filtered = [ex for ex in available if ex.mechanic == 'isolation']
        return filtered[:count]
    
    def _build_focus_area_exercises(self, focus_areas: List[str], week: int) -> List[Exercise]:
        exercises = []
        for area in focus_areas:
            if random.random() < 0.6:
                available = self.exercise_selector.get_exercises([area], week)['main']
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
        
    def _get_warmup(self, split_type: str) -> List[Exercise]:
        """انتخاب گرم کردن اختصاصی برای هر نوع جلسه"""
        warmups = {
            'push': [{
                'type': 'mobility',
                'content': [
                    {'name': 'Band Shoulder Dislocates', 'sets': 2, 'reps': '10-12'},
                    {'name': 'Scapular Wall Slides', 'sets': 2, 'reps': '12-15'},
                    {'name': 'Dynamic Chest Stretch', 'sets': 2, 'duration': '30s'}
                ],
                'notes': 'Focus on shoulder mobility and chest activation'
            }],
            'pull': [{
                'type': 'mobility',
                'content': [
                    {'name': 'Band Pull-Aparts', 'sets': 2, 'reps': '15-20'},
                    {'name': 'Cat-Cow Stretch', 'sets': 2, 'reps': '10-12'},
                    {'name': 'Lat Stretch', 'sets': 2, 'duration': '30s'}
                ],
                'notes': 'Focus on upper back mobility and lat activation'
            }],
            'legs': [{
                'type': 'mobility',
                'content': [
                    {'name': 'Hip Circle Walks', 'sets': 2, 'reps': '10 each direction'},
                    {'name': 'Bodyweight Squats with Pause', 'sets': 2, 'reps': '12-15'},
                    {'name': 'Dynamic Hamstring Stretch', 'sets': 2, 'duration': '30s'}
                ],
                'notes': 'Focus on hip mobility and leg activation'
            }]
        }
        return warmups.get(split_type, [])
        
    def _get_cooldown(self, split_type: str) -> List[Exercise]:
        """انتخاب سرد کردن اختصاصی برای هر نوع جلسه"""
        cooldowns = {
            'push': [{
                'type': 'cooldown',
                'content': [
                    {'name': 'Chest Stretch', 'duration': '60s', 'notes': 'Focus on pec minor'},
                    {'name': 'Shoulder Stretch', 'duration': '45s each side', 'notes': 'Include internal rotation'},
                    {'name': 'Foam Roll Upper Back', 'duration': '90s', 'notes': 'Focus on tight spots'}
                ],
                'notes': 'Emphasize chest and shoulder recovery'
            }],
            'pull': [{
                'type': 'cooldown',
                'content': [
                    {'name': 'Lat Stretch', 'duration': '60s each side', 'notes': 'Include overhead reach'},
                    {'name': 'Biceps Stretch', 'duration': '45s each arm', 'notes': 'Include shoulder extension'},
                    {'name': 'Foam Roll Upper Back', 'duration': '90s', 'notes': 'Focus on rhomboids'}
                ],
                'notes': 'Emphasize back and biceps recovery'
            }],
            'legs': [{
                'type': 'cooldown',
                'content': [
                    {'name': 'Quad Stretch', 'duration': '60s each leg', 'notes': 'Include hip flexor'},
                    {'name': 'Hamstring Stretch', 'duration': '45s each leg', 'notes': 'Include sciatic nerve glides'},
                    {'name': 'Foam Roll Calves', 'duration': '90s each leg', 'notes': 'Focus on medial head'}
                ],
                'notes': 'Emphasize leg recovery and mobility'
            }]
        }
        return cooldowns.get(split_type, [])
        
    def _validate_split_schedule(self, program: Dict):
        # اطمینان از توالی مناسب بین جلسات
        trained_muscles = defaultdict(list)
        for day, exercises in program['weekly_plan'].items():
            # اطمینان از اینکه day تاریخ است
            training_date = convert_day_to_date(day, datetime.now())
            for ex in exercises:
                if 'primary_muscles' in ex:
                    for muscle in ex['primary_muscles']:
                        trained_muscles[muscle].append(training_date)
        
        for muscle, days in trained_muscles.items():
            min_recovery = RecoveryManager.BASE_RECOVERY_DAYS.get(muscle, 2)
            for i in range(1, len(days)):
                if (days[i] - days[i-1]).days < min_recovery:
                    self._adjust_exercise_scheduling(program, muscle)

    def _add_warmup_cooldown(self, program: Dict):
        """افزودن گرم کردن و سرد کردن متناسب برای هر جلسه"""
        for day, exercises in program['weekly_plan'].items():
            split_type = self.DAY_SEQUENCE[list(program['weekly_plan'].keys()).index(day) % len(self.DAY_SEQUENCE)]
            warmup = self._get_warmup(split_type)
            cooldown = self._get_cooldown(split_type)
            program['weekly_plan'][day] = warmup + exercises + cooldown

    def _validate_volume(self, program: Dict):
        # اعتبارسنجی حجم کلی برنامه
        total_volume = sum(self.volume_manager.muscle_volume.values())
        volume_range = self.volume_manager.VOLUME_TARGETS[self.user.goal][self.settings.experience_level]
        target = (volume_range[0] + volume_range[1]) / 2  # میانگین محدوده حجم
        if total_volume < target * 0.8:
            self._adjust_program(program, increase=True)
        elif total_volume > target * 1.2:
            self._adjust_program(program, increase=False)

    def _adjust_program(self, program: Dict, increase: bool):
        # تنظیم برنامه بر اساس حجم کلی
        adjustment_factor = 1.1 if increase else 0.9
        for day in program['weekly_plan']:
            for exercise in program['weekly_plan'][day]:
                if isinstance(exercise, dict) and 'sets' in exercise:
                    exercise['sets'] = math.ceil(exercise['sets'] * adjustment_factor)

    def _add_exercise(self, program: Dict, day: str):
        # اطمینان از اینکه day تاریخ است
        training_date = convert_day_to_date(day, datetime.now())
        available_muscles = [m for m in self.MUSCLE_GROUPS['primary'].values() 
                           if self.recovery_manager.can_train(m, training_date)]
        if available_muscles:
            muscle = random.choice(available_muscles)
            exercises = self._build_muscle_exercises(muscle, 1, self.current_week, True)
            if exercises:
                program['weekly_plan'][day].extend(exercises)

    def _adjust_exercise_scheduling(self, program: Dict, muscle: str):
        """
        پیاده‌سازی موقت: زمان‌بندی تمرینات را برای ریکاوری بهتر تنظیم می‌کند (موقت)
        این متد فعلاً فقط یک پیاده‌سازی ساده است و هیچ تغییری ایجاد نمی‌کند.
        بعداً باید منطق کامل اضافه شود.
        """
        pass
