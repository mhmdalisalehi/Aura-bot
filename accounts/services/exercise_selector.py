from typing import List, Dict, Tuple
import random
from exercises.models import Exercise
from accounts.models import UserProfile, TrainingSettings, InjuryExerciseClassification
from django.db.models import Q

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
            'safety': ExerciseScorer._safety_score(exercise, settings.injuries, user.physical_limitations),
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
    def _safety_score(exercise: Exercise, injuries: List[str], limitations: List[str]) -> float:
        """
        محاسبه امتیاز ایمنی (وزن: 3.0)
        - بررسی آسیب‌ها و محدودیت‌های فیزیکی
        - اگر تمرین ناایمن باشد، امتیاز کل صفر می‌شود
        """
        if not injuries and not limitations:
            return 1.0
            
        # بررسی آسیب‌ها
        injury_classifications = InjuryExerciseClassification.objects.filter(
            exercise=exercise,
            injury__in=injuries
        )
        
        if injury_classifications.filter(classification='avoid').exists():
            return 0.0  # تمرین ممنوع است
            
        if injury_classifications.filter(classification='safe').exists():
            return 0.8  # جایگزین امن
            
        # بررسی محدودیت‌های فیزیکی
        if limitations and exercise.contraindications:
            if any(lim in exercise.contraindications for lim in limitations):
                return 0.0
                
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
        
    def get_exercises(
        self,
        target_muscles: List[str],
        week: int,
        count: int = 5,
        include_complementary: bool = True,
        include_warmup: bool = True,
        include_cooldown: bool = True
    ) -> Dict[str, List[Tuple[Exercise, float]]]:
        """
        دریافت تمرینات مناسب برای عضلات هدف با ساختار حرفه‌ای
        شامل: گرم‌کننده، تمرینات اصلی، تمرینات مکمل، و سردکننده
        """
        workout_structure = {}
        
        # 1. تمرینات گرم‌کننده
        if include_warmup:
            workout_structure['warmup'] = self._get_warmup_exercises(target_muscles, week)
        
        # 2. تمرینات اصلی
        main_exercises = self._get_main_exercises(target_muscles, week)
        scored_main = self._score_and_select_exercises(main_exercises, week, count)
        
        # توزیع تمرینات ترکیبی و ایزوله
        workout_structure['main'] = self._distribute_exercises(scored_main)
        
        # 3. تمرینات مکمل
        if include_complementary:
            workout_structure['complementary'] = self._get_complementary_exercises(
                [ex[0] for ex in scored_main],
                week
            )
            
            # اضافه کردن تمرینات تثبیت‌کننده
            workout_structure['stabilization'] = self._get_stabilization_exercises(
                target_muscles,
                week
            )
        
        # 4. تمرینات سردکننده
        if include_cooldown:
            workout_structure['cooldown'] = self._get_cooldown_exercises(target_muscles, week)
        
        return workout_structure
    
    def _get_warmup_exercises(self, target_muscles: List[str], week: int) -> List[Tuple[Exercise, float]]:
        """
        انتخاب تمرینات گرم‌کننده از دیتابیس موجود
        - استفاده از تمرینات سبک و پویا
        - تمرینات با تجهیزات سبک یا بدون تجهیزات
        """
        query = Q(
            # تمرینات سبک و پویا
            Q(category__in=['cardio', 'plyometrics']) |
            # تمرینات کششی پویا
            Q(category='stretching', level='beginner') |
            # تمرینات با وزن بدن
            Q(category='weighted_bodyweight', equipment='body')
        )
        
        # فیلتر بر اساس عضلات هدف
        if target_muscles:
            query &= (
                Q(primary_muscles__overlap=target_muscles) |
                Q(secondary_muscles__overlap=target_muscles)
            )
        
        # اولویت با تمرینات سبک‌تر
        warmup_exercises = Exercise.objects.filter(query).order_by('level')
        return self._score_and_select_exercises(warmup_exercises, week, count=3)
    
    def _get_cooldown_exercises(self, target_muscles: List[str], week: int) -> List[Tuple[Exercise, float]]:
        """
        انتخاب تمرینات سردکننده از دیتابیس موجود
        - استفاده از تمرینات کششی
        - تمرینات سبک
        - تمرینات با وزن بدن
        """
        query = Q(
            # تمرینات کششی
            Q(category='stretching') |
            # تمرینات سبک با وزن بدن
            Q(category='weighted_bodyweight', equipment='body', level='beginner') |
            # تمرینات موبایلیتی
            Q(category='strength', mechanic='isolation', level='beginner')
        )
        
        # فیلتر بر اساس عضلات هدف
        if target_muscles:
            query &= (
                Q(primary_muscles__overlap=target_muscles) |
                Q(secondary_muscles__overlap=target_muscles)
            )
        
        cooldown_exercises = Exercise.objects.filter(query)
        return self._score_and_select_exercises(cooldown_exercises, week, count=3)
    
    def _get_stabilization_exercises(self, target_muscles: List[str], week: int) -> List[Tuple[Exercise, float]]:
        """
        انتخاب تمرینات تثبیت‌کننده از دیتابیس موجود
        - استفاده از تمرینات هسته
        - تمرینات تعادلی
        - تمرینات با وزن بدن
        """
        query = Q(
            # تمرینات هسته
            Q(primary_muscles__contains=['abs', 'core', 'lower_back']) |
            # تمرینات تعادلی
            Q(category='weighted_bodyweight', equipment='body') |
            # تمرینات پایداری
            Q(category='strength', mechanic='isolation', level__in=['beginner', 'intermediate'])
        )
        
        # فیلتر تجهیزات
        if self.settings.available_equipment:
            query &= Q(equipment__in=self.settings.available_equipment)
        
        stabilization_exercises = Exercise.objects.filter(query)
        return self._score_and_select_exercises(stabilization_exercises, week, count=2)
    
    def _score_and_select_exercises(
        self,
        exercises: List[Exercise],
        week: int,
        count: int
    ) -> List[Tuple[Exercise, float]]:
        """امتیازدهی و انتخاب بهترین تمرینات"""
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
        scored_exercises: List[Tuple[Exercise, float]]
    ) -> List[Tuple[Exercise, float]]:
        """
        توزیع هوشمند تمرینات ترکیبی و ایزوله
        - تمرینات ترکیبی اولویت دارند
        - توزیع مناسب بر اساس سطح تجربه
        """
        compound_exercises = []
        isolation_exercises = []
        
        # جداسازی تمرینات ترکیبی و ایزوله
        for exercise, score in scored_exercises:
            if exercise.mechanic == 'compound':
                compound_exercises.append((exercise, score))
            else:
                isolation_exercises.append((exercise, score))
        
        # توزیع بر اساس سطح تجربه
        if self.settings.experience_level == 'beginner':
            # برای مبتدیان: 60% ترکیبی، 40% ایزوله
            compound_count = min(3, len(compound_exercises))
            isolation_count = min(2, len(isolation_exercises))
        elif self.settings.experience_level == 'intermediate':
            # برای متوسط: 50% ترکیبی، 50% ایزوله
            compound_count = min(2, len(compound_exercises))
            isolation_count = min(3, len(isolation_exercises))
        else:
            # برای حرفه‌ای: 40% ترکیبی، 60% ایزوله
            compound_count = min(2, len(compound_exercises))
            isolation_count = min(3, len(isolation_exercises))
        
        # ترکیب تمرینات با اولویت ترکیبی
        distributed_exercises = compound_exercises[:compound_count]
        distributed_exercises.extend(isolation_exercises[:isolation_count])
        
        return distributed_exercises
    
    def _get_main_exercises(self, target_muscles: List[str], week: int) -> List[Exercise]:
        """
        انتخاب تمرینات اصلی با فیلترهای حرفه‌ای
        - تمرینات ترکیبی برای مبتدیان
        - ترکیب مناسب تمرینات بر اساس هدف
        """
        query = Q(primary_muscles__overlap=target_muscles)
        
        # فیلتر تجهیزات
        if self.settings.available_equipment:
            query &= Q(equipment__in=self.settings.available_equipment)
        
        # فیلتر سطح تجربه
        if self.settings.experience_level == 'beginner':
            query &= (
                Q(level='beginner') |
                # برخی تمرینات متوسط برای مبتدیان پیشرفته
                Q(level='intermediate', mechanic='compound')
            )
        elif self.settings.experience_level == 'intermediate':
            query &= Q(level__in=['beginner', 'intermediate'])
        
        # فیلتر بر اساس هدف
        if self.user.goal == 'muscle_gain':
            query &= (
                # تمرینات ترکیبی و قدرتی
                Q(mechanic='compound', category__in=['strength', 'powerlifting']) |
                # تمرینات ایزوله برای حجم
                Q(mechanic='isolation', category='strength')
            )
        elif self.user.goal == 'strength':
            query &= (
                # تمرینات ترکیبی قدرتی
                Q(mechanic='compound', category__in=['strength', 'powerlifting']) |
                # تمرینات المپیک
                Q(category='olympic_weightlifting')
            )
        elif self.user.goal == 'weight_loss':
            query &= (
                # تمرینات ترکیبی با شدت بالا
                Q(mechanic='compound', category__in=['strength', 'crossfit']) |
                # تمرینات کاردیو
                Q(category='cardio') |
                # تمرینات متابولیک
                Q(category='plyometrics')
            )
        elif self.user.goal == 'endurance':
            query &= (
                # تمرینات کاردیو
                Q(category='cardio') |
                # تمرینات استقامتی
                Q(category__in=['strength', 'crossfit'], mechanic='compound')
            )
        
        # فیلتر محدودیت‌های فیزیکی
        if hasattr(self.user, 'physical_limitations') and self.user.physical_limitations:
            query &= ~Q(contraindications__overlap=self.user.physical_limitations)
        
        return Exercise.objects.filter(query)
    
    def _get_complementary_exercises(
        self,
        main_exercises: List[Exercise],
        week: int,
        count: int = 2
    ) -> List[Tuple[Exercise, float]]:
        """
        انتخاب تمرینات مکمل حرفه‌ای
        - تمرینات آنتاگونیست
        - تمرینات تثبیت‌کننده
        - تمرینات تعادلی
        """
        complementary_muscles = set()
        
        # جمع‌آوری عضلات ثانویه و آنتاگونیست
        for exercise in main_exercises:
            if exercise.secondary_muscles:
                complementary_muscles.update(exercise.secondary_muscles)
            
            # اضافه کردن عضلات آنتاگونیست بر اساس نوع حرکت
            if exercise.force == 'push':
                complementary_muscles.update(['back', 'biceps', 'rear_deltoids'])
            elif exercise.force == 'pull':
                complementary_muscles.update(['chest', 'triceps', 'front_deltoids'])
            elif exercise.force == 'static':
                complementary_muscles.update(['core', 'lower_back'])
        
        if not complementary_muscles:
            return []
        
        # ساخت کوئری برای تمرینات مکمل
        query = Q(
            # تمرینات آنتاگونیست
            Q(primary_muscles__overlap=list(complementary_muscles)) |
            # تمرینات تثبیت‌کننده
            Q(category__in=['strength', 'weighted_bodyweight'], mechanic='isolation') |
            # تمرینات تعادلی
            Q(category='plyometrics', level__in=['beginner', 'intermediate'])
        )
        
        # فیلتر تجهیزات
        if self.settings.available_equipment:
            query &= Q(equipment__in=self.settings.available_equipment)
        
        # دریافت و امتیازدهی به تمرینات مکمل
        complementary = Exercise.objects.filter(query)
        return self._score_and_select_exercises(complementary, week, count)
    
    def update_history(self, exercise_id: int, week: int):
        """به‌روزرسانی تاریخچه تمرینات"""
        self.exercise_history[exercise_id] = week 