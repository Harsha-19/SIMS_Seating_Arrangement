from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from api.models import Enrollment


class Command(BaseCommand):
    help = "Remove duplicate enrollments while keeping the latest or oldest record in each duplicate group."

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep',
            choices=['latest', 'oldest'],
            default='latest',
            help='Which duplicate record to keep inside each (student, program, semester) group.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview duplicate groups without deleting rows.',
        )

    def handle(self, *args, **options):
        keep_latest = options['keep'] == 'latest'
        dry_run = options['dry_run']

        duplicate_groups = (
            Enrollment.objects.values('student_id', 'program_id', 'semester')
            .annotate(row_count=Count('id'))
            .filter(row_count__gt=1)
        )

        deleted_ids = []
        for group in duplicate_groups:
            rows = list(
                Enrollment.objects.filter(
                    student_id=group['student_id'],
                    program_id=group['program_id'],
                    semester=group['semester'],
                ).order_by(
                    '-created_at' if keep_latest else 'created_at',
                    '-id' if keep_latest else 'id',
                )
            )
            delete_candidates = rows[1:]
            deleted_ids.extend(row.id for row in delete_candidates)

        if dry_run:
            self.stdout.write(
                f"Would delete {len(deleted_ids)} duplicate rows across {duplicate_groups.count()} groups."
            )
            return

        with transaction.atomic():
            deleted_count, _ = Enrollment.objects.filter(id__in=deleted_ids).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted_count} duplicate Enrollment rows. Kept {'latest' if keep_latest else 'oldest'} entries."
            )
        )
