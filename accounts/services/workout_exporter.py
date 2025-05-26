from typing import Dict, List
import json
from datetime import datetime
from accounts.models import UserProfile, TrainingSettings
from exercises.models import Exercise

class WorkoutExporter:
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        self.user = user
        self.settings = settings
        
    def export_to_json(self, program: Dict) -> str:
        """خروجی گرفتن برنامه به فرمت JSON"""
        export_data = {
            'user_info': self._get_user_info(),
            'program_info': self._get_program_info(),
            'weekly_plan': self._format_weekly_plan(program['weekly_plan'])
        }
        
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    
    def export_to_text(self, program: Dict) -> str:
        """خروجی گرفتن برنامه به فرمت متنی"""
        text = []
        
        # اطلاعات کاربر
        text.append("=== اطلاعات کاربر ===")
        text.extend(self._format_user_info())
        text.append("")
        
        # اطلاعات برنامه
        text.append("=== اطلاعات برنامه ===")
        text.extend(self._format_program_info())
        text.append("")
        
        # برنامه هفتگی
        text.append("=== برنامه هفتگی ===")
        text.extend(self._format_weekly_plan_text(program['weekly_plan']))
        
        return "\n".join(text)
    
    def _get_user_info(self) -> Dict:
        """دریافت اطلاعات کاربر"""
        return {
            'name': self.user.name,
            'age': self.user.age,
            'gender': self.user.gender,
            'weight': self.user.weight,
            'height': self.user.height,
            'body_type': self.user.body_type,
            'goal': self.user.goal,
            'experience_level': self.settings.experience_level
        }
    
    def _get_program_info(self) -> Dict:
        """دریافت اطلاعات برنامه"""
        return {
            'created_at': datetime.now().isoformat(),
            'split_type': self.settings.split_type,
            'training_days': list(self.settings.training_days.keys()),
            'available_equipment': self.settings.available_equipment
        }
    
    def _format_weekly_plan(self, weekly_plan: Dict) -> Dict:
        """فرمت‌بندی برنامه هفتگی برای JSON"""
        formatted_plan = {}
        
        for day, exercises in weekly_plan.items():
            formatted_plan[day] = []
            for exercise in exercises:
                formatted_exercise = {
                    'name': exercise['exercise_name'],
                    'type': exercise['type'],
                    'muscle_group': exercise['muscle_group'],
                    'sets': exercise['sets'],
                    'reps': exercise['reps'],
                    'rest_seconds': exercise.get('rest_seconds', 60),
                    'notes': exercise.get('notes', '')
                }
                formatted_plan[day].append(formatted_exercise)
                
        return formatted_plan
    
    def _format_user_info(self) -> List[str]:
        """فرمت‌بندی اطلاعات کاربر برای متن"""
        return [
            f"نام: {self.user.name}",
            f"سن: {self.user.age}",
            f"جنسیت: {self.user.gender}",
            f"وزن: {self.user.weight} کیلوگرم",
            f"قد: {self.user.height} سانتی‌متر",
            f"تیپ بدنی: {self.user.body_type}",
            f"هدف: {self.user.goal}",
            f"سطح تجربه: {self.settings.experience_level}"
        ]
    
    def _format_program_info(self) -> List[str]:
        """فرمت‌بندی اطلاعات برنامه برای متن"""
        return [
            f"تاریخ ایجاد: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"نوع برنامه: {self.settings.split_type}",
            f"روزهای تمرین: {', '.join(self.settings.training_days.keys())}",
            f"تجهیزات در دسترس: {', '.join(self.settings.available_equipment)}"
        ]
    
    def _format_weekly_plan_text(self, weekly_plan: Dict) -> List[str]:
        """فرمت‌بندی برنامه هفتگی برای متن"""
        text = []
        
        for day, exercises in weekly_plan.items():
            text.append(f"\n{day}:")
            for i, exercise in enumerate(exercises, 1):
                text.append(f"\n{i}. {exercise['exercise_name']}")
                text.append(f"   نوع: {exercise['type']}")
                text.append(f"   عضله: {exercise['muscle_group']}")
                text.append(f"   ست‌ها: {exercise['sets']}")
                text.append(f"   تکرار: {exercise['reps']}")
                text.append(f"   استراحت: {exercise.get('rest_seconds', 60)} ثانیه")
                if 'notes' in exercise:
                    text.append(f"   نکات: {exercise['notes']}")
                    
        return text 