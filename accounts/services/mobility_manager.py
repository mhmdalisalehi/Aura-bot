# from typing import List, Optional
# from exercises.models import Exercise
# from accounts.models import UserProfile, TrainingSettings
# from django.db.models import Q

# from logger_util import get_logger
# logger = get_logger('mobility_manager', 'logs/mobility_manager.log')

# class MobilityManager:
#     """
#     مدیریت حرفه‌ای موبیلیتی و انعطاف‌پذیری
#     - تنظیم تمرینات بر اساس نوع (گرم کردن، سرد کردن، ریکاوری فعال)
#     - مدیریت محدودیت‌های فیزیکی و آسیب‌ها
#     - همگام‌سازی با سایر بخش‌های برنامه
#     """

#     MOBILITY_CATEGORIES = {
#         'warmup': ['dynamic_stretching', 'mobility', 'activation'],
#         'cooldown': ['static_stretching', 'foam_rolling', 'mobility'],
#         'active_recovery': ['light_cardio', 'mobility', 'dynamic_stretching']
#     }

#     SPLIT_SPECIFIC_EXERCISES = {
#         'push': {
#             'warmup': ['shoulder_mobility', 'chest_opening', 'wrist_mobility'],
#             'cooldown': ['chest_stretch', 'shoulder_stretch', 'tricep_stretch']
#         },
#         'pull': {
#             'warmup': ['back_mobility', 'lat_activation', 'scapular_mobility'],
#             'cooldown': ['back_stretch', 'lat_stretch', 'bicep_stretch']
#         },
#         'legs': {
#             'warmup': ['hip_mobility', 'ankle_mobility', 'glute_activation'],
#             'cooldown': ['quad_stretch', 'hamstring_stretch', 'calf_stretch']
#         },
#         'full_body': {
#             'warmup': ['full_body_mobility', 'joint_mobility', 'core_activation'],
#             'cooldown': ['full_body_stretch', 'foam_rolling', 'breathing']
#         }
#     }

#     AGE_MULTIPLIERS = {
#         '18-25': 1.2,
#         '26-35': 1.0,
#         '36-45': 0.8,
#         '46+': 0.6
#     }

#     def __init__(self, user: UserProfile, settings: TrainingSettings):
#         self.user = user
#         self.settings = settings
#         self.mobility_history = {}
#         self.mobility_status = {}
#         self.recovery_needs = {}
#         logger.info(f"MobilityManager initialized for user {user.id}")

#     def get_mobility_exercises(
#         self,
#         target_areas: List[str] = None,
#         exercise_type: str = 'warmup',
#         split_type: str = None
#     ) -> List[Exercise]:
#         logger.info(f"Selecting mobility exercises: target_areas={target_areas}, exercise_type={exercise_type}, split_type={split_type}")
#         categories = self.MOBILITY_CATEGORIES.get(exercise_type, ['mobility'])
#         qs = Exercise.objects.filter(category__in=categories)
#         exercises = [
#             ex for ex in qs
#             if (
#                 (not split_type or (split_type in self.SPLIT_SPECIFIC_EXERCISES and ex.name in self.SPLIT_SPECIFIC_EXERCISES[split_type][exercise_type]))
#             ) and (
#                 not target_areas or
#                 (ex.primary_muscles and any(m in ex.primary_muscles for m in target_areas)) or
#                 (ex.secondary_muscles and any(m in ex.secondary_muscles for m in target_areas))
#             ) and (
#                 ex.level <= self._get_max_difficulty()
#             )
#         ]
#         logger.debug(f"Found {len(exercises)} mobility exercises after initial filter")
#         exercises = self._filter_by_limitations(exercises)
#         logger.debug(f"After limitations filter: {len(exercises)} exercises")
#         exercises = self._adjust_for_demographics(exercises)
#         logger.debug(f"After demographics filter: {len(exercises)} exercises")
#         exercises = self._prioritize_exercises(exercises, target_areas)
#         logger.debug(f"After prioritization: {len(exercises)} exercises")
#         if not exercises:
#             logger.warning(f"No mobility exercises found for {target_areas} and type {exercise_type}")
#         else:
#             logger.info(f"Returning {len(exercises)} mobility exercises for {target_areas} and type {exercise_type}")
#         return list(exercises)

#     def get_warmup_exercises(self, split_type: str) -> List[Exercise]:
#         logger.info(f"Getting warmup exercises for split_type={split_type}")
#         target_areas = self._get_target_areas_for_split(split_type)
#         return self.get_mobility_exercises(
#             target_areas=target_areas,
#             exercise_type='warmup',
#             split_type=split_type
#         )

#     def get_cooldown_exercises(self, split_type: str) -> List[Exercise]:
#         logger.info(f"Getting cooldown exercises for split_type={split_type}")
#         target_areas = self._get_target_areas_for_split(split_type)
#         return self.get_mobility_exercises(
#             target_areas=target_areas,
#             exercise_type='cooldown',
#             split_type=split_type
#         )

#     def get_active_recovery_exercises(self, target_areas: List[str]) -> List[Exercise]:
#         logger.info(f"Getting active recovery exercises for target_areas={target_areas}")
#         return self.get_mobility_exercises(
#             target_areas=target_areas,
#             exercise_type='active_recovery'
#         )

#     def _get_target_areas_for_split(self, split_type: str) -> List[str]:
#         areas = {
#             'push': ['shoulders', 'chest', 'triceps'],
#             'pull': ['back', 'biceps', 'shoulders'],
#             'legs': ['quadriceps', 'hamstrings', 'glutes', 'calves'],
#             'full_body': ['shoulders', 'hips', 'spine', 'core']
#         }
#         result = areas.get(split_type, ['shoulders', 'hips', 'spine'])
#         logger.debug(f"Target areas for split_type={split_type}: {result}")
#         return result

#     def _get_max_difficulty(self) -> str:
#         level = {
#             'beginner': 'beginner',
#             'intermediate': 'intermediate',
#             'expert': 'expert'
#         }.get(self.settings.experience_level, 'beginner')
#         logger.debug(f"Max difficulty for experience_level={self.settings.experience_level}: {level}")
#         return level

#     def _filter_by_limitations(self, exercises: List[Exercise]) -> List[Exercise]:
#         if not self.user.physical_limitations:
#             logger.debug("No physical limitations for user.")
#             return exercises
#         logger.debug(f"Filtering exercises by physical limitations: {self.user.physical_limitations}")
#         return exercises.exclude(
#             contraindications__overlap=self.user.physical_limitations
#         )

#     def _adjust_for_demographics(self, exercises: List[Exercise]) -> List[Exercise]:
#         age_multiplier = self._get_age_multiplier()
#         logger.debug(f"Age multiplier for user age={self.user.age}: {age_multiplier}")
#         if age_multiplier < 1.0:
#             exercises = exercises.exclude(
#                 category__in=['plyometrics', 'dynamic_stretching']
#             )
#             logger.debug("Excluded plyometrics and dynamic_stretching for older user.")
#         if self.user.gender == 'female':
#             exercises = exercises.filter(
#                 Q(category__in=['mobility', 'stretching']) |
#                 Q(level='beginner')
#             )
#             logger.debug("Filtered exercises for female user.")
#         return exercises

#     def _get_age_multiplier(self) -> float:
#         age = self.user.age
#         if age <= 25:
#             return self.AGE_MULTIPLIERS['18-25']
#         elif age <= 35:
#             return self.AGE_MULTIPLIERS['26-35']
#         elif age <= 45:
#             return self.AGE_MULTIPLIERS['36-45']
#         else:
#             return self.AGE_MULTIPLIERS['46+']

#     def _prioritize_exercises(self, exercises: List[Exercise], target_areas: List[str]) -> List[Exercise]:
#         if not exercises:
#             logger.debug("No exercises to prioritize.")
#             return []
#         for exercise in exercises:
#             score = 1.0
#             if exercise.id in self.mobility_history:
#                 days_since = self.mobility_history[exercise.id]
#                 score *= (1 + days_since * 0.1)
#             for muscle in exercise.primary_muscles:
#                 if muscle in self.recovery_needs:
#                     score *= (1 + self.recovery_needs[muscle] * 0.2)
#             if target_areas:
#                 overlap = len(set(exercise.primary_muscles) & set(target_areas))
#                 score *= (1 + overlap * 0.3)
#             exercise.priority_score = score
#             logger.debug(f"Exercise {exercise.name} (id={exercise.id}) priority_score={score}")
#         sorted_exercises = sorted(exercises, key=lambda x: x.priority_score, reverse=True)
#         logger.debug(f"Exercises sorted by priority_score.")
#         return sorted_exercises

#     def update_mobility_status(self, exercise_id: int, target_areas: List[str]):
#         logger.info(f"Updating mobility status for exercise_id={exercise_id}, target_areas={target_areas}")
#         self.mobility_history[exercise_id] = 0
#         for ex_id in self.mobility_history:
#             if ex_id != exercise_id:
#                 self.mobility_history[ex_id] += 1
#         for area in target_areas:
#             if area in self.mobility_status:
#                 self.mobility_status[area] = min(1.0, self.mobility_status[area] + 0.1)
#             else:
#                 self.mobility_status[area] = 0.1
#         logger.debug(f"Mobility history: {self.mobility_history}")
#         logger.debug(f"Mobility status: {self.mobility_status}")

#     def update_recovery_needs(self, muscle: str, need_level: float):
#         logger.info(f"Updating recovery need for muscle={muscle}, need_level={need_level}")
#         self.recovery_needs[muscle] = min(1.0, need_level)
#         logger.debug(f"Recovery needs: {self.recovery_needs}")

#     def reset_mobility_status(self):
#         logger.info("Resetting mobility status/history/recovery needs.")
#         self.mobility_history = {}
#         self.mobility_status = {}
#         self.recovery_needs = {}