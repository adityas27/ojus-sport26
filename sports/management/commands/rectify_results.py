from django.core.management.base import BaseCommand
from django.db import transaction
from sports.models import Results

class Command(BaseCommand):
    help = 'Updates branch in Results based on player or team'

    def handle(self, *args, **options):
        results = Results.objects.select_related('player', 'team').all()
        updated_count = 0

        with transaction.atomic():
            for res in results:
                if res.player:
                    res.branch = res.player.branch
                elif res.team:
                    res.branch = res.team.branch
                
                res.save()
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} result records'))