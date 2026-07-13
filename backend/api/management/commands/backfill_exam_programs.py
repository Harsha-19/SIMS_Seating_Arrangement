from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.models import Exam, Program


class Command(BaseCommand):
    help = "Assigns a default Program to Exam rows where program is NULL."

    def add_arguments(self, parser):
        parser.add_argument(
            '--program-id',
            type=int,
            help='Optional Program ID to assign to exams with a null program.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        program_id = options.get('program_id')
        default_program = None

        if program_id is not None:
            default_program = Program.objects.filter(id=program_id).first()
            if not default_program:
                raise CommandError(f'Program with id={program_id} does not exist.')
        else:
            default_program = Program.objects.order_by('id').first()
            if not default_program:
                default_program, _ = Program.objects.get_or_create(name='UNASSIGNED')

        updated = Exam.objects.filter(program__isnull=True).update(program=default_program)
        self.stdout.write(
            self.style.SUCCESS(
                f'Assigned program {default_program.id} ({default_program.name}) to {updated} exam(s).'
            )
        )
