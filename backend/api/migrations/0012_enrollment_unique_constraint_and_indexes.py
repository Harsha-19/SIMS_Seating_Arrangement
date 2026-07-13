from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_enrollment_semester_constraints'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='enrollment',
            index=models.Index(fields=['program', 'semester'], name='api_enrollm_program_d5793e_idx'),
        ),
        migrations.AddIndex(
            model_name='enrollment',
            index=models.Index(fields=['program', 'semester', 'section'], name='api_enrollm_program_2ed346_idx'),
        ),
    ]
