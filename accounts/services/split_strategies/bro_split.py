from typing import Dict, List, Optional
import random
import math
from exercises.models import Exercise
from .base import SplitStrategy

class BroSplitStrategy(SplitStrategy):
    """
    استراتژی Bro Split (تمرین هر گروه عضلانی در یک روز جداگانه)
    ساختار پیش‌فرض:
    - روز 1: سینه
    - روز 2: پشت
    - روز 3: پاها
    - روز 4: سرشانه
    - روز 5: بازوها (جلو/پشت بازو)
    - روز 6: تکمیلی (اختیاری)
    """
    MUSCLE_DAY_MAPPING = {
        'chest': ['chest', 'triceps'],
        'back': ['back', 'biceps'],
        'legs': ['quadriceps', 'hamstrings', 'glutes', 'calves'],
        'shoulders': ['shoulders', 'traps', 'rear_delts'],
        'arms': ['biceps', 'triceps', 'forearms'],
        'core': ['abs', 'obliques', 'lower_back']
    }
    
    DAY_PRIORITY = ['chest', 'back', 'legs', 'shoulders', 'arms', 'core']
    
    def generate(self, week: int) -> Dict:
        program = {'weekly_plan': {}}
        available_days = list(self.settings.training_days.keys())
        
        # توزیع روزهای تمرین بر اساس اولویت
        for i, muscle_day in enumerate(self.DAY_PRIORITY):
            if i >= len(available_days):
                break
                
            day_name = available_days[i]
            program['weekly_plan'][day_name] = self._build_muscle_day(
                muscle_day, 
                week
            )
            self.split_map[day_name] = muscle_day
        
        # روزهای اضافی برای تمرینات تکمیلی
        if len(available_days) > len(self.DAY_PRIORITY):
            extra_days = available_days[len(self.DAY_PRIORITY):]
            for day in extra_days:
                program['weekly_plan'][day] = self._build_hybrid_day(week)
                self.split_map[day] = 'hybrid'
        
        self._add_warmup_cooldown(program)
        return program
    
    def _build_muscle_day(self, muscle_day: str, week: int) -> List[Dict]:
        """ساخت برنامه برای یک روز اختصاصی یک گروه عضلانی"""
        exercises = []
        primary_muscles = self.MUSCLE_DAY_MAPPING[muscle_day]
        
        # تمرینات اصلی (4-5 تمرین برای عضله اصلی)
        primary_count = {
            'beginner': 3,
            'intermediate': 4,
            'expert': 5
        }.get(self.settings.experience_level, 4)
        
        # تمرینات ترکیبی برای عضله اصلی
        main_muscle = primary_muscles[0]
        compound_exercises = self.exercise_selector.get_exercises(
            [main_muscle],
            week
        )
        
        for ex in compound_exercises[:min(2, len(compound_exercises))]:
            volume = self._get_volume_for_muscle(main_muscle, week, is_compound=True)
            exercises.append(self._create_exercise_entry(ex, volume, True))
        
        # تمرینات تکمیلی برای عضله اصلی
        isolation_exercises = self.exercise_selector.get_exercises(
            [main_muscle],
            week
        )
        
        for ex in isolation_exercises[:primary_count - 2]:
            volume = self._get_volume_for_muscle(main_muscle, week, is_compound=False)
            exercises.append(self._create_exercise_entry(ex, volume, False))
        
        # تمرینات برای عضلات ثانویه (1-2 تمرین)
        if len(primary_muscles) > 1:
            secondary_muscles = primary_muscles[1:]
            for muscle in secondary_muscles:
                if random.random() < 0.7:  # 70% شانس اضافه کردن تمرین ثانویه
                    ex = self._select_secondary_exercise(muscle, week)
                    if ex:
                        exercises.append(ex)
        
        return exercises
    
    def _get_volume_for_muscle(self, muscle: str, week: int, is_compound: bool) -> Dict:
        """محاسبه حجم تمرین بر اساس عضله و نوع حرکت"""
        base_volume = self.volume_manager.adjust_volume(muscle, week)
        
        # تنظیم حجم برای Bro Split (حجم بیشتر در هر جلسه)
        adjusted_sets = base_volume['sets'] * {
            'compound': 1.2,
            'isolation': 1.0
        }.get('compound' if is_compound else 'isolation', 1.0)
        
        return {
            'sets': math.ceil(adjusted_sets),
            'reps': base_volume['reps']
        }
    
    def _select_secondary_exercise(self, muscle: str, week: int) -> Optional[Dict]:
        """انتخاب تمرین برای عضلات ثانویه"""
        available = self.exercise_selector.get_exercises([muscle], week)
        if available:
            volume = self._get_volume_for_muscle(muscle, week, is_compound=False)
            ex = random.choice(available)
            return self._create_exercise_entry(ex, volume, False)
        return None
    
    def _build_hybrid_day(self, week: int) -> List[Dict]:
        """ساخت روزهای ترکیبی (برای روزهای اضافی)"""
        options = [
            ('core', ['abs', 'obliques']),
            ('weak_points', self._get_user_weak_points()),
            ('cardio', ['conditioning'])
        ]
        
        selected_focus = random.choice(options)
        exercises = []
        
        if selected_focus[0] == 'core':
            for muscle in selected_focus[1]:
                ex = self._select_secondary_exercise(muscle, week)
                if ex:
                    exercises.append(ex)
        
        elif selected_focus[0] == 'weak_points':
            for muscle in selected_focus[1]:
                ex = self._select_secondary_exercise(muscle, week)
                if ex:
                    exercises.append({
                        **ex,
                        'tags': ['weak_point_focus'],
                        'intensity_notes': 'Higher volume'
                    })
        
        else:  # cardio/conditioning
            exercises.append({
                'type': 'conditioning',
                'content': self._select_cardio_protocol()
            })
        
        return exercises
    
    def _get_user_weak_points(self) -> List[str]:
        """تعیین نقاط ضعف کاربر بر اساس تیپ بدنی و هدف"""
        weak_points = {
            'mesomorph': ['calves', 'rear_delts'],
            'ectomorph': ['legs', 'back'],
            'endomorph': ['shoulders', 'arms']
        }.get(self.user.body_type, [])
        
        if self.user.goal == 'muscle_gain':
            weak_points.extend(['traps', 'upper_chest'])
        return list(set(weak_points))
    
    def _select_cardio_protocol(self) -> List[str]:
        """انتخاب پروتکل کاردیو بر اساس هدف کاربر"""
        if self.user.goal == 'weight_loss':
            return ['HIIT (30s sprint, 60s walk) x 8 rounds']
        return ['Moderate pace (30-45 mins)']
    
    def _create_exercise_entry(self, exercise: Exercise, volume: Dict, is_compound: bool) -> Dict:
        """ساخت وروردی استاندارد برای تمرین"""
        return {
            'exercise_id': exercise.id,
            'exercise_name': exercise.name,
            'type': 'compound' if is_compound else 'isolation',
            'muscle_group': exercise.primary_muscles[0],
            'sets': volume['sets'],
            'reps': volume['reps'],
            'rest_seconds': self._calculate_rest_time(exercise, is_compound),
            'notes': self._generate_exercise_notes(exercise, is_compound)
        }
               
    def _calculate_rest_time(self, exercise: Exercise, is_compound: bool) -> int:
        """محاسبه زمان استراحت برای Bro Split"""
        if is_compound:
            return 90 if self.user.goal == 'muscle_gain' else 120
        return 60 if 'arms' in exercise.primary_muscles else 75
    
    def _generate_exercise_notes(self, exercise: Exercise, is_compound: bool) -> str:
        """تولید نکات تمرینی"""
        notes = []
        if is_compound:
            notes.append('Focus on form and controlled tempo')
        
        if self.user.body_type == 'mesomorph':
            notes.append('Push to failure on last set')
        elif self.user.body_type == 'endomorph':
            notes.append('Moderate intensity, focus on mind-muscle connection')
        
        return '. '.join(notes) 