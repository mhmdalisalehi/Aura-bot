from typing import Dict, List
import random
from exercises.models import Exercise
from .base import SplitStrategy

class UpperLowerSplitStrategy(SplitStrategy):
    """
    استراتژی Upper/Lower
    ساختار پیش‌فرض:
    - روز 1: Upper Body (بالاتنه)
    - روز 2: Lower Body (پایین تنه)
    - روز 3: Upper Body
    - روز 4: Lower Body
    """
    MUSCLE_GROUPS = {
        'upper': ['chest', 'back', 'shoulders', 'biceps', 'triceps'],
        'lower': ['quadriceps', 'hamstrings', 'glutes', 'calves']
    }
    
    DAY_SEQUENCE = ['upper', 'lower', 'upper', 'lower']
    
    def generate(self, week: int) -> Dict:
        program = {'weekly_plan': {}}
        sequence_idx = 0
        
        for day in self.settings.training_days:
            if sequence_idx >= len(self.DAY_SEQUENCE):
                sequence_idx = 0
                
            split_type = self.DAY_SEQUENCE[sequence_idx]
            program['weekly_plan'][day] = self._build_day_plan(split_type, week)
            self.split_map[day] = split_type
            sequence_idx += 1
            
        self._validate_split_schedule(program)
        self._add_warmup_cooldown(program)
        self._validate_volume(program)
        return program
    
    def _build_day_plan(self, split_type: str, week: int) -> List[Dict]:
        exercises = []
        target_muscles = self.MUSCLE_GROUPS[split_type]
        
        # اولویت‌بندی عضلات اصلی برای هر جلسه
        priority_muscles = {
            'upper': ['chest', 'back', 'shoulders'],
            'lower': ['quadriceps', 'hamstrings']
        }
        
        # اضافه کردن تمرینات اصلی
        for muscle in priority_muscles[split_type]:
            if not self.recovery_manager.can_train([muscle], timezone.now()):
                continue
                
            volume = self.volume_manager.adjust_volume(muscle, week)
            available_exercises = self.exercise_selector.get_exercises([muscle], week)
            
            if available_exercises:
                selected_exercise = random.choice(available_exercises)
                exercises.append(self._create_exercise_entry(
                    selected_exercise, 
                    volume,
                    is_compound=True
                ))
                self._update_tracking(muscle, selected_exercise, volume)

        # اضافه کردن تمرینات تکمیلی
        for muscle in list(set(target_muscles) - set(priority_muscles[split_type])):
            if random.random() < 0.6:  # 60% احتمال اضافه کردن تمرین تکمیلی
                volume = self.volume_manager.adjust_volume(muscle, week)
                available_exercises = self.exercise_selector.get_exercises([muscle], week)
                if available_exercises:
                    selected_exercise = random.choice(available_exercises)
                    exercises.append(self._create_exercise_entry(
                        selected_exercise,
                        volume,
                        is_compound=False
                    ))
                    self._update_tracking(muscle, selected_exercise, volume)

        return exercises
    
    def _create_exercise_entry(self, exercise: Exercise, volume: Dict, is_compound: bool) -> Dict:
        return {
            'exercise_id': exercise.id,
            'exercise_name': exercise.name,
            'type': 'compound' if is_compound else 'accessory',
            'muscle_group': exercise.primary_muscles[0],
            'sets': volume['sets'],
            'reps': self._determine_rep_range(exercise, is_compound),
            'rest_seconds': self._calculate_rest_time(exercise, is_compound),
            'intensity_notes': self._generate_intensity_notes(exercise)
        }
    
    def _determine_rep_range(self, exercise: Exercise, is_compound: bool) -> str:
        if self.user.goal == 'muscle_gain':
            return '8-12' if is_compound else '12-15'
        return '4-6' if is_compound else '8-10'
    
    def _calculate_rest_time(self, exercise: Exercise, is_compound: bool) -> int:
        base_times = {
            'compound': 90 if self.user.goal == 'muscle_gain' else 120,
            'accessory': 60
        }
        return base_times['compound' if is_compound else 'accessory']
    
    def _generate_intensity_notes(self, exercise: Exercise) -> str:
        if self.user.body_type == 'mesomorph':
            return 'RPE 8-9' 
        return 'RPE 7-8' if self.user.body_type == 'endomorph' else 'RPE 6-7'
    
    def _validate_split_schedule(self, program: Dict):
        """اعتبارسنجی توالی تمرینات"""
        trained_muscles = defaultdict(list)
        for day, exercises in program['weekly_plan'].items():
            for ex in exercises:
                if 'muscle_group' in ex:
                    trained_muscles[ex['muscle_group']].append(day)
        
        for muscle, days in trained_muscles.items():
            min_recovery = self.recovery_manager.MIN_RECOVERY_DAYS.get(muscle, 2)
            for i in range(1, len(days)):
                if (days[i] - days[i-1]).days < min_recovery:
                    self._adjust_exercise_scheduling(program, muscle)
    
    def _adjust_exercise_scheduling(self, program: Dict, muscle: str):
        """تنظیم زمان‌بندی تمرینات برای رعایت زمان استراحت"""
        # پیاده‌سازی منطق تنظیم زمان‌بندی
        pass 