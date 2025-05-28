from typing import List, Dict, Tuple
import random
from exercises.models import Exercise
from accounts.models import UserProfile, TrainingSettings, InjuryExerciseClassification
from django.db.models import Q
import logging

class ExerciseScorer:
    """سیستم امتیازدهی هوشمند به تمرینات با وزن‌های حرفه‌ای"""
    
    # وزن‌های امتیازدهی (مجموع = 10)
    WEIGHTS = {
        'safety': 3.0,        # ایمنی (آسیب‌ها و محدودیت‌ها)
        'effectiveness': 2.5, # اثربخشی (هدف و تیپ بدنی)
        'experience': 1.5,    # تجربه و سطح
        'demographics': 1.0,  # سن و جنسیت
        'time': 1.0,         # زمان و کارایی
        'location': 0.5,     # محل تمرین
        'history': 0.5       # تاریخچه تمرینات
    }
    
    @staticmethod
    def calculate_exercise_score(
        exercise: Exercise,
        user: UserProfile,
        settings: TrainingSettings,
        week: int,
        last_trained: int = None
    ) -> float:
        """محاسبه امتیاز نهایی با وزن‌های حرفه‌ای"""
        scores = {
            'safety': ExerciseScorer._safety_score(exercise, settings.injuries),
            'effectiveness': ExerciseScorer._effectiveness_score(exercise, user),
            'experience': ExerciseScorer._experience_score(exercise, settings.experience_level),
            'demographics': ExerciseScorer._demographic_score(exercise, user.age, user.gender),
            'time': ExerciseScorer._time_efficiency_score(exercise, settings.training_duration_minutes),
            'location': ExerciseScorer._location_score(exercise, settings.preferred_location),
            'history': ExerciseScorer._history_score(week, last_trained) if last_trained is not None else 1.0
        }
        
        # محاسبه امتیاز نهایی با وزن‌ها
        final_score = sum(
            score * ExerciseScorer.WEIGHTS[category]
            for category, score in scores.items()
        )
        
        # نرمال‌سازی امتیاز نهایی (تقسیم بر مجموع وزن‌ها)
        return final_score / sum(ExerciseScorer.WEIGHTS.values())
    
    @staticmethod
    def _safety_score(exercise: Exercise, injuries: List[str]) -> float:
        """
        محاسبه امتیاز ایمنی (وزن: 3.0)
        - بررسی آسیب‌ها
        - اگر تمرین ناایمن باشد، امتیاز کل صفر می‌شود
        """
        if not injuries:
            return 1.0
        injury_classifications = InjuryExerciseClassification.objects.filter(
            exercise=exercise,
            injury__in=injuries
        )
        if injury_classifications.filter(classification='avoid').exists():
            return 0.0  # تمرین ممنوع است
        if injury_classifications.filter(classification='safe').exists():
            return 0.8  # جایگزین امن
        return 1.0
    
    @staticmethod
    def _effectiveness_score(exercise: Exercise, user: UserProfile) -> float:
        """
        محاسبه امتیاز اثربخشی (وزن: 2.5)
        - ترکیب هدف و تیپ بدنی
        """
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
        
        # محاسبه امتیاز هدف
        goal_score = goal_scores.get(user.goal, {}).get(exercise.category, 1.0)
        
        # محاسبه امتیاز تیپ بدنی
        body_type_score = body_type_scores.get(user.body_type, {}).get(exercise.category, 1.0)
        
        # ترکیب امتیازها با وزن بیشتر برای هدف
        return (goal_score * 0.6) + (body_type_score * 0.4)
    
    @staticmethod
    def _experience_score(exercise: Exercise, experience_level: str) -> float:
        """
        محاسبه امتیاز تجربه (وزن: 1.5)
        - تطابق سطح تمرین با تجربه کاربر
        """
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
        """
        محاسبه امتیاز دموگرافیک (وزن: 1.0)
        - تطابق با سن و جنسیت
        """
        score = 1.0
        
        # تنظیم بر اساس سن
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
                
        # تنظیم بر اساس جنسیت
        if gender == 'female':
            if exercise.category == 'powerlifting':
                score *= 0.8
            elif exercise.category in ['stretching', 'mobility']:
                score *= 1.2
            elif exercise.category == 'cardio':
                score *= 1.1
                
        return score
    
    @staticmethod
    def _time_efficiency_score(exercise: Exercise, available_minutes: int) -> float:
        """
        محاسبه امتیاز کارایی زمانی (وزن: 1.0)
        - تطابق با زمان در دسترس
        """
        if available_minutes < 30:  # زمان خیلی کم
            if exercise.mechanic == 'compound':
                return 1.4
            return 0.6
        elif available_minutes < 45:  # زمان کم
            if exercise.mechanic == 'compound':
                return 1.2
            elif exercise.mechanic == 'isolation':
                return 0.8
            return 1.0
        elif available_minutes < 60:  # زمان متوسط
            if exercise.mechanic == 'compound':
                return 1.1
            elif exercise.mechanic == 'isolation':
                return 1.0
            return 1.2
        else:  # زمان کافی
            if exercise.mechanic == 'isolation':
                return 1.2
            return 1.0
    
    @staticmethod
    def _location_score(exercise: Exercise, preferred_location: str) -> float:
        """
        محاسبه امتیاز محل تمرین (وزن: 0.5)
        - تطابق با تجهیزات و فضای موجود
        """
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
        """
        محاسبه امتیاز تاریخچه (وزن: 0.5)
        - تنوع در تمرینات
        """
        weeks_since_last = current_week - last_trained
        if weeks_since_last <= 1:
            return 0.4  # تمرینات اخیر امتیاز کمتری دارند
        elif weeks_since_last <= 2:
            return 0.8  # تمرینات با فاصله مناسب
        elif weeks_since_last <= 3:
            return 1.2  # تمرینات با فاصله زیاد
        return 1.0  # فاصله خیلی زیاد

class ExerciseSelector:
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        self.exercise_history = {}
        self.scorer = ExerciseScorer()
        self.current_week = 1

    def get_exercises(
        self,
        target_muscles: List[str],
        week: int,
        count: int = 5,
        include_complementary: bool = True,
        include_warmup: bool = True,
        include_cooldown: bool = True
    ) -> Dict[str, List[Exercise]]:
        """
        دریافت تمرینات مناسب برای عضلات هدف با ساختار حرفه‌ای
        فقط مدل‌ها در زنجیره
        """
        workout_structure = {}
        if include_warmup:
            workout_structure['warmup'] = [ex for ex, _ in self._get_warmup_exercises(target_muscles, week)]
        main_exercises = self._get_main_exercises(target_muscles, week)
        scored_main = self._score_and_select_exercises(main_exercises, week, count)
        workout_structure['main'] = [ex for ex, _ in scored_main]
        if include_complementary:
            workout_structure['complementary'] = [ex for ex, _ in self._get_complementary_exercises([ex for ex, _ in scored_main], week)]
            workout_structure['stabilization'] = [ex for ex, _ in self._get_stabilization_exercises(target_muscles, week)]
        if include_cooldown:
            workout_structure['cooldown'] = [ex for ex, _ in self._get_cooldown_exercises(target_muscles, week)]
        return workout_structure

    def _get_warmup_exercises(self, target_muscles: List[str], week: int) -> List[Tuple[Exercise, float]]:
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
        return self._score_and_select_exercises(warmup_exercises, week, count=3)

    def _get_cooldown_exercises(self, target_muscles: List[str], week: int) -> List[Tuple[Exercise, float]]:
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
        return self._score_and_select_exercises(cooldown_exercises, week, count=3)

    def _get_stabilization_exercises(self, target_muscles: List[str], week: int) -> List[Tuple[Exercise, float]]:
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
        return self._score_and_select_exercises(stabilization_exercises, week, count=2)

    def _score_and_select_exercises(
        self,
        exercises: List[Exercise],
        week: int,
        count: int
    ) -> List[Tuple[Exercise, float]]:
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
        return scored_exercises[:count]

    def _distribute_exercises(
        self,
        exercises: List[Tuple[Exercise, float]]
    ) -> List[Tuple[Exercise, float]]:
        """توزیع تمرینات ترکیبی و ایزوله
        
        Args:
            exercises: لیست تمرینات با امتیاز
            
        Returns:
            لیست توزیع شده تمرینات
        """
        compound_exercises = []
        isolation_exercises = []
        
        for exercise, score in exercises:
            if exercise.mechanic == 'compound':
                compound_exercises.append((exercise, score))
            else:
                isolation_exercises.append((exercise, score))
            
        # اولویت با تمرینات ترکیبی
        return compound_exercises + isolation_exercises
    
    def _get_main_exercises(self, target_muscles: List[str], week: int):
        """
        انتخاب تمرینات اصلی با فیلترهای حرفه‌ای
        - تمرینات ترکیبی برای مبتدیان
        - ترکیب مناسب تمرینات بر اساس هدف
        """
        # کوئری ساده فقط روی عضلات هدف
        qs = Exercise.objects.all()
        exercises = [
            ex for ex in qs
            if (
                (ex.primary_muscles and any(m in ex.primary_muscles for m in target_muscles)) or
                (ex.secondary_muscles and any(m in ex.secondary_muscles for m in target_muscles))
            )
        ]
        # فیلتر تجهیزات
        if self.settings.available_equipment:
            exercises = [ex for ex in exercises if ex.equipment in self.settings.available_equipment]
        # فیلتر سطح تجربه
        if self.settings.experience_level == 'beginner':
            exercises = [ex for ex in exercises if ex.level == 'beginner' or (ex.level == 'intermediate' and ex.mechanic == 'compound')]
        elif self.settings.experience_level == 'intermediate':
            exercises = [ex for ex in exercises if ex.level in ['beginner', 'intermediate', 'expert']]
        # فیلتر بر اساس هدف
        if self.user.goal:
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
        return list(exercises)
    
    def _get_complementary_exercises(
        self,
        main_exercises: List,
        week: int,
        count: int = 2
    ) -> List[Tuple[Exercise, float]]:
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
        scored = self._score_and_select_exercises(complementary, week, count)
        return scored
    
    def update_history(self, exercise_id: int, week: int):
        """به‌روزرسانی تاریخچه تمرینات
        
        Args:
            exercise_id: شناسه تمرین
            week: شماره هفته
        """
        self.exercise_history[exercise_id] = week

    def get_alternative_exercises(self, exercise_id: int, physical_limitations=None) -> List[Exercise]:
        """
        دریافت لیست تمرینات جایگزین مناسب
        - تمرینات با همان گروه عضلانی
        - تمرینات با سطح دشواری مشابه
        - تمرینات سازگار با محدودیت‌های فیزیکی
        """
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
            # مقداردهی current_week اگر به صورت داینامیک ست شده باشد
            week = getattr(self, 'current_week', 1)
            scored_alternatives = self._score_and_select_exercises(
                alternatives,
                week,
                count=5
            )
            return [ex[0] for ex in scored_alternatives]
        except Exercise.DoesNotExist:
            return []
        except Exception as e:
            print(f"خطا در دریافت تمرینات جایگزین: {str(e)}")
            return []

    def get_mobility_exercises(self, target_areas: list = None, exercise_type: str = 'warmup', split_type: str = None) -> list:
        exercises = super().get_mobility_exercises(target_areas, exercise_type, split_type)
        if not exercises:
            logging.warning(f"هیچ تمرین موبیلیتی برای {target_areas} و نوع {exercise_type} پیدا نشد!")
        return exercises