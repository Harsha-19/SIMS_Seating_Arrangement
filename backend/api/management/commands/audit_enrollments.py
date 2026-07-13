from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from api.models import Enrollment, ODD_SEMESTERS, EVEN_SEMESTERS


class Command(BaseCommand):
    help = "Audit enrollment integrity, semester balance, and duplicate patterns."

    def handle(self, *args, **options):
        duplicates = list(
            Enrollment.objects.values('student_id', 'program_id', 'semester')
            .annotate(row_count=Count('id'))
            .filter(row_count__gt=1)
            .order_by('-row_count', 'student_id', 'program_id', 'semester')
        )
        odd_students = Enrollment.objects.filter(
            semester__in=ODD_SEMESTERS
        ).values('student_id').distinct().count()
        even_students = Enrollment.objects.filter(
            semester__in=EVEN_SEMESTERS
        ).values('student_id').distinct().count()
        both_students = Enrollment.objects.values('student_id').annotate(
            odd_hits=Count('id', filter=Q(semester__in=ODD_SEMESTERS), distinct=True),
            even_hits=Count('id', filter=Q(semester__in=EVEN_SEMESTERS), distinct=True),
        ).filter(odd_hits__gt=0, even_hits__gt=0).count()
        semester_distribution = list(
            Enrollment.objects.values('semester')
            .annotate(
                enrollment_rows=Count('id'),
                distinct_students=Count('student_id', distinct=True),
            )
            .order_by('semester')
        )

        self.stdout.write(self.style.MIGRATE_HEADING("Enrollment Audit"))
        self.stdout.write(f"Duplicate enrollment groups: {len(duplicates)}")
        self.stdout.write(f"Distinct ODD students: {odd_students}")
        self.stdout.write(f"Distinct EVEN students: {even_students}")
        self.stdout.write(f"Students present in both ODD and EVEN: {both_students}")

        self.stdout.write(self.style.MIGRATE_HEADING("Semester Distribution"))
        for row in semester_distribution:
            self.stdout.write(
                f"Semester {row['semester']}: rows={row['enrollment_rows']} "
                f"distinct_students={row['distinct_students']}"
            )

        balanced = len({row['distinct_students'] for row in semester_distribution}) == 1 if semester_distribution else False
        if balanced:
            self.stdout.write(
                self.style.WARNING(
                    "All semesters have the same distinct-student count. "
                    "This looks artificially symmetric and should be reviewed."
                )
            )

        if duplicates:
            self.stdout.write(self.style.MIGRATE_HEADING("Top Duplicate Groups"))
            for row in duplicates[:20]:
                self.stdout.write(
                    f"student={row['student_id']} program={row['program_id']} "
                    f"semester={row['semester']} duplicates={row['row_count']}"
                )
