from django.core.management.base import BaseCommand
from api.models import Exam, Room, Student, Program, Enrollment, ExamGroup
from django.utils import timezone

class Command(BaseCommand):
    help = 'Seeds test data for seating generation'

    def handle(self, *args, **kwargs):
        # 1. Ensure a Program exists (case-insensitive lookup)
        program = Program.objects.filter(name__iexact='Computer Science').first()
        if not program:
            program = Program.objects.create(name='COMPUTER SCIENCE')
        
        # 2. Ensure a Room exists
        room, _ = Room.objects.get_or_create(
            room_number='101',
            defaults={
                'total_capacity': 30,
                'rows': 5,
                'column_layout': [3, 3]
            }
        )
        
        # 3. Ensure an Exam exists (force ID 1 if possible, or just ensure one exists)
        exam, created = Exam.objects.get_or_create(
            id=1,
            defaults={
                'subject': 'Data Structures',
                'date': timezone.now().date(),
                'exam_type': 'CORE',
                'semester': 1,
                'program': program
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Exam 1: {exam.subject}'))
        
        # 4. Ensure an ExamGroup exists for this exam
        ExamGroup.objects.get_or_create(
            exam=exam,
            program=program,
            semester=1,
            subject='Data Structures'
        )

        # 5. Ensure some Students exist for this specific program/semester
        test_students_count = Enrollment.objects.filter(program=program, semester=1).count()
        if test_students_count < 10:
            for i in range(1, 11 - test_students_count):
                reg_no = f'TEST{timezone.now().strftime("%y%m%d")}{i:03d}'
                student, _ = Student.objects.get_or_create(
                    reg_no=reg_no,
                    defaults={'name': f'Test Student {i}'}
                )
                Enrollment.objects.get_or_create(
                    student=student,
                    program=program,
                    semester=1
                )
            self.stdout.write(self.style.SUCCESS(f'Created {10 - test_students_count} new test students for {program.name}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Found {test_students_count} students already enrolled in {program.name} Sem 1'))

        self.stdout.write(self.style.SUCCESS(f'Test data ready. Exam ID: {exam.id}, Room ID: {room.id}'))
