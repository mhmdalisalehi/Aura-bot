import csv
from django.core.management.base import BaseCommand
from exercises.models import Exercise
from accounts.models import  InjuryExerciseClassification

class Command(BaseCommand):
    help = 'Import injury classification data from CSV'

    def handle(self, *args, **kwargs):
        file_path =file_path = r"C:\Users\dante\Downloads\injury_exercise_classification.csv"
        count = 0

        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                injury_map = {
                    "Lower Back Injury": "lower_back",
                    "Knee Injury": "knee",
                    "Shoulder Injury": "shoulder",
                    "Neck Injury": "neck",
                    "Wrist Injury": "wrist",
                    "Elbow Injury": "elbow",
                    "Hip Injury": "hip",
                    "Chest Injury": "chest"
                }

                classification_map = {
                    "Avoid": "avoid",
                    "Safe Alternative": "safe"
                }

                injury_key = injury_map.get(row['Injury'].strip())
                classification_key = classification_map.get(row['Classification'].strip())

                try:
                    exercise = Exercise.objects.get(name__iexact=row['Exercise'].strip())
                    InjuryExerciseClassification.objects.get_or_create(
                        injury=injury_key,
                        exercise=exercise,
                        classification=classification_key
                    )
                    count += 1
                except Exercise.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Exercise not found: {row['Exercise']}"))

        self.stdout.write(self.style.SUCCESS(f"Imported {count} injury classifications."))
