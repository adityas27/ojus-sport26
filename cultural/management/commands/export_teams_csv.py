import csv
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from cultural.models import Team, Event, TEAM_EVENTS

User = get_user_model()


class Command(BaseCommand):
    help = 'Export cultural event teams to separate CSVs by event with leader and member details'

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
            help='Export only specific event (e.g., valorant, paintball). If not provided, exports all team events.'
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
                events = Event.objects.filter(slug=event_filter, teams__isnull=False).distinct()
            else:
                # Get all events that have teams
                events = Event.objects.filter(slug__in=TEAM_EVENTS).distinct()
            
            total_teams = 0
            
            for event in events:
                teams = Team.objects.filter(event=event).prefetch_related('members')
                
                if not teams.exists():
                    self.stdout.write(
                        self.style.WARNING(f'⚠ No teams found for event: {event.name}')
                    )
                    continue
                
                # Create CSV file for this event
                output_file = os.path.join(output_dir, f'{event.slug}.csv')
                
                with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['team_name', 'leader_name', 'leader_phone', 'member_name', 'member_phone', 'event']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    
                    for team in teams:
                        leader_name = team.leader.get_full_name() or team.leader.username
                        leader_phone = team.leader.phone_number or ''
                        
                        # If team has members, write one row per member
                        members = team.members.all()
                        if members.exists():
                            for member in members:
                                member_name = member.get_full_name() or member.username
                                member_phone = member.phone_number or ''
                                
                                writer.writerow({
                                    'team_name': team.name,
                                    'leader_name': leader_name,
                                    'leader_phone': leader_phone,
                                    'member_name': member_name,
                                    'member_phone': member_phone,
                                    'event': event.name,
                                })
                        else:
                            # If no members, write leader only
                            writer.writerow({
                                'team_name': team.name,
                                'leader_name': leader_name,
                                'leader_phone': leader_phone,
                                'member_name': '',
                                'member_phone': '',
                                'event': event.name,
                            })
                    
                    total_teams += teams.count()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Exported {teams.count()} teams for {event.name} to {output_file}'
                    )
                )
            
            if total_teams > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✓ Successfully exported {total_teams} total teams to {output_dir}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING('⚠ No teams found to export')
                )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error exporting teams: {str(e)}')
            )
