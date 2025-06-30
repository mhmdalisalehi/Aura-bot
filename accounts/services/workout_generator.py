from typing import Dict, List
from datetime import datetime
from accounts.models import UserProfile, TrainingSettings
from exercises.models import Exercise
from .exercise_selector import ExerciseSelector
from .volume_manager import WorkoutVolumeManager
from .recovery_manager import RecoveryManager
from .workout_utils import (
    calculate_rest_time,
    calculate_intensity,
    get_exercise_notes
)
from .workout_validator import WorkoutValidator
from .base_manager import BaseWorkoutManager

from logger_util import get_logger
logger = get_logger('workout_generator', 'logs/workout_generator.log')

class WorkoutGenerator(BaseWorkoutManager):
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        super().__init__(user, settings)
        logger.info(f"WorkoutGenerator initialized for user {user.id}")

    def generate_workout(self, target_muscles: List[str], week: int) -> Dict:
        logger.info(f"Generating workout for muscles: {target_muscles}, week: {week}")
        try:
            if not self.recovery_manager.can_train(target_muscles, datetime.now()):
                logger.error(f"Target muscles {target_muscles} need rest.")
                raise ValueError("Target muscles need rest")
            exercises = self.exercise_selector.get_exercises(
                target_muscles,
                week
            )
            logger.info(f"Selected exercises: {exercises}")
            workout = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'target_muscles': target_muscles,
                'exercises': []
            }
            # Add General Warmup at the start
            for exercise_tuple in exercises.get('main', []):
                exercise = exercise_tuple[0] if isinstance(exercise_tuple, tuple) else exercise_tuple
                logger.info(f"Preparing exercise data for: {getattr(exercise, 'name', str(exercise))}")
                exercise_data = self._prepare_exercise_data(exercise, week)
                workout['exercises'].append(exercise_data)
                if hasattr(exercise, 'id'):
                    self.exercise_selector.update_history(exercise.id, week)
            # Add Full Body Stretch at the end

            is_valid, errors = self.validator.validate_workout(workout)
            logger.info(f"Workout validation result: {is_valid}, errors: {errors}")
            if not is_valid:
                logger.info(f"Workout is not valid: {errors}")
                raise ValueError(f"Workout is not valid: {', '.join(errors)}")
            logger.info(f"Generated workout: {workout}")
            return workout
        except Exception as e:
            logger.info(f"Exception in generate_workout: {str(e)}")
            raise ValueError(f"Error in generating workout: {str(e)}")

    def _prepare_exercise_data(self, exercise: Exercise, week: int) -> Dict:
        logger.info(f"_prepare_exercise_data for: {getattr(exercise, 'name', str(exercise))}, week: {week}")
        try:
            volume = self.volume_manager.adjust_volume(
                exercise.primary_muscles[0],
                week
            )
            logger.info(f"Volume for {exercise.name}: {volume}")
            rest_time = calculate_rest_time(exercise, self.settings.experience_level)
            intensity = calculate_intensity(exercise, volume['sets'], volume['reps'])
            notes = get_exercise_notes(exercise, self.settings.experience_level)
            logger.info(f"rest_time: {rest_time}, intensity: {intensity}, notes: {notes}")
            return {
                'exercise_id': exercise.id,
                'exercise_name': exercise.name,
                'type': exercise.type,
                'muscle_group': exercise.primary_muscles[0],
                'sets': volume['sets'],
                'reps': volume['reps'],
                'rest_seconds': rest_time,
                'intensity': intensity,
                'notes': notes
            }
        except Exception as e:
            logger.info(f"Exception in _prepare_exercise_data: {str(e)}")
            raise ValueError(f"Error in preparing exercise data: {str(e)}")

    def _format_mobility_exercises(self, exercises: List, exercise_type: str) -> List[Dict]:
        """فرمت‌بندی تمرینات موبیلیتی با مدیریت خطا"""
        try:
            formatted = []
            for item in exercises:
                exercise = item[0] if isinstance(item, tuple) else item
                formatted.append({
                    'exercise_id': exercise.id,
                    'exercise_name': exercise.name,
                    'type': exercise_type,
                    'duration_seconds': self._get_mobility_duration(exercise_type),
                    'notes': self._get_mobility_notes(exercise_type)
                })
            return formatted
        except Exception as e:
            logger.info(f"Error in formatting mobility exercises: {str(e)}")
            raise ValueError(f"Error in formatting mobility exercises: {str(e)}")

    def _get_mobility_duration(self, exercise_type: str) -> int:
        """دریافت مدت زمان تمرینات موبیلیتی"""
        return 60 if exercise_type == 'warmup' else 45

    def _get_mobility_notes(self, exercise_type: str) -> str:
        """دریافت نکات تمرینات موبیلیتی"""
        return "روی فرم صحیح تمرکز کنید" if exercise_type == 'warmup' else "کشش ملایم و آرام"

    def adjust_workout(self, workout: Dict, feedback: Dict) -> Dict:
        """تنظیم تمرین بر اساس بازخورد"""
        if 'volume_feedback' in feedback:
            self._adjust_volume(workout, feedback['volume_feedback'])
        if 'intensity_feedback' in feedback:
            self._adjust_intensity(workout, feedback['intensity_feedback'])
        if 'sequence_feedback' in feedback:
            self._adjust_sequence(workout, feedback['sequence_feedback'])
        logger.info("Workout adjusted based on feedback")
        return workout

    def _adjust_volume(self, workout: Dict, feedback: Dict):
        """تنظیم حجم تمرینات"""
        for exercise in workout['exercises']:
            muscle = exercise['muscle_group']
            if muscle in feedback:
                if 'sets' in feedback[muscle]:
                    exercise['sets'] = feedback[muscle]['sets']
                if 'reps' in feedback[muscle]:
                    exercise['reps'] = feedback[muscle]['reps']

    def _adjust_intensity(self, workout: Dict, feedback: Dict):
        """تنظیم شدت تمرینات"""
        for exercise in workout['exercises']:
            if exercise['exercise_id'] in feedback:
                if 'rest_seconds' in feedback[exercise['exercise_id']]:
                    exercise['rest_seconds'] = feedback[exercise['exercise_id']]['rest_seconds']

    def _adjust_sequence(self, workout: Dict, feedback: Dict):
        """تنظیم توالی تمرینات"""
        if 'new_sequence' in feedback:
            workout['exercises'] = [
                workout['exercises'][i] for i in feedback['new_sequence']
            ]