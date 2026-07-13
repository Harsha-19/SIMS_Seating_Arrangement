from django.db import migrations, models


def normalize_existing_enrollments(apps, schema_editor):
    Enrollment = apps.get_model('api', 'Enrollment')

    odd_semesters = {1, 3, 5}
    even_semesters = {2, 4, 6}
    invalid_ids = []

    for enrollment in Enrollment.objects.all().only('id', 'semester', 'sem_type'):
        if enrollment.semester in odd_semesters:
            expected = 'ODD'
        elif enrollment.semester in even_semesters:
            expected = 'EVEN'
        else:
            invalid_ids.append(enrollment.id)
            continue

        if enrollment.sem_type != expected:
            enrollment.sem_type = expected
            enrollment.save(update_fields=['sem_type'])

    if invalid_ids:
        raise ValueError(
            f"Invalid enrollment semester values found for IDs: {invalid_ids}. "
            "Semester must be between 1 and 6 before applying constraints."
        )


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_enrollment_program_alter_semester_unique_together_and_more'),
    ]

    operations = [
        migrations.RunPython(normalize_existing_enrollments, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='enrollment',
            constraint=models.CheckConstraint(
                check=models.Q(semester__in=(1, 2, 3, 4, 5, 6)),
                name='enrollment_semester_range_valid',
            ),
        ),
        migrations.AddConstraint(
            model_name='enrollment',
            constraint=models.CheckConstraint(
                check=(
                    (models.Q(semester__in=(1, 3, 5)) & models.Q(sem_type='ODD')) |
                    (models.Q(semester__in=(2, 4, 6)) & models.Q(sem_type='EVEN'))
                ),
                name='enrollment_semester_sem_type_match',
            ),
        ),
    ]
