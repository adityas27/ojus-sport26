import json
from django.core.management.base import BaseCommand
from sports.models import Sport

class Command(BaseCommand):
    help = 'Populate Sports data from JSON file'

    def handle(self, *args, **kwargs):
        # Load JSON data
        json_file_path = 'sports_data_final_with_contacts.json'

        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Day mapping
        day_mapping = {
            "day1": 1,  # 26-12-2025
            "day2": 2,  # 27-12-2025
            "day3": 3,  # 29-12-2025
            "day4": 4,  # 30-12-2025
            "day5": 5   # 31-12-2025
        }

        sports_created = 0
        sports_updated = 0

        # Process indoor and outdoor sports
        for category in ["indoor", "outdoor"]:
            for day_key, sports_list in data[category].items():
                day_number = day_mapping[day_key]

                for sport_data in sports_list:
                    # Check if sport already exists
                    sport, created = Sport.objects.update_or_create(
                        slug=sport_data['slug'],
                        defaults={
                            'name': sport_data['name'],
                            'description': sport_data['description'],
                            'isTeamBased': sport_data['isTeamBased'],
                            'venue': sport_data.get('venue', ''),
                            'is_finalized': sport_data.get('is_finalized', False),
                            'teamSize': sport_data.get('teamLimit', 0),
                            'day': day_number,
                            'time': sport_data.get('time', ''),
                            'img': sport_data.get('img_url', '')
                        }
                    )

                    if created:
                        sports_created += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'Created: {sport.name}')
                        )
                    else:
                        sports_updated += 1
                        self.stdout.write(
                            self.style.WARNING(f'Updated: {sport.name}')
                        )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Created: {sports_created}, Updated: {sports_updated}'
            )
        )