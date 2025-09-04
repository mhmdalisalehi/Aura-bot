import os
import logging
from django.db import models
from typing import Dict, List, Optional
from collections import defaultdict
import random
import math
from exercises.models import Exercise
from accounts.models import UserProfile, TrainingSettings, InjuryExerciseClassification
from django.db.models import Q
from datetime import datetime
import calendar
import datetime

# --- Logging Setup ---
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

def get_logger(class_name: str):
    logger = logging.getLogger(class_name)
    if not logger.handlers:
        handler = logging.FileHandler(os.path.join(LOGS_DIR, f"{class_name}.log"), encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

current_date = datetime.datetime.now()

def format_workout_plan_for_telegram(program: Dict) -> str:
    logger = get_logger("format_workout_plan_for_telegram")
    logger.info("Formatting workout plan for Telegram.")
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
        if isinstance(date, str):
            try:
                date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            except Exception:
                date_obj = date
        else:
            date_obj = date
        day_str = f"📅 {calendar.day_name[date_obj.weekday()]}, {date_obj.strftime('%B')} {date_obj.day}"
        lines = [day_str]
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
            if ex_type in ['cardio', 'conditioning']:
                line = f"{emoji} Cardio: {name} — {reps if reps else ''}"
            else:
                sets_reps = f"{sets} sets × {reps} reps" if sets and reps else ''
                line = f"{idx}️⃣ {name} — {sets_reps}"
            notes = ex.get('notes') or ex.get('intensity_notes')
            if notes:
                line += f"\n   Notes: {notes}"
            if ex_type not in ['cardio', 'conditioning']:
                line += f"\n   Type: {ex_type.capitalize()}"
            lines.append(line)
        day_lines.append('\n'.join(lines))
    logger.info("Workout plan formatted successfully.")
    return '\n\n'.join(day_lines)

def get_next_weekday_dates(selected_days, weeks_ahead=1, start_date=None):
    logger = get_logger("get_next_weekday_dates")
    logger.info(f"Mapping user-selected weekdays: {selected_days}")
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
        start_date = datetime.datetime.today().date()
    weekday_map = {day: i for i, day in enumerate(
        ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    )}
    result = []
    for week in range(weeks_ahead):
        for day in selected_days:
            day_en = fa_to_en.get(day, day).lower()
            target = weekday_map[day_en]
            days_ahead = (target - start_date.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            date = start_date + datetime.timedelta(days=days_ahead + 7 * week)
            result.append(date)
    logger.info(f"Mapped dates: {result}")
    return result

class ExerciseSelector:
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
    }

    def __init__(self, user_profile, training_settings):
        self.logger = get_logger(self.__class__.__name__)
        self.user_profile = user_profile
        self.training_settings = training_settings
        self.exercise_history = defaultdict(list)
        self.logger.info("Initialized ExerciseSelector.")

    def _expand_muscle_groups(self, muscle_groups: List[str]) -> List[str]:
        expanded = []
        for mg in muscle_groups:
            expanded += self.MUSCLE_GROUP_MAP.get(mg, [mg])
        expanded = list(set(expanded))
        self.logger.info(f"Expanded muscle groups {muscle_groups} to {expanded}")
        return expanded

    def get_exercises(self, muscle_groups: List[str], week: int) -> List[Exercise]:
        db_muscles = self._expand_muscle_groups(muscle_groups)
        self.logger.info(f"Selecting exercises for muscles: {db_muscles}")
        muscle_q = Q()
        for muscle in db_muscles:
            muscle_q |= Q(primary_muscles__contains=[muscle])
        user_level = self.training_settings.experience_level
        level_order = ['beginner', 'intermediate', 'expert']
        allowed_levels = level_order[:level_order.index(user_level)+1]
        base_query = Exercise.objects.filter(
            muscle_q,
            Q(equipment__in=self.training_settings.available_equipment),
            Q(level__in=allowed_levels)
        )
        self.logger.info(f"Base query count: {base_query.count()}")
        user_injuries = self.user_profile.physical_limitations or []
        safe_ex_ids = set()
        if user_injuries:
            avoid_ex_ids = InjuryExerciseClassification.objects.filter(
                injury__in=user_injuries,
                classification='avoid'
            ).values_list('exercise_id', flat=True)
            base_query = base_query.exclude(id__in=avoid_ex_ids)
            self.logger.info(f"After injury exclusion: {base_query.count()}")
            safe_ex_ids = set(InjuryExerciseClassification.objects.filter(
                injury__in=user_injuries,
                classification='safe'
            ).values_list('exercise_id', flat=True))
        exercises = list(base_query)
        for ex in exercises:
            ex.is_safe = ex.id in safe_ex_ids
        self.logger.info(f"Final exercises after all filtering: {len(exercises)}")
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
    # Recommended weekly set range per muscle (science-based, e.g. 10-20 sets/week)
    WEEKLY_SETS_RANGE = {
        'chest': (10, 20), 'back': (12, 22), 'shoulders': (8, 16), 'biceps': (6, 14),
        'triceps': (6, 14), 'quadriceps': (10, 20), 'hamstrings': (8, 16),
        'glutes': (8, 16), 'calves': (8, 16), 'core': (8, 16), 'forearms': (4, 10), 'neck': (2, 6)
    }
    # Max sets per session per muscle (to avoid junk volume)
    MAX_SETS_PER_SESSION = 10

    def __init__(self, user_profile, training_settings):
        self.logger = get_logger(self.__class__.__name__)
        self.user_profile = user_profile
        self.training_settings = training_settings
        self.muscle_volume = defaultdict(float)
        self.logger.info("Initialized WorkoutVolumeManager.")

    def calculate_volume(self, exercise: Exercise, sets: int, reps: int) -> float:
        intensity = self._estimate_intensity(exercise, reps)
        volume = sets * reps * intensity
        self.logger.info(f"Calculated volume: {volume} for {exercise.name} ({sets}x{reps})")
        return volume

    def _estimate_intensity(self, exercise: Exercise, reps: int) -> float:
        rm_table = {
            3: 0.93, 5: 0.87, 8: 0.80, 
            10: 0.75, 12: 0.70, 15: 0.65
        }
        closest_rep = min(rm_table.keys(), key=lambda x: abs(x - reps))
        intensity = rm_table[closest_rep]
        self.logger.info(f"Estimated intensity for {reps} reps: {intensity}")
        return intensity

    def weekly_sets_target(self, muscle_group: str, week: int) -> int:
        """Calculate science-based weekly sets for a muscle group."""
        min_sets, max_sets = self.WEEKLY_SETS_RANGE.get(muscle_group, (8, 16))
        # Adjust for user goal and experience
        goal_factor = {
            'muscle_gain': 1.0, 'strength': 0.85, 'endurance': 0.7, 'weight_loss': 0.8
        }[self.user_profile.goal]
        exp_factor = {
            'beginner': 0.7, 'intermediate': 1.0, 'expert': 1.2
        }[self.training_settings.experience_level]
        body_type_factor = 1.0
        if self.user_profile.body_type == 'mesomorph':
            body_type_factor = 1.1
        elif self.user_profile.body_type == 'ectomorph':
            body_type_factor = 0.9
        elif self.user_profile.body_type == 'endomorph':
            body_type_factor = 1.0
        # Deload every 4th week
        deload_factor = 0.6 if week % 4 == 0 else 1.0
        sets = int(min_sets * goal_factor * exp_factor * body_type_factor * deload_factor)
        sets = max(min(sets, max_sets), min_sets)
        self.logger.info(f"Weekly sets for {muscle_group}: {sets}")
        return sets

    def per_session_sets(self, muscle_group: str, week: int, num_sessions: int) -> int:
        """Distribute weekly sets across sessions, capped per session."""
        weekly_sets = self.weekly_sets_target(muscle_group, week)
        per_session = int(round(weekly_sets / max(num_sessions, 1)))
        per_session = min(per_session, self.MAX_SETS_PER_SESSION)
        self.logger.info(f"Per-session sets for {muscle_group}: {per_session}")
        return per_session

    def recommend_sets_reps(self, muscle_group: str, is_compound: bool) -> dict:
        """
        Recommend sets and reps for compound/isolation exercises,
        adapting to user experience and muscle group.
        """
        # Example: adjust sets by experience level
        level = self.training_settings.experience_level
        goal = self.user_profile.goal

        # Base sets
        if is_compound:
            sets = {'beginner': 3, 'intermediate': 4, 'expert': 5}[level]
            reps = {
                'muscle_gain': '6-10',
                'strength': '4-8',
                'endurance': '10-15',
                'weight_loss': '8-12'
            }[goal]
        else:
            sets = {'beginner': 2, 'intermediate': 3, 'expert': 3}[level]
            reps = {
                'muscle_gain': '10-15',
                'strength': '8-12',
                'endurance': '15-20',
                'weight_loss': '12-15'
            }[goal]

        # Optionally, tweak for specific muscle groups (e.g., calves, forearms, core)
        if muscle_group in ['calves', 'forearms', 'core', 'neck']:
            reps = '15-20'

        return {'sets': sets, 'reps': reps}

    def is_overtrained(self, muscle_group: str, assigned_sets: int, week: int) -> bool:
        """Check if muscle is overtrained this week."""
        max_sets = self.WEEKLY_SETS_RANGE.get(muscle_group, (8, 16))[1]
        return assigned_sets > max_sets

    def is_undertrained(self, muscle_group: str, assigned_sets: int, week: int) -> bool:
        """Check if muscle is undertrained this week."""
        min_sets = self.WEEKLY_SETS_RANGE.get(muscle_group, (8, 16))[0]
        return assigned_sets < min_sets

    def recommend_num_exercises(self, muscle_group: str, week: int, num_sessions: int) -> int:
        """Recommend number of exercises per muscle per session."""
        # Usually 1-2 per muscle per session is enough
        weekly_sets = self.weekly_sets_target(muscle_group, week)
        per_session_sets = self.per_session_sets(muscle_group, week, num_sessions)
        if per_session_sets >= 6:
            return 2
        return 1

    def adjust_volume(self, muscle_group: str, week: int) -> Dict[str, int]:
        volume_range = self.VOLUME_TARGETS[self.user_profile.goal][self.training_settings.experience_level]
        base_volume = (volume_range[0] + volume_range[1]) / 2
        if self.user_profile.body_type == 'mesomorph':
            base_volume *= 1.2 if week % 4 != 0 else 0.6
        elif self.user_profile.body_type == 'ectomorph':
            base_volume *= 0.8 if week % 4 != 0 else 0.5
        allocated_volume = base_volume * self._muscle_priority(muscle_group)
        sets = math.ceil(allocated_volume / 2)
        reps = (8, 12) if self.user_profile.goal == 'muscle_gain' else (4, 6)
        self.logger.info(f"Adjusted volume for {muscle_group}: sets={sets}, reps={reps}")
        return {'sets': sets, 'reps': reps}

    def _muscle_priority(self, muscle_group: str) -> float:
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
        priority = priorities[self.user_profile.goal].get(muscle_group, 0.1)
        self.logger.info(f"Muscle priority for {muscle_group}: {priority}")
        return priority

class RecoveryManager:
    MIN_RECOVERY_DAYS = {
        'chest': 2, 'back': 2, 'quadriceps': 3,
        'hamstrings': 2, 'shoulders': 2, 'biceps': 2,
        'triceps': 2, 'calves': 1, 'core': 1
    }
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.last_trained = {}
        self.logger.info("Initialized RecoveryManager.")

    def can_train(self, muscle_groups: List[str], on_date: datetime.date) -> bool:
        for muscle in muscle_groups:
            last_date = self.last_trained.get(muscle)
            if last_date is not None:
                min_days = self.MIN_RECOVERY_DAYS.get(muscle, 2)
                days_diff = (on_date - last_date).days
                if days_diff < 0:
                    self.logger.warning(f"last_trained date {last_date} for {muscle} is in the future compared to {on_date}. Allowing training.")
                    continue  # Allow training if last_date is in the future
                if days_diff < min_days:
                    self.logger.info(f"Cannot train {muscle} on {on_date}: last trained {last_date} ({days_diff} days ago, need {min_days})")
                    return False
        self.logger.info(f"Can train {muscle_groups} on {on_date}")
        return True

    def record_training(self, muscle_group: str, date: datetime.date):
        self.last_trained[muscle_group] = date
        self.logger.info(f"Recorded training for {muscle_group} on {date}")

class WorkoutGenerator:
    def __init__(self, user_profile: UserProfile, training_settings: TrainingSettings):
        self.logger = get_logger(self.__class__.__name__)
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
        self.logger.info("Initialized WorkoutGenerator.")

    def generate_program(self, week: int, start_date=None) -> Dict:
        self.logger.info(f"Generating program for week {week}, start_date={start_date}")
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
        if body_type == 'mesomorph':
            base_volume *= 1.2 if not week_is_deload else 0.6
        elif body_type == 'ectomorph':
            base_volume *= 0.8 if not week_is_deload else 0.5
        self.logger.info(f"Base volume after adjustment: {base_volume}")
        for muscle in all_target_muscles:
            sets = self.volume_manager.adjust_volume(muscle, week)['sets']
            self.logger.info(f"Target sets for {muscle}: {sets}")
            self.target_weekly_volume[muscle] = sets
        strategy = self.split_strategies[self.settings.split_type](
            self.user, 
            self.settings,
            self.exercise_selector,
            self.volume_manager,
            self.recovery_manager,
            self.target_weekly_volume,
            self.weekly_muscle_volume
        )
        program = strategy.generate(week, dates)
        self.logger.info("Program generated successfully.")
        
        self.logger.info("=== Weekly sets per muscle ===")
        for muscle, sets in self.weekly_muscle_volume.items():
            self.logger.info(f"{muscle}: {sets} sets")
                
        return program

class SplitStrategy:
    def __init__(self, user, settings, exercise_selector, volume_manager, recovery_manager, target_weekly_volume, weekly_muscle_volume):
        self.logger = get_logger(self.__class__.__name__)
        self.user = user
        self.settings = settings
        self.exercise_selector = exercise_selector
        self.volume_manager = volume_manager
        self.recovery_manager = recovery_manager
        self.split_map = {}
        self.target_weekly_volume = target_weekly_volume
        self.weekly_muscle_volume = weekly_muscle_volume
        self.logger.info("Initialized SplitStrategy.")

    def generate(self, week: int) -> Dict:
        self.logger.warning("Base SplitStrategy.generate called. Should be overridden.")
        pass

    def _add_warmup_cooldown(self, program: Dict):
        self.logger.info("Adding warmup/cooldown (noop).")
        pass
    
    def _validate_volume(self, program: Dict):
        self.logger.info("Validating volume (noop).")
        pass

class BroSplitStrategy(SplitStrategy):
    MUSCLE_DAY_MAPPING = {
        'chest': ['chest', 'triceps'],
        'back': ['back', 'biceps'],
        'legs': ['quadriceps', 'hamstrings', 'glutes', 'calves'],
        'shoulders': ['shoulders', 'traps', 'rear_delts'],
        'arms': ['biceps', 'triceps', 'forearms'],
        'core': ['abs', 'obliques', 'lower_back']
    }
    DAY_PRIORITY = ['chest', 'back', 'legs', 'shoulders', 'arms','core']
    def generate(self, week: int, dates: list) -> Dict:
        self.logger.info(f"Generating BroSplit for week {week} and dates {dates}")
        program = {'weekly_plan': {}}
        for i, muscle_day in enumerate(self.DAY_PRIORITY):
            if i >= len(dates):
                break
            day_date = dates[i]
            primary_muscles = self.MUSCLE_DAY_MAPPING[muscle_day]
            if self.recovery_manager.can_train(primary_muscles, day_date):
                program['weekly_plan'][day_date] = self._build_muscle_day(muscle_day, week)
                for muscle in primary_muscles:
                    self.recovery_manager.record_training(muscle, day_date)
            else:
                self.logger.info(f"Skipping {muscle_day} on {day_date} due to recovery.")
                program['weekly_plan'][day_date] = []
        if len(dates) > len(self.DAY_PRIORITY):
            extra_days = dates[len(self.DAY_PRIORITY):]
            for day_date in extra_days:
                program['weekly_plan'][day_date] = self._build_hybrid_day(week)
        self._add_warmup_cooldown(program)
        self.logger.info("BroSplit program generated.")
        return program
    
    def _build_muscle_day(self, muscle_day: str, week: int) -> List[Dict]:
        self.logger.info(f"Building muscle day for {muscle_day}, week {week}")
        exercises = []
        primary_muscles = self.MUSCLE_DAY_MAPPING[muscle_day]
        main_muscle = primary_muscles[0]
        primary_count = {
            'beginner': 3,
            'intermediate': 4,
            'expert': 5
        }.get(self.settings.experience_level, 4)
        for muscle in primary_muscles:
            remaining_sets = self.target_weekly_volume.get(muscle, 0) - self.weekly_muscle_volume.get(muscle, 0)
            if remaining_sets <= 0:
                continue
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
                exercises.append(self._create_exercise_entry(ex, volume, True))
                self.weekly_muscle_volume[muscle] += sets_this_session
                remaining_sets -= sets_this_session
                if remaining_sets <= 0:
                    break
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
                    exercises.append(self._create_exercise_entry(ex, volume, False))
                    self.weekly_muscle_volume[muscle] += sets_this_session
                    remaining_sets -= sets_this_session
                    if remaining_sets <= 0:
                        break
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
        self.logger.info(f"Built muscle day for {muscle_day}: {len(exercises)} exercises.")
        return exercises

    def _get_volume_for_muscle(self, muscle: str, week: int, is_compound: bool) -> Dict:
        base_volume = self.volume_manager.adjust_volume(muscle, week)
        adjusted_sets = base_volume['sets'] * {
            'compound': 1.2,
            'isolation': 1.0
        }.get('compound' if is_compound else 'isolation', 1.0)
        return {
            'sets': math.ceil(adjusted_sets),
            'reps': base_volume['reps']
        }
    
    def _select_secondary_exercise(self, muscle: str, week: int) -> Optional[Dict]:
        available = self.exercise_selector.get_exercises([muscle], week)
        if available:
            volume = self._get_volume_for_muscle(muscle, week, is_compound=False)
            ex = random.choice(available)
            return self._create_exercise_entry(ex, volume, False)
        return None
    
    def _build_hybrid_day(self, week: int) -> List[Dict]:
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
        else:
            exercises.append({
                'type': 'conditioning',
                'content': self._select_cardio_protocol()
            })
        self.logger.info(f"Built hybrid day: {len(exercises)} exercises.")
        return exercises
    
    def _get_user_weak_points(self) -> List[str]:
        weak_points = {
            'mesomorph': ['calves', 'rear_delts'],
            'ectomorph': ['legs', 'back'],
            'endomorph': ['shoulders', 'arms']
        }.get(self.user.body_type, [])
        if self.user.goal == 'muscle_gain':
            weak_points.extend(['traps', 'upper_chest'])
        return list(set(weak_points))
    
    def _select_cardio_protocol(self) -> List[str]:
        if self.user.goal == 'weight_loss':
            return ['HIIT (30s sprint, 60s walk) x 8 rounds']
        return ['Moderate pace (30-45 mins)']
    
    def _create_exercise_entry(self, exercise: Exercise, volume: Dict, is_compound: bool) -> Dict:
        entry = {
            'exercise_id': exercise.id,
            'exercise_name': exercise.name,
            'type': 'compound' if is_compound else 'isolation',
            'muscle_group': exercise.primary_muscles[0],
            'sets': volume['sets'],
            'reps': volume['reps'],
            'rest_seconds': self._calculate_rest_time(exercise, is_compound),
            'notes': self._generate_exercise_notes(exercise, is_compound)
        }
        self.logger.info(f"Created exercise entry: {entry}")
        return entry
    
    def _calculate_rest_time(self, exercise: Exercise, is_compound: bool) -> int:
        if is_compound:
            return 90 if self.user.goal == 'muscle_gain' else 120
        return 60 if 'arms' in exercise.primary_muscles else 75
    
    def _generate_exercise_notes(self, exercise: Exercise, is_compound: bool) -> str:
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
        self.logger.info(f"Generating PushPullLegsSplit for week {week} and dates {dates}")
        program = {'weekly_plan': {}}
        sequence_idx = 0
        for i, day_date in enumerate(dates):
            if sequence_idx >= len(self.DAY_SEQUENCE):
                sequence_idx = 0
            split_type = self.DAY_SEQUENCE[sequence_idx]
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
                self.logger.info(f"Skipping {split_type} on {day_date} due to recovery.")
                program['weekly_plan'][day_date] = []
            sequence_idx += 1
        self._add_warmup_cooldown(program)
        self._validate_volume(program)
        self.logger.info("PushPullLegsSplit program generated.")
        return program
    
    def _build_day_plan(self, split_type: str, week: int, day_date: datetime.date) -> List[Dict]:
        self.logger.info(f"Building day plan for {split_type} on {day_date}")
        exercises = []
        target_muscles = self.MUSCLE_GROUPS[split_type]
        priority_muscles = {
            'push': ['chest', 'shoulders', 'triceps'],
            'pull': ['back', 'biceps'],
            'legs': ['quadriceps', 'hamstrings', 'glutes']
        }[split_type]
        for muscle in priority_muscles:
            if not self.recovery_manager.can_train([muscle], day_date):
                continue
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
            compound_exs = [ex for ex in self.exercise_selector.get_exercises([muscle], week)
                            if ex.mechanic == 'compound' and ex.category == 'strength']
            if compound_exs:
                selected = random.choice(compound_exs)
                exercises.append(self._create_exercise_entry(selected, volume, is_compound=True))
                self.weekly_muscle_volume[muscle] += sets_this_session
                self.recovery_manager.record_training(muscle, day_date)
        self.logger.info(f"Built day plan for {split_type}: {len(exercises)} exercises.")
        return exercises

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
        self.logger.info(f"Generating FullBodySplit for week {week} and dates {dates}")
        program = {'weekly_plan': {}}
        for day_date in dates:
            exercises = self._build_fullbody_day(week, day_date)
            program['weekly_plan'][day_date] = exercises
            for ex in exercises:
                if 'exercise_name' in ex and 'muscle_group' in ex:
                    self.recovery_manager.record_training(ex['muscle_group'], day_date)
        self._add_warmup_cooldown(program)
        self._validate_volume(program)
        self.logger.info("FullBodySplit program generated.")
        return program
    
    def _build_fullbody_day(self, week: int, day_date: datetime.date) -> List[Dict]:
        self.logger.info(f"Building fullbody day for {day_date}")
        exercises = []
        target_count = self.EXERCISE_PER_MUSCLE[self.settings.experience_level]
        for muscle in self.MUSCLE_GROUPS:
            if len(exercises) >= 6:
                break
            if not self.recovery_manager.can_train([muscle], day_date):
                continue
            remaining_sets = self.target_weekly_volume.get(muscle, 0) - self.weekly_muscle_volume.get(muscle, 0)
            if remaining_sets <= 0:
                continue
            sets_this_session = min(3, remaining_sets)
            if sets_this_session < 1:
                continue
            compound_exs = [ex for ex in self.exercise_selector.get_exercises([muscle], week)
                            if ex.mechanic == 'compound' and ex.category == 'strength']
            selected = random.sample(compound_exs, min(1, len(compound_exs)))
            for ex in selected:
                volume = {
                    'sets': sets_this_session,
                    'reps': (8, 12)
                }
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
        self.logger.info(f"Built fullbody day: {len(exercises)} exercises.")
        return exercises

class UpperLowerSplitStrategy(SplitStrategy):
    MUSCLE_GROUPS = {
        'upper': ['chest', 'back', 'shoulders', 'biceps', 'triceps'],
        'lower': ['quadriceps', 'hamstrings', 'glutes', 'calves']
    }

    def generate(self, week: int, dates: list) -> Dict:
        self.logger.info(f"Generating UpperLowerSplit for week {week} and dates {dates}")
        program = {'weekly_plan': {}}
        day_counter = 0
        num_sessions = len(dates) // 2  # Approximate upper/lower split sessions
        for i, day_date in enumerate(dates):
            split_type = 'upper' if day_counter % 2 == 0 else 'lower'
            exercises = self._build_day_plan(split_type, week, day_date, num_sessions)
            program['weekly_plan'][day_date] = exercises
            self.split_map[day_date] = split_type
            for ex in exercises:
                if 'exercise_name' in ex and 'muscle_group' in ex:
                    self.recovery_manager.record_training(ex['muscle_group'], day_date)
            day_counter += 1
        self._add_warmup_cooldown(program)
        self._validate_volume(program)
        # Over/under-training check (log only)
        for muscle in self.MUSCLE_GROUPS['upper'] + self.MUSCLE_GROUPS['lower']:
            sets = self.weekly_muscle_volume.get(muscle, 0)
            if self.volume_manager.is_overtrained(muscle, sets, week):
                self.logger.warning(f"{muscle} is overtrained: {sets} sets")
            if self.volume_manager.is_undertrained(muscle, sets, week):
                self.logger.warning(f"{muscle} is undertrained: {sets} sets")
        self.logger.info("UpperLowerSplit program generated.")
        return program

    def _build_day_plan(self, split_type: str, week: int, day_date: datetime.date, num_sessions: int) -> List[Dict]:
        self.logger.info(f"Building {split_type} day for {day_date}")
        exercises = []
        target_muscles = self.MUSCLE_GROUPS[split_type]
        for muscle in target_muscles:
            if not self.recovery_manager.can_train([muscle], day_date):
                continue
            weekly_target = self.volume_manager.weekly_sets_target(muscle, week)
            assigned_sets = self.weekly_muscle_volume.get(muscle, 0)
            remaining_sets = weekly_target - assigned_sets
            if remaining_sets <= 0:
                continue
            sets_this_session = min(
                self.volume_manager.per_session_sets(muscle, week, num_sessions),
                remaining_sets
            )
            if sets_this_session < 1:
                continue
            num_exs = self.volume_manager.recommend_num_exercises(muscle, week, num_sessions)
            # Compound exercises
            compound_exs = [ex for ex in self.exercise_selector.get_exercises([muscle], week)
                            if ex.mechanic == 'compound' and ex.category == 'strength']
            for ex in random.sample(compound_exs, min(1, len(compound_exs))):
                sr = self.volume_manager.recommend_sets_reps(muscle, is_compound=True)
                exercises.append({
                    'exercise_id': ex.id,
                    'exercise_name': ex.name,
                    'muscle_group': muscle,
                    'type': 'compound',
                    'sets': min(sr['sets'], sets_this_session),
                    'reps': sr['reps'],
                    'rest_seconds': self._calculate_rest_time(ex)
                })
                self.weekly_muscle_volume[muscle] += min(sr['sets'], sets_this_session)
                sets_this_session -= min(sr['sets'], sets_this_session)
                if sets_this_session <= 0:
                    break
            # Isolation exercises (if more sets remain)
            if sets_this_session > 0 and num_exs > 1:
                isolation_exs = [ex for ex in self.exercise_selector.get_exercises([muscle], week)
                                 if ex.mechanic == 'isolation' and ex.category == 'strength']
                for ex in random.sample(isolation_exs, min(num_exs - 1, len(isolation_exs))):
                    sr = self.volume_manager.recommend_sets_reps(muscle, is_compound=False)
                    exercises.append({
                        'exercise_id': ex.id,
                        'exercise_name': ex.name,
                        'muscle_group': muscle,
                        'type': 'isolation',
                        'sets': min(sr['sets'], sets_this_session),
                        'reps': sr['reps'],
                        'rest_seconds': 60
                    })
                    self.weekly_muscle_volume[muscle] += min(sr['sets'], sets_this_session)
                    sets_this_session -= min(sr['sets'], sets_this_session)
                    if sets_this_session <= 0:
                        break
        # Accessory/support exercise
        accessory_muscles = ['core', 'forearms'] if split_type == 'upper' else ['calves', 'neck']
        for acc in accessory_muscles:
            acc_exs = self.exercise_selector.get_exercises([acc], week)
            if acc_exs:
                acc_ex = random.choice(acc_exs)
                exercises.append({
                    'exercise_id': acc_ex.id,
                    'exercise_name': acc_ex.name,
                    'muscle_group': acc,
                    'type': 'accessory',
                    'sets': 2,
                    'reps': "15-20",
                    'rest_seconds': 45
                })
                break
        self.logger.info(f"Built {split_type} day: {len(exercises)} exercises.")
        return exercises

    def _calculate_rest_time(self, exercise: Exercise) -> int:
        if exercise.mechanic == 'compound':
            return 90 if self.user.goal == 'muscle_gain' else 120
        return 60 if 'arms' in exercise.primary_muscles else 75

class WorkoutQualityEvaluator:
    @staticmethod
    def evaluate(program: Dict) -> float:
        logger = get_logger("WorkoutQualityEvaluator")
        logger.info("Evaluating workout program quality.")
        score = 0
        criteria = {
            'muscle_coverage': 30,
            'volume_adequacy': 25,
            'exercise_variety': 20,
            'recovery_time': 15,
            'progressive_overload': 10
        }
        score += criteria['muscle_coverage'] * WorkoutQualityEvaluator._muscle_coverage_score(program)
        score += criteria['volume_adequacy'] * WorkoutQualityEvaluator._volume_score(program)
        logger.info(f"Program scored {score}/100.")
        return min(100, max(0, score))
    
    @staticmethod
    def _muscle_coverage_score(program: Dict) -> float:
        trained_muscles = set()
        for day in program['weekly_plan'].values():
            for exercise in day:
                if isinstance(exercise, dict)  and 'primary_muscles' in exercise:
                    trained_muscles.update(exercise['primary_muscles'])
        score = len(trained_muscles) / 15
        logger = get_logger("WorkoutQualityEvaluator")
        logger.info(f"Muscle coverage score: {score}")
        return score
    
    @staticmethod
    def _volume_score(program: Dict) -> float:
        logger = get_logger("WorkoutQualityEvaluator")
        logger.info("Volume score: 0.8 (sample)")
        return 0.8  # Sample value