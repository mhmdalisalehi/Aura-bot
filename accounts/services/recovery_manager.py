from typing import List, Dict, Optional
from django.utils import timezone
from datetime import timedelta
from accounts.models import UserProfile, TrainingSettings
from exercises.models import Exercise

from logger_util import get_logger
logger = get_logger('recovery_manager', 'logs/recovery_manager.log')

class RecoveryManager:
    """
    مدیریت حرفه‌ای ریکاوری
    - تنظیم زمان ریکاوری بر اساس شدت، سن، جنسیت و محدودیت‌ها
    - مدیریت ریکاوری فعال و غیرفعال
    - همگام‌سازی با سایر بخش‌های برنامه
    """

    BASE_RECOVERY_DAYS = {
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

    AGE_MULTIPLIERS = {
        '18-25': 0.8,
        '26-35': 1.0,
        '36-45': 1.2,
        '46+': 1.5
    }

    GENDER_MULTIPLIERS = {
        'male': 1.0,
        'female': 0.9
    }

    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        self.last_trained = {}
        self.recovery_status = {}
        self.fatigue_level = {}
        self.active_recovery_exercises = {}
        logger.info(f"RecoveryManager initialized for user {user.id}")

    def can_train(self, muscles: List[str], current_time: timezone.datetime) -> bool:
        logger.info(f"Checking if user can train muscles={muscles} at {current_time}")
        for muscle in muscles:
            if not self._check_recovery(muscle, current_time):
                logger.info(f"Cannot train muscle={muscle} (not recovered)")
                return False
        logger.info("All muscles are ready for training.")
        return True

    def _check_recovery(self, muscle: str, current_time: timezone.datetime) -> bool:
        if muscle not in self.last_trained:
            logger.debug(f"Muscle {muscle} has no training history, considered recovered.")
            return True
        recovery_time = self._calculate_recovery_time(muscle)
        last_training = self.last_trained[muscle][-1]
        if (current_time - last_training).days < recovery_time:
            logger.debug(f"Muscle {muscle} not recovered: days since last={ (current_time - last_training).days }, needed={recovery_time}")
            return False
        if self.fatigue_level.get(muscle, 0) > 0.8:
            logger.debug(f"Muscle {muscle} fatigue too high: {self.fatigue_level.get(muscle, 0)}")
            return False
        logger.debug(f"Muscle {muscle} is recovered.")
        return True

    def _calculate_recovery_time(self, muscle: str) -> int:
        base_time = self.BASE_RECOVERY_DAYS.get(muscle, 2)
        age_multiplier = self._get_age_multiplier()
        gender_multiplier = self.GENDER_MULTIPLIERS.get(self.user.gender, 1.0)
        intensity_multiplier = self._get_intensity_multiplier(muscle)
        injury_multiplier = self._get_injury_multiplier(muscle)
        recovery_time = base_time * age_multiplier * gender_multiplier * intensity_multiplier * injury_multiplier
        logger.debug(f"Calculated recovery time for muscle={muscle}: base={base_time}, age_mult={age_multiplier}, gender_mult={gender_multiplier}, intensity_mult={intensity_multiplier}, injury_mult={injury_multiplier} => {recovery_time}")
        return max(1, min(int(recovery_time), 7))

    def _get_age_multiplier(self) -> float:
        age = self.user.age
        if age <= 25:
            return self.AGE_MULTIPLIERS['18-25']
        elif age <= 35:
            return self.AGE_MULTIPLIERS['26-35']
        elif age <= 45:
            return self.AGE_MULTIPLIERS['36-45']
        else:
            return self.AGE_MULTIPLIERS['46+']

    def _get_intensity_multiplier(self, muscle: str) -> float:
        if muscle not in self.last_trained:
            return 1.0
        last_volume = self._get_last_volume(muscle)
        if last_volume > 0.8:
            logger.debug(f"Muscle {muscle} last volume high: {last_volume}")
            return 1.3
        elif last_volume > 0.5:
            logger.debug(f"Muscle {muscle} last volume moderate: {last_volume}")
            return 1.1
        return 1.0

    def _get_injury_multiplier(self, muscle: str) -> float:
        if not self.user.physical_limitations:
            return 1.0
        related_injuries = self._get_related_injuries(muscle)
        if related_injuries:
            logger.debug(f"Muscle {muscle} has related injuries: {related_injuries}")
            return 1.5
        return 1.0

    def _get_related_injuries(self, muscle: str) -> List[str]:
        muscle_injury_map = {
            'chest': ['shoulder_injury', 'chest_injury'],
            'back': ['back_injury', 'spine_injury'],
            'shoulders': ['shoulder_injury', 'rotator_cuff'],
            'quadriceps': ['knee_injury', 'quad_injury'],
            'hamstrings': ['hamstring_injury', 'knee_injury'],
            # ... سایر عضلات
        }
        related_injuries = muscle_injury_map.get(muscle, [])
        found = [inj for inj in related_injuries if inj in self.user.physical_limitations]
        logger.debug(f"Related injuries for muscle={muscle}: {found}")
        return found

    def get_recovery_status(self, muscle: str) -> Dict:
        if muscle not in self.last_trained:
            logger.info(f"Muscle {muscle} has no training history, considered fully recovered.")
            return {
                'can_train': True,
                'days_since_last_training': None,
                'recovery_time_needed': self._calculate_recovery_time(muscle),
                'fatigue_level': 0,
                'active_recovery_recommended': False
            }
        last_training = self.last_trained[muscle][-1]
        days_since = (timezone.now() - last_training).days
        recovery_time = self._calculate_recovery_time(muscle)
        fatigue = self.fatigue_level.get(muscle, 0)
        can_train = days_since >= recovery_time and fatigue <= 0.8
        logger.info(f"Recovery status for muscle={muscle}: can_train={can_train}, days_since={days_since}, recovery_needed={recovery_time}, fatigue={fatigue}")
        return {
            'can_train': can_train,
            'days_since_last_training': days_since,
            'recovery_time_needed': recovery_time,
            'fatigue_level': fatigue,
            'active_recovery_recommended': self._should_recommend_active_recovery(muscle)
        }

    def _should_recommend_active_recovery(self, muscle: str) -> bool:
        if muscle not in self.last_trained:
            return False
        days_since = (timezone.now() - self.last_trained[muscle][-1]).days
        fatigue = self.fatigue_level.get(muscle, 0)
        recommend = 0.5 <= days_since <= 1.5 and fatigue > 0.3
        logger.debug(f"Should recommend active recovery for muscle={muscle}: {recommend}")
        return recommend

    def get_active_recovery_exercises(self, muscle: str) -> List[Exercise]:
        if not self._should_recommend_active_recovery(muscle):
            logger.info(f"No active recovery recommended for muscle={muscle}")
            return []
        logger.info(f"Getting active recovery exercises for muscle={muscle}")
        exercises = Exercise.objects.filter(
            category__in=['mobility', 'stretching'],
            primary_muscles__contains=[muscle],
            level='beginner'
        ).order_by('?')[:3]
        logger.debug(f"Found {len(exercises)} active recovery exercises for muscle={muscle}")
        return exercises

    def update_training_status(self, muscle: str, volume: float, intensity: float):
        logger.info(f"Updating training status for muscle={muscle}, volume={volume}, intensity={intensity}")
        if muscle not in self.last_trained:
            self.last_trained[muscle] = []
        self.last_trained[muscle].append(timezone.now())
        self.fatigue_level[muscle] = min(1.0, volume * intensity)
        self._adjust_recovery_time(muscle, intensity)
        logger.debug(f"Updated last_trained: {self.last_trained[muscle]}")
        logger.debug(f"Updated fatigue_level: {self.fatigue_level[muscle]}")

    def _adjust_recovery_time(self, muscle: str, intensity: float):
        if intensity > 0.8:
            self.BASE_RECOVERY_DAYS[muscle] = min(
                self.BASE_RECOVERY_DAYS.get(muscle, 2) + 1,
                4
            )
            logger.debug(f"Increased BASE_RECOVERY_DAYS for muscle={muscle} due to high intensity.")
        elif intensity < 0.5:
            self.BASE_RECOVERY_DAYS[muscle] = max(
                self.BASE_RECOVERY_DAYS.get(muscle, 2) - 1,
                1
            )
            logger.debug(f"Decreased BASE_RECOVERY_DAYS for muscle={muscle} due to low intensity.")

    def _get_last_volume(self, muscle: str) -> float:
        if muscle not in self.last_trained:
            return 0.0
        # This should be fetched from a VolumeManager; returning a mock value for now.
        logger.debug(f"Returning mock last volume for muscle={muscle}")
        return 0.7

    def reset_recovery_times(self):
        logger.info("Resetting all recovery times and fatigue levels.")
        self.last_trained = {}
        self.fatigue_level = {}
        self.recovery_status = {}
        self.active_recovery_exercises = {}