from accounts.models import UserProfile, TrainingSettings
from .exercise_selector import ExerciseSelector
from .volume_manager import WorkoutVolumeManager
from .recovery_manager import RecoveryManager
from .workout_validator import WorkoutValidator

from logger_util import get_logger

logger = get_logger('base_manager', 'logs/base_manager.log')

class BaseWorkoutManager:
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        logger.info(f"Initializing BaseWorkoutManager for user {self.user} with settings {self.settings}")
        self._initialize_managers()
        self._validate_managers()

    def _initialize_managers(self):
        try:
            logger.info("Initializing managers...")
            self.exercise_selector = ExerciseSelector(self.user, self.settings)
            self.volume_manager = WorkoutVolumeManager(self.user, self.settings)
            self.recovery_manager = RecoveryManager(self.user, self.settings)
            self.validator = WorkoutValidator(self.user, self.settings)
            self.validator.set_managers(
                self.volume_manager,
                self.recovery_manager,
                self.exercise_selector
            )
            logger.info("All managers initialized successfully.")
        except Exception as e:
            logger.error(f"Error in initializing managers: {str(e)}")
            raise ValueError(f"Error in initializing managers: {str(e)}")

    def _validate_managers(self):
        logger.info("Validating managers...")
        if not all([
            self.exercise_selector,
            self.volume_manager,
            self.recovery_manager,
            self.validator
        ]):
            logger.error("Some managers are not initialized")
            raise ValueError("Some managers are not initialized")
        logger.info("All managers validated successfully.")