from typing import Dict, List, Union, Optional
import json
from datetime import datetime
from functools import lru_cache
import pandas as pd
from accounts.models import UserProfile, TrainingSettings, BotUser
from exercises.models import Exercise
from .workout_utils import get_exercise_notes

class WorkoutExportError(Exception):
    """خطای مخصوص خروجی گرفتن برنامه"""
    pass

class WorkoutExporter:
    def __init__(self, user: UserProfile, settings: TrainingSettings):
        if not user or not settings:
            raise WorkoutExportError("اطلاعات کاربر یا تنظیمات ناقص است")
        self.user = user
        self.settings = settings
        try:
            self.bot_user = BotUser.objects.get(id=user.user.id)
        except BotUser.DoesNotExist:
            raise WorkoutExportError("کاربر بات یافت نشد")
        
    def export_to_json(self, program: Dict) -> str:
        """خروجی گرفتن برنامه به فرمت JSON با جزئیات کامل"""
        try:
            export_data = {
                'user_info': self._get_user_info(),
                'program_info': self._get_program_info(),
                'weekly_plan': self._format_weekly_plan(program['weekly_plan']),
                'recovery_info': self._get_recovery_info(program),
                'nutrition_tips': self._get_nutrition_tips(),
                'progress_tracking': self._get_progress_tracking_info()
            }
            return json.dumps(export_data, indent=2, ensure_ascii=False)
        except Exception as e:
            raise WorkoutExportError(f"خطا در خروجی JSON: {str(e)}")

    def export_to_excel(self, program: Dict, output_path: str) -> None:
        """خروجی گرفتن برنامه به فرمت Excel"""
        try:
            # ایجاد DataFrame برای هر بخش
            user_df = pd.DataFrame([self._get_user_info()])
            program_df = pd.DataFrame([self._get_program_info()])
            
            # تبدیل برنامه هفتگی به DataFrame
            weekly_data = []
            for day, exercises in program['weekly_plan'].items():
                for exercise in exercises:
                    exercise_data = {
                        'day': day,
                        **exercise
                    }
                    weekly_data.append(exercise_data)
            weekly_df = pd.DataFrame(weekly_data)
            
            # ذخیره در فایل Excel با چند شیت
            with pd.ExcelWriter(output_path) as writer:
                user_df.to_excel(writer, sheet_name='اطلاعات کاربر', index=False)
                program_df.to_excel(writer, sheet_name='اطلاعات برنامه', index=False)
                weekly_df.to_excel(writer, sheet_name='برنامه هفتگی', index=False)
                
        except Exception as e:
            raise WorkoutExportError(f"خطا در خروجی Excel: {str(e)}")

    @lru_cache(maxsize=32)
    def _get_user_info(self) -> Dict:
        """دریافت اطلاعات کامل کاربر با کش"""
        bot_user = self.user.user
        name = f"{bot_user.first_name or ''} {bot_user.last_name or ''}".strip()
        return {
            'telegram_id': bot_user.telegram_id,
            'username': bot_user.username,
            'name': name,
            'age': self.user.age,
            'gender': self.user.gender,
            'weight': self.user.weight_kg,
            'height': self.user.height_cm,
            'body_type': self.user.body_type,
            'goal': self.user.goal,
            'experience_level': self.settings.experience_level,
            'medical_conditions': getattr(self.user, 'medical_conditions', None),
            'injuries': getattr(self.user, 'injuries', None),
            'preferred_exercises': getattr(self.user, 'preferred_exercises', None),
            'avoided_exercises': getattr(self.user, 'avoided_exercises', None)
        }
    
    def _get_program_info(self) -> Dict:
        """دریافت اطلاعات کامل برنامه"""
        return {
            'created_at': datetime.now().isoformat(),
            'split_type': self.settings.split_type,
            'training_days': list(self.settings.training_days.keys()),
            'available_equipment': self.settings.available_equipment,
            'training_goal': self.settings.training_goal,
            'cardio_preference': self.settings.cardio_preference,
            'rest_preference': self.settings.rest_preference,
            'program_duration_weeks': self.settings.program_duration_weeks,
            'intensity_preference': self.settings.intensity_preference
        }
    
    def _format_weekly_plan(self, weekly_plan: Dict) -> Dict:
        """فرمت‌بندی برنامه هفتگی برای JSON با جزئیات بیشتر"""
        formatted_plan = {}
        
        for day, exercises in weekly_plan.items():
            formatted_plan[day] = []
            for exercise in exercises:
                exercise_obj = Exercise.objects.get(name=exercise['exercise_name'])
                notes = get_exercise_notes(exercise_obj, self.settings.experience_level)
                
                formatted_exercise = {
                    'name': exercise['exercise_name'],
                    'type': exercise['type'],
                    'muscle_group': exercise['muscle_group'],
                    'sets': exercise['sets'],
                    'reps': exercise['reps'],
                    'rest_seconds': exercise.get('rest_seconds', 60),
                    'intensity': exercise.get('intensity', 0.7),
                    'technique': exercise.get('technique', ''),
                    'notes': notes,
                    'equipment': exercise_obj.equipment,
                    'difficulty': exercise_obj.difficulty,
                    'video_url': exercise_obj.video_url if hasattr(exercise_obj, 'video_url') else None,
                    'alternative_exercises': exercise.get('alternative_exercises', [])
                }
                formatted_plan[day].append(formatted_exercise)
                
        return formatted_plan
    
    def _get_recovery_info(self, program: Dict) -> Dict:
        """دریافت اطلاعات ریکاوری"""
        return {
            'recommended_sleep_hours': self._get_sleep_recommendation(),
            'active_recovery_days': self._get_active_recovery_days(program),
            'stretching_routine': self._get_stretching_routine(),
            'recovery_techniques': self._get_recovery_techniques()
        }
    
    def _get_nutrition_tips(self) -> Dict:
        """دریافت نکات تغذیه بر اساس هدف و تیپ بدنی"""
        nutrition_tips = {
            'general': [
                "روزانه 8-10 لیوان آب بنوشید",
                "وعده‌های غذایی را در زمان‌های منظم مصرف کنید",
                "از مصرف غذاهای فرآوری شده خودداری کنید"
            ],
            'pre_workout': [
                "2-3 ساعت قبل از تمرین یک وعده غذایی کامل مصرف کنید",
                "30 دقیقه قبل از تمرین یک میان‌وعده سبک بخورید",
                "از کافئین برای افزایش انرژی استفاده کنید"
            ],
            'post_workout': [
                "در عرض 30 دقیقه بعد از تمرین پروتئین مصرف کنید",
                "کربوهیدرات‌های پیچیده را برای ریکاوری مصرف کنید",
                "الکترولیت‌های از دست رفته را جایگزین کنید"
            ]
        }
        
        # اضافه کردن نکات مخصوص بر اساس هدف
        if self.user.goal == 'muscle_gain':
            nutrition_tips['specific'] = [
                "مصرف پروتئین را به 1.6-2.2 گرم به ازای هر کیلوگرم وزن بدن افزایش دهید",
                "کالری مازاد 300-500 کالری در روز داشته باشید",
                "از مکمل‌های پروتئینی و کراتین استفاده کنید"
            ]
        elif self.user.goal == 'fat_loss':
            nutrition_tips['specific'] = [
                "کالری دریافتی را 300-500 کالری کمتر از نیاز روزانه تنظیم کنید",
                "مصرف پروتئین را بالا نگه دارید (1.6-2 گرم به ازای هر کیلوگرم)",
                "کربوهیدرات‌ها را در زمان‌های مناسب مصرف کنید"
            ]
            
        return nutrition_tips
    
    def _get_progress_tracking_info(self) -> Dict:
        """دریافت اطلاعات پیگیری پیشرفت"""
        return {
            'metrics_to_track': self._get_tracking_metrics(),
            'measurement_frequency': self._get_measurement_frequency(),
            'progress_photos': self._get_photo_guidelines(),
            'strength_tracking': self._get_strength_tracking_guide()
        }
    
    def _format_user_info(self) -> List[str]:
        """فرمت‌بندی اطلاعات کاربر برای متن"""
        bot_user = self.user.user
        name = f"{bot_user.first_name or ''} {bot_user.last_name or ''}".strip()
        return [
            f"شناسه تلگرام: {bot_user.telegram_id}",
            f"نام کاربری: {bot_user.username}",
            f"نام: {name}",
            f"سن: {self.user.age}",
            f"جنسیت: {self.user.gender}",
            f"وزن: {self.user.weight_kg} کیلوگرم",
            f"قد: {self.user.height_cm} سانتی‌متر",
            f"تیپ بدنی: {self.user.body_type}",
            f"هدف: {self.user.goal}",
            f"سطح تجربه: {self.settings.experience_level}",
            f"محدودیت‌های پزشکی: {', '.join(getattr(self.user, 'medical_conditions', []) or []) if getattr(self.user, 'medical_conditions', None) else 'ندارد'}",
            f"آسیب‌های قبلی: {', '.join(getattr(self.user, 'injuries', []) or []) if getattr(self.user, 'injuries', None) else 'ندارد'}"
        ]
    
    def _format_program_info(self) -> List[str]:
        """فرمت‌بندی اطلاعات برنامه برای متن"""
        return [
            f"تاریخ ایجاد: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"نوع برنامه: {self.settings.split_type}",
            f"روزهای تمرین: {', '.join(self.settings.training_days.keys())}",
            f"تجهیزات در دسترس: {', '.join(self.settings.available_equipment)}",
            f"هدف تمرین: {self.settings.training_goal}",
            f"مدت برنامه: {self.settings.program_duration_weeks} هفته",
            f"ترجیح شدت: {self.settings.intensity_preference}"
        ]
    
    def _format_weekly_plan_text(self, weekly_plan: Dict) -> List[str]:
        """فرمت‌بندی برنامه هفتگی برای متن با جزئیات بیشتر"""
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
                text.append(f"   شدت: {exercise.get('intensity', 0.7)}")
                if exercise.get('technique'):
                    text.append(f"   تکنیک: {exercise['technique']}")
                if exercise.get('notes'):
                    text.append("   نکات:")
                    for note in exercise['notes']:
                        text.append(f"      - {note}")
                if exercise.get('alternative_exercises'):
                    text.append("   حرکات جایگزین:")
                    for alt in exercise['alternative_exercises']:
                        text.append(f"      - {alt}")
                    
        return text
    
    def _get_sleep_recommendation(self) -> Dict:
        """دریافت توصیه‌های خواب"""
        return {
            'hours': 7-9,
            'tips': [
                "قبل از خواب از نور آبی خودداری کنید",
                "دمای اتاق را خنک نگه دارید",
                "از مصرف کافئین بعد از ساعت 4 عصر خودداری کنید",
                "یک برنامه خواب منظم داشته باشید"
            ]
        }
    
    def _get_active_recovery_days(self, program: Dict) -> List[str]:
        """تعیین روزهای ریکاوری فعال"""
        training_days = set(program['weekly_plan'].keys())
        all_days = {'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'}
        return list(all_days - training_days)
    
    def _get_stretching_routine(self) -> Dict:
        """دریافت برنامه کشش"""
        return {
            'daily': [
                "کشش گردن",
                "کشش شانه",
                "کشش مچ دست",
                "کشش کمر",
                "کشش همسترینگ"
            ],
            'post_workout': [
                "کشش عضلات تمرین داده شده",
                "کشش پویا برای بهبود ریکاوری",
                "تمرینات تنفسی"
            ]
        }
    
    def _get_recovery_techniques(self) -> List[str]:
        """دریافت تکنیک‌های ریکاوری"""
        return [
            "ماساژ",
            "غوطه‌وری در آب سرد",
            "فوم رولینگ",
            "تمرینات تنفسی",
            "مدیتیشن"
        ]
    
    def _get_tracking_metrics(self) -> List[str]:
        """دریافت معیارهای پیگیری پیشرفت"""
        metrics = ["وزن بدن", "دور کمر", "دور بازو", "دور سینه", "دور ران"]
        if self.user.goal == 'muscle_gain':
            metrics.extend(["وزن‌های استفاده شده در حرکات اصلی", "تعداد تکرارها"])
        elif self.user.goal == 'fat_loss':
            metrics.extend(["درصد چربی بدن", "عکس‌های پیشرفت"])
        return metrics
    
    def _get_measurement_frequency(self) -> Dict:
        """دریافت دفعات اندازه‌گیری"""
        return {
            'weight': 'هفته‌ای یکبار',
            'measurements': 'دوهفته یکبار',
            'strength': 'هر جلسه',
            'photos': 'ماهانه'
        }
    
    def _get_photo_guidelines(self) -> List[str]:
        """دریافت راهنمای عکس‌های پیشرفت"""
        return [
            "عکس‌ها را در نور مناسب بگیرید",
            "از زوایای مختلف عکس بگیرید",
            "در یک زمان ثابت از روز عکس بگیرید",
            "از لباس‌های یکسان استفاده کنید"
        ]
    
    def _get_strength_tracking_guide(self) -> Dict:
        """دریافت راهنمای پیگیری قدرت"""
        return {
            'main_lifts': [
                "اسکات",
                "ددلیفت",
                "پرس سینه",
                "پرس سرشانه"
            ],
            'tracking_method': "ثبت وزن و تکرار در هر ست",
            'progression': "افزایش 2.5-5 کیلوگرم در هر هفته"
        }

    def export_to_text(self, program: Dict, include_sections: Optional[List[str]] = None) -> str:
        """خروجی گرفتن برنامه به فرمت متنی با قابلیت انتخاب بخش‌ها"""
        if include_sections is None:
            include_sections = ['user_info', 'program_info', 'nutrition_tips', 
                              'recovery_info', 'weekly_plan', 'progress_tracking']
        
        section_formatters = {
            'user_info': (self._format_user_info, "=== اطلاعات کاربر ==="),
            'program_info': (self._format_program_info, "=== اطلاعات برنامه ==="),
            'nutrition_tips': (self._format_nutrition_tips, "=== نکات تغذیه ==="),
            'recovery_info': (lambda: self._format_recovery_info(program), "=== اطلاعات ریکاوری ==="),
            'weekly_plan': (lambda: self._format_weekly_plan_text(program['weekly_plan']), "=== برنامه هفتگی ==="),
            'progress_tracking': (self._format_progress_tracking_info, "=== راهنمای پیگیری پیشرفت ===")
        }
        
        text = []
        for section in include_sections:
            if section in section_formatters:
                formatter, header = section_formatters[section]
                text.append(header)
                text.extend(formatter())
                text.append("")
        
        return "\n".join(text)

    def _format_progress_tracking_info(self) -> List[str]:
        """فرمت‌بندی اطلاعات پیگیری پیشرفت برای متن"""
        info = self._get_progress_tracking_info()
        text = []
        
        text.append("معیارهای پیگیری:")
        for metric in info['metrics_to_track']:
            text.append(f"- {metric}")
            
        text.append("\nدفعات اندازه‌گیری:")
        for metric, frequency in info['measurement_frequency'].items():
            text.append(f"- {metric}: {frequency}")
            
        text.append("\nراهنمای عکس‌های پیشرفت:")
        for guideline in info['progress_photos']:
            text.append(f"- {guideline}")
            
        text.append("\nپیگیری قدرت:")
        text.append(f"حرکات اصلی: {', '.join(info['strength_tracking']['main_lifts'])}")
        text.append(f"روش پیگیری: {info['strength_tracking']['tracking_method']}")
        text.append(f"پیشرفت: {info['strength_tracking']['progression']}")
        
        return text 