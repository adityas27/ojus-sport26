from django.core.management.base import BaseCommand
from sports.models import Registration

class Command(BaseCommand):
    help = 'Updates Registration branch/year from Student records'

    def handle(self, *args, **options):
        regs = Registration.objects.select_related('student').all()
        count = 0
        for reg in regs:
            reg.branch = reg.student.branch
            reg.year = reg.student.year
            reg.save()
            count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} records'))