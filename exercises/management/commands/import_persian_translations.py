import csv
from django.core.management.base import BaseCommand
from exercises.models import Exercise

class Command(BaseCommand):
    help = 'Import Persian translations for Exercise model from a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file with Persian translations')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        updated = 0
        not_found = []
        with open(csv_file, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.stdout.write(self.style.NOTICE(f"CSV fieldnames: {reader.fieldnames}"))
            first_row = next(reader)
            self.stdout.write(self.style.NOTICE(f"First row keys: {list(first_row.keys())}"))
            self.stdout.write(self.style.NOTICE(f"First row values: {list(first_row.values())}"))
            f.seek(0)
            reader = csv.DictReader(f)
            db_exercises = {e.name.strip().lower(): e for e in Exercise.objects.all()}
            for row in reader:
                english_name = row.get('\ufeffname', '').strip()
                persian_name = row.get('name_in_persian', '').strip()
                persian_instructions = row.get('instructions_in_persian', '').strip()
                if not english_name:
                    continue
                normalized_name = english_name.strip().lower()
                exercise = db_exercises.get(normalized_name)
                if exercise:
                    exercise.name_in_persian = persian_name
                    exercise.instructions_in_persian = persian_instructions
                    exercise.save()
                    updated += 1
                else:
                    not_found.append(english_name)
                    self.stdout.write(self.style.WARNING(f"Exercise with name '{english_name}' does not exist."))
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} exercises with Persian translations."))
        if not_found:
            self.stdout.write(self.style.WARNING(f"Names not found: {not_found}"))
        # Print all Exercise names in DB for debugging
        all_names = list(Exercise.objects.values_list('name', flat=True))
        self.stdout.write(self.style.NOTICE(f"All Exercise names in DB: {all_names}"))
