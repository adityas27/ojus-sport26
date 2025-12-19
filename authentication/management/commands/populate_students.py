# management/commands/populate_students.py
import os
import pandas as pd
from django.core.management.base import BaseCommand
from authentication.models import Student

class Command(BaseCommand):
    help = 'Populate Student model with data from CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **options):
        csv_file = options['csv_file']

        # Expand user and resolve absolute path so callers can pass relative or absolute paths
        csv_path = os.path.abspath(os.path.expanduser(csv_file))

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'CSV file not found: {csv_path}'))
            self.stdout.write(self.style.ERROR('Provide the correct path or place the file in the backend directory.'))
            self.stdout.write(self.style.ERROR('Example:'))
            self.stdout.write(self.style.ERROR(r"py manage.py populate_students C:\\path\\to\\students.csv"))
            return

        try:
            df = pd.read_csv(csv_path)
            students_created = 0
            
            for index, row in df.iterrows():
                try:
                    moodle_id = int(row['Student ID'])
                    
                    # Skip if student exists
                    if Student.objects.filter(moodleID=moodle_id).exists():
                        self.stdout.write(
                            self.style.WARNING(f'Student {moodle_id} already exists')
                        )
                        continue
                    last_name = row['Last Name'].strip()
                    # Create student
                    student = Student(
                        moodleID=moodle_id,
                        first_name=row['First Name'].strip(),
                        last_name=row['Last Name'].strip(),
                        email=f"{moodle_id}@apsit.edu.in",
                        year=self.get_year_code(row['Class']),
                        branch=self.get_branch_code(row['Department']),
                        phone_number='',
                        is_active=True
                    )
                    
                    student.set_password(f'{moodle_id}_{last_name}@Apsit')
                    student.save()
                    students_created += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Created student {moodle_id}')
                    )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error with row {index}: {str(e)}')
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {students_created} students')
            )
            
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR('CSV file not found')
            )

    def get_branch_code(self, department):
        mapping = {
            'CIVIL': 'CIVIL',
            'COMPS': 'COMPS',
            'IT': 'IT', 
            'AIML': 'AIML',
            'DS': 'DS',
            'MECH': 'MECH'
        }
        return mapping.get(department.upper(), 'COMPS')
    
    def get_year_code(self, year):
        mapping = {
                'FE-REG': 'FE',
                'SE-REG': 'SE',
                'TE-REG': 'TE', 
                'BE-REG': 'BE'
            }
        return mapping.get(year.upper(), 'FE')