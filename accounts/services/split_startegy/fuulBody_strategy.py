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
    
    def generate(self, week: int) -> Dict:
        """تولید برنامه تمرینی با ویژگی‌های حرفه‌ای"""
        program = {'weekly_plan': {}}
        
        # اولویت‌بندی روزها بر اساس ریکاوری
        prioritized_days = self._prioritize_days_by_recovery(list(self.settings.training_days.keys()))
        
        for day in prioritized_days:
            # بررسی ریکاوری قبل از تولید برنامه
            if not self._check_recovery_for_day(day):
                # تنظیم مجدد روز در صورت نیاز به استراحت
                day = self._find_next_available_day(prioritized_days)
                
            program['weekly_plan'][day] = self._build_fullbody_day(week)
            self._validate_day_plan(program['weekly_plan'][day])
            
        self._balance_volume_across_days(program)
        self._add_warmup_cooldown(program)
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
        
    def _check_recovery_for_day(self, day: str) -> bool:
        """بررسی ریکاوری برای یک روز تمرین"""
        primary_muscles = []
        for group in self.MUSCLE_GROUPS['primary'].values():
            primary_muscles.extend(group)
            
        return all(self.recovery_manager.can_train(muscle, datetime.strptime(day, '%Y-%m-%d')) 
                  for muscle in primary_muscles)
        
    def _find_next_available_day(self, available_days: List[str]) -> str:
        """یافتن روز بعدی مناسب برای تمرین"""
        for day in available_days:
            if self._check_recovery_for_day(day):
                return day
        return available_days[0]  # اگر روز مناسب پیدا نشد
        
    def _build_fullbody_day(self, week: int) -> List[Dict]:
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
        
        # اضافه کردن گرم کردن و سرد کردن
        exercises = self._get_warmup() + exercises + self._get_cooldown()
        
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
        
    def _apply_advanced_techniques(self, exercises: List[Dict]) -> List[Dict]:
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
                exercises[i]['technique'] = technique
                exercises[i]['technique_notes'] = self._get_technique_notes(technique)
                
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
        
    def _adjust_exercise_volume(self, exercises: List[Dict]) -> List[Dict]:
        """تنظیم حجم تمرینات"""
        for exercise in exercises:
            is_primary = exercise['type'] == 'compound'
            multiplier = (self.MUSCLE_GROUPS['volume_multipliers']['primary'] 
                        if is_primary else 
                        self.MUSCLE_GROUPS['volume_multipliers']['secondary'])
            
            base_volume = self.volume_manager.adjust_volume(
                exercise['muscle_group'],
                self.current_week
            )
            
            # تنظیم حجم بر اساس ضریب
            adjusted_sets = math.ceil(base_volume['sets'] * multiplier)
            
            # تنظیم بر اساس تیپ بدنی
            if self.user.body_type == 'ectomorph':
                adjusted_sets = max(2, adjusted_sets - 1)
            elif self.user.body_type == 'mesomorph':
                adjusted_sets = min(6, adjusted_sets + 1)
                
            exercise.update({
                'sets': adjusted_sets,
                'reps': base_volume['reps'],
                'volume_multiplier': multiplier
            })
            
        return exercises
        
    def _get_warmup(self) -> List[Dict]:
        """انتخاب گرم کردن اختصاصی برای تمرین تمام بدن"""
        return [{
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
        
    def _get_cooldown(self) -> List[Dict]:
        """انتخاب سرد کردن اختصاصی برای تمرین تمام بدن"""
        return [{
            'type': 'cooldown',
            'content': [
                {'name': 'Full Body Stretch', 'duration': '5-10min', 'notes': 'Include all major muscle groups'},
                {'name': 'Foam Rolling', 'duration': '5-10min', 'notes': 'Focus on tight areas'},
                {'name': 'Deep Breathing', 'duration': '2-3min', 'notes': 'Calm down and relax'},
                {'name': 'Light Walking', 'duration': '5min', 'notes': 'Active recovery'}
            ],
            'notes': 'Emphasize full body recovery and flexibility'
        }]
        
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
        base_sets = 3 if is_primary else 2
        
        # تنظیم بر اساس سطح تجربه
        if self.settings.experience_level == 'beginner':
            base_sets = max(2, base_sets - 1)
        elif self.settings.experience_level == 'expert':
            base_sets = min(5, base_sets + 1)
            
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
            
    def _validate_day_plan(self, exercises: List[Dict]):
        """اعتبارسنجی برنامه روزانه"""
        # بررسی تعداد تمرینات
        if len(exercises) > 8:  # حداکثر 8 تمرین در روز
            exercises = exercises[:8]
            
        # بررسی توزیع گروه‌های عضلانی
        muscle_counts = defaultdict(int)
        for ex in exercises:
            if isinstance(ex, dict) and 'muscle_group' in ex:
                muscle_counts[ex['muscle_group']] += 1
                
        # تنظیم در صورت نیاز
        for muscle, count in muscle_counts.items():
            if count > 2:  # حداکثر 2 تمرین برای هر عضله
                self._adjust_muscle_exercises(exercises, muscle, count)
                
    def _adjust_muscle_exercises(self, exercises: List[Dict], muscle: str, count: int):
        """تنظیم تمرینات یک عضله خاص"""
        muscle_exercises = [ex for ex in exercises if ex.get('muscle_group') == muscle]
        if len(muscle_exercises) > 2:
            # حذف تمرینات اضافی با اولویت تمرینات ایزوله
            to_remove = len(muscle_exercises) - 2
            isolation_exercises = [ex for ex in muscle_exercises if ex['type'] == 'isolation']
            for ex in isolation_exercises[:to_remove]:
                exercises.remove(ex)
                
    def _balance_volume_across_days(self, program: Dict):
        """تعادل حجم تمرینات در روزهای مختلف"""
        daily_volumes = []
        for day, exercises in program['weekly_plan'].items():
            total = sum(self.volume_manager.calculate_volume(
                Exercise.objects.get(id=ex['exercise_id']),
                ex['sets'],
                ex['reps']
            ) for ex in exercises if isinstance(ex, dict))
            daily_volumes.append(total)
            
        avg_volume = sum(daily_volumes) / len(daily_volumes)
        for i, vol in enumerate(daily_volumes):
            if vol < avg_volume * 0.8:
                self._add_exercise(program, list(program['weekly_plan'].keys())[i])
            elif vol > avg_volume * 1.2:
                self._remove_exercise(program, list(program['weekly_plan'].keys())[i])
                
    def _add_exercise(self, program: Dict, day: str):
        """اضافه کردن تمرین به برنامه"""
        available_muscles = [m for m in self.MUSCLE_GROUPS['primary'].values() 
                           if self.recovery_manager.can_train(m, datetime.strptime(day, '%Y-%m-%d'))]
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
            isolation_exercises = [ex for ex in exercises if ex.get('type') == 'isolation']
            if isolation_exercises:
                program['weekly_plan'][day].remove(random.choice(isolation_exercises))
            else:
                program['weekly_plan'][day].pop()
