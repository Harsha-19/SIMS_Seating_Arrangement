import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from api.models import Department, Semester

# Create superuser
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("Superuser created: admin / admin123")

depts_data = [
    'BCA', 'BBA', 'BCOM', 'BSC FORENSIC', 'BA'
]

sems_data = [
    '1st Sem', '2nd Sem', '3rd Sem', '4th Sem', '5th Sem', '6th Sem'
]

for name in depts_data:
    dept, created = Department.objects.get_or_create(name=name)
    if created:
        print(f"Created Department: {name}")
    for sem_name in sems_data:
        _, s_created = Semester.objects.get_or_create(name=sem_name, department=dept)
        if s_created:
            print(f"  Created Semester: {sem_name} for {name}")

print("Pre-population complete.")
