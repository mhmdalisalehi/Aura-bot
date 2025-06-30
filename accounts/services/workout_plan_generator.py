import os
os.makedirs('logs', exist_ok=True)
from pprint import pprint
from typing import Dict, List
from datetime import datetime, timedelta
from accounts.models import UserProfile, TrainingSettings
from exercises.models import Exercise
from .split_startegy.bro_split import BroSplitStrategy
from .split_startegy.ppl_strategy import PushPullLegsSplitStrategy
from .split_startegy.uperlower_strategy import UpperLowerSplitStrategy
from .split_startegy.fuulBody_strategy import FullBodySplitStrategy
from .exercise_selector import ExerciseSelector
from .volume_manager import WorkoutVolumeManager
from .recovery_manager import RecoveryManager
from .workout_validator import WorkoutValidator
from .workout_utils import (
    calculate_rest_time,
    calculate_intensity,
    get_next_training_day,
    get_muscle_groups_for_split,
    get_exercise_notes
)
from accounts.services.split_rotation_manager import update_split_if_needed
from accounts.services.date_converter import convert_day_to_date, convert_persian_to_english_weekday
from .base_manager import BaseWorkoutManager
from logger_util import get_logger

logger = get_logger('workout_plan_generator', 'logs/workout_plan_generator.log')

def get_field(obj, field):
    if isinstance(obj, dict):
        return obj.get(field)
    return getattr(obj, field, None)

class WorkoutPlanGenerator(BaseWorkoutManager):
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        super().__init__(user, settings)
        logger.info(f"Initialized WorkoutPlanGenerator for user_id={user.id}")

    def generate_plan(self) -> Dict:
        try:
            logger.info("Starting workout plan generation.")
            strategy = self._get_split_strategy()
            weekly_plan = {}
            current_date = datetime.now()
            week_plan = strategy.generate(1)
            logger.info(f"Generated raw plan before validation: {week_plan}")
            weekly_plan.update(self._add_dates_to_plan(week_plan['weekly_plan'], current_date))
            # Flatten and validate
            plain_weekly_plan = {}
            # Ensure all exercises have required fields for validation
            def ensure_required_fields(ex):
                required_fields = [
                    'exercise_id', 'exercise_name', 'type', 'muscle_group', 'sets', 'reps', 'rest_seconds'
                ]
                defaults = {
                    'exercise_id': 0,
                    'exercise_name': 'Unknown',
                    'type': 'unknown',
                    'muscle_group': 'Unknown',
                    'sets': 1,
                    'reps': '8-12',
                    'rest_seconds': 30
                }
                if isinstance(ex, dict):
                    for k in required_fields:
                        if k not in ex:
                            ex[k] = defaults[k]
                return ex

            def expand_and_ensure_fields(ex, ex_type=None):
                # If this is a container (has 'content'), expand it
                if isinstance(ex, dict) and 'content' in ex:
                    expanded = []
                    for idx, item in enumerate(ex['content']):
                        # Map fields from content item to required fields
                        exercise_dict = {
                            'exercise_id': 0,
                            'exercise_name': item.get('name', f'Unknown {ex_type or ex.get("type", "")}{idx+1}') if isinstance(item, dict) else str(item),
                            'type': ex_type or ex.get('type', 'mobility'),
                            'muscle_group': 'Unknown',
                            'sets': 1,
                            'reps': '8-12',
                            'rest_seconds': 30,
                            'duration_seconds': 60,
                            'notes': item.get('notes', '') if isinstance(item, dict) else ''
                        }
                        # Try to map duration if present
                        if isinstance(item, dict):
                            dur = item.get('duration')
                            if dur:
                                try:
                                    if 'min' in dur:
                                        mins = int(dur.split('min')[0].strip())
                                        exercise_dict['duration_seconds'] = mins * 60
                                    elif 's' in dur:
                                        secs = int(dur.split('s')[0].strip())
                                        exercise_dict['duration_seconds'] = secs
                                except Exception:
                                    logger.info(f"Could not parse duration: {dur}")
                        expanded.append(exercise_dict)
                    return expanded
                else:
                    return [ensure_required_fields(ex)]

            for day, day_plan in weekly_plan.items():
                all_exercises = []
                if isinstance(day_plan, dict):
                    if 'warmup' in day_plan:
                        for e in day_plan['warmup']:
                            all_exercises.extend(expand_and_ensure_fields(e, 'warmup'))
                    if 'main' in day_plan:
                        all_exercises.extend([ensure_required_fields(e) for e in day_plan['main']])
                    if 'cooldown' in day_plan:
                        for e in day_plan['cooldown']:
                            all_exercises.extend(expand_and_ensure_fields(e, 'cooldown'))
                else:
                    all_exercises.extend([ensure_required_fields(e) for e in day_plan])
                # --- Convert all dicts to SimpleNamespace for attribute access ---
                from types import SimpleNamespace
                def dict_to_namespace(d):
                    if isinstance(d, dict):
                        return SimpleNamespace(**d)
                    return d
                all_exercises = [dict_to_namespace(ex) if isinstance(ex, dict) else ex for ex in all_exercises]
                plain_weekly_plan[day] = all_exercises
            is_valid, errors = self.validator.validate_program({'weekly_plan': plain_weekly_plan})
            if not is_valid:
                logger.info(f"Validation failed: {errors}")
                logger.info("Problematic plan structure:\n" + pprint.pformat(plain_weekly_plan, indent=2, width=120))
                raise ValueError(f"Program is not valid: {', '.join(errors)}")
            logger.info("Workout plan validated successfully.")
            return {'weekly_plan': plain_weekly_plan}
        except Exception as e:
            logger.error(f"Exception in generate_plan: {str(e)}", exc_info=True)
            raise ValueError(f"Error in generating workout plan: {str(e)}")
            
    def _add_dates_to_plan(self, week_plan: Dict, current_date: datetime) -> Dict:
        logger.info("Adding dates to weekly plan.")
        dated_plan = {}
        for day, exercises in week_plan.items():
            if not exercises:
                logger.info(f"No exercises generated for day {day}!")
            training_date = convert_day_to_date(day, current_date)
            main_exercises = []
            if isinstance(exercises, dict):
                main_items = exercises.get('main', [])
                if main_items and all(isinstance(ex, dict) for ex in main_items):
                    main_exercises = main_items
                else:
                    for ex in main_items:
                        if isinstance(ex, dict):
                            main_exercises.append(ex)
                        elif hasattr(ex, 'id') and hasattr(ex, 'name'):
                            main_exercises.append({
                                'exercise_id': ex.id,
                                'exercise_name': ex.name,
                                'type': getattr(ex, 'type', 'compound'),
                                'muscle_group': ex.primary_muscles[0] if hasattr(ex, 'primary_muscles') and ex.primary_muscles else 'Unknown',
                                'sets': getattr(ex, 'sets', 3),
                                'reps': getattr(ex, 'reps', '8-12'),
                                'rest_seconds': getattr(ex, 'rest_seconds', 60),
                                'intensity': getattr(ex, 'intensity', 0.7),
                                'notes': getattr(ex, 'notes', '')
                            })
            else:
                for exercise in exercises:
                    if isinstance(exercise, dict):
                        main_exercises.append(exercise)
                    elif hasattr(exercise, 'id') and hasattr(exercise, 'name'):
                        main_exercises.append({
                            'exercise_id': exercise.id,
                            'exercise_name': exercise.name,
                            'type': getattr(exercise, 'type', 'compound'),
                            'muscle_group': exercise.primary_muscles[0] if hasattr(exercise, 'primary_muscles') and exercise.primary_muscles else 'Unknown',
                            'sets': getattr(exercise, 'sets', 3),
                            'reps': getattr(exercise, 'reps', '8-12'),
                            'rest_seconds': getattr(exercise, 'rest_seconds', 60),
                            'intensity': getattr(exercise, 'intensity', 0.7),
                            'notes': getattr(exercise, 'notes', '')
                        })
            # --- INJECT VOLUME MANAGER LOGIC HERE ---
            for exercise in main_exercises:
                muscle = exercise.get('muscle_group', 'full_body')
                ex_type = exercise.get('type', 'compound')
                # Only adjust for real muscle groups, not 'full_body', 'warmup', 'cooldown', etc.
                if muscle not in ['full_body', 'warmup', 'cooldown', 'mobility', None, '']:
                    # Use week=1 for now, or pass the correct week if available
                    volume = self.volume_manager.adjust_volume(muscle, week=1, exercise_type=ex_type)
                    exercise['sets'] = volume['sets']
                    exercise['reps'] = volume['reps']
            dated_plan[training_date.strftime('%Y-%m-%d')] = main_exercises
        logger.info("Dates added to weekly plan.")
        return dated_plan 
    
    def _find_next_available_date(self, start_date: datetime, target_muscles: List[str]) -> datetime:
        logger.info(f"Finding next available date for muscles {target_muscles} starting from {start_date}")
        current_date = start_date
        max_attempts = 14
        for _ in range(max_attempts):
            if self.recovery_manager.can_train(target_muscles, current_date):
                logger.info(f"Found available date: {current_date}")
                return current_date
            current_date += timedelta(days=1)
        logger.info("Cannot find a suitable date for training after 14 attempts.")
        raise ValueError("Cannot find a suitable date for training")
        
    def _get_split_strategy(self):
        try:
            logger.info(f"Selecting split strategy: {self.settings.split_type}")
            strategies = {
                'bro_split':   BroSplitStrategy,
                'ppl': PushPullLegsSplitStrategy,
                'upper_lower': UpperLowerSplitStrategy,
                'full_body': FullBodySplitStrategy
            }
            strategy_class = strategies.get(self.settings.split_type)
            if not strategy_class:
                logger.info(f"Invalid split type: {self.settings.split_type}")
                raise ValueError(f"Invalid split type: {self.settings.split_type}")
            logger.info(f"Instantiating strategy class: {strategy_class.__name__}")
            return strategy_class(
                self.user,
                self.settings,
                self.exercise_selector,
                self.volume_manager,
                self.recovery_manager
            )
        except Exception as e:
            logger.info(f"Error in selecting strategy: {str(e)}", exc_info=True)
            raise ValueError(f"Error in selecting strategy: {str(e)}")
        
    def _get_plan_metadata(self, weeks: int) -> Dict:
        logger.info(f"Getting plan metadata for {weeks} weeks.")
        return {
            'user_id': self.user.id,
            'created_at': datetime.now().isoformat(),
            'weeks': weeks,
            'split_type': self.settings.split_type,
            'experience_level': self.settings.experience_level,
            'goal': self.user.goal,
            'available_equipment': self.settings.available_equipment,
            'training_days': list(self.settings.training_days.keys())
        }
        
    def adjust_plan(self, plan: Dict, feedback: Dict) -> Dict:
        logger.info("Adjusting plan based on feedback.")
        if 'volume_feedback' in feedback:
            self._adjust_volume(plan, feedback['volume_feedback'])
        if 'intensity_feedback' in feedback:
            self._adjust_intensity(plan, feedback['intensity_feedback'])
        if 'sequence_feedback' in feedback:
            self._adjust_sequence(plan, feedback['sequence_feedback'])
        is_valid, errors = self.validator.validate_program(plan)
        if not is_valid:
            logger.info(f"Adjusted plan is not valid: {errors}")
            raise ValueError(f"Program is not valid: {', '.join(errors)}")
        logger.info("Plan adjusted and validated successfully.")
        return plan
        
    def _adjust_volume(self, plan: Dict, feedback: Dict):
        logger.info("Adjusting volume based on feedback.")
        for day, exercises in plan['weekly_plan'].items():
            for exercise in exercises:
                muscle = exercise['muscle_group']
                if muscle in feedback:
                    if 'sets' in feedback[muscle]:
                        logger.debug(f"Adjusting sets for {muscle} on {day}: {exercise['sets']} -> {feedback[muscle]['sets']}")
                        exercise['sets'] = feedback[muscle]['sets']
                    if 'reps' in feedback[muscle]:
                        logger.debug(f"Adjusting reps for {muscle} on {day}: {exercise['reps']} -> {feedback[muscle]['reps']}")
                        exercise['reps'] = feedback[muscle]['reps']
                        
    def _adjust_intensity(self, plan: Dict, feedback: Dict):
        logger.info("Adjusting intensity based on feedback.")
        for day, exercises in plan['weekly_plan'].items():
            for exercise in exercises:
                if exercise['exercise_id'] in feedback:
                    if 'rest_seconds' in feedback[exercise['exercise_id']]:
                        logger.debug(f"Adjusting rest_seconds for exercise_id {exercise['exercise_id']} on {day}: {exercise['rest_seconds']} -> {feedback[exercise['exercise_id']]['rest_seconds']}")
                        exercise['rest_seconds'] = feedback[exercise['exercise_id']]['rest_seconds']
                        
    def _adjust_sequence(self, plan: Dict, feedback: Dict):
        logger.info("Adjusting exercise sequence based on feedback.")
        for day, exercises in plan['weekly_plan'].items():
            if day in feedback:
                new_sequence = feedback[day]
                logger.debug(f"New sequence for {day}: {new_sequence}")
                plan['weekly_plan'][day] = [exercises[i] for i in new_sequence] 
        
    def _parse_duration(self, duration_str: str) -> int:
        try:
            if 'min' in duration_str:
                minutes = int(duration_str.split('min')[0].strip())
                return minutes * 60
            elif 's' in duration_str:
                seconds = int(duration_str.split('s')[0].strip())
                return seconds
            else:
                return 60
        except (ValueError, AttributeError):
            logger.info(f"Could not parse duration string: {duration_str}")
            return 60
    
    def save_plan_to_db(self, plan: Dict, weeks: int = 4):
        logger.info("Saving plan to database.")
        from accounts.models import WorkoutPlan, WorkoutDay, WorkoutExercise

        workout_plan = WorkoutPlan.objects.create(
            user=self.user.user,
            settings=self.settings,
            weeks=weeks,
            split_type=self.settings.split_type,
            experience_level=self.settings.experience_level,
            goal=self.user.goal,
            available_equipment=self.settings.available_equipment,
            training_days=self.settings.training_days
        )
        for day_idx, (date_str, exercises) in enumerate(plan['weekly_plan'].items()):
            workout_day = WorkoutDay.objects.create(
                plan=workout_plan,
                date=date_str,
                order=day_idx
            )
            for ex_idx, exercise in enumerate(exercises):
                ex_obj = None
                if 'exercise_id' in exercise and exercise['exercise_id']:
                    try:
                        ex_obj = Exercise.objects.get(id=exercise['exercise_id'])
                    except Exercise.DoesNotExist:
                        logger.warning(f"Exercise with id {exercise['exercise_id']} does not exist in DB.")
                        ex_obj = None
                WorkoutExercise.objects.create(
                    day=workout_day,
                    exercise=ex_obj,
                    exercise_name=exercise.get('exercise_name', ''),
                    type=exercise.get('type', ''),
                    muscle_group=exercise.get('muscle_group', ''),
                    sets=exercise.get('sets', 0),
                    reps=exercise.get('reps', ''),
                    rest_seconds=exercise.get('rest_seconds', 60),
                    intensity=exercise.get('intensity', 0.7),
                    notes=exercise.get('notes', ''),
                    order=ex_idx
                )
        logger.info("Plan saved to database successfully.")
        return workout_plan