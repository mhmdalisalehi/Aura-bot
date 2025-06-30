from typing import Dict, List, Tuple
from exercises.models import Exercise
from accounts.models import UserProfile, TrainingSettings

from logger_util import get_logger
logger = get_logger('volume_manager', 'logs/volume_manager.log')

class WorkoutVolumeManager:
    """
    مدیریت حرفه‌ای حجم تمرینات
    - تنظیم حجم بر اساس هدف، تجربه و وضعیت فیزیکی
    - مدیریت پیشرفت تدریجی
    - تنظیم حجم بر اساس نوع تمرین
    - مدیریت ریکاوری و خستگی
    """

    VOLUME_TARGETS = {
        'muscle_gain': {
            'beginner': (10, 12),
            'intermediate': (12, 16),
            'expert': (14, 20)
        },
        'strength': {
            'beginner': (8, 10),
            'intermediate': (10, 14),
            'expert': (12, 16)
        },
        'weight_loss': {
            'beginner': (12, 15),
            'intermediate': (15, 18),
            'expert': (18, 22)
        },
        'endurance': {
            'beginner': (15, 18),
            'intermediate': (18, 22),
            'expert': (20, 25)
        }
    }

    REP_RANGES = {
        'muscle_gain': {
            'compound': '6-8',
            'isolation': '8-12',
            'accessory': '12-15'
        },
        'strength': {
            'compound': '3-5',
            'isolation': '6-8',
            'accessory': '8-10'
        },
        'weight_loss': {
            'compound': '8-12',
            'isolation': '12-15',
            'accessory': '15-20'
        },
        'endurance': {
            'compound': '12-15',
            'isolation': '15-20',
            'accessory': '20-25'
        }
    }

    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        self.muscle_volume = {}
        self.weekly_volume = {}
        self.progression_week = 1
        self.deload_week = False
        logger.info(f"WorkoutVolumeManager initialized for user {user.id}")

    def adjust_volume(self, muscle: str, week: int, exercise_type: str = 'compound') -> Dict:
        logger.info(f"Adjusting volume for muscle={muscle}, week={week}, exercise_type={exercise_type}")
        if self._should_deload(week):
            logger.info(f"Deload week detected for week={week}, muscle={muscle}")
            return self._get_deload_volume(muscle, exercise_type)
        base_volume = self._get_base_volume(muscle, exercise_type)
        logger.info(f"Base volume for {muscle}: {base_volume}")
        adjusted_volume = self._adjust_for_experience(base_volume)
        logger.info(f"After experience adjustment: {adjusted_volume}")
        adjusted_volume = self._adjust_for_recovery(adjusted_volume, muscle)
        logger.info(f"After recovery adjustment: {adjusted_volume}")
        adjusted_volume = self._adjust_for_progression(adjusted_volume, week)
        logger.info(f"After progression adjustment: {adjusted_volume}")
        adjusted_volume = self._adjust_for_exercise_type(adjusted_volume, exercise_type)
        logger.info(f"After exercise type adjustment: {adjusted_volume}")
        adjusted_volume = self._adjust_for_goal(adjusted_volume, exercise_type)
        logger.info(f"After goal adjustment: {adjusted_volume}")
        self._update_volume_history(muscle, adjusted_volume)
        logger.info(f"Final adjusted volume for {muscle}: {adjusted_volume}")
        return adjusted_volume

    def _get_base_volume(self, muscle: str, exercise_type: str) -> Dict:
        base_volumes = {
            'chest': {'compound': 4, 'isolation': 3, 'accessory': 2},
            'back': {'compound': 4, 'isolation': 3, 'accessory': 2},
            'shoulders': {'compound': 3, 'isolation': 2, 'accessory': 2},
            'biceps': {'compound': 2, 'isolation': 3, 'accessory': 2},
            'triceps': {'compound': 2, 'isolation': 3, 'accessory': 2},
            'quadriceps': {'compound': 4, 'isolation': 3, 'accessory': 2},
            'hamstrings': {'compound': 3, 'isolation': 2, 'accessory': 2},
            'calves': {'compound': 2, 'isolation': 3, 'accessory': 1},
            'abs': {'compound': 2, 'isolation': 3, 'accessory': 2}
        }
        sets = base_volumes.get(muscle, {'compound': 3, 'isolation': 2, 'accessory': 2})[exercise_type]
        if self.user.goal == 'strength':
            sets = int(sets * 0.8)
        elif self.user.goal == 'endurance':
            sets = int(sets * 1.2)
        logger.info(f"Base sets for {muscle} ({exercise_type}): {sets}")
        return {
            'sets': sets,
            'reps': self.REP_RANGES[self.user.goal][exercise_type]
        }

    def _adjust_for_experience(self, volume: Dict) -> Dict:
        experience_multiplier = {
            'beginner': 0.7,
            'intermediate': 1.0,
            'expert': 1.2
        }.get(self.settings.experience_level, 1.0)
        logger.info(f"Experience multiplier: {experience_multiplier}")
        return {
            'sets': int(volume['sets'] * experience_multiplier),
            'reps': volume['reps']
        }

    def _adjust_for_recovery(self, volume: Dict, muscle: str) -> Dict:
        if muscle in self.muscle_volume:
            current_volume = self.muscle_volume[muscle]
            threshold = self._get_volume_threshold(muscle)
            logger.info(f"Current volume for {muscle}: {current_volume}, threshold: {threshold}")
            if current_volume > threshold * 1.2:
                logger.info(f"Volume for {muscle} is very high, reducing by 30%")
                return {
                    'sets': int(volume['sets'] * 0.7),
                    'reps': volume['reps']
                }
            elif current_volume > threshold:
                logger.info(f"Volume for {muscle} is high, reducing by 20%")
                return {
                    'sets': int(volume['sets'] * 0.8),
                    'reps': volume['reps']
                }
        return volume

    def _adjust_for_progression(self, volume: Dict, week: int) -> Dict:
        if week > self.progression_week:
            self.progression_week = week
            if week % 4 == 0:
                logger.info(f"Increasing sets for progression at week {week}")
                return {
                    'sets': volume['sets'] + 1,
                    'reps': volume['reps']
                }
            elif week % 2 == 0:
                logger.info(f"Increasing intensity for progression at week {week}")
                return {
                    'sets': volume['sets'],
                    'reps': self._increase_intensity(volume['reps'])
                }
        return volume

    def _adjust_for_exercise_type(self, volume: Dict, exercise_type: str) -> Dict:
        type_multiplier = {
            'compound': 1.2,
            'isolation': 1.0,
            'accessory': 0.8
        }.get(exercise_type, 1.0)
        logger.info(f"Type multiplier for {exercise_type}: {type_multiplier}")
        return {
            'sets': int(volume['sets'] * type_multiplier),
            'reps': volume['reps']
        }

    def _adjust_for_goal(self, volume: Dict, exercise_type: str) -> Dict:
        goal_adjustments = {
            'muscle_gain': {
                'compound': {'sets': 1.1, 'reps': '8-12'},
                'isolation': {'sets': 1.0, 'reps': '10-15'},
                'accessory': {'sets': 0.9, 'reps': '12-15'}
            },
            'strength': {
                'compound': {'sets': 1.2, 'reps': '4-6'},
                'isolation': {'sets': 0.8, 'reps': '6-8'},
                'accessory': {'sets': 0.7, 'reps': '8-10'}
            },
            'weight_loss': {
                'compound': {'sets': 1.0, 'reps': '12-15'},
                'isolation': {'sets': 0.9, 'reps': '15-20'},
                'accessory': {'sets': 0.8, 'reps': '20-25'}
            },
            'endurance': {
                'compound': {'sets': 0.9, 'reps': '15-20'},
                'isolation': {'sets': 0.8, 'reps': '20-25'},
                'accessory': {'sets': 0.7, 'reps': '25-30'}
            }
        }
        adjustment = goal_adjustments.get(self.user.goal, {}).get(exercise_type, {})
        logger.info(f"Goal adjustment for {self.user.goal} {exercise_type}: {adjustment}")
        return {
            'sets': int(volume['sets'] * adjustment.get('sets', 1.0)),
            'reps': adjustment.get('reps', volume['reps'])
        }

    def _should_deload(self, week: int) -> bool:
        if week % 8 == 0:
            self.deload_week = True
            logger.info(f"Deload week (every 8 weeks): week={week}")
            return True
        if self._check_fatigue():
            self.deload_week = True
            logger.info("Deload triggered due to high fatigue/volume.")
            return True
        self.deload_week = False
        return False

    def _get_deload_volume(self, muscle: str, exercise_type: str) -> Dict:
        base_volume = self._get_base_volume(muscle, exercise_type)
        logger.info(f"Deload volume for {muscle}: sets reduced by 50%")
        return {
            'sets': int(base_volume['sets'] * 0.5),
            'reps': self._decrease_intensity(base_volume['reps'])
        }

    def _check_fatigue(self) -> bool:
        if not self.muscle_volume:
            return False
        total_volume = sum(self.muscle_volume.values())
        max_volume = sum(
            self.VOLUME_TARGETS[self.user.goal][self.settings.experience_level]
        ) * 1.2
        logger.info(f"Total volume: {total_volume}, Max allowed: {max_volume}")
        return total_volume > max_volume

    def _get_volume_threshold(self, muscle: str) -> int:
        thresholds = {
            'chest': 20,
            'back': 20,
            'shoulders': 15,
            'biceps': 12,
            'triceps': 12,
            'quadriceps': 20,
            'hamstrings': 15,
            'calves': 12,
            'abs': 12
        }
        return thresholds.get(muscle, 15)

    def _increase_intensity(self, rep_range: str) -> str:
        if '-' in rep_range:
            min_rep, max_rep = map(int, rep_range.split('-'))
            new_range = f"{max(min_rep-1, 1)}-{max(max_rep-1, 1)}"
            logger.info(f"Increasing intensity: {rep_range} -> {new_range}")
            return new_range
        return rep_range

    def _decrease_intensity(self, rep_range: str) -> str:
        if '-' in rep_range:
            min_rep, max_rep = map(int, rep_range.split('-'))
            new_range = f"{min_rep+2}-{max_rep+2}"
            logger.info(f"Decreasing intensity: {rep_range} -> {new_range}")
            return new_range
        return rep_range

    def _update_volume_history(self, muscle: str, volume: Dict):
        if muscle not in self.muscle_volume:
            self.muscle_volume[muscle] = 0
        if isinstance(volume['reps'], str) and '-' in volume['reps']:
            min_rep, max_rep = map(int, volume['reps'].split('-'))
            avg_reps = (min_rep + max_rep) / 2
        else:
            avg_reps = int(volume['reps'])
        self.muscle_volume[muscle] += volume['sets'] * avg_reps
        logger.info(f"Updated muscle_volume[{muscle}] = {self.muscle_volume[muscle]}")

    def reset_weekly_volume(self):
        logger.info("Resetting weekly volume and deload if needed.")
        self.weekly_volume = {}
        if self.deload_week:
            self.muscle_volume = {k: v * 0.5 for k, v in self.muscle_volume.items()}
            self.deload_week = False