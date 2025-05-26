from typing import Dict
from collections import defaultdict

class WorkoutQualityEvaluator:
    @staticmethod
    def evaluate(program: Dict) -> float:
        """ارزیابی کیفیت برنامه تمرینی (امتیاز 0-100)"""
        score = 0
        
        # معیارهای ارزیابی
        criteria = {
            'muscle_coverage': 30,
            'volume_adequacy': 25,
            'exercise_variety': 20,
            'recovery_time': 15,
            'progressive_overload': 10
        }
        
        # محاسبه امتیاز برای هر معیار
        score += criteria['muscle_coverage'] * WorkoutQualityEvaluator._muscle_coverage_score(program)
        score += criteria['volume_adequacy'] * WorkoutQualityEvaluator._volume_score(program)
        score += criteria['exercise_variety'] * WorkoutQualityEvaluator._variety_score(program)
        score += criteria['recovery_time'] * WorkoutQualityEvaluator._recovery_score(program)
        score += criteria['progressive_overload'] * WorkoutQualityEvaluator._progression_score(program)
        
        return min(100, max(0, score))
    
    @staticmethod
    def _muscle_coverage_score(program: Dict) -> float:
        """محاسبه امتیاز پوشش عضلانی"""
        trained_muscles = set()
        for day in program['weekly_plan'].values():
            for exercise in day:
                if isinstance(exercise, dict) and 'muscle_group' in exercise:
                    trained_muscles.add(exercise['muscle_group'])
        return len(trained_muscles) / 15  # فرض 15 گروه عضلانی اصلی
    
    @staticmethod
    def _volume_score(program: Dict) -> float:
        """محاسبه امتیاز حجم تمرین"""
        total_volume = 0
        for day in program['weekly_plan'].values():
            for exercise in day:
                if isinstance(exercise, dict) and 'sets' in exercise and 'reps' in exercise:
                    sets = exercise['sets']
                    reps = exercise['reps']
                    if isinstance(reps, str):
                        reps = int(reps.split('-')[0])  # استفاده از حداقل تکرار
                    total_volume += sets * reps
        
        # ارزیابی حجم بر اساس استانداردها
        if total_volume < 100:
            return 0.5
        elif total_volume < 200:
            return 0.7
        elif total_volume < 300:
            return 0.9
        return 1.0
    
    @staticmethod
    def _variety_score(program: Dict) -> float:
        """محاسبه امتیاز تنوع تمرینات"""
        exercise_types = defaultdict(int)
        for day in program['weekly_plan'].values():
            for exercise in day:
                if isinstance(exercise, dict) and 'type' in exercise:
                    exercise_types[exercise['type']] += 1
        
        # ارزیابی تنوع
        if len(exercise_types) < 2:
            return 0.5
        elif len(exercise_types) < 3:
            return 0.7
        elif len(exercise_types) < 4:
            return 0.9
        return 1.0
    
    @staticmethod
    def _recovery_score(program: Dict) -> float:
        """محاسبه امتیاز زمان استراحت"""
        total_rest = 0
        exercise_count = 0
        for day in program['weekly_plan'].values():
            for exercise in day:
                if isinstance(exercise, dict) and 'rest_seconds' in exercise:
                    total_rest += exercise['rest_seconds']
                    exercise_count += 1
        
        if exercise_count == 0:
            return 0.5
            
        avg_rest = total_rest / exercise_count
        if avg_rest < 60:
            return 0.5
        elif avg_rest < 90:
            return 0.7
        elif avg_rest < 120:
            return 0.9
        return 1.0
    
    @staticmethod
    def _progression_score(program: Dict) -> float:
        """محاسبه امتیاز پیشرفت تدریجی"""
        # بررسی وجود نشانه‌های پیشرفت تدریجی
        has_progression = False
        for day in program['weekly_plan'].values():
            for exercise in day:
                if isinstance(exercise, dict):
                    if 'progression_notes' in exercise or 'intensity_notes' in exercise:
                        has_progression = True
                        break
        
        return 1.0 if has_progression else 0.5 