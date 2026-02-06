import csv
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from cultural.models import Registration, Event

User = get_user_model()


class Command(BaseCommand):
    help = 'Export cultural event registrations to separate CSVs by event with participant details'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='.',
            help='Output directory for CSV files (default: current directory)'
        )
        parser.add_argument(
            '--event',
            type=str,
            help='Export only specific event (e.g., web-design, photography). If not provided, exports all events with registrations.'
        )

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        event_filter = options.get('event')
        
        # Ensure output directory exists
        if output_dir != '.' and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        try:
            # Determine which events to export
            if event_filter:
                events = Event.objects.filter(slug=event_filter, registration__isnull=False).distinct()
            else:
                # Get all events that have registrations
                events = Event.objects.filter(registration__isnull=False).distinct()
            
            total_registrations = 0
            
            for event in events:
                registrations = Registration.objects.filter(event=event).select_related('student')
                
                if not registrations.exists():
                    self.stdout.write(
                        self.style.WARNING(f'⚠ No registrations found for event: {event.name}')
                    )
                    continue
                
                # Create CSV file for this event (using event slug for filename)
                output_file = os.path.join(output_dir, f'{event.slug}.csv')
                
                with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['name', 'event', 'phone_number']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    
                    for reg in registrations:
                        writer.writerow({
                            'name': reg.student.get_full_name() or reg.student.username,
                            'event': event.name,
                            'phone_number': reg.student.phone_number or '',
                        })
                    
                    total_registrations += registrations.count()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Exported {registrations.count()} registrations for {event.name} to {output_file}'
                    )
                )
            
            if total_registrations > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✓ Successfully exported {total_registrations} total registrations to {output_dir}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING('⚠ No registrations found to export')
                )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error exporting registrations: {str(e)}')
            )
