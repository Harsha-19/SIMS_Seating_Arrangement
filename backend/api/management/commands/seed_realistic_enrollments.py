import random

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Enrollment, Program, Student, derive_sem_type


PROGRAM_DISTRIBUTION = {
    'BCA': {1: 180, 2: 140, 3: 120, 4: 95, 5: 70, 6: 55},
    'BSC': {1: 210, 2: 160, 3: 135, 4: 110, 5: 80, 6: 60},
    'BCOM': {1: 260, 2: 220, 3: 175, 4: 140, 5: 105, 6: 85},
    'BA': {1: 150, 2: 120, 3: 100, 4: 90, 5: 65, 6: 50},
}

SECTIONS = ['A', 'B', 'C']
FIRST_NAMES = ['Aarav', 'Ishita', 'Vihaan', 'Diya', 'Reyansh', 'Anika', 'Kabir', 'Meera', 'Arjun', 'Myra']
LAST_NAMES = ['Sharma', 'Patel', 'Reddy', 'Gupta', 'Nair', 'Iyer', 'Singh', 'Das', 'Jain', 'Khan']


class Command(BaseCommand):
    help = "Seed realistic, intentionally uneven enrollment data for testing."

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Delete existing students and enrollments first.')
        parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducible data generation.')

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(options['seed'])

        if options['clear']:
            Enrollment.objects.all().delete()
            Student.objects.all().delete()

        program_cache = {}
        created_students = 0
        created_enrollments = 0

        for program_name, semesters in PROGRAM_DISTRIBUTION.items():
            program_cache[program_name], _ = Program.objects.get_or_create(name=program_name)

        for program_name, semesters in PROGRAM_DISTRIBUTION.items():
            program = program_cache[program_name]
            for semester, target_count in semesters.items():
                for idx in range(target_count):
                    reg_no = f"{program_name}{semester:01d}{idx + 1:04d}"
                    student, student_created = Student.objects.get_or_create(
                        reg_no=reg_no,
                        defaults={
                            'name': f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}".upper(),
                        },
                    )
                    if student_created:
                        created_students += 1
                    _, enrollment_created = Enrollment.objects.get_or_create(
                        student=student,
                        program=program,
                        semester=semester,
                        defaults={
                            'section': random.choices(SECTIONS, weights=[0.5, 0.35, 0.15])[0],
                            'sem_type': derive_sem_type(semester),
                        },
                    )
                    if enrollment_created:
                        created_enrollments += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {created_students} students and {created_enrollments} enrollments with uneven semester distribution."
            )
        )
