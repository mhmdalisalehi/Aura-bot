from typing import List, Dict, Tuple
import random
from exercises.models import Exercise
from accounts.models import UserProfile, TrainingSettings, InjuryExerciseClassification
from django.db.models import Q

from logger_util import get_logger
logger = get_logger('exercise_selector', 'logs/exercise_selector.log')

MUSCLE_NAME_MAP = {
    "back": ["middle back", "lats", "lower back", "traps"],
    "upper_chest": ["chest"],
    "lateral_delts": ["shoulders"],
    "rear_delts": ["shoulders"],
    "outer_quads": ["quadriceps"],
    "hamstring_insertion": ["hamstrings"],
    "glute_medius": ["glutes"],
    # Add more mappings as needed
}

def map_muscle_names(muscles: list) -> list:
    mapped = []
    for m in muscles:
        mapped.extend(MUSCLE_NAME_MAP.get(m, [m]))
    logger.debug(f"Mapped muscle names: {muscles} -> {mapped}")
    return mapped

class ExerciseScorer:
    """سیستم امتیازدهی هوشمند به تمرینات با وزن‌های حرفه‌ای"""

    WEIGHTS = {
        'safety': 3.0,
        'effectiveness': 2.5,
        'experience': 1.5,
        'demographics': 1.0,
        'time': 1.0,
        'location': 0.5,
        'history': 0.5
    }

    @staticmethod
    def calculate_exercise_score(
        exercise: Exercise,
        user: UserProfile,
        settings: TrainingSettings,
        week: int,
        last_trained: int = None
    ) -> float:
        logger.debug(f"Scoring exercise {exercise.name} (id={exercise.id}) for user {user.id}, week {week}")
        scores = {
            'safety': ExerciseScorer._safety_score(exercise, settings.injuries),
            'effectiveness': ExerciseScorer._effectiveness_score(exercise, user),
            'experience': ExerciseScorer._experience_score(exercise, settings.experience_level),
            'demographics': ExerciseScorer._demographic_score(exercise, user.age, user.gender),
            'time': ExerciseScorer._time_efficiency_score(exercise, settings.training_duration_minutes),
            'location': ExerciseScorer._location_score(exercise, settings.preferred_location),
            'history': ExerciseScorer._history_score(week, last_trained) if last_trained is not None else 1.0
        }
        logger.debug(f"Score breakdown for {exercise.name}: {scores}")
        final_score = sum(
            score * ExerciseScorer.WEIGHTS[category]
            for category, score in scores.items()
        )
        logger.debug(f"Final score for {exercise.name}: {final_score}")
        return final_score / sum(ExerciseScorer.WEIGHTS.values())

    @staticmethod
    def _safety_score(exercise: Exercise, injuries: List[str]) -> float:
        if not injuries:
            return 1.0
        injury_classifications = InjuryExerciseClassification.objects.filter(
            exercise=exercise,
            injury__in=injuries
        )
        if injury_classifications.filter(classification='avoid').exists():
            logger.info(f"Exercise {exercise.name} is marked as 'avoid' for injuries {injuries}")
            return 0.0
        if injury_classifications.filter(classification='safe').exists():
            logger.info(f"Exercise {exercise.name} is marked as 'safe' for injuries {injuries}")
            return 0.8
        return 1.0

    @staticmethod
    def _effectiveness_score(exercise: Exercise, user: UserProfile) -> float:
        goal_scores = {
            'muscle_gain': {
                'compound': 1.3,
                'isolation': 1.2,
                'strength': 1.0,
                'hypertrophy': 1.4
            },
            'strength': {
                'compound': 1.5,
                'strength': 1.4,
                'powerlifting': 1.3,
                'isolation': 0.7
            },
            'weight_loss': {
                'compound': 1.4,
                'cardio': 1.3,
                'metabolic': 1.2,
                'isolation': 0.8
            },
            'endurance': {
                'cardio': 1.5,
                'compound': 1.2,
                'endurance': 1.4,
                'isolation': 0.6
            }
        }
        body_type_scores = {
            'ectomorph': {
                'compound': 1.4,
                'strength': 1.3,
                'hypertrophy': 1.2,
                'isolation': 0.8
            },
            'mesomorph': {
                'compound': 1.2,
                'strength': 1.1,
                'hypertrophy': 1.3,
                'isolation': 1.0
            },
            'endomorph': {
                'compound': 1.1,
                'strength': 0.9,
                'hypertrophy': 1.2,
                'isolation': 1.3
            }
        }
        goal_score = goal_scores.get(user.goal, {}).get(exercise.category, 1.0)
        body_type_score = body_type_scores.get(user.body_type, {}).get(exercise.category, 1.0)
        score = (goal_score * 0.6) + (body_type_score * 0.4)
        logger.debug(f"Effectiveness score for {exercise.name}: {score}")
        return score

    @staticmethod
    def _experience_score(exercise: Exercise, experience_level: str) -> float:
        if experience_level == 'beginner':
            if exercise.level == 'beginner':
                return 1.5
            elif exercise.level == 'intermediate':
                return 0.7
            return 0.3
        elif experience_level == 'intermediate':
            if exercise.level == 'beginner':
                return 0.8
            elif exercise.level == 'intermediate':
                return 1.3
            return 0.6
        else:  # expert
            if exercise.level == 'beginner':
                return 0.6
            elif exercise.level == 'intermediate':
                return 0.9
            return 1.2

    @staticmethod
    def _demographic_score(exercise: Exercise, age: int, gender: str) -> float:
        score = 1.0
        if age > 50:
            if exercise.category in ['plyometrics', 'strongman', 'crossfit']:
                score *= 0.4
            elif exercise.mechanic == 'compound':
                score *= 0.7
            elif exercise.category == 'stretching':
                score *= 1.2
        elif age > 35:
            if exercise.category in ['plyometrics', 'strongman']:
                score *= 0.7
            elif exercise.mechanic == 'compound':
                score *= 0.9
        if gender == 'female':
            if exercise.category == 'powerlifting':
                score *= 0.8
            elif exercise.category in ['stretching', 'mobility']:
                score *= 1.2
            elif exercise.category == 'cardio':
                score *= 1.1
        logger.debug(f"Demographic score for {exercise.name}: {score}")
        return score

    @staticmethod
    def _time_efficiency_score(exercise: Exercise, available_minutes: int) -> float:
        if available_minutes < 30:
            if exercise.mechanic == 'compound':
                return 1.4
            return 0.6
        elif available_minutes < 45:
            if exercise.mechanic == 'compound':
                return 1.2
            elif exercise.mechanic == 'isolation':
                return 0.8
            return 1.0
        elif available_minutes < 60:
            if exercise.mechanic == 'compound':
                return 1.1
            elif exercise.mechanic == 'isolation':
                return 1.0
            return 1.2
        else:
            if exercise.mechanic == 'isolation':
                return 1.2
            return 1.0

    @staticmethod
    def _location_score(exercise: Exercise, preferred_location: str) -> float:
        location_equipment_map = {
            'home': {
                'primary': ['body', 'dumbbell', 'bands', 'kettlebells'],
                'secondary': ['resistance_bands', 'medicine_ball', 'foam_roll']
            },
            'gym': {
                'primary': ['machine', 'cable', 'barbell', 'body', 'dumbbell'],
                'secondary': ['kettlebells', 'medicine_ball', 'exercise_ball']
            },
            'outdoor': {
                'primary': ['body', 'bands'],
                'secondary': ['resistance_bands', 'medicine_ball']
            }
        }
        location_data = location_equipment_map.get(preferred_location, {})
        primary_equipment = location_data.get('primary', [])
        secondary_equipment = location_data.get('secondary', [])
        if exercise.equipment in primary_equipment:
            return 1.2
        elif exercise.equipment in secondary_equipment:
            return 1.0
        return 0.7

    @staticmethod
    def _history_score(current_week: int, last_trained: int) -> float:
        weeks_since_last = current_week - last_trained
        if weeks_since_last <= 1:
            return 0.4
        elif weeks_since_last <= 2:
            return 0.8
        elif weeks_since_last <= 3:
            return 1.2
        return 1.0

class ExerciseSelector:
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        self.exercise_history = {}
        self.scorer = ExerciseScorer()
        self.current_week = 1
        logger.info(f"ExerciseSelector initialized for user {user.id}")

    def get_exercises(
        self,
        target_muscles: List[str],
        week: int,
        count: int = 5,
        include_complementary: bool = True,
        include_warmup: bool = True,
        include_cooldown: bool = True
    ) -> Dict[str, List[Exercise]]:
        logger.info(f"Selecting exercises for target_muscles={target_muscles}, week={week}, count={count}")
        workout_structure = {}
        if include_warmup:
            logger.debug("Selecting warmup exercises")
            workout_structure['warmup'] = [ex for ex, _ in self._get_warmup_exercises(target_muscles, week)]
        main_exercises = self._get_main_exercises(target_muscles, week)
        logger.debug(f"Found {len(main_exercises)} main exercises before scoring")
        scored_main = self._score_and_select_exercises(main_exercises, week, count)
        logger.info(f"Selected main exercises: {[ex.name for ex, _ in scored_main]}")
        workout_structure['main'] = [ex for ex, _ in scored_main]
        if include_complementary:
            logger.debug("Selecting complementary and stabilization exercises")
            workout_structure['complementary'] = [ex for ex, _ in self._get_complementary_exercises([ex for ex, _ in scored_main], week)]
            workout_structure['stabilization'] = [ex for ex, _ in self._get_stabilization_exercises(target_muscles, week)]
        if include_cooldown:
            logger.debug("Selecting cooldown exercises")
            workout_structure['cooldown'] = [ex for ex, _ in self._get_cooldown_exercises(target_muscles, week)]
        logger.info(f"Workout structure keys: {list(workout_structure.keys())}")
        return workout_structure

    def _get_warmup_exercises(self, target_muscles: List[str], week: int) -> List[Tuple[Exercise, float]]:
        logger.debug(f"Getting warmup exercises for {target_muscles}, week {week}")
        qs = Exercise.objects.filter(level='beginner')
        warmup_exercises = [
            ex for ex in qs
            if (
                (ex.category in ['cardio', 'plyometrics']) or
                (ex.category == 'stretching') or
                (ex.category == 'weighted_bodyweight' and ex.equipment == 'body')
            ) and (
                not target_muscles or
                (ex.primary_muscles and any(m in ex.primary_muscles for m in target_muscles)) or
                (ex.secondary_muscles and any(m in ex.secondary_muscles for m in target_muscles))
            )
        ]
        logger.debug(f"Found {len(warmup_exercises)} warmup exercises")
        return self._score_and_select_exercises(warmup_exercises, week, count=3)

    def _get_cooldown_exercises(self, target_muscles: List[str], week: int) -> List[Tuple[Exercise, float]]:
        logger.debug(f"Getting cooldown exercises for {target_muscles}, week {week}")
        qs = Exercise.objects.filter(level='beginner')
        cooldown_exercises = [
            ex for ex in qs
            if (
                (ex.category == 'stretching') or
                (ex.category == 'weighted_bodyweight' and ex.equipment == 'body') or
                (ex.category == 'strength' and ex.mechanic == 'isolation')
            ) and (
                not target_muscles or
                (ex.primary_muscles and any(m in ex.primary_muscles for m in target_muscles)) or
                (ex.secondary_muscles and any(m in ex.secondary_muscles for m in target_muscles))
            )
        ]
        logger.debug(f"Found {len(cooldown_exercises)} cooldown exercises")
        return self._score_and_select_exercises(cooldown_exercises, week, count=3)

    def _get_stabilization_exercises(self, target_muscles: List[str], week: int) -> List[Tuple[Exercise, float]]:
        logger.debug(f"Getting stabilization exercises for {target_muscles}, week {week}")
        qs = Exercise.objects.filter(level__in=['beginner', 'intermediate'])
        stabilization_exercises = [
            ex for ex in qs
            if (
                (ex.primary_muscles and any(m in ['abs', 'core', 'lower_back'] for m in ex.primary_muscles)) or
                (ex.category == 'weighted_bodyweight' and ex.equipment == 'body') or
                (ex.category == 'strength' and ex.mechanic == 'isolation')
            ) and (
                not self.settings.available_equipment or ex.equipment in self.settings.available_equipment
            )
        ]
        logger.debug(f"Found {len(stabilization_exercises)} stabilization exercises")
        return self._score_and_select_exercises(stabilization_exercises, week, count=2)

    def _score_and_select_exercises(
        self,
        exercises: List[Exercise],
        week: int,
        count: int
    ) -> List[Tuple[Exercise, float]]:
        logger.debug(f"Scoring {len(exercises)} exercises for week {week}, selecting top {count}")
        scored_exercises = []
        for exercise in exercises:
            last_trained = self.exercise_history.get(exercise.id)
            score = self.scorer.calculate_exercise_score(
                exercise,
                self.user,
                self.settings,
                week,
                last_trained
            )
            scored_exercises.append((exercise, score))
        scored_exercises.sort(key=lambda x: x[1], reverse=True)
        logger.debug(f"Top scored exercises: {[ex.name for ex, _ in scored_exercises[:count]]}")
        return scored_exercises[:count]

    def _distribute_exercises(
        self,
        exercises: List[Tuple[Exercise, float]]
    ) -> List[Tuple[Exercise, float]]:
        logger.debug("Distributing compound and isolation exercises")
        compound_exercises = []
        isolation_exercises = []
        for exercise, score in exercises:
            if exercise.mechanic == 'compound':
                compound_exercises.append((exercise, score))
            else:
                isolation_exercises.append((exercise, score))
        logger.debug(f"Compound: {len(compound_exercises)}, Isolation: {len(isolation_exercises)}")
        return compound_exercises + isolation_exercises

    def _get_main_exercises(self, target_muscles: List[str], week: int):
        logger.debug(f"Getting main exercises for {target_muscles}, week {week}")
        qs = Exercise.objects.all()
        exercises = [
            ex for ex in qs
            if (
                (ex.primary_muscles and any(m in ex.primary_muscles for m in target_muscles)) or
                (ex.secondary_muscles and any(m in ex.secondary_muscles for m in target_muscles))
            )
        ]
        logger.debug(f"Main exercises after muscle filter: {len(exercises)}")
        if self.settings.available_equipment:
            exercises = [ex for ex in exercises if ex.equipment in self.settings.available_equipment]
            logger.debug(f"Main exercises after equipment filter: {len(exercises)}")
        if self.settings.experience_level == 'beginner':
            exercises = [ex for ex in exercises if ex.level == 'beginner' or (ex.level == 'intermediate' and ex.mechanic == 'compound')]
        elif self.settings.experience_level == 'intermediate':
            exercises = [ex for ex in exercises if ex.level in ['beginner', 'intermediate', 'expert']]
        logger.debug(f"Main exercises after experience filter: {len(exercises)}")
        if self.user.goal:
            before_goal = len(exercises)
            if self.user.goal == 'muscle_gain':
                exercises = [ex for ex in exercises if (
                    ex.category in ['strength', 'powerlifting', 'weighted_bodyweight'] or
                    ex.mechanic == 'compound' or
                    (ex.mechanic == 'isolation' and ex.category == 'strength')
                )]
            elif self.user.goal == 'strength':
                exercises = [ex for ex in exercises if (
                    ex.category in ['strength', 'powerlifting', 'weighted_bodyweight', 'olympic_weightlifting'] or
                    ex.mechanic == 'compound'
                )]
            elif self.user.goal == 'weight_loss':
                exercises = [ex for ex in exercises if (
                    ex.category in ['strength', 'crossfit', 'weighted_bodyweight', 'cardio', 'plyometrics'] or
                    ex.mechanic == 'compound'
                )]
            elif self.user.goal == 'endurance':
                exercises = [ex for ex in exercises if (
                    ex.category in ['cardio', 'plyometrics', 'strength', 'crossfit', 'weighted_bodyweight'] or
                    ex.mechanic == 'compound'
                )]
            logger.debug(f"Main exercises after goal filter ({self.user.goal}): {before_goal} -> {len(exercises)}")
        return list(exercises)

    def _get_complementary_exercises(
        self,
        main_exercises: List,
        week: int,
        count: int = 2
    ) -> List[Tuple[Exercise, float]]:
        logger.debug(f"Getting complementary exercises for main_exercises (count={len(main_exercises)}), week {week}")
        complementary_muscles = set()
        for exercise in main_exercises:
            ex = exercise
            if hasattr(self, 'exercise_to_dict'):
                ex = self.exercise_to_dict(ex, 'complementary')
            if ex.secondary_muscles:
                complementary_muscles.update(ex.secondary_muscles)
            if ex.force == 'push':
                complementary_muscles.update(['back', 'biceps', 'rear_deltoids'])
            elif ex.force == 'pull':
                complementary_muscles.update(['chest', 'triceps', 'front_deltoids'])
            elif ex.force == 'static':
                complementary_muscles.update(['core', 'lower_back'])
        if not complementary_muscles:
            logger.info("No complementary muscles found, skipping complementary exercises.")
            return []
        qs = Exercise.objects.all()
        complementary = [
            ex for ex in qs
            if (
                (ex.primary_muscles and any(m in ex.primary_muscles for m in complementary_muscles)) or
                (ex.category in ['strength', 'weighted_bodyweight'] and ex.mechanic == 'isolation') or
                (ex.category == 'plyometrics' and ex.level in ['beginner', 'intermediate'])
            ) and (
                not self.settings.available_equipment or ex.equipment in self.settings.available_equipment
            )
        ]
        logger.debug(f"Found {len(complementary)} complementary exercises")
        scored = self._score_and_select_exercises(complementary, week, count)
        logger.info(f"Selected complementary exercises: {[ex.name for ex, _ in scored]}")
        return scored

    def update_history(self, exercise_id: int, week: int):
        self.exercise_history[exercise_id] = week
        logger.info(f"Updated exercise history: exercise_id={exercise_id}, week={week}")

    def get_alternative_exercises(self, exercise_id: int, physical_limitations=None) -> List[Exercise]:
        logger.info(f"Getting alternative exercises for exercise_id={exercise_id}")
        try:
            main_exercise = Exercise.objects.get(id=exercise_id)
            qs = Exercise.objects.filter(level=main_exercise.level)
            alternatives = [
                ex for ex in qs
                if (
                    (ex.primary_muscles and any(m in ex.primary_muscles for m in main_exercise.primary_muscles)) or
                    (ex.secondary_muscles and any(m in ex.secondary_muscles for m in main_exercise.secondary_muscles))) and (
                    not self.settings.available_equipment or ex.equipment in self.settings.available_equipment
                ) and (
                    not physical_limitations or not any(injury in (ex.injuries or []) for injury in physical_limitations)
                )
            ]
            week = getattr(self, 'current_week', 1)
            scored_alternatives = self._score_and_select_exercises(
                alternatives,
                week,
                count=5
            )
            logger.info(f"Found {len(scored_alternatives)} alternative exercises for exercise_id={exercise_id}")
            return [ex[0] for ex in scored_alternatives]
        except Exercise.DoesNotExist:
            logger.warning(f"Exercise with id={exercise_id} does not exist.")
            return []
        except Exception as e:
            logger.error(f"Error getting alternative exercises for exercise_id={exercise_id}: {str(e)}")
            return []

    def get_mobility_exercises(self, target_areas: list = None, exercise_type: str = 'warmup', split_type: str = None) -> list:
        logger.info(f"Getting mobility exercises for target_areas={target_areas}, exercise_type={exercise_type}, split_type={split_type}")
        exercises = super().get_mobility_exercises(target_areas, exercise_type, split_type)
        if not exercises:
            logger.warning(f"No mobility exercises found for {target_areas} and type {exercise_type}")
        else:
            logger.info(f"Found {len(exercises)} mobility exercises for {target_areas} and type {exercise_type}")
        return exercises