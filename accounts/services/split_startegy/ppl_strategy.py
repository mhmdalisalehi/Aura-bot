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
from accounts.services.date_converter import convert_day_to_date
from accounts.services.workout_utils import get_progression_notes, get_exercise_notes, calculate_rest_time
from logger_util import get_logger

logger = get_logger('ppl_split', 'logs/ppl_split.log')
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
    
    DAY_SEQUENCE = ['push', 'pull', 'legs', 'push', 'pull', 'legs']
    
    ADVANCED_TECHNIQUES = {
        'beginner': ['drop_sets', 'rest_pause'],
        'intermediate': ['drop_sets', 'rest_pause', 'supersets', 'giant_sets'],
        'expert': ['drop_sets', 'rest_pause', 'supersets', 'giant_sets', 
                  'pyramids', 'negatives', 'forced_reps', 'cluster_sets']
    }
    
    WARMUP_MAP = {
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
    COOLDOWN_MAP = {
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

    def generate(self, week: int) -> Dict:
        logger.info(f"Generating PPL split program for week {week}")
        program = {'weekly_plan': {}}
        sequence_idx = 0
        for day in self.settings.training_days:
            if sequence_idx >= len(self.DAY_SEQUENCE):
                sequence_idx = 0
            split_type = self.DAY_SEQUENCE[sequence_idx]
            logger.debug(f"Building {split_type} day for {day}")
            program['weekly_plan'][day] = self._build_day_plan(split_type, week)
            sequence_idx += 1
        self._validate_split_schedule(program)
        self._add_warmup_cooldown(program, self.WARMUP_MAP, self.COOLDOWN_MAP, self.DAY_SEQUENCE)
        self._validate_volume(program)
        dated_program = {}
        base_date = datetime.now()
        for day, exercises in program['weekly_plan'].items():
            training_date = convert_day_to_date(day, base_date)
            dated_program[training_date.strftime('%Y-%m-%d')] = exercises
        logger.info("PPL split program generated successfully")
        return dated_program
    
    def _build_day_plan(self, split_type: str, week: int) -> List[Exercise]:
        logger.debug(f"Building day plan for {split_type}, week {week}")
        exercises = []
        muscle_config = self.MUSCLE_GROUPS[split_type]
        exercise_counts = self._get_exercise_counts(split_type)
        for muscle in muscle_config['primary']:
            exercises.extend(self._build_muscle_exercises(
                muscle, 
                exercise_counts['primary'],
                week,
                is_primary=True
            ))
        for muscle in muscle_config['secondary']:
            if random.random() < 0.8:
                exercises.extend(self._build_muscle_exercises(
                    muscle,
                    exercise_counts['secondary'],
                    week,
                    is_primary=False
                ))
        focus_exercises = self._build_focus_area_exercises(
            muscle_config['focus_areas'],
            week
        )
        exercises.extend(focus_exercises)
        exercises = self._apply_advanced_techniques(exercises, muscle_config['techniques'])
        exercises = self._adjust_exercise_volume(exercises, muscle_config['volume_multiplier'])
        logger.debug(f"Built {len(exercises)} exercises for {split_type} day")
        exercises = self._get_warmup(split_type) + exercises + self._get_cooldown(split_type)
        return exercises
    
    def _get_exercise_counts(self, split_type: str) -> Dict[str, int]:
        base_counts = {
            'beginner': {'primary': 3, 'secondary': 1},
            'intermediate': {'primary': 4, 'secondary': 2},
            'expert': {'primary': 5, 'secondary': 2}
        }.get(self.settings.experience_level, {'primary': 4, 'secondary': 2})
        if self.user.body_type == 'ectomorph':
            base_counts['primary'] = max(3, base_counts['primary'] - 1)
        elif self.user.body_type == 'mesomorph':
            base_counts['primary'] = min(6, base_counts['primary'] + 1)
        logger.debug(f"Exercise counts for {split_type}: {base_counts}")
        return base_counts
    
    def _build_muscle_exercises(self, muscle: str, count: int, week: int, is_primary: bool) -> List[Exercise]:
        available = self.exercise_selector.get_exercises(map_muscle_names([muscle]), week)['main']
        if is_primary:
            filtered = [ex for ex in available if ex.mechanic == 'compound']
        else:
            filtered = [ex for ex in available if ex.mechanic == 'isolation']
        logger.debug(f"Selected {len(filtered[:count])} exercises for muscle {muscle} (primary={is_primary})")
        return filtered[:count]
    
    def _build_focus_area_exercises(self, focus_areas: List[str], week: int) -> List[Exercise]:
        exercises = []
        for area in focus_areas:
            if random.random() < 0.6:
                available = self.exercise_selector.get_exercises(map_muscle_names([area]), week)['main']
                filtered = [ex for ex in available if ex.mechanic == 'isolation']
                if filtered:
                    exercises.extend(filtered[:1])
        logger.debug(f"Built {len(exercises)} focus area exercises")
        return exercises
    
    def _apply_advanced_techniques(self, exercises: List[Exercise], 
                                 available_techniques: List[str]) -> List[Exercise]:
        if not exercises:
            return exercises
        allowed_techniques = [
            tech for tech in available_techniques
            if tech in self.ADVANCED_TECHNIQUES.get(self.settings.experience_level, [])
        ]
        if not allowed_techniques:
            return exercises
        for i in range(len(exercises)):
            if random.random() < 0.3:
                technique = random.choice(allowed_techniques)
                exercises[i].technique = technique
                exercises[i].technique_notes = self._get_technique_notes(technique)
                logger.debug(f"Applied technique {technique} to exercise {getattr(exercises[i], 'name', '')}")
        return exercises
        
    def _get_technique_notes(self, technique: str) -> str:
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
        for exercise in exercises:
            muscle_group = (exercise.primary_muscles[0] if exercise.primary_muscles else
                            (exercise.secondary_muscles[0] if exercise.secondary_muscles else 'full_body'))
            base_volume = self.volume_manager.adjust_volume(
                muscle_group,
                self.current_week
            )
            adjusted_sets = math.ceil(base_volume['sets'] * multiplier)
            if self.user.body_type == 'ectomorph':
                adjusted_sets = max(3, adjusted_sets - 1)
            elif self.user.body_type == 'mesomorph':
                adjusted_sets = min(8, adjusted_sets + 1)
            logger.debug(f"Adjusted sets for {getattr(exercise, 'name', '')}: {getattr(exercise, 'sets', None)} -> {adjusted_sets}")
            exercise.sets = adjusted_sets
            exercise.reps = base_volume['reps']
            exercise.volume_multiplier = multiplier
        return exercises
        
    def _validate_split_schedule(self, program: Dict):
        trained_muscles = defaultdict(list)
        for day, exercises in program['weekly_plan'].items():
            training_date = convert_day_to_date(day, datetime.now())
            for ex in exercises:
                if hasattr(ex, 'primary_muscles') and ex.primary_muscles:
                    for muscle in ex.primary_muscles:
                        trained_muscles[muscle].append(training_date)
        for muscle, days in trained_muscles.items():
            min_recovery = RecoveryManager.BASE_RECOVERY_DAYS.get(muscle, 2)
            for i in range(1, len(days)):
                if (days[i] - days[i-1]).days < min_recovery:
                    logger.warning(f"Insufficient recovery for {muscle} between {days[i-1]} and {days[i]}")
                    self._adjust_exercise_scheduling(program, muscle)

    def _add_warmup_cooldown(self, program: Dict, warmup_map: Dict, cooldown_map: Dict, day_sequence: List[str]):
        for day, exercises in program['weekly_plan'].items():
            split_type = day_sequence[list(program['weekly_plan'].keys()).index(day) % len(day_sequence)]
            warmup = warmup_map.get(split_type, [])
            cooldown = cooldown_map.get(split_type, [])
            program['weekly_plan'][day] = warmup + exercises + cooldown

    def _validate_volume(self, program: Dict):
        total_volume = sum(self.volume_manager.muscle_volume.values())
        volume_range = self.volume_manager.VOLUME_TARGETS[self.user.goal][self.settings.experience_level]
        target = (volume_range[0] + volume_range[1]) / 2
        if total_volume < target * 0.8:
            logger.info("Total volume too low, increasing program volume")
            self._adjust_program(program, increase=True)
        elif total_volume > target * 1.2:
            logger.info("Total volume too high, decreasing program volume")
            self._adjust_program(program, increase=False)

    def _adjust_program(self, program: Dict, increase: bool):
        adjustment_factor = 1.1 if increase else 0.9
        for day in program['weekly_plan']:
            for exercise in program['weekly_plan'][day]:
                if isinstance(exercise, dict) and 'sets' in exercise:
                    exercise['sets'] = math.ceil(exercise['sets'] * adjustment_factor)

    def _add_exercise(self, program: Dict, day: str):
        training_date = convert_day_to_date(day, datetime.now())
        available_muscles = [m for m in self.MUSCLE_GROUPS['primary'].values() 
                           if self.recovery_manager.can_train(m, training_date)]
        if available_muscles:
            muscle = random.choice(available_muscles)
            exercises = self._build_muscle_exercises(muscle, 1, self.current_week, True)
            if exercises:
                program['weekly_plan'][day].extend(exercises)
                logger.debug(f"Added exercise for muscle {muscle} on {day}")

    def _adjust_exercise_scheduling(self, program: Dict, muscle: str):
        logger.warning(f"Adjusting exercise scheduling for muscle {muscle} due to insufficient recovery")
        # Implementation placeholder

    def _create_exercise_entry(self, exercise: Exercise, is_primary: bool) -> dict:
        if isinstance(exercise, dict):
            logger.error('Only Exercise model instances are allowed, not dict')
            raise TypeError('Only Exercise model instances are allowed, not dict')
        muscles = exercise.primary_muscles if is_primary else exercise.secondary_muscles
        muscle_group = muscles[0] if muscles else 'full_body'
        logger.debug(f"Creating exercise entry for {exercise.name} (primary={is_primary})")
        ex_type = 'compound' if is_primary else 'isolation'
        # Only use volume manager for real muscle groups
        if muscle_group not in ['full_body', 'warmup', 'cooldown', 'mobility', None, '']:
            volume = self.volume_manager.adjust_volume(muscle_group, self.current_week, ex_type)
            sets = volume['sets']
            reps = volume['reps']
        else:
            sets = getattr(exercise, 'sets', 4) if is_primary else getattr(exercise, 'sets', 3)
            reps = getattr(exercise, 'reps', '8-12')
        return {
            'exercise_id': exercise.id,
            'exercise_name': exercise.name,
            'type': ex_type,
            'muscle_group': muscle_group,
            'secondary_muscles': exercise.secondary_muscles if not is_primary else [],
            'mechanic': exercise.mechanic,
            'equipment': exercise.equipment,
            'difficulty': getattr(exercise, 'difficulty', ''),
            'sets': sets,
            'reps': reps,
            'rest_seconds': calculate_rest_time(exercise.mechanic, 0.7),
            'technique': getattr(exercise, 'technique', None),
            'technique_notes': getattr(exercise, 'technique_notes', None),
            'notes': get_exercise_notes(self.settings.experience_level, is_primary),
            'progression': get_progression_notes(self.settings.experience_level),
            'alternatives': self.get_exercise_alternatives(exercise) if self.settings.injuries else None
        }