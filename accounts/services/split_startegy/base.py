from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from accounts.models import UserProfile, TrainingSettings
from exercises.models import Exercise
from ..workout_validator import WorkoutValidator
import logging
import math

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
                return self._generate_deload_week(week)
            program = self._generate_base_program(week)
            program = self._adjust_volume_and_intensity(program, week)
            program = self._add_mobility_exercises(program)
            # Warning if no exercises generated for a day
            for day, exercises in program.items():
                if not exercises:
                    logging.warning(f"No exercises generated for day {day}!")
            is_valid, errors = self.validator.validate_program({'weekly_plan': program})
            if not is_valid:
                raise ValueError(f"Program is not valid: {', '.join(errors)}")
            return program
        except Exception as e:
            raise ValueError(f"Error in generating program: {str(e)}")
            
    def _should_deload(self, week: int) -> bool:
        """
        Check if a deload is needed
        
        Args:
            week: Week number
            
        Returns:
            bool: Whether a deload is needed
        """
        # Deload every 4-6 weeks
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
                    logging.warning(f"Invalid item in day {day} for deload: {exercise}")
                    continue
                # Convert model to dict only at this point
                deload_exercise = {
                    'exercise_id': exercise.id,
                    'exercise_name': exercise.name,
                    'type': getattr(exercise, 'type', 'compound'),
                    'muscle_group': exercise.primary_muscles[0] if exercise.primary_muscles else 'full_body',
                    'sets': max(1, getattr(exercise, 'sets', 3) // 2),
                    'reps': '12-15',
                    'rest_seconds': getattr(exercise, 'rest_seconds', 60),
                    'intensity': getattr(exercise, 'intensity', 0.7),
                    'notes': getattr(exercise, 'notes', '')
                }
                deload_exercises.append(deload_exercise)
            if not deload_exercises:
                logging.warning(f"No deload exercise generated for day {day}!")
            deload_program[day] = deload_exercises
        return deload_program
        
    def _generate_base_program(self, week: int) -> Dict:
        """
        Generate a base program
        
        Args:
            week: Week number
            
        Returns:
            Dict: Base program
        """
        raise NotImplementedError("This method must be implemented in child classes")
        
    def _adjust_volume_and_intensity(self, program: Dict, week: int) -> Dict:
        """
        Adjust volume and intensity of exercises
        
        Args:
            program: Workout program
            week: Week number
            
        Returns:
            Dict: Adjusted program
        """
        adjusted_program = {}
        for day, exercises in program.items():
            adjusted_exercises = []
            for exercise in exercises:
                if not hasattr(exercise, 'id'):
                    logging.warning(f"Invalid item in day {day}: {exercise}")
                    continue
                # Only model
                adjusted_exercises.append(exercise)
            if not adjusted_exercises:
                logging.warning(f"No adjusted exercise generated for day {day}!")
            adjusted_program[day] = adjusted_exercises
        return adjusted_program
        
    def _calculate_intensity(self, exercise: Dict, week: int) -> float:
        """
        Calculate exercise intensity
        
        Args:
            exercise: Exercise information
            week: Week number
            
        Returns:
            float: Exercise intensity (0-1)
        """
        base_intensity = 0.7  # Base intensity
        
        # Gradual intensity increase
        week_factor = min(1.0, 0.7 + (week * 0.05))
        
        # Adjust based on exercise type
        type_factor = {
            'compound': 1.0,
            'isolation': 0.8,
            'accessory': 0.6
        }.get(exercise['type'], 0.7)
        
        return min(1.0, base_intensity * week_factor * type_factor)
        
    def _add_mobility_exercises(self, program: Dict) -> Dict:
        """
        Add mobility exercises
        
        Args:
            program: Workout program
            
        Returns:
            Dict: Program with mobility exercises
        """
        for day, exercises in program.items():
            if not exercises:
                logging.warning(f"No main exercise for adding mobility in day {day}!")
                continue
            # Assuming get_mobility_exercises returns a model
            warmup = self.exercise_selector.get_mobility_exercises(
                target_areas=exercises[0].primary_muscles if hasattr(exercises[0], 'primary_muscles') else [],
                exercise_type='warmup'
            )
            cooldown = self.exercise_selector.get_mobility_exercises(
                target_areas=exercises[-1].primary_muscles if hasattr(exercises[-1], 'primary_muscles') else [],
                exercise_type='cooldown'
            )
            program[day] = list(warmup) + list(exercises) + list(cooldown)
        return program
        
    def get_exercise_alternatives(self, exercise):
        """
        Get exercise alternatives
        
        Args:
            exercise: Original exercise
            
        Returns:
            List[Dict]: List of exercise alternatives
        """
        exercise_id = exercise['exercise_id'] if isinstance(exercise, dict) else exercise.id
        return self.exercise_selector.get_alternative_exercises(
            exercise_id,
            self.user.physical_limitations
        )
        
    def _validate_exercise_balance(self, exercises: List[Dict]) -> Tuple[bool, List[str]]:
        """
        Check exercise balance
        
        Args:
            exercises: List of exercises
            
        Returns:
            Tuple[bool, List[str]]: (Validity, List of errors)
        """
        errors = []
        exercise_counts = {}
        
        # Count exercises of each type
        for exercise in exercises:
            ex_type = exercise['type']
            exercise_counts[ex_type] = exercise_counts.get(ex_type, 0) + 1
            
        # Check limits
        for ex_type, count in exercise_counts.items():
            limits = self.EXERCISE_LIMITS.get(ex_type, {'min': 2, 'max': 5})
            if count < limits['min']:
                errors.append(f"Number of {ex_type} exercises is less than the allowed limit")
            elif count > limits['max']:
                errors.append(f"Number of {ex_type} exercises exceeds the allowed limit")
                
        return len(errors) == 0, errors

    def _prioritize_days_by_recovery(self, available_days: List[str]) -> List[str]:
        """Prioritize days based on recovery score"""
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
        """Calculate recovery score for a day"""
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
        return score

    def _check_recovery_for_day(self, day: str, primary_muscles: List[str] = None) -> bool:
        """Check recovery for a training day"""
        from accounts.services.date_converter import convert_day_to_date
        training_date = convert_day_to_date(day, datetime.now())
        if primary_muscles is None and hasattr(self, 'MUSCLE_GROUPS'):
            # تلاش برای استخراج عضلات اصلی از MUSCLE_GROUPS
            primary_muscles = []
            if isinstance(self.MUSCLE_GROUPS, dict):
                for group in self.MUSCLE_GROUPS.values():
                    if isinstance(group, dict) and 'primary' in group:
                        primary_muscles.extend(group['primary'])
                    elif isinstance(group, list):
                        primary_muscles.extend(group)
        if not primary_muscles:
            primary_muscles = ['full_body']
        return all(self.recovery_manager.can_train(muscle, training_date) for muscle in primary_muscles)

    def _find_next_available_day(self, available_days: List[str], primary_muscles: List[str] = None) -> str:
        """Find the next available day for training"""
        for day in available_days:
            if self._check_recovery_for_day(day, primary_muscles):
                return day
        return available_days[0]  # fallback if none found
    
    def _get_warmup(self, split_type: str, warmup_map: dict) -> list:
        """Generic warmup getter for a split type using a provided mapping."""
        return warmup_map.get(split_type, [])

    def _get_cooldown(self, split_type: str, cooldown_map: dict) -> list:
        """Generic cooldown getter for a split type using a provided mapping."""
        return cooldown_map.get(split_type, [])

    def _add_warmup_cooldown(self, program: Dict, warmup_map: dict, cooldown_map: dict, day_sequence: list):
        """Add warmup and cooldown to each session using provided mappings and sequence."""
        for idx, (day, exercises) in enumerate(program['weekly_plan'].items()):
            split_type = day_sequence[idx % len(day_sequence)]
            warmup = self._get_warmup(split_type, warmup_map)
            cooldown = self._get_cooldown(split_type, cooldown_map)
            program['weekly_plan'][day] = warmup + exercises + cooldown

    def _validate_volume(self, program: Dict):
        """Validate total program volume and auto-adjust if needed."""
        total_volume = sum(self.volume_manager.muscle_volume.values())
        volume_range = self.volume_manager.VOLUME_TARGETS[self.user.goal][self.settings.experience_level]
        target = (volume_range[0] + volume_range[1]) / 2
        if total_volume < target * 0.8:
            self._adjust_program(program, increase=True)
        elif total_volume > target * 1.2:
            self._adjust_program(program, increase=False)

    def _adjust_program(self, program: Dict, increase: bool):
        """Adjust all sets in the program up or down by 10%."""
        adjustment_factor = 1.1 if increase else 0.9
        for day in program['weekly_plan']:
            for exercise in program['weekly_plan'][day]:
                if isinstance(exercise, dict) and 'sets' in exercise:
                    exercise['sets'] = math.ceil(exercise['sets'] * adjustment_factor)
