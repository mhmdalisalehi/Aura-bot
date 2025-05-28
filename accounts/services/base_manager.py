from accounts.models import UserProfile, TrainingSettings
from .exercise_selector import ExerciseSelector
from .volume_manager import WorkoutVolumeManager
from .recovery_manager import RecoveryManager
from .mobility_manager import MobilityManager
from .workout_validator import WorkoutValidator

class BaseWorkoutManager:
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        self._initialize_managers()
        self._validate_managers()

    def _initialize_managers(self):
        try:
            self.exercise_selector = ExerciseSelector(self.user, self.settings)
            self.volume_manager = WorkoutVolumeManager(self.user, self.settings)
            self.recovery_manager = RecoveryManager(self.user, self.settings)
            self.mobility_manager = MobilityManager(self.user, self.settings)
            self.validator = WorkoutValidator(self.user, self.settings)
            self.validator.set_managers(
                self.volume_manager,
                self.recovery_manager,
                self.mobility_manager,
                self.exercise_selector
            )
        except Exception as e:
            raise ValueError(f"Error in initializing managers: {str(e)}")

    def _validate_managers(self):
        if not all([
            self.exercise_selector,
            self.volume_manager,
            self.recovery_manager,
            self.mobility_manager,
            self.validator
        ]):
            raise ValueError("Some managers are not initialized")
