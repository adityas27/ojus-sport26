import csv
from django.core.management.base import BaseCommand
from sports.models import Registration, Sport

class Command(BaseCommand):
    help = 'Export sport registrations to CSV'

    def handle(self, *args, **options):
        sports = Sport.objects.all()
        
        for sport in sports:
            regs = Registration.objects.filter(sport=sport).select_related('student')
            
            if regs.exists():
                filename = f"{sport.slug}.csv"
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Full Name', 'Moodle ID', 'Branch', 'Year', 'Remarks'])
                    
                    for reg in regs:
                        s = reg.student
                        name = f"{s.first_name} {s.last_name}".strip() or s.username
                        writer.writerow([name, s.moodleID, reg.branch, reg.year, ""])
                
                self.stdout.write(self.style.SUCCESS(f'Created {filename}'))