from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from accounts.models import UserProfile, TrainingSettings
from exercises.models import Exercise
from ..workout_validator import WorkoutValidator
from logger_util import get_logger
import math

logger = get_logger('split_strategy', 'logs/split_strategy.log')

class SplitStrategy:
    """
    Base class for workout splitting strategies
    This class acts as a professional personal trainer and provides the following features:
    - Advanced workout management
    - Smart adjustment of volume and intensity
    - Support for progressive progression
    - Management of fatigue and recovery
    - Compatibility with physical limitations
    - Support for alternative workouts
    """
    
    # Default limits for each type of exercise
    EXERCISE_LIMITS = {
        'compound': {'min': 3, 'max': 6},    # Number of compound exercises
        'isolation': {'min': 2, 'max': 4},   # Number of isolation exercises
        'accessory': {'min': 1, 'max': 3}    # Number of accessory exercises
    }
    
    # Rep ranges for each goal
    REP_RANGES = {
        'muscle_gain': {'min': 6, 'max': 12},
        'strength': {'min': 3, 'max': 6},
        'weight_loss': {'min': 12, 'max': 20},
        'endurance': {'min': 15, 'max': 30}
    }
    
    def __init__(self, user: UserProfile, settings: TrainingSettings, 
                 exercise_selector, volume_manager, recovery_manager):
        """
        Initialize the workout splitting strategy
        
        Args:
            user: User profile
            settings: Workout settings
            exercise_selector: Exercise selector
            volume_manager: Volume manager
            recovery_manager: Recovery manager
        """
        self.user = user
        self.settings = settings
        self.exercise_selector = exercise_selector
        self.volume_manager = volume_manager
        self.recovery_manager = recovery_manager
        self.validator = WorkoutValidator(user, settings)
        self.split_map = {}
        self._validate_initialization()
        
    def _validate_initialization(self):
        """Validation of initial value"""
        if not all([self.user, self.settings, self.exercise_selector, 
                   self.volume_manager, self.recovery_manager]):
            logger.error("All required parameters must be provided")
            raise ValueError("All required parameters must be provided")
            
    def generate(self, week: int) -> Dict:
        """
        Generate a workout program for a specific week
        
        Args:
            week: Week number
            
        Returns:
            Dict: Generated workout program
            
        Raises:
            ValueError: If there is an error in generating the program
        """
        try:
            if self._should_deload(week):
                logger.info(f"Generating deload week for week {week}")
                return self._generate_deload_week(week)
            program = self._generate_base_program(week)
            program = self._adjust_volume_and_intensity(program, week)
            program = self._add_mobility_exercises(program)
            for day, exercises in program.items():
                if not exercises:
                    logger.warning(f"No exercises generated for day {day}!")
            is_valid, errors = self.validator.validate_program({'weekly_plan': program})
            logger.info(f"Program validation result: {is_valid}, errors: {errors}")
            if not is_valid:
                logger.error(f"Program is not valid: {errors}")
                raise ValueError(f"Program is not valid: {', '.join(errors)}")
            logger.info("Program generated successfully")
            return program
        except Exception as e:
            logger.error(f"Error in generating program: {str(e)}")
            raise ValueError(f"Error in generating program: {str(e)}")
            
    def _should_deload(self, week: int) -> bool:
        """
        Check if a deload is needed
        
        Args:
            week: Week number
            
        Returns:
            bool: Whether a deload is needed
        """
        return week % 4 == 0 and week > 0
        
    def _generate_deload_week(self, week: int) -> Dict:
        """
        Generate a deload week
        
        Args:
            week: Week number
            
        Returns:
            Dict: Deload program
        """
        base_program = self._generate_base_program(week)
        deload_program = {}
        for day, exercises in base_program.items():
            deload_exercises = []
            for exercise in exercises:
                if not hasattr(exercise, 'id'):
                    logger.warning(f"Invalid item in day {day} for deload: {exercise}")
                    continue
                deload_exercise = {
                    'exercise_id': exercise.id,
                    'exercise_name': exercise.name,
                    'type': getattr(exercise, 'type', 'compound'),
                    'muscle_group': exercise.primary_muscles[0] if exercise.primary_muscles else 'Unknown',
                    'sets': max(1, getattr(exercise, 'sets', 3) // 2),
                    'reps': '12-15',
                    'rest_seconds': getattr(exercise, 'rest_seconds', 60),
                    'intensity': getattr(exercise, 'intensity', 0.7),
                    'notes': getattr(exercise, 'notes', '')
                }
                deload_exercises.append(deload_exercise)
            if not deload_exercises:
                logger.warning(f"No deload exercise generated for day {day}!")
            deload_program[day] = deload_exercises
        logger.info("Deload week generated")
        return deload_program
        
    def _generate_base_program(self, week: int) -> Dict:
        raise NotImplementedError("This method must be implemented in child classes")
        
    def _adjust_volume_and_intensity(self, program: Dict, week: int) -> Dict:
        adjusted_program = {}
        for day, exercises in program.items():
            adjusted_exercises = []
            for exercise in exercises:
                if not hasattr(exercise, 'id'):
                    logger.warning(f"Invalid item in day {day}: {exercise}")
                    continue
                adjusted_exercises.append(exercise)
            if not adjusted_exercises:
                logger.warning(f"No adjusted exercise generated for day {day}!")
            adjusted_program[day] = adjusted_exercises
        logger.info("Volume and intensity adjusted")
        return adjusted_program
        
    def _calculate_intensity(self, exercise: Dict, week: int) -> float:
        base_intensity = 0.7
        week_factor = min(1.0, 0.7 + (week * 0.05))
        type_factor = {
            'compound': 1.0,
            'isolation': 0.8,
            'accessory': 0.6
        }.get(exercise['type'], 0.7)
        intensity = min(1.0, base_intensity * week_factor * type_factor)
        logger.debug(f"Calculated intensity for {exercise.get('exercise_name', '')}: {intensity}")
        return intensity
        
    def _add_mobility_exercises(self, program: Dict) -> Dict:
        for day, exercises in program.items():
            if not exercises:
                logger.warning(f"No main exercise for adding mobility in day {day}!")
                continue
            warmup = self.exercise_selector.get_mobility_exercises(
                target_areas=exercises[0].primary_muscles if hasattr(exercises[0], 'primary_muscles') else [],
                exercise_type='warmup'
            )
            cooldown = self.exercise_selector.get_mobility_exercises(
                target_areas=exercises[-1].primary_muscles if hasattr(exercises[-1], 'primary_muscles') else [],
                exercise_type='cooldown'
            )
            program[day] = list(warmup) + list(exercises) + list(cooldown)
        logger.info("Mobility exercises added")
        return program
        
    def get_exercise_alternatives(self, exercise):
        exercise_id = exercise['exercise_id'] if isinstance(exercise, dict) else exercise.id
        alternatives = self.exercise_selector.get_alternative_exercises(
            exercise_id,
            self.user.physical_limitations
        )
        logger.info(f"Alternatives for exercise {exercise_id}: {alternatives}")
        return alternatives
        
    def _validate_exercise_balance(self, exercises: List[Dict]) -> Tuple[bool, List[str]]:
        errors = []
        exercise_counts = {}
        for exercise in exercises:
            ex_type = exercise['type']
            exercise_counts[ex_type] = exercise_counts.get(ex_type, 0) + 1
        for ex_type, count in exercise_counts.items():
            limits = self.EXERCISE_LIMITS.get(ex_type, {'min': 2, 'max': 5})
            if count < limits['min']:
                errors.append(f"Number of {ex_type} exercises is less than the allowed limit")
            elif count > limits['max']:
                errors.append(f"Number of {ex_type} exercises exceeds the allowed limit")
        if errors:
            logger.warning(f"Exercise balance errors: {errors}")
        return len(errors) == 0, errors

    def _prioritize_days_by_recovery(self, available_days: List[str]) -> List[str]:
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
        logger.info(f"Prioritized days by recovery: {prioritized}")
        return prioritized

    def _calculate_recovery_score(self, day: str) -> float:
        from accounts.services.date_converter import convert_day_to_date
        training_date = convert_day_to_date(day, datetime.now())
        score = 1.0
        if hasattr(self.user, 'last_training_date') and self.user.last_training_date:
            days_since_last = (training_date - self.user.last_training_date).days
            score *= min(1.0, days_since_last / 2)
        if hasattr(self.user, 'body_type'):
            if self.user.body_type == 'ectomorph':
                score *= 1.2
            elif self.user.body_type == 'mesomorph':
                score *= 0.9
        logger.debug(f"Recovery score for day {day}: {score}")
        return score

    def _check_recovery_for_day(self, day: str, primary_muscles: List[str] = None) -> bool:
        from accounts.services.date_converter import convert_day_to_date
        training_date = convert_day_to_date(day, datetime.now())
        if primary_muscles is None and hasattr(self, 'MUSCLE_GROUPS'):
            primary_muscles = []
            if isinstance(self.MUSCLE_GROUPS, dict):
                for group in self.MUSCLE_GROUPS.values():
                    if isinstance(group, dict) and 'primary' in group:
                        primary_muscles.extend(group['primary'])
                    elif isinstance(group, list):
                        primary_muscles.extend(group)
        if not primary_muscles:
            primary_muscles = ['full_body']
        can_train = all(self.recovery_manager.can_train(muscle, training_date) for muscle in primary_muscles)
        logger.debug(f"Check recovery for day {day}, muscles {primary_muscles}: {can_train}")
        return can_train

    def _find_next_available_day(self, available_days: List[str], primary_muscles: List[str] = None) -> str:
        for day in available_days:
            if self._check_recovery_for_day(day, primary_muscles):
                logger.info(f"Next available day found: {day}")
                return day
        logger.warning("No available day found with full recovery, returning first available day")
        return available_days[0]
    
    def _get_warmup(self, split_type: str, warmup_map: dict) -> list:
        return warmup_map.get(split_type, [])

    def _get_cooldown(self, split_type: str, cooldown_map: dict) -> list:
        return cooldown_map.get(split_type, [])

    def _add_warmup_cooldown(self, program: Dict, warmup_map: dict, cooldown_map: dict, day_sequence: list):
        for idx, (day, exercises) in enumerate(program['weekly_plan'].items()):
            split_type = day_sequence[idx % len(day_sequence)]
            warmup = self._get_warmup(split_type, warmup_map)
            cooldown = self._get_cooldown(split_type, cooldown_map)
            if isinstance(exercises, dict) and 'main' in exercises:
                exercises = exercises['main']
            program['weekly_plan'][day] = warmup + exercises + cooldown
        logger.info("Warmup and cooldown added to all sessions")

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
                    old_sets = exercise['sets']
                    exercise['sets'] = math.ceil(exercise['sets'] * adjustment_factor)
                    logger.debug(f"Adjusted sets for {exercise.get('exercise_name', '')}: {old_sets} -> {exercise['sets']}")