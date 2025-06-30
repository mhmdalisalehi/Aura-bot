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

logger = get_logger('upper_lower_split', 'logs/upper_lower_split.log')
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
    
    ADVANCED_TECHNIQUES = {
        'beginner': ['drop_sets', 'rest_pause'],
        'intermediate': ['drop_sets', 'rest_pause', 'supersets', 'giant_sets'],
        'expert': ['drop_sets', 'rest_pause', 'supersets', 'giant_sets', 
                  'pyramids', 'negatives', 'forced_reps', 'cluster_sets']
    }
    
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
        logger.info(f"Generating upper/lower split program for week {week}")
        self.current_week = week
        program = {'weekly_plan': {}}
        day_counter = 0
        for day in self.settings.training_days.keys():
            split_type = 'upper' if day_counter % 2 == 0 else 'lower'
            logger.debug(f"Building {split_type} day for {day}")
            program['weekly_plan'][day] = self._build_day_plan(split_type, week)
            self.split_map[day] = split_type
            day_counter += 1
        self._validate_split_schedule(program)
        self._add_warmup_cooldown(program, self.WARMUP_MAP, self.COOLDOWN_MAP, self.DAY_SEQUENCE)
        self._validate_volume(program)
        logger.info("Upper/lower split program generated successfully")
        return program

    def _build_day_plan(self, split_type: str, week: int) -> dict:
        logger.debug(f"Building day plan for {split_type}, week {week}")
        exercises = []
        muscle_config = self.MUSCLE_GROUPS[split_type]
        for muscle, priority_exercises in muscle_config['exercise_priority'].items():
            # Use base volume to determine how many compound exercises to select
            base_volume = self.volume_manager._get_base_volume(muscle, 'compound')
            count = base_volume['sets']
            exercises.extend(self._build_priority_exercises(
                muscle,
                priority_exercises,
                count,
                week,
                is_primary=True
            ))
        for muscle in muscle_config['secondary']:
            # Use base volume for isolation
            base_volume = self.volume_manager._get_base_volume(muscle, 'isolation')
            count = base_volume['sets']
            if random.random() < 0.8:
                exercises.extend(self._build_muscle_exercises(
                    muscle,
                    count,
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
        # Filter exercises so total sets per muscle/type do not exceed recommended
        exercises = self._limit_exercises_by_volume(exercises)
        main_exercises = [
            self._create_exercise_entry(ex, is_primary=(ex.mechanic == 'compound'))
            for ex in exercises
        ]
        main_exercises = [ex for ex in main_exercises if ex is not None]
        logger.debug(f"main_exercises for {split_type} day: {[ex['exercise_name'] for ex in main_exercises]}")
        if not main_exercises:
            logger.warning(f"No main exercises generated for {split_type} day! Check exercise selection logic.")
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
        logger.debug(f"Built {len(exercises)} priority exercises for muscle {muscle}")
        return exercises

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

    def _apply_advanced_techniques(self, exercises: List[Exercise], available_techniques: List[str]) -> List[Exercise]:
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
            ex_type = 'compound' if exercise.mechanic == 'compound' else 'isolation'
            base_volume = self.volume_manager.adjust_volume(
                muscle_group,
                self.current_week,
                ex_type
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

    def _limit_exercises_by_volume(self, exercises: List[Exercise]) -> List[Exercise]:
        # Limit total sets per muscle group/type to not exceed base recommendations
        muscle_type_sets = defaultdict(int)
        filtered = []
        for ex in exercises:
            muscle_group = (ex.primary_muscles[0] if ex.primary_muscles else
                            (ex.secondary_muscles[0] if ex.secondary_muscles else 'full_body'))
            ex_type = 'compound' if ex.mechanic == 'compound' else 'isolation'
            base_volume = self.volume_manager._get_base_volume(muscle_group, ex_type)
            max_sets = base_volume['sets']
            if muscle_type_sets[(muscle_group, ex_type)] + ex.sets <= max_sets:
                filtered.append(ex)
                muscle_type_sets[(muscle_group, ex_type)] += ex.sets
            else:
                logger.debug(f"Skipping {ex.name} for {muscle_group} ({ex_type}) to avoid exceeding set limit")
        return filtered

    def _create_exercise_entry(self, exercise: Exercise, is_primary: bool) -> Optional[dict]:
        if isinstance(exercise, dict):
            logger.error('Only Exercise model instances are allowed, not dict')
            raise TypeError('Only Exercise model instances are allowed, not dict')
        muscles = exercise.primary_muscles if is_primary else exercise.secondary_muscles
        muscle_group = muscles[0] if muscles else None
        if not muscle_group or muscle_group in ['full_body', 'Unknown', '', None]:
            logger.warning(f"Exercise {exercise.name} has invalid muscle_group, skipping.")
            return None
        logger.debug(f"Creating exercise entry for {exercise.name} (primary={is_primary})")
        ex_type = 'compound' if is_primary else 'isolation'
        volume = self.volume_manager.adjust_volume(muscle_group, self.current_week, ex_type)
        sets = volume['sets']
        reps = volume['reps']
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

        
    def _adjust_program(self, program: Dict, increase: bool):
        adjustment_factor = 1.1 if increase else 0.9
        for day in program['weekly_plan']:
            for exercise in program['weekly_plan'][day]:
                if isinstance(exercise, dict) and 'sets' in exercise:
                    exercise['sets'] = math.ceil(exercise['sets'] * adjustment_factor)

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
           
    def _validate_split_schedule(self, program: Dict):
        trained_muscles = defaultdict(list)
        for day, exercises in program['weekly_plan'].items():
            for ex in exercises:
                if isinstance(ex, dict) and 'muscle_group' in ex:
                    muscle = ex['muscle_group']
                    trained_muscles[muscle].append(day)
        for muscle, days in trained_muscles.items():
            min_recovery = RecoveryManager.BASE_RECOVERY_DAYS.get(muscle, 2)
            for i in range(1, len(days)):
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
                if (date2 - date1).days < min_recovery:
                    logger.warning(f"Insufficient recovery for {muscle} between {date1} and {date2}")
                    self._adjust_exercise_scheduling(program, muscle)
                    
    def _adjust_exercise_scheduling(self, program: Dict, muscle: str):
        logger.warning(f"Adjusting exercise scheduling for muscle {muscle} due to insufficient recovery")
        for day, exercises in program['weekly_plan'].items():
            for ex in exercises:
                if isinstance(ex, dict) and ex.get('muscle_group') == muscle:
                    if random.random() < 0.5:
                        ex['sets'] = max(2, ex['sets'] - 1)
                        logger.debug(f"Reduced sets for {muscle} on {day}")
                    else:
                        exercise_id = ex.get('exercise_id') if isinstance(ex, dict) else getattr(ex, 'id', None)
                        if exercise_id:
                            try:
                                exercise_obj = Exercise.objects.get(id=exercise_id)
                                alternatives = self.get_exercise_alternatives(exercise_obj)
                                if alternatives:
                                    alt = random.choice(alternatives)
                                    ex.update(self._create_exercise_entry(alt, ex['type'] == 'compound'))
                                    logger.debug(f"Replaced exercise for {muscle} on {day} with alternative")
                            except Exercise.DoesNotExist:
                                logger.error(f'Exercise with id {exercise_id} does not exist.')
                                continue
                        else:
                            logger.error(f"No valid exercise_id found for muscle {muscle} on {day}")
                            continue