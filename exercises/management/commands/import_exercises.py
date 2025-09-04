import json
import os
from django.core.management.base import BaseCommand
from exercises.models import Exercise, ExerciseImage
from django.core.files import File

class Command(BaseCommand):
    help = 'Import exercises from folder structure'

    def add_arguments(self, parser):
        parser.add_argument('root_dir', type=str, help='Path to the root exercises folder')

    def handle(self, *args, **kwargs):
        root_dir = kwargs['root_dir']

        for folder_name in os.listdir(root_dir):
            folder_path = os.path.join(root_dir, folder_name)
            if not os.path.isdir(folder_path):
                continue

            json_path = os.path.join(folder_path, 'exercise.json')
            img_folder = os.path.join(folder_path, 'images')

            if not os.path.exists(json_path):
                self.stdout.write(self.style.WARNING(f'Skipped {folder_name}, no exercise.json'))
                continue

            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            exercise, created = Exercise.objects.get_or_create(
                name=data.get('name'),
                defaults={
                    'aliases': data.get('aliases', []),
                    'primary_muscles': data.get('primaryMuscles', []),
                    'secondary_muscles': data.get('secondaryMuscles', []),
                    'force': data.get('force'),
                    'name_in_persian': data.get('name_in_persian'),
                    'level': data.get('level'),
                    'mechanic': data.get('mechanic'),
                    'equipment': data.get('equipment'),
                    'category': data.get('category'),
                    'instructions': data.get('instructions', []),
                    'instructions_in_persian': data.get('instructions_in_persian', []),
                    'description': data.get('description', ''),
                    'tips': data.get('tips', []),
                }
            )
            if not created:
                # Update fields for existing exercise
                exercise.primary_muscles = data.get('primaryMuscles', [])
                exercise.secondary_muscles = data.get('secondaryMuscles', [])
                exercise.force = data.get('force')
                exercise.name_in_persian = data.get('name_in_persian')
                exercise.level = data.get('level')
                exercise.mechanic = data.get('mechanic')
                exercise.equipment = data.get('equipment')
                exercise.category = data.get('category')
                exercise.instructions = data.get('instructions', [])
                exercise.instructions_in_persian = data.get('instructions_in_persian', [])
                exercise.description = data.get('description', '')
                exercise.tips = data.get('tips', [])
                exercise.save()

            if os.path.exists(img_folder):
                for image_name in os.listdir(img_folder):
                    image_path = os.path.join(img_folder, image_name)
                    if image_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                        with open(image_path, 'rb') as img_file:
                            ExerciseImage.objects.create(
                                exercise=exercise,
                                image=File(img_file, name=image_name)
                            )

            self.stdout.write(self.style.SUCCESS(f'✅ Imported: {data.get("name")}'))
