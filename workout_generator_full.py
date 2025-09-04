# from django.db import models
# from typing import Dict, List, Optional
# from collections import defaultdict
# import random
# import math
# from exercises.models import Exercise
# from accounts.models import UserProfile, TrainingSettings, InjuryExerciseClassification
# from django.db.models import Q
# from datetime import timedelta, datetime
# import random

# current_date = datetime.now()

# # --- کد کامل کلاس‌ها ---
# from django.db import models
# from typing import Dict, List, Optional
# from collections import defaultdict
# import random
# import math
# from exercises.models import Exercise
# from accounts.models import UserProfile, TrainingSettings, InjuryExerciseClassification
# from django.db.models import Q
# from datetime import timedelta, datetime
# import random

# current_date = datetime.now()

# class ExerciseSelector:
#     def __init__(self, user_profile, training_settings):
#         self.user_profile = user_profile
#         self.training_settings = training_settings
#         self.exercise_history = defaultdict(list)
        
#     def get_exercises(self, muscle_groups: List[str], week: int) -> List[Exercise]:
#         # منطق انتخاب هوشمندانه تمرینات با در نظر گرفتن تاریخچه و تنوع
#         base_query = Exercise.objects.filter(
#             primary_muscles__overlap=muscle_groups,
#             equipment__in=self.training_settings.available_equipment,
#             level=self.training_settings.experience_level
#         )
        
#         # فیلترهای پیشرفته بر اساس تیپ بدنی
#         if self.user_profile.body_type == 'mesomorph':
#             base_query = base_query.filter(mechanic='compound').order_by('?')
#         elif self.user_profile.body_type == 'ectomorph':
#             base_query = base_query.filter(category='strength')
#         else:
#             base_query = base_query.filter(category__in=['strength', 'cardio'])

#         # حذف تمرینات تکراری در هفته‌های متوالی
#         recent_exercises = set()
#         for w in range(max(0, week-2), week):
#             recent_exercises.update(self.exercise_history[w])
            
#         exercises = [ex for ex in base_query if ex.id not in recent_exercises]
        
#         # اولویت‌بندی بر اساس اثربخشی برای هدف کاربر
#         if self.user_profile.goal == 'muscle_gain':
#             exercises.sort(key=lambda x: x.metabolic_stress_factor, reverse=True)
#         else:
#             exercises.sort(key=lambda x: x.mechanical_tension_factor, reverse=True)
            
#         return exercises[:5]

# class WorkoutVolumeManager:
#     VOLUME_TARGETS = {
#         'muscle_gain': {
#             'beginner': (60, 80),
#             'intermediate': (80, 120),
#             'expert': (120, 150)
#         },
#         'strength': {
#             'beginner': (40, 60),
#             'intermediate': (60, 90),
#             'expert': (90, 120)
#         },
#         'endurance': {
#             'beginner': (80, 100),
#             'intermediate': (100, 140),
#             'expert': (140, 180)
#         },
#         'weight_loss': {
#             'beginner': (70, 90),
#             'intermediate': (90, 130),
#             'expert': (130, 170)
#         }
#     }
    
#     def __init__(self, user_profile, training_settings):
#         self.user_profile = user_profile
#         self.training_settings = training_settings
#         self.muscle_volume = defaultdict(float)
        
#     def calculate_volume(self, exercise: Exercise, sets: int, reps: int) -> float:
#         # محاسبه حجم با در نظر گرفتن فاکتور شدت (بر اساس %1RM)
#         intensity = self._estimate_intensity(exercise, reps)
#         return sets * reps * intensity
    
#     def _estimate_intensity(self, exercise: Exercise, reps: int) -> float:
#         # تخمین شدت بر اساس تکرارها (بر اساس جدول RM)
#         rm_table = {
#             3: 0.93, 5: 0.87, 8: 0.80, 
#             10: 0.75, 12: 0.70, 15: 0.65
#         }
#         closest_rep = min(rm_table.keys(), key=lambda x: abs(x - reps))
#         return rm_table[closest_rep]
    
#     def adjust_volume(self, muscle_group: str, week: int) -> Dict[str, int]:
#         # تنظیم حجم بر اساس سیکل پیشرونده و تیپ بدنی
#         volume_range = self.VOLUME_TARGETS[self.user_profile.goal][self.training_settings.experience_level]
#         base_volume = (volume_range[0] + volume_range[1]) / 2  # میانگین محدوده حجم
        
#         # تطبیق حجم برای تیپ بدنی
#         if self.user_profile.body_type == 'mesomorph':
#             base_volume *= 1.2 if week % 4 != 0 else 0.6  # Deload در هفته 4
#         elif self.user_profile.body_type == 'ectomorph':
#             base_volume *= 0.8 if week % 4 != 0 else 0.5
            
#         # توزیع حجم بین گروه‌های عضلانی
#         allocated_volume = base_volume * self._muscle_priority(muscle_group)
#         return {
#             'sets': math.ceil(allocated_volume / 25),  # فرض 25 واحد حجم به ازای هر ست
#             'reps': (8, 12) if self.user_profile.goal == 'muscle_gain' else (4, 6)
#         }
    
#     def _muscle_priority(self, muscle_group: str) -> float:
#         # اولویت‌بندی عضلات بر اساس هدف کاربر
#         priorities = {
#             'muscle_gain': {'chest': 0.25, 'back': 0.25, 'quadriceps': 0.2, 
#                            'shoulders': 0.15, 'hamstrings': 0.15},
#             'strength': {'chest': 0.2, 'back': 0.2, 'quadriceps': 0.25, 
#                         'shoulders': 0.15, 'hamstrings': 0.2},
#             'endurance': {'chest': 0.15, 'back': 0.15, 'quadriceps': 0.2, 
#                          'shoulders': 0.15, 'hamstrings': 0.2, 'core': 0.15},
#             'weight_loss': {'chest': 0.15, 'back': 0.15, 'quadriceps': 0.2, 
#                            'shoulders': 0.15, 'hamstrings': 0.2, 'core': 0.15}
#         }
#         return priorities[self.user_profile.goal].get(muscle_group, 0.1)

# class RecoveryManager:
#     MIN_RECOVERY_DAYS = {
#         'chest': 2, 'back': 2, 'quadriceps': 3,
#         'hamstrings': 2, 'shoulders': 2, 'biceps': 2,
#         'triceps': 2, 'calves': 1, 'core': 1
#     }
    
#     def __init__(self):
#         self.last_trained = defaultdict(list)
        
#     def can_train(self, muscle_groups: List[str], day: str) -> bool:
#         # بررسی فاصله کافی بین تمرینات یک گروه عضلانی
#         for muscle in muscle_groups:
#             last_sessions = self.last_trained[muscle]
#             if last_sessions:
#                 recovery_days = self.MIN_RECOVERY_DAYS.get(muscle, 2)
#                 if (day - last_sessions[-1]).days < recovery_days:
#                     return False
#         return True

# class WorkoutGenerator:
#     def __init__(self, user_profile: UserProfile, training_settings: TrainingSettings):
#         self.user = user_profile
#         self.settings = training_settings
#         self.exercise_selector = ExerciseSelector(user_profile, training_settings)
#         self.volume_manager = WorkoutVolumeManager(user_profile, training_settings)
#         self.recovery_manager = RecoveryManager()
#         self.split_strategies = {
#             'upper_lower': UpperLowerSplitStrategy,
#             'push_pull_legs': PushPullLegsSplitStrategy,
#             'full_body': FullBodySplitStrategy,
#             'bro_split': BroSplitStrategy,

#         }
        
#     def generate_program(self, week: int) -> Dict:
#         strategy = self.split_strategies[self.settings.split_type](
#             self.user, 
#             self.settings,
#             self.exercise_selector,
#             self.volume_manager,
#             self.recovery_manager
#         )
#         return strategy.generate(week)

# class SplitStrategy:
#     def __init__(self, user, settings, exercise_selector, volume_manager, recovery_manager):
#         self.user = user
#         self.settings = settings
#         self.exercise_selector = exercise_selector
#         self.volume_manager = volume_manager
#         self.recovery_manager = recovery_manager
#         self.split_map = {}
        
#     def generate(self, week: int) -> Dict:
#         # متد اصلی برای تولید برنامه
#         pass

# class BroSplitStrategy(SplitStrategy):
#     """
#     استراتژی Bro Split (تمرین هر گروه عضلانی در یک روز جداگانه)
#     ساختار پیش‌فرض:
#     - روز 1: سینه
#     - روز 2: پشت
#     - روز 3: پاها
#     - روز 4: سرشانه
#     - روز 5: بازوها (جلو/پشت بازو)
#     - روز 6: تکمیلی (اختیاری)
#     """
#     MUSCLE_DAY_MAPPING = {
#         'chest': ['chest', 'triceps'],  # سینه + تکمیلی جلو بازو
#         'back': ['back', 'biceps'],      # پشت + تکمیلی جلو بازو
#         'legs': ['quadriceps', 'hamstrings', 'glutes', 'calves'],
#         'shoulders': ['shoulders', 'traps', 'rear_delts'],
#         'arms': ['biceps', 'triceps', 'forearms'],
#         'core': ['abs', 'obliques', 'lower_back']  # اختیاری
#     }
    
#     DAY_PRIORITY = ['chest', 'back', 'legs', 'shoulders', 'arms','core']
    
#     def generate(self, week: int) -> Dict:
#         program = {'weekly_plan': {}}
#         available_days = list(self.settings.training_days.keys())
        
#         # توزیع روزهای تمرین بر اساس اولویت
#         for i, muscle_day in enumerate(self.DAY_PRIORITY):
#             if i >= len(available_days):
#                 break
                
#             day_name = available_days[i]
#             program['weekly_plan'][day_name] = self._build_muscle_day(
#                 muscle_day, 
#                 week
#             )
        
#         # روزهای اضافی برای تمرینات تکمیلی
#         if len(available_days) > len(self.DAY_PRIORITY):
#             extra_days = available_days[len(self.DAY_PRIORITY):]
#             for day in extra_days:
#                 program['weekly_plan'][day] = self._build_hybrid_day(week)
        
#         self._add_warmup_cooldown(program)
#         return program
    
#     def _build_muscle_day(self, muscle_day: str, week: int) -> List[Dict]:
#         """ساخت برنامه برای یک روز اختصاصی یک گروه عضلانی"""
#         exercises = []
#         primary_muscles = self.MUSCLE_DAY_MAPPING[muscle_day]
        
#         # تمرینات اصلی (4-5 تمرین برای عضله اصلی)
#         primary_count = {
#             'beginner': 3,
#             'intermediate': 4,
#             'expert': 5
#         }.get(self.settings.experience_level, 4)
        
#         # تمرینات ترکیبی برای عضله اصلی
#         main_muscle = primary_muscles[0]
#         compound_exercises = self.exercise_selector.get_exercises(
#             [main_muscle],
#             week,
#             mechanic='compound'
#         )
        
#         for ex in compound_exercises[:min(2, len(compound_exercises))]:
#             volume = self._get_volume_for_muscle(main_muscle, week, is_compound=True)
#             exercises.append(self._create_exercise_entry(ex, volume, True))
        
#         # تمرینات تکمیلی برای عضله اصلی
#         isolation_exercises = self.exercise_selector.get_exercises(
#             [main_muscle],
#             week,
#             mechanic='isolation'
#         )
        
#         for ex in isolation_exercises[:primary_count - 2]:
#             volume = self._get_volume_for_muscle(main_muscle, week, is_compound=False)
#             exercises.append(self._create_exercise_entry(ex, volume, False))
        
#         # تمرینات برای عضلات ثانویه (1-2 تمرین)
#         if len(primary_muscles) > 1:
#             secondary_muscles = primary_muscles[1:]
#             for muscle in secondary_muscles:
#                 if random.random() < 0.7:  # 70% شانس اضافه کردن تمرین ثانویه
#                     ex = self._select_secondary_exercise(muscle, week)
#                     if ex:
#                         exercises.append(ex)
        
#         return exercises
    
#     def _get_volume_for_muscle(self, muscle: str, week: int, is_compound: bool) -> Dict:
#         """محاسبه حجم تمرین بر اساس عضله و نوع حرکت"""
#         base_volume = self.volume_manager.adjust_volume(muscle, week)
        
#         # تنظیم حجم برای Bro Split (حجم بیشتر در هر جلسه)
#         adjusted_sets = base_volume['sets'] * {
#             'compound': 1.2,
#             'isolation': 1.0
#         }.get('compound' if is_compound else 'isolation', 1.0)
        
#         return {
#             'sets': math.ceil(adjusted_sets),
#             'reps': base_volume['reps']
#         }
    
#     def _select_secondary_exercise(self, muscle: str, week: int) -> Optional[Dict]:
#         """انتخاب تمرین برای عضلات ثانویه"""
#         available = self.exercise_selector.get_exercises([muscle], week)
#         if available:
#             volume = self._get_volume_for_muscle(muscle, week, is_compound=False)
#             ex = random.choice(available)
#             return self._create_exercise_entry(ex, volume, False)
#         return None
    
#     def _build_hybrid_day(self, week: int) -> List[Dict]:
#         """ساخت روزهای ترکیبی (برای روزهای اضافی)"""
#         options = [
#             ('core', ['abs', 'obliques']),
#             ('weak_points', self._get_user_weak_points()),
#             ('cardio', ['conditioning'])
#         ]
        
#         selected_focus = random.choice(options)
#         exercises = []
        
#         if selected_focus[0] == 'core':
#             for muscle in selected_focus[1]:
#                 ex = self._select_secondary_exercise(muscle, week)
#                 if ex:
#                     exercises.append(ex)
        
#         elif selected_focus[0] == 'weak_points':
#             for muscle in selected_focus[1]:
#                 ex = self._select_secondary_exercise(muscle, week)
#                 if ex:
#                     exercises.append({
#                         **ex,
#                         'tags': ['weak_point_focus'],
#                         'intensity_notes': 'Higher volume'
#                     })
        
#         else:  # cardio/conditioning
#             exercises.append({
#                 'type': 'conditioning',
#                 'content': self._select_cardio_protocol()
#             })
        
#         return exercises
    
#     def _get_user_weak_points(self) -> List[str]:
#         """تعیین نقاط ضعف کاربر بر اساس تیپ بدنی و هدف"""
#         weak_points = {
#             'mesomorph': ['calves', 'rear_delts'],
#             'ectomorph': ['legs', 'back'],
#             'endomorph': ['shoulders', 'arms']
#         }.get(self.user.body_type, [])
        
#         if self.user.goal == 'muscle_gain':
#             weak_points.extend(['traps', 'upper_chest'])
#         return list(set(weak_points))
    
#     def _select_cardio_protocol(self) -> List[str]:
#         """انتخاب پروتکل کاردیو بر اساس هدف کاربر"""
#         if self.user.goal == 'weight_loss':
#             return ['HIIT (30s sprint, 60s walk) x 8 rounds']
#         return ['Moderate pace (30-45 mins)']
    
#     def _create_exercise_entry(self, exercise: Exercise, volume: Dict, is_compound: bool) -> Dict:
#         """ساخت وروردی استاندارد برای تمرین"""
#         return {
#             'exercise_id': exercise.id,
#             'exercise_name': exercise.name,
#             'type': 'compound' if is_compound else 'isolation',
#             'muscle_group': exercise.primary_muscles[0],
#             'sets': volume['sets'],
#             'reps': volume['reps'],
#             'rest_seconds': self._calculate_rest_time(exercise, is_compound),
#             'notes': self._generate_exercise_notes(exercise, is_compound)
#         }
    
#     def _calculate_rest_time(self, exercise: Exercise, is_compound: bool) -> int:
#         """محاسبه زمان استراحت برای Bro Split"""
#         if is_compound:
#             return 90 if self.user.goal == 'muscle_gain' else 120
#         return 60 if 'arms' in exercise.primary_muscles else 75
    
#     def _generate_exercise_notes(self, exercise: Exercise, is_compound: bool) -> str:
#         """تولید نکات تمرینی"""
#         notes = []
#         if is_compound:
#             notes.append('Focus on form and controlled tempo')
        
#         if self.user.body_type == 'mesomorph':
#             notes.append('Push to failure on last set')
#         elif self.user.body_type == 'endomorph':
#             notes.append('Moderate intensity, focus on mind-muscle connection')
        
#         return '. '.join(notes)

# class PushPullLegsSplitStrategy(SplitStrategy):
#     MUSCLE_GROUPS = {
#         'push': ['chest', 'triceps', 'shoulders'],
#         'pull': ['back', 'biceps', 'rear_delts'],
#         'legs': ['quadriceps', 'hamstrings', 'glutes', 'calves']
#     }
    
#     DAY_SEQUENCE = ['push', 'pull', 'legs', 'push', 'pull', 'legs']
    
#     def generate(self, week: int) -> Dict:
#         program = {'weekly_plan': {}}
#         sequence_idx = 0
        
#         for day in self.settings.training_days:
#             if sequence_idx >= len(self.DAY_SEQUENCE):
#                 sequence_idx = 0
                
#             split_type = self.DAY_SEQUENCE[sequence_idx]
#             program['weekly_plan'][day] = self._build_day_plan(split_type, week)
#             sequence_idx += 1
            
#         self._validate_split_schedule(program)
#         self._add_warmup_cooldown(program)
#         self._validate_volume(program)
#         return program
    
#     def _build_day_plan(self, split_type: str, week: int) -> List[Dict]:
#         exercises = []
#         target_muscles = self.MUSCLE_GROUPS[split_type]
        
#         # اولویت‌بندی عضلات اصلی برای هر جلسه
#         priority_muscles = {
#             'push': ['chest', 'shoulders', 'triceps'],
#             'pull': ['back', 'biceps'],
#             'legs': ['quadriceps', 'hamstrings']
#         }
        
#         for muscle in priority_muscles[split_type]:
#             if not self.recovery_manager.can_train(muscle, current_date):
#                 continue
                
#             volume = self.volume_manager.adjust_volume(muscle, week)
#             available_exercises = self.exercise_selector.get_exercises([muscle], week)
            
#             if available_exercises:
#                 selected_exercise = random.choice(available_exercises)
#                 exercises.append(self._create_exercise_entry(
#                     selected_exercise, 
#                     volume,
#                     is_compound=True
#                 ))
#                 self._update_tracking(muscle, selected_exercise)

#         # اضافه کردن تمرینات تکمیلی
#         for muscle in list(set(target_muscles) - set(priority_muscles[split_type])):
#             if random.random() < 0.7:  # 70% احتمال اضافه کردن تمرین تکمیلی
#                 volume = self.volume_manager.adjust_volume(muscle, week)
#                 available_exercises = self.exercise_selector.get_exercises([muscle], week)
#                 if available_exercises:
#                     selected_exercise = random.choice(available_exercises)
#                     exercises.append(self._create_exercise_entry(
#                         selected_exercise,
#                         volume,
#                         is_compound=False
#                     ))
#                     self._update_tracking(muscle, selected_exercise)

#         return exercises
    
#     def _create_exercise_entry(self, exercise: Exercise, volume: Dict, is_compound: bool) -> Dict:
#         return {
#             'exercise_id': exercise.id,
#             'exercise_name': exercise.name,
#             'type': 'compound' if is_compound else 'accessory',
#             'sets': volume['sets'],
#             'reps': self._determine_rep_range(exercise, is_compound),
#             'rest_seconds': self._calculate_rest_time(exercise, is_compound),
#             'intensity_notes': self._generate_intensity_notes(exercise)
#         }
    
#     def _determine_rep_range(self, exercise: Exercise, is_compound: bool) -> str:
#         if self.user.goal == 'muscle_gain':
#             return '8-12' if is_compound else '12-15'
#         return '4-6' if is_compound else '8-10'
    
#     def _calculate_rest_time(self, exercise: Exercise, is_compound: bool) -> int:
#         base_times = {
#             'compound': 90 if self.user.goal == 'muscle_gain' else 120,
#             'accessory': 60
#         }
#         return base_times['compound' if is_compound else 'accessory']
    
#     def _generate_intensity_notes(self, exercise: Exercise) -> str:
#         if self.user.body_type == 'mesomorph':
#             return 'RPE 8-9' 
#         return 'RPE 7-8' if self.user.body_type == 'endomorph' else 'RPE 6-7'
    
#     def _validate_split_schedule(self, program: Dict):
#         # اطمینان از توالی مناسب بین جلسات
#         trained_muscles = defaultdict(list)
#         for day, exercises in program['weekly_plan'].items():
#             for ex in exercises:
#                 if 'primary_muscles' in ex:
#                     for muscle in ex['primary_muscles']:
#                         trained_muscles[muscle].append(day)
        
#         for muscle, days in trained_muscles.items():
#             min_recovery = RecoveryManager.MIN_RECOVERY_DAYS.get(muscle, 2)
#             for i in range(1, len(days)):
#                 if (days[i] - days[i-1]).days < min_recovery:
#                     self._adjust_exercise_scheduling(program, muscle)

#     def _add_warmup_cooldown(self, program: Dict):
#         """افزودن گرم کردن و سرد کردن متناسب برای هر جلسه"""
#         for day, exercises in program['weekly_plan'].items():
#             split_type = self.DAY_SEQUENCE[list(program['weekly_plan'].keys()).index(day) % len(self.DAY_SEQUENCE)]
#             warmup = self._get_warmup(split_type)
#             cooldown = self._get_cooldown(split_type)
#             # Ensure main is a list of main exercises
#             program['weekly_plan'][day] = {
#                 'main': exercises,
#                 'warmup': warmup,
#                 'cooldown': cooldown
#             }

#     def _get_warmup(self, split_type: str) -> List[Dict]:
#         """انتخاب گرم کردن اختصاصی برای هر نوع جلسه"""
#         warmups = {
#             'push': [{
#                 'type': 'mobility',
#                 'content': ['Band Shoulder Dislocates', 
#                            'Scapular Wall Slides',
#                            'Dynamic Chest Stretch']
#             }],
#             'pull': [{
#                 'type': 'mobility',
#                 'content': ['Band Pull-Aparts',
#                            'Cat-Cow Stretch',
#                            'Lat Stretch']
#             }],
#             'legs': [{
#                 'type': 'mobility',
#                 'content': ['Hip Circle Walks', 
#                            'Bodyweight Squats with Pause',
#                            'Dynamic Hamstring Stretch']
#             }]
#         }
#         return warmups.get(split_type, [])

#     def _get_cooldown(self, split_type: str) -> List[Dict]:
#         """انتخاب سرد کردن اختصاصی برای هر نوع جلسه"""
#         cooldowns = {
#             'push': [{
#                 'type': 'cooldown',
#                 'content': ['Stretch Chest', 'Stretch Shoulders', 'Foam Roll Upper Back']
#             }],
#             'pull': [{
#                 'type': 'cooldown',
#                 'content': ['Stretch Lats', 'Stretch Biceps', 'Foam Roll Upper Back']
#             }],
#             'legs': [{
#                 'type': 'cooldown',
#                 'content': ['Stretch Quads', 'Stretch Hamstrings', 'Foam Roll Calves']
#             }]
#         }
#         return cooldowns.get(split_type, [])

#     def _validate_volume(self, program: Dict):
#         # اعتبارسنجی حجم کلی برنامه
#         total_volume = sum(self.volume_manager.muscle_volume.values())
#         volume_range = self.volume_manager.VOLUME_TARGETS[self.user.goal][self.settings.experience_level]
#         target = (volume_range[0] + volume_range[1]) / 2  # میانگین محدوده حجم
#         if total_volume < target * 0.8:
#             self._adjust_program(program, increase=True)
#         elif total_volume > target * 1.2:
#             self._adjust_program(program, increase=False)

#     def _adjust_program(self, program: Dict, increase: bool):
#         # تنظیم برنامه بر اساس حجم کلی
#         adjustment_factor = 1.1 if increase else 0.9
#         for day in program['weekly_plan']:
#             for exercise in program['weekly_plan'][day]:
#                 if isinstance(exercise, dict) and 'sets' in exercise:
#                     exercise['sets'] = math.ceil(exercise['sets'] * adjustment_factor)

# class FullBodySplitStrategy(SplitStrategy):
#     MUSCLE_GROUPS = [
#         'chest', 'back', 'quadriceps', 
#         'hamstrings', 'shoulders', 'core'
#     ]
    
#     EXERCISE_PER_MUSCLE = {
#         'beginner': 1,
#         'intermediate': 2,
#         'expert': 2
#     }
    
#     def generate(self, week: int) -> Dict:
#         program = {'weekly_plan': {}}
        
#         for day in self.settings.training_days:
#             program['weekly_plan'][day] = self._build_fullbody_day(week)
            
#         self._balance_volume_across_days(program)
#         return program
    
#     def _build_fullbody_day(self, week: int) -> List[Dict]:
#         exercises = []
#         target_count = self.EXERCISE_PER_MUSCLE[self.settings.experience_level]
        
#         for muscle in self.MUSCLE_GROUPS:
#             if len(exercises) >= 6:  # حداکثر 6 تمرین در روز
#                 break
                
#             if self.recovery_manager.can_train(muscle, current_date):
#                 available_exercises = self.exercise_selector.get_exercises([muscle], week)
#                 selected = random.sample(available_exercises, min(target_count, len(available_exercises)))
                
#                 for ex in selected:
#                     volume = self.volume_manager.adjust_volume(muscle, week)
#                     exercises.append({
#                         'exercise_id': ex.id,
#                         'exercise_name': ex.name,
#                         'sets': volume['sets'],
#                         'reps': '10-15' if self.user.goal == 'endurance' else '6-12',
#                         'rest_seconds': 75
#                     })
#                     self._update_tracking(muscle, ex)
        
#         return exercises
    
#     def _balance_volume_across_days(self, program: Dict):
#         # اطمینان از توزیع یکنواخت حجم در روزهای مختلف
#         daily_volumes = []
#         for day in program['weekly_plan']:
#             total = sum(self.volume_manager.calculate_volume(ex['exercise'], ex['sets'], ex['reps']) 
#                       for ex in program['weekly_plan'][day] if 'exercise' in ex)
#             daily_volumes.append(total)
        
#         avg_volume = sum(daily_volumes) / len(daily_volumes)
#         for i, vol in enumerate(daily_volumes):
#             if vol < avg_volume * 0.8:
#                 self._add_exercise(program, list(program['weekly_plan'].keys())[i])
#             elif vol > avg_volume * 1.2:
#                 self._remove_exercise(program, list(program['weekly_plan'].keys())[i])

# class UpperLowerSplitStrategy(SplitStrategy):
#     MUSCLE_GROUPS = {
#         'upper': ['chest', 'back', 'shoulders', 'biceps', 'triceps'],
#         'lower': ['quadriceps', 'hamstrings', 'glutes', 'calves']
#     }
    
#     def generate(self, week: int) -> Dict:
#         program = {'weekly_plan': {}}
#         day_counter = 0
        
#         for day in self.settings.training_days:
#             split_type = 'upper' if day_counter % 2 == 0 else 'lower'
#             program['weekly_plan'][day] = self._build_day_plan(split_type, week)
#             self.split_map[day] = split_type
#             day_counter += 1
        
#         self._add_warmup_cooldown(program)
#         self._validate_volume(program)
#         return program
    
#     def _build_day_plan(self, split_type: str, week: int) -> List[Dict]:
#         exercises = []
#         target_muscles = self.MUSCLE_GROUPS[split_type]
        
#         for muscle in target_muscles:
#             if not self.recovery_manager.can_train(muscle, current_date):
#                 continue
                
#             volume = self.volume_manager.adjust_volume(muscle, week)
#             available_exercises = self.exercise_selector.get_exercises([muscle], week)
            
#             if available_exercises:
#                 selected_exercise = random.choice(available_exercises)
#                 exercises.append({
#                     'exercise_id': selected_exercise.id,
#                     'exercise_name': selected_exercise.name,
#                     'sets': volume['sets'],
#                     'reps': f"{volume['reps'][0]}-{volume['reps'][1]}",
#                     'rest_seconds': self._calculate_rest_time(selected_exercise)
#                 })
#                 self._update_tracking(muscle, selected_exercise)
                
#         return exercises
    
#     def _calculate_rest_time(self, exercise: Exercise) -> int:
#         # محاسبه زمان استراحت بر اساس نوع تمرین و هدف
#         if exercise.category == 'strength':
#             return 120 if 'compound' in exercise.mechanic else 90
#         return 60 if self.user.goal == 'muscle_gain' else 45
    
#     def _update_tracking(self, muscle: str, exercise: Exercise):
#         # به روزرسانی تاریخچه تمرین و حجم
#         self.recovery_manager.last_trained[muscle].append(current_date)
#         self.volume_manager.muscle_volume[muscle] += (
#             self.volume_manager.calculate_volume(
#                 exercise, 
#                 exercise.sets, 
#                 exercise.reps
#             )
#         )
        
#     def _add_warmup_cooldown(self, program: Dict):
#         # افزودن گرم کردن و سرد کردن متناسب
#         for day, exercises in program['weekly_plan'].items():
#             split_type = self.split_map[day]
#             warmup = self._get_warmup(split_type)
#             cooldown = self._get_cooldown(split_type)
#             # Ensure main is a list of main exercises
#             program['weekly_plan'][day] = {
#                 'main': exercises,
#                 'warmup': warmup,
#                 'cooldown': cooldown
#             }
            
#     def _get_warmup(self, split_type: str) -> List[Dict]:
#         # منطق انتخاب گرم کردن اختصاصی
#         if split_type == 'upper':
#             return [{
#                 'type': 'mobility',
#                 'content': ['Band Shoulder Dislocates', 
#                            'Scapular Wall Slides',
#                            'Dynamic Chest Stretch']
#             }]
#         else:
#             return [{
#                 'type': 'mobility',
#                 'content': ['Hip Circle Walks', 
#                            'Bodyweight Squats with Pause',
#                            'Dynamic Hamstring Stretch']
#             }]
    
#     def _get_cooldown(self, split_type: str) -> list:
#         # منطق انتخاب سرد کردن اختصاصی
#         if split_type == 'upper':
#             return [{
#                 'type': 'cooldown',
#                 'content': ['Stretch Chest', 'Stretch Shoulders', 'Foam Roll Upper Back']
#             }]
#         else:
#             return [{
#                 'type': 'cooldown',
#                 'content': ['Stretch Quads', 'Stretch Hamstrings', 'Foam Roll Calves']
#             }]
    
#     def _validate_volume(self, program: Dict):
#         # اعتبارسنجی حجم کلی برنامه
#         total_volume = sum(self.volume_manager.muscle_volume.values())
#         volume_range = self.volume_manager.VOLUME_TARGETS[self.user.goal][self.settings.experience_level]
#         target = (volume_range[0] + volume_range[1]) / 2  # میانگین محدوده حجم
        
#         if total_volume < target * 0.8:
#             self._adjust_program(program, increase=True)
#         elif total_volume > target * 1.2:
#             self._adjust_program(program, increase=False)
            
#     def _adjust_program(self, program: Dict, increase: bool):
#         # تنظیم برنامه بر اساس حجم کلی
#         adjustment_factor = 1.1 if increase else 0.9
#         for day in program['weekly_plan']:
#             for exercise in program['weekly_plan'][day]:
#                 if isinstance(exercise, dict) and 'sets' in exercise:
#                     exercise['sets'] = math.ceil(exercise['sets'] * adjustment_factor)

# class WorkoutQualityEvaluator:
#     @staticmethod
#     def evaluate(program: Dict) -> float:
#         # سیستم امتیازدهی به برنامه (0-100)
#         score = 0
        
#         # معیارهای ارزیابی
#         criteria = {
#             'muscle_coverage': 30,
#             'volume_adequacy': 25,
#             'exercise_variety': 20,
#             'recovery_time': 15,
#             'progressive_overload': 10
#         }
        
#         # محاسبه امتیاز برای هر معیار
#         score += criteria['muscle_coverage'] * WorkoutQualityEvaluator._muscle_coverage_score(program)
#         score += criteria['volume_adequacy'] * WorkoutQualityEvaluator._volume_score(program)
#         # ... محاسبات دیگر معیارها
        
#         return min(100, max(0, score))
    
#     @staticmethod
#     def _muscle_coverage_score(program: Dict) -> float:
#         # محاسبه پوشش عضلانی
#         trained_muscles = set()
#         for day in program['weekly_plan'].values():
#             for exercise in day:
#                 if isinstance(exercise, dict) and 'primary_muscles' in exercise:
#                     trained_muscles.update(exercise['primary_muscles'])
#         return len(trained_muscles) / 15  # فرض 15 گروه عضلانی اصلی
    
#     @staticmethod
#     def _volume_score(program: Dict) -> float:
#         # مقایسه حجم با اهداف استاندارد
#         # ... منطق محاسباتی
#         return 0.8  # مقدار نمونه