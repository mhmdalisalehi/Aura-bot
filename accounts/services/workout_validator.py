from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from accounts.models import UserProfile, TrainingSettings
from exercises.models import Exercise

from logger_util import get_logger
logger = get_logger('workout_validator', 'logs/workout_validator.log')

class WorkoutValidator:
    """
    اعتبارسنجی حرفه‌ای برنامه تمرینی
    - بررسی تعادل و توالی تمرینات
    - بررسی سازگاری با محدودیت‌های فیزیکی
    - همگام‌سازی با سایر بخش‌های برنامه
    - بررسی پیشرفت و ریکاوری
    """
    
    VOLUME_LIMITS = {
        'chest': {'min': 8, 'max': 20},
        'back': {'min': 8, 'max': 20},
        'shoulders': {'min': 6, 'max': 15},
        'biceps': {'min': 4, 'max': 12},
        'triceps': {'min': 4, 'max': 12},
        'quadriceps': {'min': 8, 'max': 20},
        'hamstrings': {'min': 6, 'max': 15},
        'calves': {'min': 4, 'max': 12},
        'abs': {'min': 4, 'max': 12}
    }
    INTENSITY_LIMITS = {
        'compound': {'min': 3, 'max': 8},
        'isolation': {'min': 2, 'max': 4},
        'accessory': {'min': 2, 'max': 3}
    }
    REP_RANGES = {
        'muscle_gain': {'min': 6, 'max': 12},
        'strength': {'min': 3, 'max': 6},
        'weight_loss': {'min': 12, 'max': 20},
        'endurance': {'min': 15, 'max': 30}
    }
    
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        self.volume_manager = None
        self.recovery_manager = None
        self.exercise_selector = None
        self._validate_initialization()
        logger.info("WorkoutValidator initialized.")

    def _validate_initialization(self):
        if not self.user or not self.settings:
            logger.error("User and settings must be provided")
            raise ValueError("User and settings must be provided")
            
    def set_managers(self, volume_manager, recovery_manager, exercise_selector):
        self.volume_manager = volume_manager
        self.recovery_manager = recovery_manager
        self.exercise_selector = exercise_selector
        logger.info("Managers set for WorkoutValidator.")

    def validate_program(self, program: Dict) -> Tuple[bool, List[str]]:
        logger.info("validate_program called")
        try:
            errors = []
            if not self._validate_structure(program):
                logger.warning("Program structure is not valid")
                errors.append("Program structure is not valid")
                return False, errors
            balance_errors = self._validate_exercise_balance(program)
            logger.info(f"balance_errors: {balance_errors}")
            errors.extend(balance_errors)
            volume_errors = self._validate_volume(program)
            logger.info(f"volume_errors: {volume_errors}")
            errors.extend(volume_errors)
            sequence_errors = self._validate_sequence(program)
            logger.info(f"sequence_errors: {sequence_errors}")
            errors.extend(sequence_errors)
            limitation_errors = self._validate_limitations(program)
            logger.info(f"limitation_errors: {limitation_errors}")
            errors.extend(limitation_errors)
            if self.recovery_manager:
                recovery_errors = self._validate_recovery(program)
                logger.info(f"recovery_errors: {recovery_errors}")
                errors.extend(recovery_errors)
            else:
                logger.warning("Recovery manager is not set")
                errors.append("Recovery manager is not set")
            logger.info(f"validate_program result: {len(errors) == 0}, errors: {errors}")
            return len(errors) == 0, errors
        except Exception as e:
            logger.error(f"Exception in validate_program: {str(e)}")
            return False, [f"Error in program validation: {str(e)}"]

    def _validate_structure(self, program: Dict) -> bool:
        required_keys = ['weekly_plan']
        if not all(key in program for key in required_keys):
            logger.error("Missing required keys in program structure")
            return False
        if not isinstance(program['weekly_plan'], dict):
            logger.error("weekly_plan is not a dict")
            return False
        for day, exercises in program['weekly_plan'].items():
            if not isinstance(exercises, list):
                logger.error(f"Exercises for day {day} is not a list")
                return False
            for exercise in exercises:
                if not self._validate_exercise_structure(exercise):
                    logger.error(f"Exercise structure invalid for {exercise}")
                    return False
        return True

    def _validate_exercise_structure(self, exercise) -> bool:
        required_fields = [
            'exercise_id', 'exercise_name', 'type', 
            'muscle_group', 'sets', 'reps', 'rest_seconds'
        ]
        if isinstance(exercise, dict):
            valid = all(field in exercise for field in required_fields)
        else:
            valid = all(hasattr(exercise, field) for field in required_fields)
        if not valid:
            logger.warning(f"Exercise structure missing fields: {exercise}")
        return valid

    def _validate_exercise_balance(self, program: Dict) -> List[str]:
        errors = []
        exercise_counts = {}
        muscle_counts = {}
        for day, exercises in program['weekly_plan'].items():
            for exercise in exercises:
                ex_type = exercise['type'] if isinstance(exercise, dict) else exercise.type
                muscle = exercise['muscle_group'] if isinstance(exercise, dict) else exercise.muscle_group
                exercise_counts[ex_type] = exercise_counts.get(ex_type, 0) + 1
                muscle_counts[muscle] = muscle_counts.get(muscle, 0) + 1
        for ex_type, count in exercise_counts.items():
            limits = self.INTENSITY_LIMITS.get(ex_type, {'min': 2, 'max': 5})
            if count < limits['min']:
                errors.append(f"Number of {ex_type} exercises is less than allowed")
            elif count > limits['max']:
                errors.append(f"Number of {ex_type} exercises is more than allowed")
        for muscle, count in muscle_counts.items():
            limits = self.VOLUME_LIMITS.get(muscle, {'min': 4, 'max': 12})
            if count < limits['min']:
                errors.append(f"Number of {muscle} exercises is less than allowed")
            elif count > limits['max']:
                errors.append(f"Number of {muscle} exercises is more than allowed")
        if errors:
            logger.warning(f"Exercise balance errors: {errors}")
        return errors

    def _validate_volume(self, program: Dict) -> List[str]:
        errors = []
        muscle_volume = {}
        for day, exercises in program['weekly_plan'].items():
            for exercise in exercises:
                muscle = exercise.muscle_group
                if muscle not in muscle_volume:
                    muscle_volume[muscle] = 0
                volume = self._calculate_exercise_volume(exercise)
                muscle_volume[muscle] += volume
                if not self._is_valid_exercise_volume(exercise):
                    errors.append(f"Volume of exercise {exercise.exercise_name} is not valid")
        for muscle, volume in muscle_volume.items():
            if not self._is_valid_muscle_volume(muscle, volume):
                errors.append(f"Total volume for {muscle} is not valid")
        if errors:
            logger.warning(f"Volume errors: {errors}")
        return errors

    def _calculate_exercise_volume(self, exercise: Exercise) -> int:
        sets = exercise.sets
        reps = exercise.reps
        if isinstance(reps, str):
            reps = int(reps.split('-')[0])
        return sets * reps

    def _is_valid_exercise_volume(self, exercise: Exercise) -> bool:
        sets = exercise.sets
        reps = exercise.reps
        if not isinstance(sets, int) or sets < 1 or sets > 10:
            logger.warning(f"Invalid sets: {sets}")
            return False
        if isinstance(reps, str):
            try:
                min_reps, max_reps = map(int, reps.split('-'))
                rep_range = self.REP_RANGES.get(self.user.goal, {'min': 8, 'max': 12})
                if min_reps < rep_range['min'] or max_reps > rep_range['max']:
                    logger.warning(f"Invalid reps range: {reps}")
                    return False
            except Exception as e:
                logger.error(f"Error parsing reps: {reps} - {e}")
                return False
        return True

    def _is_valid_muscle_volume(self, muscle: str, volume: int) -> bool:
        limits = self.VOLUME_LIMITS.get(muscle, {'min': 4, 'max': 12})
        valid = limits['min'] <= volume <= limits['max']
        if not valid:
            logger.warning(f"Muscle volume for {muscle} not valid: {volume}")
        return valid

    def _validate_sequence(self, program: Dict) -> List[str]:
        errors = []
        trained_muscles = {}
        days = sorted(program['weekly_plan'].keys())
        for i in range(1, len(days)):
            prev_day = datetime.strptime(days[i-1], '%Y-%m-%d')
            curr_day = datetime.strptime(days[i], '%Y-%m-%d')
            if (curr_day - prev_day).days < 1:
                errors.append("Training days must be at least one day apart")
        for day, exercises in program['weekly_plan'].items():
            for exercise in exercises:
                muscle = exercise.muscle_group
                if muscle not in trained_muscles:
                    trained_muscles[muscle] = []
                trained_muscles[muscle].append(day)
        for muscle, days in trained_muscles.items():
            if len(days) > 1:
                for i in range(1, len(days)):
                    prev_day = datetime.strptime(days[i-1], '%Y-%m-%d')
                    curr_day = datetime.strptime(days[i], '%Y-%m-%d')
                    min_recovery = self._get_min_recovery_days(muscle)
                    if (curr_day - prev_day).days < min_recovery:
                        errors.append(f"Rest time for {muscle} is not enough")
        if errors:
            logger.warning(f"Sequence errors: {errors}")
        return errors

    def _get_min_recovery_days(self, muscle: str) -> int:
        recovery_days = {
            'chest': 2,
            'back': 2,
            'shoulders': 2,
            'biceps': 2,
            'triceps': 2,
            'quadriceps': 3,
            'hamstrings': 3,
            'glutes': 2,
            'calves': 2,
            'abs': 1
        }
        return recovery_days.get(muscle, 2)

    def _validate_limitations(self, program: Dict) -> List[str]:
        errors = []
        if not self.user.physical_limitations:
            return errors
        for day, exercises in program['weekly_plan'].items():
            for exercise in exercises:
                if not self._is_exercise_safe(exercise):
                    errors.append(f"Exercise {exercise.exercise_name} is not compatible with physical limitations")
        if errors:
            logger.warning(f"Limitation errors: {errors}")
        return errors

    def _is_exercise_safe(self, exercise: Exercise) -> bool:
        if hasattr(self.user, 'physical_limitations'):
            for limitation in self.user.physical_limitations:
                if limitation in exercise.muscle_group:
                    logger.warning(f"Exercise {exercise.exercise_name} not safe for limitation {limitation}")
                    return False
        if exercise.difficulty not in ['beginner', 'intermediate']:
            logger.warning(f"Exercise {exercise.exercise_name} difficulty not allowed: {exercise.difficulty}")
            return False
        return True

    def _validate_recovery(self, program: Dict) -> List[str]:
        errors = []
        if not self.recovery_manager:
            return errors
        for day, exercises in program['weekly_plan'].items():
            target_muscles = [ex.muscle_group for ex in exercises]
            if not self.recovery_manager.can_train(target_muscles, datetime.strptime(day, '%Y-%m-%d')):
                errors.append(f"Muscles in {day} need rest")
        if errors:
            logger.warning(f"Recovery errors: {errors}")
        return errors

    def _is_valid_mobility_exercise(self, exercise: Exercise, exercise_type: str) -> bool:
        # Allow custom warmup/cooldown with id=0
        if getattr(exercise, 'exercise_id', None) == 0:
            return True
        try:
            ex = Exercise.objects.get(id=exercise.exercise_id)
            if exercise_type == 'warmup':
                return ex.category in ['cardio', 'plyometrics', 'stretching']
            else:
                return ex.category in ['stretching', 'mobility']
        except Exercise.DoesNotExist:
            logger.warning(f"Exercise with id {exercise.exercise_id} does not exist")
            return False

    def validate_workout(self, workout: Dict) -> Tuple[bool, List[str]]:
        logger.info("validate_workout called")
        try:
            errors = []
            if not self._validate_workout_structure(workout):
                errors.append("Workout structure is not valid")
                logger.warning("Workout structure is not valid")
                return False, errors
            if 'exercises' in workout:
                exercise_errors = self._validate_workout_exercises(workout['exercises'])
                errors.extend(exercise_errors)
            if 'warmup' in workout:
                warmup_errors = self._validate_mobility_exercises(workout['warmup'], 'warmup')
                errors.extend(warmup_errors)
            if 'cooldown' in workout:
                cooldown_errors = self._validate_mobility_exercises(workout['cooldown'], 'cooldown')
                errors.extend(cooldown_errors)
            if self.recovery_manager:
                target_muscles = [ex.muscle_group for ex in workout.get('exercises', [])]
                if not self.recovery_manager.can_train(target_muscles, datetime.strptime(workout['date'], '%Y-%m-%d')):
                    errors.append("Muscles in target need rest")
            else:
                errors.append("Recovery manager is not set")
            logger.info(f"validate_workout result: {len(errors) == 0}, errors: {errors}")
            return len(errors) == 0, errors
        except Exception as e:
            logger.error(f"Exception in validate_workout: {str(e)}")
            return False, [f"Error in workout validation: {str(e)}"]

    def _validate_workout_structure(self, workout: Dict) -> bool:
        required_keys = ['date', 'target_muscles']
        optional_keys = ['exercises', 'warmup', 'cooldown']
        if not all(key in workout for key in required_keys):
            logger.warning("Workout missing required keys")
            return False
        if not isinstance(workout['date'], str):
            logger.warning("Workout date is not a string")
            return False
        if not isinstance(workout['target_muscles'], list):
            logger.warning("Workout target_muscles is not a list")
            return False
        try:
            datetime.strptime(workout['date'], '%Y-%m-%d')
        except ValueError:
            logger.warning("Workout date format invalid")
            return False
        for key in optional_keys:
            if key in workout and not isinstance(workout[key], list):
                logger.warning(f"Workout {key} is not a list")
                return False
        return True

    def _validate_workout_exercises(self, exercises: List[Exercise]) -> List[str]:
        errors = []
        if not exercises:
            errors.append("Exercise list is empty")
            logger.warning("Exercise list is empty")
            return errors
        for i, exercise in enumerate(exercises, 1):
            if not self._validate_exercise_structure(exercise):
                errors.append(f"Exercise structure {i} is not valid")
                logger.warning(f"Exercise structure {i} is not valid")
                continue
            if not self._is_valid_exercise_volume(exercise):
                errors.append(f"Volume of exercise {i} ({exercise.exercise_name}) is not valid")
                logger.warning(f"Volume of exercise {i} ({exercise.exercise_name}) is not valid")
            if not self._is_exercise_safe(exercise):
                errors.append(f"Exercise {i} ({exercise.exercise_name}) is not compatible with physical limitations")
                logger.warning(f"Exercise {i} ({exercise.exercise_name}) is not compatible with physical limitations")
            if i > 1:
                prev_exercise = exercises[i-2]
                if not self._is_valid_exercise_sequence(prev_exercise, exercise):
                    errors.append(f"Exercise sequence {i-1} and {i} is not appropriate")
                    logger.warning(f"Exercise sequence {i-1} and {i} is not appropriate")
        return errors

    def _is_valid_exercise_sequence(self, prev_exercise: Exercise, curr_exercise: Exercise) -> bool:
        if (prev_exercise.type == 'isolation' and curr_exercise.type == 'compound'):
            logger.warning("Isolation before compound exercise found")
            return False
        if (prev_exercise.muscle_group in ['biceps', 'triceps'] and 
            curr_exercise.muscle_group in ['chest', 'back']):
            logger.warning("Small muscle before large muscle found")
            return False
        return True

    def _validate_mobility_exercises(self, exercises: List[Exercise], exercise_type: str) -> List[str]:
        errors = []
        if not exercises:
            errors.append(f"{exercise_type} exercises are missing")
            logger.warning(f"{exercise_type} exercises are missing")
            return errors
        for i, exercise in enumerate(exercises, 1):
            if not all(hasattr(exercise, field) for field in ['exercise_id', 'exercise_name', 'duration_seconds']):
                errors.append(f"{exercise_type} exercise structure {i} is not valid")
                logger.warning(f"{exercise_type} exercise structure {i} is not valid")
                continue
            duration = exercise.duration_seconds
            if exercise_type == 'warmup':
                if duration < 30 or duration > 300:
                    errors.append(f"Warmup duration for exercise {i} is not valid")
                    logger.warning(f"Warmup duration for exercise {i} is not valid")
            else:
                if duration < 20 or duration > 180:
                    errors.append(f"Cooldown duration for exercise {i} is not valid")
                    logger.warning(f"Cooldown duration for exercise {i} is not valid")
            if not self._is_valid_mobility_exercise(exercise, exercise_type):
                errors.append(f"{exercise_type} exercise type {i} is not valid")
                logger.warning(f"{exercise_type} exercise type {i} is not valid")
        return errors

    def _is_valid_mobility_exercise(self, exercise: Exercise, exercise_type: str) -> bool:
        try:
            ex = Exercise.objects.get(id=exercise.exercise_id)
            if exercise_type == 'warmup':
                return ex.category in ['cardio', 'plyometrics', 'stretching']
            else:
                return ex.category in ['stretching', 'mobility']
        except Exercise.DoesNotExist:
            logger.warning(f"Exercise with id {exercise.exercise_id} does not exist")
            return False