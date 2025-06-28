from django.db import models
from typing import Dict, List, Optional
from collections import defaultdict
import random
import math
from exercises.models import Exercise
from accounts.models import UserProfile, TrainingSettings, InjuryExerciseClassification
from django.db.models import Q
from datetime import datetime
import random
import datetime

current_date = datetime.datetime.now()

import calendar

def format_workout_plan_for_telegram(program: Dict) -> str:
    """
    Format a workout plan (program['weekly_plan']) for Telegram message.
    """
    emoji_map = {
        'compound': '🏋️',
        'isolation': '💪',
        'accessory': '💪',
        'cardio': '🔥',
        'conditioning': '🔥',
        'mobility': '🧘',
        'cooldown': '🧊',
    }
    weekly_plan = program.get('weekly_plan', program)
    day_lines = []
    for date, day_content in sorted(weekly_plan.items()):
        # Format date
        if isinstance(date, str):
            try:
                date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            except Exception:
                date_obj = date
        else:
            date_obj = date
        day_str = f"📅 {calendar.day_name[date_obj.weekday()]}, {date_obj.strftime('%B')} {date_obj.day}"
        lines = [day_str]
        # Get main exercises (handle both dict and list)
        if isinstance(day_content, dict):
            main_exs = day_content.get('main', [])
        else:
            main_exs = day_content
        for idx, ex in enumerate(main_exs, 1):
            ex_type = ex.get('type', 'compound')
            emoji = emoji_map.get(ex_type, '🏋️')
            name = ex.get('exercise_name', ex.get('name', ''))
            sets = ex.get('sets')
            reps = ex.get('reps')
            # Cardio/conditioning special format
            if ex_type in ['cardio', 'conditioning']:
                line = f"{emoji} Cardio: {name} — {reps if reps else ''}"
            else:
                sets_reps = f"{sets} sets × {reps} reps" if sets and reps else ''
                line = f"{idx}️⃣ {name} — {sets_reps}"
            # Notes
            notes = ex.get('notes') or ex.get('intensity_notes')
            if notes:
                line += f"\n   Notes: {notes}"
            # Type
            if ex_type not in ['cardio', 'conditioning']:
                line += f"\n   Type: {ex_type.capitalize()}"
            lines.append(line)
        day_lines.append('\n'.join(lines))
    return '\n\n'.join(day_lines)

def get_next_weekday_dates(selected_days, weeks_ahead=1, start_date=None):
    """
    Map user-selected weekdays to the next upcoming calendar dates.
    """
    import datetime

    # Persian to English mapping
    fa_to_en = {
        'شنبه': 'saturday',
        'یکشنبه': 'sunday',
        'دوشنبه': 'monday',
        'سه‌شنبه': 'tuesday',
        'سه شنبه': 'tuesday',
        'چهارشنبه': 'wednesday',
        'پنجشنبه': 'thursday',
        'جمعه': 'friday',
    }

    if start_date is None:
        start_date = datetime.date.today()
    weekday_map = {day: i for i, day in enumerate(
        ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    )}
    result = []
    for week in range(weeks_ahead):
        for day in selected_days:
            # Convert Persian to English if needed
            day_en = fa_to_en.get(day, day).lower()
            target = weekday_map[day_en]
            days_ahead = (target - start_date.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7  # Always get the next, not today
            date = start_date + datetime.timedelta(days=days_ahead + 7 * week)
            result.append(date)
    return result

class ExerciseSelector:
    # Add this mapping at the class level
    MUSCLE_GROUP_MAP = {
        "back": ["middle back", "lower back", "lats", "traps"],
        "chest": ["chest"],
        "shoulders": ["shoulders"],
        "biceps": ["biceps"],
        "triceps": ["triceps"],
        "quadriceps": ["quadriceps"],
        "hamstrings": ["hamstrings"],
        "glutes": ["glutes"],
        "calves": ["calves"],
        "forearms": ["forearms"],
        "abdominals": ["abdominals"],
        "core": ["abdominals", "lower back", "obliques"],
        "traps": ["traps"],
        "neck": ["neck"],
        # Add others as needed
    }

    def __init__(self, user_profile, training_settings):
        self.user_profile = user_profile
        self.training_settings = training_settings
        self.exercise_history = defaultdict(list)

    def _expand_muscle_groups(self, muscle_groups: List[str]) -> List[str]:
        expanded = []
        for mg in muscle_groups:
            expanded += self.MUSCLE_GROUP_MAP.get(mg, [mg])
        return list(set(expanded))

    def get_exercises(self, muscle_groups: List[str], week: int) -> List[Exercise]:
        db_muscles = self._expand_muscle_groups(muscle_groups)
        print(f"\n🔎 [LOG] Muscle(s): {db_muscles}")

        # Build Q object for "any" muscle in db_muscles
        muscle_q = Q()
        for muscle in db_muscles:
            muscle_q |= Q(primary_muscles__contains=[muscle])

        # Allow lower levels for higher-level users
        user_level = self.training_settings.experience_level
        level_order = ['beginner', 'intermediate', 'expert']
        allowed_levels = level_order[:level_order.index(user_level)+1]
        print(f"   [LOG] Allowed levels for user: {allowed_levels}")

        base_query = Exercise.objects.filter(
            muscle_q,
            Q(equipment__in=self.training_settings.available_equipment),
            Q(level__in=allowed_levels)
        )
        print(f"   [LOG] After base filtering (muscle+equipment+level): {base_query.count()} exercises")

        # --- Step 2: Injury filtering (avoid and safe in one step) ---
        user_injuries = self.user_profile.physical_limitations or []
        safe_ex_ids = set()
        if user_injuries:
            avoid_ex_ids = InjuryExerciseClassification.objects.filter(
                injury__in=user_injuries,
                classification='avoid'
            ).values_list('exercise_id', flat=True)
            base_query = base_query.exclude(id__in=avoid_ex_ids)
            print(f"   [LOG] After injury exclusion: {base_query.count()} exercises")
            safe_ex_ids = set(InjuryExerciseClassification.objects.filter(
                injury__in=user_injuries,
                classification='safe'
            ).values_list('exercise_id', flat=True))

        exercises = list(base_query)
        for ex in exercises:
            ex.is_safe = ex.id in safe_ex_ids

        print(f"   [LOG] Final exercises after all filtering: {len(exercises)}")

        # --- Step 3: Return a diverse set of top 5 exercises ---
        return exercises


class WorkoutVolumeManager:
    VOLUME_TARGETS = {
        'muscle_gain': {
            'beginner': (60, 80),
            'intermediate': (80, 120),
            'expert': (120, 150)
        },
        'strength': {
            'beginner': (40, 60),
            'intermediate': (60, 90),
            'expert': (90, 120)
        },
        'endurance': {
            'beginner': (80, 100),
            'intermediate': (100, 140),
            'expert': (140, 180)
        },
        'weight_loss': {
            'beginner': (70, 90),
            'intermediate': (90, 130),
            'expert': (130, 170)
        }
    }
    
    def __init__(self, user_profile, training_settings):
        self.user_profile = user_profile
        self.training_settings = training_settings
        self.muscle_volume = defaultdict(float)
        
    def calculate_volume(self, exercise: Exercise, sets: int, reps: int) -> float:
        # محاسبه حجم با در نظر گرفتن فاکتور شدت (بر اساس %1RM)
        intensity = self._estimate_intensity(exercise, reps)
        return sets * reps * intensity
    
    def _estimate_intensity(self, exercise: Exercise, reps: int) -> float:
        # تخمین شدت بر اساس تکرارها (بر اساس جدول RM)
        rm_table = {
            3: 0.93, 5: 0.87, 8: 0.80, 
            10: 0.75, 12: 0.70, 15: 0.65
        }
        closest_rep = min(rm_table.keys(), key=lambda x: abs(x - reps))
        return rm_table[closest_rep]
    
    def adjust_volume(self, muscle_group: str, week: int) -> Dict[str, int]:
        # تنظیم حجم بر اساس سیکل پیشرونده و تیپ بدنی
        volume_range = self.VOLUME_TARGETS[self.user_profile.goal][self.training_settings.experience_level]
        base_volume = (volume_range[0] + volume_range[1]) / 2  # میانگین محدوده حجم
        
        # تطبیق حجم برای تیپ بدنی
        if self.user_profile.body_type == 'mesomorph':
            base_volume *= 1.2 if week % 4 != 0 else 0.6  # Deload در هفته 4
        elif self.user_profile.body_type == 'ectomorph':
            base_volume *= 0.8 if week % 4 != 0 else 0.5
            
        # توزیع حجم بین گروه‌های عضلانی
        allocated_volume = base_volume * self._muscle_priority(muscle_group)
        return {
            'sets': math.ceil(allocated_volume / 2),  # فرض 25 واحد حجم به ازای هر ست
            'reps': (8, 12) if self.user_profile.goal == 'muscle_gain' else (4, 6)
        }
    
    def _muscle_priority(self, muscle_group: str) -> float:
        # اولویت‌بندی عضلات بر اساس هدف کاربر
        priorities = {
            'muscle_gain': {'chest': 0.25, 'back': 0.25, 'quadriceps': 0.2, 
                           'shoulders': 0.15, 'hamstrings': 0.15},
            'strength': {'chest': 0.2, 'back': 0.2, 'quadriceps': 0.25, 
                        'shoulders': 0.15, 'hamstrings': 0.2},
            'endurance': {'chest': 0.15, 'back': 0.15, 'quadriceps': 0.2, 
                         'shoulders': 0.15, 'hamstrings': 0.2, 'core': 0.15},
            'weight_loss': {'chest': 0.15, 'back': 0.15, 'quadriceps': 0.2, 
                           'shoulders': 0.15, 'hamstrings': 0.2, 'core': 0.15}
        }
        return priorities[self.user_profile.goal].get(muscle_group, 0.1)

class RecoveryManager:
    MIN_RECOVERY_DAYS = {
        'chest': 2, 'back': 2, 'quadriceps': 3,
        'hamstrings': 2, 'shoulders': 2, 'biceps': 2,
        'triceps': 2, 'calves': 1, 'core': 1
    }

    def __init__(self):
        # Track last trained date for each muscle
        self.last_trained = {}  # muscle: datetime.date

    def can_train(self, muscle_groups: List[str], on_date: datetime.date) -> bool:
        """
        Returns False if any muscle in muscle_groups was trained too recently (not enough recovery days).
        """
        for muscle in muscle_groups:
            last_date = self.last_trained.get(muscle)
            if last_date is not None:
                min_days = self.MIN_RECOVERY_DAYS.get(muscle, 2)
                if (on_date - last_date).days < min_days:
                    return False
        return True

    def record_training(self, muscle_group: str, date: datetime.date):
        """
        Record that muscle_group was trained on the given date.
        """
        self.last_trained[muscle_group] = date

class WorkoutGenerator:
    def __init__(self, user_profile: UserProfile, training_settings: TrainingSettings):
        self.user = user_profile
        self.settings = training_settings
        self.exercise_selector = ExerciseSelector(user_profile, training_settings)
        self.volume_manager = WorkoutVolumeManager(user_profile, training_settings)
        self.recovery_manager = RecoveryManager()
        self.weekly_muscle_volume = defaultdict(int)
        self.target_weekly_volume = {}
        self.split_strategies = {
            'upper_lower': UpperLowerSplitStrategy,
            'push_pull_legs': PushPullLegsSplitStrategy,
            'full_body': FullBodySplitStrategy,
            'bro_split': BroSplitStrategy,
        }

    def generate_program(self, week: int, start_date=None) -> Dict:
        # Step 1: Get real dates for selected training days
        selected_days = list(self.settings.training_days.keys())
        dates = get_next_weekday_dates(selected_days, weeks_ahead=1, start_date=start_date)
        
        all_target_muscles = [
            'chest', 'back', 'shoulders', 'biceps', 'triceps',
            'quadriceps', 'hamstrings', 'glutes', 'calves'
        ]
        goal = self.user.goal
        level = self.settings.experience_level
        body_type = self.user.body_type
        week_is_deload = (week % 4 == 0)
        volume_range = self.volume_manager.VOLUME_TARGETS[goal][level]
        base_volume = (volume_range[0] + volume_range[1]) / 2

        # Adjust for body type and deload
        if body_type == 'mesomorph':
            base_volume *= 1.2 if not week_is_deload else 0.6
        elif body_type == 'ectomorph':
            base_volume *= 0.8 if not week_is_deload else 0.5

        # 2. Distribute sets across muscles using muscle priority
        print(f"[VOLUME DEBUG] Using adjust_volume for each muscle")
        for muscle in all_target_muscles:
            sets = self.volume_manager.adjust_volume(muscle, week)['sets']
            print(f"[VOLUME DEBUG] muscle={muscle}, sets={sets}")
            self.target_weekly_volume[muscle] = sets
        # Step 2: Pass dates to strategy
        strategy = self.split_strategies[self.settings.split_type](
            self.user, 
            self.settings,
            self.exercise_selector,
            self.volume_manager,
            self.recovery_manager,
            self.target_weekly_volume,
            self.weekly_muscle_volume
        )
        return strategy.generate(week, dates)

class SplitStrategy:
    def __init__(self, user, settings, exercise_selector, volume_manager, recovery_manager, target_weekly_volume, weekly_muscle_volume):
        self.user = user
        self.settings = settings
        self.exercise_selector = exercise_selector
        self.volume_manager = volume_manager
        self.recovery_manager = recovery_manager
        self.split_map = {}
        self.target_weekly_volume = target_weekly_volume
        self.weekly_muscle_volume = weekly_muscle_volume

    def generate(self, week: int) -> Dict:
        # متد اصلی برای تولید برنامه
        pass

    def _add_warmup_cooldown(self, program: Dict):
        # Optional: Add warmup/cooldown to each day if desired
        # For now, do nothing (no-op)
        pass
    
    def _validate_volume(self, program: Dict):
        # Optional: Validate or adjust volume if needed
        # For now, do nothing (no-op)
        pass

class BroSplitStrategy(SplitStrategy):
    """
    استراتژی Bro Split (تمرین هر گروه عضلانی در یک روز جداگانه)
    ساختار پیش‌فرض:
    - روز 1: سینه
    - روز 2: پشت
    - روز 3: پاها
    - روز 4: سرشانه
    - روز 5: بازوها (جلو/پشت بازو)
    - روز 6: تکمیلی (اختیاری)
    """
    MUSCLE_DAY_MAPPING = {
        'chest': ['chest', 'triceps'],  # سینه + تکمیلی جلو بازو
        'back': ['back', 'biceps'],      # پشت + تکمیلی جلو بازو
        'legs': ['quadriceps', 'hamstrings', 'glutes', 'calves'],
        'shoulders': ['shoulders', 'traps', 'rear_delts'],
        'arms': ['biceps', 'triceps', 'forearms'],
        'core': ['abs', 'obliques', 'lower_back']  # اختیاری
    }
    
    DAY_PRIORITY = ['chest', 'back', 'legs', 'shoulders', 'arms','core']
    
    def generate(self, week: int, dates: list) -> Dict:
        program = {'weekly_plan': {}}
        for i, muscle_day in enumerate(self.DAY_PRIORITY):
            if i >= len(dates):
                break
            day_date = dates[i]
            # Only build if main muscle(s) are recovered
            primary_muscles = self.MUSCLE_DAY_MAPPING[muscle_day]
            if self.recovery_manager.can_train(primary_muscles, day_date):
                program['weekly_plan'][day_date] = self._build_muscle_day(muscle_day, week)
                # Record all trained muscles for this day
                for muscle in primary_muscles:
                    self.recovery_manager.record_training(muscle, day_date)
            else:
                program['weekly_plan'][day_date] = []  # Or skip/empty if not recovered
        if len(dates) > len(self.DAY_PRIORITY):
            extra_days = dates[len(self.DAY_PRIORITY):]
            for day_date in extra_days:
                program['weekly_plan'][day_date] = self._build_hybrid_day(week)
        self._add_warmup_cooldown(program)
        return program
    
    def _build_muscle_day(self, muscle_day: str, week: int) -> List[Dict]:
        exercises = []
        primary_muscles = self.MUSCLE_DAY_MAPPING[muscle_day]
        main_muscle = primary_muscles[0]
        primary_count = {
            'beginner': 3,
            'intermediate': 4,
            'expert': 5
        }.get(self.settings.experience_level, 4)
        print(f"\n🗓️ Building plan for {muscle_day} (muscles: {primary_muscles})")

        # --- Main muscle loop with weekly volume enforcement ---
        for muscle in primary_muscles:
            # ✅ Check how many sets are still needed for this muscle this week
            remaining_sets = self.target_weekly_volume.get(muscle, 0) - self.weekly_muscle_volume.get(muscle, 0)
            if remaining_sets <= 0:
                continue

            # 1. Compound, strength, force-matched for main muscle
            compound_exs = [ex for ex in self.exercise_selector.get_exercises([muscle], week)
                            if ex.mechanic == 'compound' and ex.category == 'strength']
            for ex in compound_exs[:min(2, len(compound_exs))]:
                sets_this_session = min(3, remaining_sets)
                if sets_this_session < 1:
                    continue
                volume = {
                    'sets': sets_this_session,
                    'reps': (8, 12)
                }
                print(f"   - {muscle}: target sets={volume['sets']}, reps={volume['reps']}")
                exercises.append(self._create_exercise_entry(ex, volume, True))
                self.weekly_muscle_volume[muscle] += sets_this_session
                remaining_sets -= sets_this_session
                if remaining_sets <= 0:
                    break

            # 2. Isolation, strength for main muscle
            if remaining_sets > 0:
                isolation_exs = [ex for ex in self.exercise_selector.get_exercises([muscle], week)
                                if ex.mechanic == 'isolation' and ex.category == 'strength']
                for ex in isolation_exs[:primary_count - 2]:
                    sets_this_session = min(3, remaining_sets)
                    if sets_this_session < 1:
                        continue
                    volume = {
                        'sets': sets_this_session,
                        'reps': (8, 12)
                    }
                    print(f"   - {muscle}: target sets={volume['sets']}, reps={volume['reps']}")
                    exercises.append(self._create_exercise_entry(ex, volume, False))
                    self.weekly_muscle_volume[muscle] += sets_this_session
                    remaining_sets -= sets_this_session
                    if remaining_sets <= 0:
                        break

        # 3. Secondary muscles: force-matched, compound or isolation
        if len(primary_muscles) > 1:
            secondary_muscles = primary_muscles[1:]
            for muscle in secondary_muscles:
                remaining_sets = self.target_weekly_volume.get(muscle, 0) - self.weekly_muscle_volume.get(muscle, 0)
                if remaining_sets <= 0:
                    continue
                if random.random() < 0.7:
                    sec_exs = [ex for ex in self.exercise_selector.get_exercises([muscle], week)
                            if ex.category == 'strength']
                    if sec_exs:
                        ex = random.choice(sec_exs)
                        is_compound = ex.mechanic == 'compound'
                        sets_this_session = min(3, remaining_sets)
                        if sets_this_session < 1:
                            continue
                        volume = {
                            'sets': sets_this_session,
                            'reps': (8, 12)
                        }
                        exercises.append(self._create_exercise_entry(ex, volume, is_compound))
                        self.weekly_muscle_volume[muscle] += sets_this_session

        # 4. Optionally add cardio for weight_loss
        if self.user.goal == 'weight_loss' and main_muscle == 'legs':
            cardio_exs = [ex for ex in self.exercise_selector.get_exercises(['conditioning'], week)
                        if ex.category == 'cardio']
            if cardio_exs:
                selected = random.choice(cardio_exs)
                exercises.append({
                    'exercise_id': selected.id,
                    'exercise_name': selected.name,
                    'type': 'cardio',
                    'sets': 1,
                    'reps': '20-30 min',
                    'rest_seconds': 0,
                    'notes': 'Steady or interval as tolerated'
                })
        return exercises
    def _get_volume_for_muscle(self, muscle: str, week: int, is_compound: bool) -> Dict:
        """محاسبه حجم تمرین بر اساس عضله و نوع حرکت"""
        base_volume = self.volume_manager.adjust_volume(muscle, week)
        
        # تنظیم حجم برای Bro Split (حجم بیشتر در هر جلسه)
        adjusted_sets = base_volume['sets'] * {
            'compound': 1.2,
            'isolation': 1.0
        }.get('compound' if is_compound else 'isolation', 1.0)
        
        return {
            'sets': math.ceil(adjusted_sets),
            'reps': base_volume['reps']
        }
    
    def _select_secondary_exercise(self, muscle: str, week: int) -> Optional[Dict]:
        """انتخاب تمرین برای عضلات ثانویه"""
        available = self.exercise_selector.get_exercises([muscle], week)
        if available:
            volume = self._get_volume_for_muscle(muscle, week, is_compound=False)
            ex = random.choice(available)
            return self._create_exercise_entry(ex, volume, False)
        return None
    
    def _build_hybrid_day(self, week: int) -> List[Dict]:
        """ساخت روزهای ترکیبی (برای روزهای اضافی)"""
        options = [
            ('core', ['abs', 'obliques']),
            ('weak_points', self._get_user_weak_points()),
            ('cardio', ['conditioning'])
        ]
        
        selected_focus = random.choice(options)
        exercises = []
        
        if selected_focus[0] == 'core':
            for muscle in selected_focus[1]:
                ex = self._select_secondary_exercise(muscle, week)
                if ex:
                    exercises.append(ex)
        
        elif selected_focus[0] == 'weak_points':
            for muscle in selected_focus[1]:
                ex = self._select_secondary_exercise(muscle, week)
                if ex:
                    exercises.append({
                        **ex,
                        'tags': ['weak_point_focus'],
                        'intensity_notes': 'Higher volume'
                    })
        
        else:  # cardio/conditioning
            exercises.append({
                'type': 'conditioning',
                'content': self._select_cardio_protocol()
            })
        
        return exercises
    
    def _get_user_weak_points(self) -> List[str]:
        """تعیین نقاط ضعف کاربر بر اساس تیپ بدنی و هدف"""
        weak_points = {
            'mesomorph': ['calves', 'rear_delts'],
            'ectomorph': ['legs', 'back'],
            'endomorph': ['shoulders', 'arms']
        }.get(self.user.body_type, [])
        
        if self.user.goal == 'muscle_gain':
            weak_points.extend(['traps', 'upper_chest'])
        return list(set(weak_points))
    
    def _select_cardio_protocol(self) -> List[str]:
        """انتخاب پروتکل کاردیو بر اساس هدف کاربر"""
        if self.user.goal == 'weight_loss':
            return ['HIIT (30s sprint, 60s walk) x 8 rounds']
        return ['Moderate pace (30-45 mins)']
    
    def _create_exercise_entry(self, exercise: Exercise, volume: Dict, is_compound: bool) -> Dict:
        """ساخت وروردی استاندارد برای تمرین"""
        return {
            'exercise_id': exercise.id,
            'exercise_name': exercise.name,
            'type': 'compound' if is_compound else 'isolation',
            'muscle_group': exercise.primary_muscles[0],
            'sets': volume['sets'],
            'reps': volume['reps'],
            'rest_seconds': self._calculate_rest_time(exercise, is_compound),
            'notes': self._generate_exercise_notes(exercise, is_compound)
        }
    
    def _calculate_rest_time(self, exercise: Exercise, is_compound: bool) -> int:
        """محاسبه زمان استراحت برای Bro Split"""
        if is_compound:
            return 90 if self.user.goal == 'muscle_gain' else 120
        return 60 if 'arms' in exercise.primary_muscles else 75
    
    def _generate_exercise_notes(self, exercise: Exercise, is_compound: bool) -> str:
        """تولید نکات تمرینی"""
        notes = []
        if is_compound:
            notes.append('Focus on form and controlled tempo')
        
        if self.user.body_type == 'mesomorph':
            notes.append('Push to failure on last set')
        elif self.user.body_type == 'endomorph':
            notes.append('Moderate intensity, focus on mind-muscle connection')
        
        return '. '.join(notes)

class PushPullLegsSplitStrategy(SplitStrategy):
    MUSCLE_GROUPS = {
        'push': ['chest', 'triceps', 'shoulders'],
        'pull': ['back', 'biceps', 'rear_delts'],
        'legs': ['quadriceps', 'hamstrings', 'glutes', 'calves']
    }
    
    DAY_SEQUENCE = ['push', 'pull', 'legs', 'push', 'pull', 'legs']
    
    def generate(self, week: int, dates: list) -> Dict:
        program = {'weekly_plan': {}}
        sequence_idx = 0
        for i, day_date in enumerate(dates):
            if sequence_idx >= len(self.DAY_SEQUENCE):
                sequence_idx = 0
            split_type = self.DAY_SEQUENCE[sequence_idx]
            # Only build if all priority muscles are recovered
            priority_muscles = {
                'push': ['chest', 'shoulders', 'triceps'],
                'pull': ['back', 'biceps'],
                'legs': ['quadriceps', 'hamstrings', 'glutes']
            }[split_type]
            if self.recovery_manager.can_train(priority_muscles, day_date):
                program['weekly_plan'][day_date] = self._build_day_plan(split_type, week, day_date)
                for muscle in priority_muscles:
                    self.recovery_manager.record_training(muscle, day_date)
            else:
                program['weekly_plan'][day_date] = []
            sequence_idx += 1
        self._validate_split_schedule(program)
        self._add_warmup_cooldown(program)
        self._validate_volume(program)
        return program
    
    def _build_day_plan(self, split_type: str, week: int, day_date: datetime.date) -> List[Dict]:
        exercises = []
        target_muscles = self.MUSCLE_GROUPS[split_type]
        priority_muscles = {
            'push': ['chest', 'shoulders', 'triceps'],
            'pull': ['back', 'biceps'],
            'legs': ['quadriceps', 'hamstrings', 'glutes']
        }[split_type]
        print(f"\n🗓️ Building plan for {split_type} (muscles: {priority_muscles})")
        for muscle in priority_muscles:
            if not self.recovery_manager.can_train([muscle], day_date):
                continue
            # ✅ Check how many sets are still needed for this muscle this week
            remaining_sets = self.target_weekly_volume.get(muscle, 0) - self.weekly_muscle_volume.get(muscle, 0)
            if remaining_sets <= 0:
                continue
            sets_this_session = min(3, remaining_sets)
            if sets_this_session < 1:
                continue
            volume = {
                'sets': sets_this_session,
                'reps': (8, 12)
            }
            print(f"   - {muscle}: target sets={volume['sets']}, reps={volume['reps']}")
            compound_exs = [ex for ex in self.exercise_selector.get_exercises([muscle], week)
                            if ex.mechanic == 'compound' and ex.force == split_type and ex.category == 'strength']
            print(f"     Found {len(compound_exs)} compound_exs exercises after filtering.")
            if compound_exs:
                selected = random.choice(compound_exs)
                exercises.append(self._create_exercise_entry(selected, volume, is_compound=True))
                self.weekly_muscle_volume[muscle] += sets_this_session
                self.recovery_manager.record_training(muscle, day_date)
        # ...existing code for isolation_targets and cardio...

class FullBodySplitStrategy(SplitStrategy):
    MUSCLE_GROUPS = [
        'chest', 'back', 'quadriceps', 
        'hamstrings', 'shoulders', 'core'
    ]
    
    EXERCISE_PER_MUSCLE = {
        'beginner': 1,
        'intermediate': 2,
        'expert': 2
    }
    
    def generate(self, week: int, dates: list) -> Dict:
        program = {'weekly_plan': {}}
        for day_date in dates:
            exercises = self._build_fullbody_day(week, day_date)
            program['weekly_plan'][day_date] = exercises
            # Record all muscles trained that day
            for ex in exercises:
                if 'exercise_name' in ex and 'muscle_group' in ex:
                    self.recovery_manager.record_training(ex['muscle_group'], day_date)
        self._balance_volume_across_days(program)
        return program
    
    def _build_fullbody_day(self, week: int, day_date: datetime.date) -> List[Dict]:
        exercises = []
        target_count = self.EXERCISE_PER_MUSCLE[self.settings.experience_level]
        print(f"\n🗓️ Building plan for fullbody)")
        for muscle in self.MUSCLE_GROUPS:
            if len(exercises) >= 6:
                break
            if not self.recovery_manager.can_train([muscle], day_date):
                continue
            # ✅ Check how many sets are still needed for this muscle this week
            remaining_sets = self.target_weekly_volume.get(muscle, 0) - self.weekly_muscle_volume.get(muscle, 0)
            if remaining_sets <= 0:
                continue
            sets_this_session = min(3, remaining_sets)
            if sets_this_session < 1:
                continue
            compound_exs = [ex for ex in self.exercise_selector.get_exercises([muscle], week)
                            if ex.mechanic == 'compound' and ex.category == 'strength']
            print(f"     Found {len(compound_exs)} compound exercises after filtering for fullbody.")
            selected = random.sample(compound_exs, min(1, len(compound_exs)))
            for ex in selected:
                volume = {
                    'sets': sets_this_session,
                    'reps': (8, 12)
                }
                print(f"   - {muscle}: target sets={volume['sets']}, reps={volume['reps']}")
                exercises.append({
                    'exercise_id': ex.id,
                    'exercise_name': ex.name,
                    'muscle_group': muscle,
                    'sets': volume['sets'],
                    'reps': '10-15' if self.user.goal == 'endurance' else '6-12',
                    'rest_seconds': 75
                })
                self.weekly_muscle_volume[muscle] += sets_this_session
                self.recovery_manager.record_training(muscle, day_date)
            # ...existing code for isolation_exs if needed...

class UpperLowerSplitStrategy(SplitStrategy):
    MUSCLE_GROUPS = {
        'upper': ['chest', 'back', 'shoulders', 'biceps', 'triceps'],
        'lower': ['quadriceps', 'hamstrings', 'glutes', 'calves']
    }
    
    def generate(self, week: int, dates: list) -> Dict:
        program = {'weekly_plan': {}}
        day_counter = 0
        for i, day_date in enumerate(dates):
            split_type = 'upper' if day_counter % 2 == 0 else 'lower'
            exercises = self._build_day_plan(split_type, week, day_date)
            program['weekly_plan'][day_date] = exercises
            self.split_map[day_date] = split_type
            # Record all muscles trained that day
            for ex in exercises:
                if 'exercise_name' in ex and 'muscle_group' in ex:
                    self.recovery_manager.record_training(ex['muscle_group'], day_date)
            day_counter += 1
        self._add_warmup_cooldown(program)
        self._validate_volume(program)
        return program
    
    def _build_day_plan(self, split_type: str, week: int, day_date: datetime.date) -> List[Dict]:
        exercises = []
        target_muscles = self.MUSCLE_GROUPS[split_type]
        print(f"\n🗓️ Building plan for {split_type} (muscles: {target_muscles})")
        for muscle in target_muscles:
            if not self.recovery_manager.can_train([muscle], day_date):
                continue
            # Log the computed target sets for this muscle
            target_sets = self.target_weekly_volume.get(muscle, 0)
            assigned_sets = self.weekly_muscle_volume.get(muscle, 0)
            print(f"[VOLUME LOG] {muscle}: target_sets={target_sets}, assigned_so_far={assigned_sets}")
            remaining_sets = target_sets - assigned_sets
            print(f"[VOLUME LOG] {muscle}: remaining_sets={remaining_sets} for this week")
            if remaining_sets <= 0:
                print(f"[VOLUME LOG] {muscle}: target met, skipping")
                continue
            sets_this_session = min(3, remaining_sets)
            if sets_this_session < 1:
                print(f"[VOLUME LOG] {muscle}: less than 1 set needed, skipping")
                continue
            available_exercises = self.exercise_selector.get_exercises([muscle], week)
            print(f"[VOLUME LOG] {muscle}: {len(available_exercises)} exercises available")
            if available_exercises:
                selected_exercise = random.choice(available_exercises)
                print(f"[VOLUME LOG] {muscle}: assigning {sets_this_session} sets to {selected_exercise.name}")
                exercises.append({
                    'exercise_id': selected_exercise.id,
                    'exercise_name': selected_exercise.name,
                    'muscle_group': muscle,
                    'sets': sets_this_session,
                    'reps': f"8-12",
                    'rest_seconds': self._calculate_rest_time(selected_exercise)
                })
                self.weekly_muscle_volume[muscle] += sets_this_session
                self.recovery_manager.record_training(muscle, day_date)
        return exercises
    
    def _calculate_rest_time(self, exercise: Exercise) -> int:
        """Calculate rest time based on exercise type."""
        if exercise.mechanic == 'compound':
            return 90 if self.user.goal == 'muscle_gain' else 120
        return 60 if 'arms' in exercise.primary_muscles else 75

class WorkoutQualityEvaluator:
    @staticmethod
    def evaluate(program: Dict) -> float:
        # سیستم امتیازدهی به برنامه (0-100)
        score = 0
        
        # معیارهای ارزیابی
        criteria = {
            'muscle_coverage': 30,
            'volume_adequacy': 25,
            'exercise_variety': 20,
            'recovery_time': 15,
            'progressive_overload': 10
        }
        
        # محاسبه امتیاز برای هر معیار
        score += criteria['muscle_coverage'] * WorkoutQualityEvaluator._muscle_coverage_score(program)
        score += criteria['volume_adequacy'] * WorkoutQualityEvaluator._volume_score(program)
        # ... محاسبات دیگر معیارها
        
        return min(100, max(0, score))
    
    @staticmethod
    def _muscle_coverage_score(program: Dict) -> float:
        # محاسبه پوشش عضلانی
        trained_muscles = set()
        for day in program['weekly_plan'].values():
            for exercise in day:
                if isinstance(exercise, dict)  and 'primary_muscles' in exercise:
                    trained_muscles.update(exercise['primary_muscles'])
        return len(trained_muscles) / 15  # فرض 15 گروه عضلانی اصلی
    
    @staticmethod
    def _volume_score(program: Dict) -> float:
        # مقایسه حجم با اهداف استاندارد
        # ... منطق محاسباتی
        return 0.8  # مقدار نمونه